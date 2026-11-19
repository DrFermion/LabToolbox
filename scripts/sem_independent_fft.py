"""Independent radial-FFT period check for the updated 650 nm LIPSS SEM set.

Deliberately a second, simpler implementation (no tile maps, no ordering
metrics) so it can serve as an independent opinion on the six-method run.
"""
import glob
import json
import os
import re

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = "C:/Users/PC/AppData/Local/hermes/cache/scratch/sem650/png"
BAND = (380.0, 1200.0)


def sidecar_px(path):
    txt = open(path[:-4] + ".txt", "rb").read().decode("latin-1")
    m = re.search(r"SM_MICRON_BAR\s+(\d+)", txt)
    return 1000.0 / float(m.group(1)) if m else 31.25


def analyse(path):
    a = np.array(Image.open(path).convert("L"), float)
    a = a[100:-100, 100:-100]          # trim the instrument footer
    a = a - gaussian_filter(a, 20)     # high-pass, kills illumination gradient
    w = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    F = np.fft.fftshift(np.abs(np.fft.fft2(a * w)))
    h, wd = F.shape
    yy, xx = np.mgrid[0:h, 0:wd]
    ky = (yy - h // 2) / h
    kx = (xx - wd // 2) / wd
    k = np.hypot(ky, kx)
    ang = np.degrees(np.arctan2(ky, kx)) % 180
    px = sidecar_px(path)
    per = np.where(k > 1e-9, px / np.maximum(k, 1e-12), np.inf)
    mask = np.logical_and(per >= BAND[0], per <= BAND[1])
    if mask.sum() < 10:
        return None
    idx = np.argmax(np.where(mask, F, 0))
    kpk = float(k.ravel()[idx])
    theta = float(ang.ravel()[idx])
    ring = np.abs(k - kpk) < 0.15 * kpk
    sel = np.logical_and(ring, mask)
    if sel.sum() > 20:
        vals = F[sel]
        snr = float(vals.max() / np.median(vals))
        bins = np.arange(0, 181, 2)
        hh, _ = np.histogram(ang[sel], bins=bins, weights=vals)
        hh = hh - hh.min()
        if hh.max() > 0:
            smooth = np.convolve(hh, np.ones(3), "same") / 3
            half = smooth > 0.5 * smooth.max()
            dloa = float(0.5 * np.sum(half) * 2.0)
        else:
            dloa = float("nan")
    else:
        snr = float("nan")
        dloa = float("nan")
    return dict(period_nm=float(px / kpk), theta_deg=theta, snr=snr,
                dloa_deg=dloa, px_nm=px)


def main():
    rows = []
    for path in sorted(glob.glob(ROOT + "/*/*.png")):
        rec = analyse(path)
        if rec is None:
            continue
        rec["coupon"] = os.path.basename(os.path.dirname(path))
        rec["field"] = os.path.basename(path)[:-4]
        rows.append(rec)
    json.dump(rows, open("fft_independent.json", "w"), indent=1)

    arr = np.array([r["period_nm"] for r in rows])
    print(f"independent radial-FFT: n={len(rows)} | period {arr.mean():.1f} ± "
          f"{arr.std(ddof=1):.1f} nm (CV {100*arr.std(ddof=1)/arr.mean():.1f}%) | "
          f"range {arr.min():.0f}-{arr.max():.0f} nm")
    for coupon in sorted({r["coupon"] for r in rows}):
        sub = [r for r in rows if r["coupon"] == coupon]
        s = np.array([r["period_nm"] for r in sub])
        d = np.array([r["dloa_deg"] for r in sub])
        print(f"  {coupon}: n={len(s):2d} | {s.mean():6.1f} ± {s.std(ddof=1):5.1f} nm "
              f"(CV {100*s.std(ddof=1)/s.mean():4.1f}%) | DLOA median {np.nanmedian(d):4.1f} deg")
    snr = np.array([r["snr"] for r in rows if np.isfinite(r["snr"])])
    print(f"\nin-band peak / ring-median: median {np.median(snr):.2f} | "
          f"min {snr.min():.2f} | max {snr.max():.2f}")
    print("weakest 5:",
          [(r["coupon"] + "/" + r["field"], round(r["snr"], 2))
           for r in sorted(rows, key=lambda r: r["snr"])[:5]])


if __name__ == "__main__":
    main()
