# -*- coding: utf-8 -*-
"""sem_quality_crosscheck.py — is "ordered area" reproducible by other estimators?

Our classifier (labtoolbox.semtexture) decides, for every 2 µm window, whether the
ripple texture passes the acceptance band.  This script implements **three independent
quality estimators** on the same windows, none of them reusing the classifier:

  Q1  orientation-only   -- tile structure tensor: coherence above a floor AND local
                            orientation within ±15° of the field axis.  No period, no
                            autocorrelation.
  Q2  spectral peak      -- tile FFT: prominence of the band-limited peak
                            (max/median − 1) ≥ 2, i.e. "a ripple period is resolvable".
  Q3  band-energy ratio  -- tile FFT: fraction of the power above 8 px that falls in the
                            annulus Λ_ref ± 20 % ≥ 0.30.
  Q4  Gabor energy       -- filtered energy of a Gabor kernel tuned to (Λ_ref, axis),
                            relative to the field median ≥ 0.5.

Every estimator returns the area fraction of the field it considers "good", so the four
numbers are directly comparable with our ordered fraction.

Usage
-----
    python scripts/sem_quality_crosscheck.py --folder "<650nm/LIPSS>" \\
        --perfield <crosscheck_perfield.csv> --outdir <dir>
"""
import os
import sys
import glob
import argparse

import numpy as np
import pandas as pd
from PIL import Image
from scipy.ndimage import gaussian_filter, gaussian_filter1d
from scipy.signal import fftconvolve

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from labtoolbox.semtexture import _crop_scalebar  # noqa: E402

TILE_UM = 2.0
C_FLOOR = 0.15
ANGLE_TOL = 15.0
PROM_MIN = 2.0
BAND_RATIO_MIN = 0.30
GABOR_REL_MIN = 0.50


# ----------------------------------------------------------------------- helpers
def load_gray(path):
    a = np.asarray(Image.open(path).convert("L"), dtype=float)
    return _crop_scalebar(a)


def structure_tensor(img, grad_sigma=1.0, tensor_sigma=4.0):
    amp = np.percentile(np.abs(img), 99) + 1e-9
    x = img / amp
    gx = gaussian_filter1d(x, grad_sigma, axis=1, order=1)
    gy = gaussian_filter1d(x, grad_sigma, axis=0, order=1)
    Jxx = gaussian_filter(gx * gx, tensor_sigma)
    Jyy = gaussian_filter(gy * gy, tensor_sigma)
    Jxy = gaussian_filter(gx * gy, tensor_sigma)
    coh = np.sqrt((Jxx - Jyy) ** 2 + 4 * Jxy ** 2) / (Jxx + Jyy + 1e-12)
    th = 0.5 * np.degrees(np.arctan2(2 * Jxy, Jxx - Jyy)) % 180.0
    return coh, th


def highpass(img, sigma_px=25.0):
    return img - gaussian_filter(img, sigma_px)


def tile_grid(h, w, tile):
    ys = list(range(0, h - tile + 1, tile))
    xs = list(range(0, w - tile + 1, tile))
    return [(y, x) for y in ys for x in xs]


