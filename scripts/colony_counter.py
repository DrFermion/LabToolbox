#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
colony_counter.py -- count bacterial colonies on plate / filter photos.

Built for hand-held or phone photos of agar plates (colonies darker than the
medium). Polarity is decided automatically, so back-lit / transmitted-light
images (colonies brighter than the medium) work too, and can be forced with
--polarity.

Pipeline
  1. optional dish detection (Hough circle) -> crop rim, mask everything off-plate
  2. illumination flattening (large-kernel background division)
  3. adaptive threshold in BOTH polarities -> keep whichever yields colony-like objects
  4. distance-transform peak seeding + watershed -> splits touching colonies
  5. size / circularity / solidity filtering
  6. annotated PNG (each colony circled + numbered), binary mask PNG, CSV row

Usage
  python colony_counter.py IMG [IMG ...] --out OUTDIR
  python colony_counter.py "C:/photos/*.jpg" --out OUTDIR --min-area 40
  python colony_counter.py scan.png --out OUT --no-dish          # flatbed scan / crop
  python colony_counter.py IMG --out OUT --polarity light        # back-lit image
  python colony_counter.py --selftest                            # synthetic accuracy check

A count here is a DETECTION result -- eyeball the annotated PNG before reporting.
Touching colonies that the watershed could not separate stay merged; the
`flags` column says when that is likely (oversized objects).
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import sys
import time

import cv2
import numpy as np
from scipy import ndimage as ndi

MAX_DIM = 1600          # working resolution (px, longest side)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def read_image(path: str) -> np.ndarray:
    data = np.fromfile(path, dtype=np.uint8)          # non-ASCII paths
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"cannot read image: {path}")
    return img


def write_image(path: str, img: np.ndarray) -> None:
    ext = os.path.splitext(path)[1] or ".png"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise RuntimeError(f"cannot encode {path}")
    buf.tofile(path)


def detect_dish(gray: np.ndarray):
    """Return (cx, cy, r) of the plate if a plausible big circle is found."""
    small = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5)
    small = cv2.medianBlur(small, 7)
    circles = cv2.HoughCircles(
        small, cv2.HOUGH_GRADIENT, dp=1.5, minDist=min(small.shape) * 0.6,
        param1=120, param2=60,
        minRadius=int(min(small.shape) * 0.30), maxRadius=int(min(small.shape) * 0.52),
    )
    if circles is None:
        return None
    c = max(circles[0], key=lambda c: c[2])
    return float(c[0] * 2), float(c[1] * 2), float(c[2] * 2)


def flatten_illumination(gray: np.ndarray) -> np.ndarray:
    """Divide out low-frequency illumination (vignetting, lamp hotspot)."""
    k = int(max(15, (min(gray.shape) // 8) | 1))
    bg = cv2.medianBlur(gray, min(k, 99))
    bg = bg.astype(np.float32) + 1.0
    flat = gray.astype(np.float32) / bg * float(np.median(bg))
    return np.clip(flat, 0, 255).astype(np.uint8)


def _split_labels(binary: np.ndarray, min_area: int) -> np.ndarray:
    """Split touching colonies. Returns an int32 label image (0 = background).

    Distance-transform peaks act as per-colony seeds; every foreground pixel is
    assigned to its nearest seed. Blobs that produce no peak get their own
    deepest-pixel seed so they are never stolen by a neighbour.
    """
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    if dist.max() <= 1:
        return np.zeros(binary.shape, np.int32)

    blobs, nb = ndi.label(binary)
    if nb == 0:
        return np.zeros(binary.shape, np.int32)

    areas = np.array(ndi.sum(binary > 0, blobs, range(1, nb + 1)), dtype=float)
    good = areas[areas >= min_area * 1.5]
    r_med = float(np.sqrt(np.median(good) / np.pi)) if good.size else float(np.sqrt(min_area / np.pi))

    fp = max(3, int(round(1.1 * r_med)))
    peaks = (dist == ndi.maximum_filter(dist, size=fp)) & (dist > max(1.0, 0.30 * r_med))
    npeaks_per_blob = np.array(ndi.sum(peaks, blobs, range(1, nb + 1)))

    # blobs with no peak: seed their deepest pixel
    for bidx in np.nonzero(npeaks_per_blob == 0)[0] + 1:
        ys, xs = np.nonzero(blobs == bidx)
        if ys.size == 0:
            continue
        j = int(np.argmax(dist[ys, xs]))
        peaks[ys[j], xs[j]] = True

    seeds, nseed = ndi.label(peaks, structure=np.ones((3, 3)))
    if nseed == 0:
        return np.zeros(binary.shape, np.int32)

    _, (iy, ix) = ndi.distance_transform_edt(seeds == 0, return_indices=True)
    labels = np.where(binary > 0, seeds[iy, ix], 0).astype(np.int32)
    return labels


def candidates(binary: np.ndarray, mask: np.ndarray, args):
    """Colony-like segments -> (list of (x, y, area, circ, solidity), label image)."""
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    b = cv2.morphologyEx(binary, cv2.MORPH_OPEN, k, iterations=1)
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, k, iterations=1)
    b[mask == 0] = 0

    labels = _split_labels(b, args.min_area)

    ids = [i for i in np.unique(labels) if i > 0]
    keep = []
    for i in ids:
        sel = labels == i
        area = int(np.count_nonzero(sel))
        if area < args.min_area or area > args.max_area:
            continue
        ys, xs = np.nonzero(sel)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        if (x1 - x0) > 0.5 * mask.shape[1] or (y1 - y0) > 0.5 * mask.shape[0]:
            continue                                     # whole-plate / background blob
        sub = sel[y0:y1, x0:x1].astype(np.uint8)
        cont = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        if not cont:
            continue
        c = max(cont, key=cv2.contourArea)
        per = cv2.arcLength(c, True)
        circ = 4 * np.pi * area / (per * per) if per > 0 else 0.0
        solidity = area / max(cv2.contourArea(cv2.convexHull(c)), 1e-6)
        if circ < args.min_circularity or solidity < args.min_solidity:
            continue
        keep.append((float(xs.mean()), float(ys.mean()), area, circ, solidity))
    binary_out = np.where(labels > 0, 255, 0).astype(np.uint8)
    return keep, binary_out


def analyse(path: str, args) -> dict:
    t0 = time.time()
    img = read_image(path)
    h0, w0 = img.shape[:2]
    scale = 1.0
    if max(h0, w0) > MAX_DIM:
        scale = MAX_DIM / max(h0, w0)
        img = cv2.resize(img, (int(w0 * scale), int(h0 * scale)), interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape

    # ---- plate mask -------------------------------------------------------
    mask = np.full(gray.shape, 255, np.uint8)
    dish = None
    if not args.no_dish:
        dish = detect_dish(gray)
        if dish is not None:
            cx, cy, r = dish
            r_in = r * (1.0 - args.rim_margin)
            mask[:] = 0
            cv2.circle(mask, (int(cx), int(cy)), int(r_in), 255, -1)

    work = flatten_illumination(gray)
    blurred = cv2.GaussianBlur(work, (5, 5), 0)

    block = int(max(31, (int(min(H, W) / args.block_div)) | 1))
    dark = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY_INV, block, args.C)
    light = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY, block, -args.C)
    dark[mask == 0] = 0
    light[mask == 0] = 0

    if args.polarity == "auto":
        # colonies are the compact minority population: take whichever polarity
        # yields more colony-like objects (dark wins ties)
        cand_dark, bin_dark = candidates(dark, mask, args)
        cand_light, bin_light = candidates(light, mask, args)
        if len(cand_dark) >= max(3, 0.5 * len(cand_light)):
            polarity, keep, binary = "dark", cand_dark, bin_dark
        else:
            polarity, keep, binary = "light", cand_light, bin_light
    elif args.polarity == "dark":
        polarity = "dark"
        keep, binary = candidates(dark, mask, args)
    else:
        polarity = "light"
        keep, binary = candidates(light, mask, args)

    count = len(keep)
    plate_area_px = float(np.count_nonzero(mask))
    areas = np.array([k[2] for k in keep], float) if keep else np.array([0.0])
    big = int(np.count_nonzero(areas > 4 * np.median(areas))) if count else 0

    flags = []
    if count == 0:
        flags.append("no-colony-detected")
    if big:
        flags.append(f"{big}-oversized(may-be-merged)")
    if count > 400:
        flags.append(">400-count-unreliable")
    if dish is None:
        flags.append("no-dish-found")

    # ---- annotation -------------------------------------------------------
    ann = img.copy()
    if dish is not None:
        cv2.circle(ann, (int(dish[0]), int(dish[1])),
                   int(dish[2] * (1 - args.rim_margin)), (0, 200, 255), 2)
    for idx, (x, y, a, ci, so) in enumerate(sorted(keep, key=lambda t: (t[1], t[0])), 1):
        r = max(6, int(round(np.sqrt(a / np.pi) * 1.7)))
        cv2.circle(ann, (int(x), int(y)), r, (0, 0, 255), 2)
        cv2.putText(ann, str(idx), (int(x) + r + 1, int(y) - r),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 255), 1, cv2.LINE_AA)

    banner = f"n = {count}  polarity={polarity}  scale={scale:.2f}  " \
             f"{'; '.join(flags) if flags else 'ok'}"
    cv2.rectangle(ann, (0, 0), (W, 26), (0, 0, 0), -1)
    cv2.putText(ann, banner, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    base = os.path.splitext(os.path.basename(path))[0]
    os.makedirs(args.out, exist_ok=True)
    ann_path = os.path.join(args.out, f"{base}_annotated.png")
    bin_path = os.path.join(args.out, f"{base}_mask.png")
    write_image(ann_path, ann)
    write_image(bin_path, binary)

    return dict(
        image=os.path.basename(path), path=os.path.abspath(path), count=count,
        plate_area_px=int(plate_area_px),
        mean_colony_px=round(float(np.median(areas)), 1) if count else 0,
        polarity=polarity, dish="yes" if dish is not None else "no",
        dish_radius_px=int(dish[2]) if dish is not None else 0,
        flags=";".join(flags) or "ok", annotated=ann_path, mask_png=bin_path,
        seconds=round(time.time() - t0, 2),
    )


# --------------------------------------------------------------------------- #
# self test: synthetic plate with a known number of colonies
# --------------------------------------------------------------------------- #
def selftest(args) -> int:
    """Synthetic plate with a known colony count, incl. 20 touching pairs."""
    rng = np.random.default_rng(7)
    S = 1200
    img = np.full((S, S, 3), 25, np.uint8)
    cv2.circle(img, (S // 2, S // 2), 540, (198, 200, 202), -1)     # agar
    pts = []
    for _ in range(180):
        while True:
            x, y = (int(v) for v in rng.integers(120, S - 120, 2))
            if (x - S / 2) ** 2 + (y - S / 2) ** 2 < 460 ** 2:
                break
        r = int(rng.integers(6, 12))
        if all(np.hypot(x - px, y - py) > r + pr + 3 for px, py, pr in pts):
            pts.append((x, y, r))
            cv2.circle(img, (x, y), r, (92, 94, 96), -1)
    for _ in range(20):                                             # touching pairs
        x, y = (int(v) for v in rng.integers(160, S - 160, 2))
        cv2.circle(img, (x, y), 8, (92, 94, 96), -1)
        cv2.circle(img, (x + 13, y), 9, (92, 94, 96), -1)
        pts += [(x, y, 8), (x + 13, y, 9)]
    img = cv2.GaussianBlur(img, (3, 3), 0.8)
    os.makedirs(args.out, exist_ok=True)
    tmp = os.path.join(args.out, "_selftest_plate.png")
    write_image(tmp, img)
    res = analyse(tmp, args)
    truth = len(pts)
    err = (res["count"] - truth) / truth * 100
    print(f"SELFTEST truth={truth} (incl. 20 merged pairs) detected={res['count']} "
          f"error={err:+.1f}% polarity={res['polarity']} flags={res['flags']}")
    print(f"  annotated -> {res['annotated']}")
    ok = abs(err) <= 5
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Count colonies on plate photos.")
    p.add_argument("images", nargs="*", help="image files or glob patterns")
    p.add_argument("--out", default="colony_out", help="output directory")
    p.add_argument("--min-area", type=int, default=25, help="min colony area in px (working res)")
    p.add_argument("--max-area", type=int, default=30000, help="max colony area in px")
    p.add_argument("--min-circularity", type=float, default=0.55)
    p.add_argument("--min-solidity", type=float, default=0.80)
    p.add_argument("--C", type=float, default=7.0, help="adaptive-threshold offset (higher = stricter)")
    p.add_argument("--block-div", type=float, default=24.0, help="adaptive block = min(H,W)/this")
    p.add_argument("--rim-margin", type=float, default=0.06, help="fraction of dish radius cropped as rim")
    p.add_argument("--polarity", choices=["auto", "dark", "light"], default="auto")
    p.add_argument("--no-dish", action="store_true", help="skip dish detection (flatbed scan / crop)")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args(argv)

    if args.selftest:
        return selftest(args)

    paths = []
    for pat in args.images:
        hit = glob.glob(pat)
        paths.extend(hit if hit else [pat])
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        p.error("no input images found")

    os.makedirs(args.out, exist_ok=True)
    rows = []
    for i, path in enumerate(paths, 1):
        try:
            r = analyse(path, args)
        except Exception as exc:                                  # noqa: BLE001
            print(f"[{i}/{len(paths)}] FAIL {os.path.basename(path)}: {exc}")
            rows.append(dict(image=os.path.basename(path), path=os.path.abspath(path),
                             count="", flags=f"error:{exc}"))
            continue
        rows.append(r)
        print(f"[{i}/{len(paths)}] {r['image']}: n={r['count']} "
              f"polarity={r['polarity']} dish={r['dish']} flags={r['flags']} "
              f"({r['seconds']}s)")

    cols = ["image", "path", "count", "plate_area_px", "mean_colony_px",
            "polarity", "dish", "dish_radius_px", "flags", "annotated", "mask_png", "seconds"]
    csv_path = os.path.join(args.out, "colony_counts.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    print(f"\nCSV -> {csv_path}")
    total = sum(r["count"] for r in rows if isinstance(r.get("count"), int))
    print(f"TOTAL colonies = {total} over {len(paths)} image(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