def gabor_kernel(period_px, theta_deg, size=None, sigma=None):
    if size is None:
        size = int(max(9, round(4 * period_px)))
        size += (size + 1) % 2
    if sigma is None:
        sigma = period_px * 0.6
    y, x = np.mgrid[-size // 2 + 1:size // 2 + 1, -size // 2 + 1:size // 2 + 1].astype(float)
    t = np.deg2rad(theta_deg)
    xr = x * np.cos(t) + y * np.sin(t)
    env = np.exp(-(x ** 2 + y ** 2) / (2 * sigma ** 2))
    k = np.cos(2 * np.pi * xr / period_px) * env
    k -= k.mean()
    return k / (np.abs(k).sum() + 1e-12)


def analyse(path, period_nm, theta_deg, px_nm):
    img = load_gray(path)
    h, w = img.shape
    tile = int(round(TILE_UM * 1000.0 / px_nm))
    if tile < 16 or tile > min(h, w):
        return None
    hp = highpass(img)
    img_med = np.median(img)

    # Q1: orientation field at tile scale is taken from the structure tensor of the field,
    # then averaged inside each tile (independent of the period machinery)
    coh, th = structure_tensor(hp)

    lam_px = period_nm / px_nm
    band_lo, band_hi = lam_px * 0.8, lam_px * 1.2          # period window for Q2/Q3
    kmin = 1.0 / band_hi
    kmax = 1.0 / band_lo

    # Gabor tuned to the field period / axis
    ker = gabor_kernel(lam_px, theta_deg + 90.0)           # theta is the gradient; crests ⟂
    gab = np.abs(fftconvolve(hp, ker, mode="same"))

    win = np.outer(np.hanning(tile), np.hanning(tile))
    fy = np.fft.fftfreq(tile)[:, None]
    fx = np.fft.fftfreq(tile)[None, :]
    kk = np.hypot(fy, fx)
    dc = kk < 1.0 / max(h, w) * 2
    inband = (kk >= kmin) & (kk <= kmax)
    above8 = (kk >= 1.0 / 8.0) & ~dc

    q1 = q2 = q3 = q4 = 0
    n = 0
    gab_vals, prom_vals, ratio_vals = [], [], []
    rows, tile_rows = [], []
    for y, x in tile_grid(h, w, tile):
        blk = img[y:y + tile, x:x + tile]
        if blk.mean() < 0.45 * img_med:
            continue
        n += 1
        # Q1
        c_t = float(np.mean(coh[y:y + tile, x:x + tile]))
        th_t = float(np.degrees(np.angle(np.mean(np.exp(1j * 2 * np.radians(
            th[y:y + tile, x:x + tile])))) / 2)) % 180.0
        d_ang = abs(((th_t - theta_deg + 90.0) % 180.0) - 90.0)
        ok1 = (c_t >= C_FLOOR) and (d_ang <= ANGLE_TOL)
        # Q2 / Q3
        P = np.abs(np.fft.fft2(hp[y:y + tile, x:x + tile] * win)) ** 2
        pk = P[inband]
        prom = (pk.max() - np.median(pk)) / (np.median(pk) + 1e-12)
        tot = P[above8].sum() + 1e-12
        ratio = P[inband].sum() / tot
        ok2 = prom >= PROM_MIN
        ok3 = ratio >= BAND_RATIO_MIN
        # Q4
        e = float(np.sqrt(np.mean(gab[y:y + tile, x:x + tile] ** 2)))
        gab_vals.append(e)
        prom_vals.append(prom)
        ratio_vals.append(ratio)
        rows.append((y, x, ok1, ok2, ok3))
        tile_rows.append(dict(y0=y, x0=x, coh_tile=c_t, d_angle=d_ang, prom=prom,
                              band_ratio=ratio, gabor=e))
        q1 += ok1
        q2 += ok2
        q3 += ok3

    if not n:
        return None
    med = float(np.median(gab_vals)) if gab_vals else 0.0
    for (y, x, ok1, ok2, ok3), e in zip(rows, gab_vals):
        if e >= GABOR_REL_MIN * med:
            q4 += 1
    # Gabor energy is normalised by the field median so the number is a *relative*
    # contrast measure (an absolute one would just follow the image brightness)
    for tr, e in zip(tile_rows, gab_vals):
        tr["gabor_rel"] = e / (med + 1e-12)
    return dict(n_tiles=n,
                Q1_orient_pct=100.0 * q1 / n,
                Q2_spectral_pct=100.0 * q2 / n,
                Q3_bandratio_pct=100.0 * q3 / n,
                Q4_gabor_pct=100.0 * q4 / n,
                mean_coh_tile=float(np.mean([t["coh_tile"] for t in tile_rows])),
                mean_abs_dangle=float(np.mean([t["d_angle"] for t in tile_rows])),
                prom_median=float(np.median(prom_vals)) if prom_vals else np.nan,
                band_ratio_median=float(np.median(ratio_vals)) if ratio_vals else np.nan,
                gabor_rel_mean=float(np.mean([t["gabor_rel"] for t in tile_rows])),
                tile_px=tile,
                _tiles=tile_rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True)
    ap.add_argument("--perfield", required=True, help="crosscheck_perfield.csv (period + axis)")
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.outdir, exist_ok=True)

    tile_rows_all = []
    pf = pd.read_csv(a.perfield)
    pf = pf.drop(columns=["coupon"], errors="ignore").rename(columns={"group": "coupon"})
    rows = []
    for r in pf.itertuples():
        path = os.path.join(a.folder, r.coupon, r.file)
        if not os.path.exists(path):
            cand = glob.glob(os.path.join(a.folder, r.coupon, os.path.splitext(r.file)[0] + "*"))
            cand = [c for c in cand if c.lower().endswith((".bmp", ".png", ".tif"))]
            if not cand:
                print(f"[skip] {r.coupon}/{r.file}")
                continue
            path = cand[0]
        period = r.M2_period_nm if np.isfinite(r.M2_period_nm) else r.M0_period_nm
        out = analyse(path, float(period), float(r.M0_theta_deg), float(r.px_nm_measured))
        if out is None:
            print(f"[skip] {r.coupon}/{r.file}: grid too small")
            continue
        out.update(file=r.file, coupon=r.coupon, stem=os.path.splitext(r.file)[0].replace("_e", ""))
        for t in out.pop("_tiles"):
            t.update(coupon=r.coupon, stem=out["stem"])
            tile_rows_all.append(t)
        rows.append(out)
        print(f"[{r.coupon}/{r.file}] Q1 {out['Q1_orient_pct']:5.1f}  Q2 {out['Q2_spectral_pct']:5.1f}  "
              f"Q3 {out['Q3_bandratio_pct']:5.1f}  Q4 {out['Q4_gabor_pct']:5.1f}", flush=True)
    df = pd.DataFrame(rows)
    out_csv = os.path.join(a.outdir, "quality_perfield.csv")
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    tdf = pd.DataFrame(tile_rows_all)
    t_csv = os.path.join(a.outdir, "quality_tiles.csv")
    tdf.to_csv(t_csv, index=False, encoding="utf-8-sig")
    print("->", out_csv, len(df), "fields;", t_csv, len(tdf), "tiles")


if __name__ == "__main__":
    main()
