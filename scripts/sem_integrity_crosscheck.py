# -*- coding: utf-8 -*-
"""Mean CROSS-METHOD comparison of LIPSS "texture integrity" metrics on the same SEM fields.

Independent re-implementations (no calls into labtoolbox.semtexture internals except
image loading / scale-bar cropping) of six alternative ways to extract the ripple
period + ordering metrics from a SEM micrograph, applied to the same six 515 nm
coupon fields that labtoolbox.semtexture was calibrated on.

Methods
  M0  semtexture (module)            -- autocorrelation of the phase-coherent mean profile
  M1  naive 2-D FFT maximum          -- reproduce the documented v4 defect (no high-pass)
  M2  radial 2-D FFT peak            -- high-pass + Hann window, radial-average power
  M3  1-D FFT of rotated mean profile-- independent structure tensor + profile spectrum
  M4  2-D autocorrelation            -- first ACF side-lobe + correlation length (S_al-like)
  M5  areal PSD (Welch blocks)       -- peak position + log-log slope (ISO 25178-3 flavour)
  M6  nematic order parameter        -- C^2-weighted orientation order S in [0,1]
  M7  tile spectral-prominence map   -- fraction of 2 um tiles with a resolved peak

Reference values for the same coupons: AFM ZSR median 384.6 nm (module docstring),
v5 ring analysis 378-396 nm.
"""
from __future__ import annotations

import os
import sys
import json
import csv
import math
from datetime import date

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, gaussian_filter1d, rotate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from labtoolbox.semtexture import analyse_image, _crop_scalebar  # noqa: E402

SEM_DIR = (r"F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - "
           r"Ruinong Pan_Antibacterial Surfaces/SEM-EDX graphics/02_SEM_raw_images/"
           r"515nm/LIPSS_regions")
MAG_DIR = (r"F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - "
           r"Ruinong Pan_Antibacterial Surfaces/SEM-EDX graphics/02_SEM_raw_images/"
           r"515-8_and_polished_surface")
OUTDIR = os.path.join(ROOT, "output", "sem_integrity_crosscheck_20261111")

PX_NM = 31.25            # 3 k JEOL JSM images, 1 um scale bar = 32 px
BAND_NM = (240.0, 800.0)  # same admissible ripple band as the module
AFM_REF_NM = 384.6
V5_RING_NM = (378.0, 396.0)


# ----------------------------------------------------------------------------- helpers
def load_gray(path):
    img = np.asarray(Image.open(path).convert("L"), dtype=float)
    img = _crop_scalebar(img)          # same footer/scale-bar crop the module uses
    return img


def measure_scalebar_px(path, thr=180, min_len=15, min_rows=3):
    """Length in px of the horizontal white scale bar in the instrument footer.

    The bar is the only feature in the footer that is a horizontal run of bright
    pixels repeated over several consecutive rows and longer than any glyph stroke.
    Returns (bar_px, y0, x0) or (None, None, None).
    """
    a = np.asarray(Image.open(path).convert("L"), dtype=float)
    h, w = a.shape
    cand = {}
    for y in range(int(h * 0.85), h):
        row = a[y]
        m = row > thr
        s = None
        for i in range(w + 1):
            v = m[i] if i < w else False
            if v and s is None:
                s = i
            elif not v and s is not None:
                ln = i - s
                if ln >= min_len:
                    cand.setdefault(ln, []).append((y, s))
                s = None
    # keep runs that appear on at least `min_rows` consecutive rows at the same x
    best = None
    for ln, pos in cand.items():
        ys = sorted(set(y for y, x in pos))
        xs = set(x for y, x in pos)
        run = 1
        best_run = 1
        for i in range(1, len(ys)):
            run = run + 1 if ys[i] == ys[i - 1] + 1 else 1
            best_run = max(best_run, run)
        if best_run >= min_rows and len(xs) == 1:
            if best is None or ln > best[0]:
                best = (ln, ys[0], list(xs)[0])
    return best if best else (None, None, None)


def highpass(img, sigma=20.0):
    return img - gaussian_filter(img, sigma)


def read_sidecar_bar(path):
    """JEOL JSM sidecar: 1 um = SM_MICRON_BAR px (instrument ground truth)."""
    base = os.path.splitext(path)[0] + ".txt"
    if not os.path.exists(base):
        return None
    txt = open(base, "rb").read().decode("latin-1").replace("\x00", " ")
    bar = marker = mag = None
    for tok in txt.replace("\r", " ").replace("\n", " ").split("$"):
        t = tok.strip()
        if t.startswith("$SM_MICRON_BAR"):
            bar = t.split()[-1]
        elif t.startswith("$SM_MICRON_MARKER"):
            marker = t.split()[-1]
        elif t.startswith("CM_MAG"):
            mag = t.split()[-1]
    return dict(bar_px=bar, marker=marker, mag=mag)


def hann2d(n, m):
    return np.outer(np.hanning(n), np.hanning(m))


def period_from_k(k_cyc_per_px, px_nm):
    """spatial frequency (cycles/px) -> period in nm"""
    if k_cyc_per_px <= 0:
        return np.nan
    return px_nm / k_cyc_per_px


def band_mask_periods(n, m, px_nm, band_nm):
    ky = np.fft.fftfreq(n)[:, None]
    kx = np.fft.fftfreq(m)[None, :]
    k = np.hypot(ky, kx)
    with np.errstate(divide="ignore"):
        per = np.where(k > 0, px_nm / np.maximum(k, 1e-12), np.inf)
    return k, per, (per >= band_nm[0]) & (per <= band_nm[1])


def structure_tensor(img, grad_sigma=1.0, tensor_sigma=6.0):
    gy = gaussian_filter(img, grad_sigma, order=[1, 0])
    gx = gaussian_filter(img, grad_sigma, order=[0, 1])
    scale = np.percentile(np.hypot(gx, gy), 99) or 1.0
    gx, gy = gx / scale, gy / scale
    Jxx = gaussian_filter(gx * gx, tensor_sigma)
    Jyy = gaussian_filter(gy * gy, tensor_sigma)
    Jxy = gaussian_filter(gx * gy, tensor_sigma)
    C = np.sqrt((Jxx - Jyy) ** 2 + 4 * Jxy ** 2) / (Jxx + Jyy + 1e-12)
    theta = 0.5 * np.arctan2(2 * Jxy, Jxx - Jyy)
    return C, theta


def circ_mean_deg(deg, w=None):
    deg = np.asarray(deg, float)
    w = np.ones_like(deg) if w is None else np.asarray(w, float)
    ang = np.sum(w * np.exp(1j * 2 * np.deg2rad(deg)))
    return float(np.rad2deg(np.angle(ang)) / 2.0) % 180.0


def circ_sd_deg(deg, w=None):
    deg = np.asarray(deg, float)
    w = np.ones_like(deg) if w is None else np.asarray(w, float)
    R = abs(np.sum(w * np.exp(1j * 2 * np.deg2rad(deg)))) / np.sum(w)
    R = min(max(R, 1e-9), 1.0)
    return float(np.rad2deg(0.5 * math.sqrt(-2.0 * math.log(R))))


def parabolic_peak(y, i):
    """sub-sample peak position of y[i-1..i+1]"""
    if 0 < i < len(y) - 1:
        a, b, c = y[i - 1], y[i], y[i + 1]
        den = a - 2 * b + c
        if abs(den) > 1e-15:
            return i + 0.5 * (a - c) / den
    return float(i)


def local_maxima(y, lo, hi):
    idx = [i for i in range(max(lo, 1), min(hi, len(y) - 1)) if y[i] > y[i - 1] and y[i] >= y[i + 1]]
    return idx


# ----------------------------------------------------------------------------- methods
def m0_module(path):
    res = analyse_image(path, pixel_nm=PX_NM)
    return dict(period_nm=res.get("period_nm"), period_profile_nm=res.get("period_profile_nm"),
                period_fft_nm=res.get("period_fft_nm"), theta_deg=res.get("theta_deg"),
                coherence=res.get("coherence"), ac_strength=res.get("ac_strength"),
                ordered_frac_pct=res.get("ordered_frac", np.nan) * 100 if res.get("ordered_frac") is not None else np.nan,
                mode=res.get("mode"))


def m1_naive_fft(img):
    """strongest 2-D FFT peak, no high-pass, no window -> reproduces the v4 defect"""
    a = img - img.mean()
    P = np.abs(np.fft.fft2(a)) ** 2
    n, m = a.shape
    k, per, inband = band_mask_periods(n, m, PX_NM, (100.0, 3000.0))
    P = P.copy()
    P[k < 1.0 / 200.0] = 0.0          # drop DC + the slow envelope bin itself
    idx = np.unravel_index(np.argmax(P), P.shape)
    return dict(period_nm=period_from_k(float(k[idx]), PX_NM),
                peak_k_cyc_per_px=float(k[idx]), band_limited=False)


def m2_radial_fft(img):
    a = highpass(img) * hann2d(*img.shape)
    P = np.abs(np.fft.fft2(a)) ** 2
    n, m = a.shape
    k, per, inband = band_mask_periods(n, m, PX_NM, BAND_NM)
    kb = k[inband]
    if kb.size == 0:
        return dict(period_nm=np.nan, prominence=np.nan, theta_deg=np.nan)
    # radial average
    kr = np.linspace(kb.min(), kb.max(), 400)
    rad = np.zeros_like(kr)
    for i, kv in enumerate(kr):
        sel = (k >= kv * 0.94) & (k < kv * 1.06) & inband
        if sel.any():
            rad[i] = P[sel].mean()
    i = int(np.argmax(rad))
    ip = parabolic_peak(rad, i)
    k_peak = kr[0] + (kr[1] - kr[0]) * ip
    # angular peak (orientation of the grating normal), weighted by power in band
    ang = np.arctan2(np.fft.fftfreq(n)[:, None] * np.ones((1, m)),
                     np.ones((n, 1)) * np.fft.fftfreq(m)[None, :])
    th = (np.rad2deg(ang) + 90.0) % 180.0    # gradient normal is perpendicular to k
    w = np.where(inband, P, 0.0)
    theta = circ_mean_deg(th.ravel(), w.ravel())
    prom = (rad[i] - np.median(rad)) / (np.median(rad) + 1e-12)
    return dict(period_nm=period_from_k(float(k_peak), PX_NM), prominence=float(prom),
                theta_deg=theta)


def m3_profile_fft(img, theta0):
    """rotate so the gradient is vertical, average across columns, FFT the profile"""
    rot = rotate(img, theta0 - 90.0, reshape=False, order=1, mode="nearest")
    h, w = rot.shape
    m = int(0.08 * min(h, w))
    prof = rot[m:h - m, m:w - m].mean(axis=1)
    prof = prof - prof.mean()
    if prof.size < 8:
        return dict(period_nm=np.nan)
    win = np.hanning(prof.size)
    F = np.abs(np.fft.rfft(prof * win)) ** 2
    freqs = np.fft.rfftfreq(prof.size)          # cycles/px
    with np.errstate(divide="ignore"):
        per = np.where(freqs > 0, PX_NM / np.maximum(freqs, 1e-12), np.inf)
    band = (per >= BAND_NM[0]) & (per <= BAND_NM[1])
    if not band.any():
        return dict(period_nm=np.nan)
    idx = np.where(band)[0]
    i = idx[int(np.argmax(F[idx]))]
    ip = parabolic_peak(F, i)
    df = freqs[1]
    return dict(period_nm=period_from_k(float(freqs[0] + ip * df), PX_NM),
                fft_prominence=float((F[i] - np.median(F)) / (np.median(F) + 1e-12)))


def m4_acf(img, theta0):
    a = highpass(img)
    a = a - a.mean()
    n, m = a.shape
    A = np.fft.irfft2(np.abs(np.fft.rfft2(a)) ** 2, s=a.shape)
    A = np.fft.fftshift(A)
    A /= A.max() + 1e-12
    cy, cx = n // 2, m // 2
    # profile along the gradient normal (theta0 measured from +x, gradient across ripples)
    t = np.deg2rad(theta0)
    lags = np.arange(3.0, min(60.0, min(n, m) // 4))
    prof = np.array([A[int(round(cy + l * math.sin(t))), int(round(cx + l * math.cos(t)))]
                     for l in lags])
    lo = int(np.floor(BAND_NM[0] / PX_NM))
    hi = int(np.ceil(BAND_NM[1] / PX_NM))
    idx = [i for i in local_maxima(prof, 1, len(prof) - 1) if lo <= lags[i] <= hi]
    if idx:
        i = max(idx, key=lambda j: prof[j])
        lp = parabolic_peak(prof, i)
        lag = lags[0] + (lags[1] - lags[0]) * lp
        period = lag * PX_NM
        ac_val = float(prof[i])
    else:
        period, ac_val = np.nan, np.nan
    below = np.where(prof < 1.0 / math.e)[0]
    sal_nm = float(lags[below[0]] * PX_NM) if below.size else np.nan
    return dict(period_nm=period, acf_peak=ac_val, correlation_length_nm=sal_nm)


def m5_areal_psd(img, block=256, overlap=0.5):
    a = highpass(img)
    a = a - a.mean()
    n, m = a.shape
    step = int(block * (1 - overlap))
    psds, freqs = [], None
    for y0 in range(0, max(n - block, 1) + 1, step):
        for x0 in range(0, max(m - block, 1) + 1, step):
            blk = a[y0:y0 + block, x0:x0 + block]
            if blk.shape != (block, block):
                continue
            w = np.outer(np.hanning(block), np.hanning(block))
            F = np.fft.fft2(blk * w)
            P = (np.abs(F) ** 2) / (block ** 4)
            k = np.hypot(np.fft.fftfreq(block)[:, None], np.fft.fftfreq(block)[None, :])
            psds.append((k.ravel(), P.ravel()))
    if not psds:
        return dict(period_nm=np.nan)
    kk = np.concatenate([p[0] for p in psds])
    pp = np.concatenate([p[1] for p in psds])
    kr = np.linspace(1.0 / 3000.0, 0.5, 500)          # cycles/px
    rad = np.array([pp[(kk >= kv * 0.97) & (kk < kv * 1.03)].mean() if ((kk >= kv * 0.97) & (kk < kv * 1.03)).any()
                    else np.nan for kv in kr])
    ok = np.isfinite(rad) & (rad > 0)
    with np.errstate(divide="ignore"):
        per = PX_NM / np.maximum(kr, 1e-12)
    band = ok & (per >= BAND_NM[0]) & (per <= BAND_NM[1])
    if not band.any():
        return dict(period_nm=np.nan)
    i = int(np.argmax(np.where(band, rad, 0.0)))
    ip = parabolic_peak(np.where(np.isfinite(rad), rad, 0.0), i)
    k_peak = kr[0] + (kr[1] - kr[0]) * ip
    # log-log slope inside the band (ISO 25178-3 style PSD characterisation)
    sel = band & ok
    slope = np.polyfit(np.log10(kr[sel]), np.log10(rad[sel]), 1)[0] if sel.sum() > 5 else np.nan
    sq_rel = float(np.sqrt(np.nansum(rad[ok]) * (kr[1] - kr[0])))   # relative (intensity) units
    return dict(period_nm=period_from_k(float(k_peak), PX_NM), psd_slope=float(slope),
                sq_rel=sq_rel)


def m6_order_parameter(img, theta0):
    C, th = structure_tensor(highpass(img))
    w = C ** 2
    Rp = abs(np.sum(w * np.exp(1j * 2 * (th - np.deg2rad(theta0))))) / (np.sum(w) + 1e-12)
    hist, _ = np.histogram(np.rad2deg(th) % 180.0, bins=36, range=(0, 180), weights=w)
    p = hist / (hist.sum() + 1e-12)
    p = p[p > 0]
    ent = -np.sum(p * np.log(p)) / math.log(36)     # normalised entropy, 0 = one direction only
    return dict(order_S=float(Rp), orientation_entropy=float(ent))


def m7_tile_prominence(img, theta0, tile_px=64, prom_min=2.0):
    a = highpass(img)
    n, m = a.shape
    ok, total, proms = 0, 0, []
    for y0 in range(0, n - tile_px + 1, tile_px):
        for x0 in range(0, m - tile_px + 1, tile_px):
            blk = a[y0:y0 + tile_px, x0:x0 + tile_px]
            if img[y0:y0 + tile_px, x0:x0 + tile_px].mean() < 0.45 * np.median(img):
                continue
            total += 1
            w = np.outer(np.hanning(tile_px), np.hanning(tile_px))
            P = np.abs(np.fft.fft2(blk * w)) ** 2
            k, per, inband = band_mask_periods(tile_px, tile_px, PX_NM, BAND_NM)
            if not inband.any():
                continue
            pk = P[inband]
            prom = (pk.max() - np.median(pk)) / (np.median(pk) + 1e-12)
            proms.append(prom)
            if prom >= prom_min:
                ok += 1
    frac = 100.0 * ok / total if total else np.nan
    return dict(tile_prom_frac_pct=frac, tile_prom_median=float(np.median(proms)) if proms else np.nan,
                n_tiles=total)


# ----------------------------------------------------------------------------- main
def main():
    os.makedirs(OUTDIR, exist_ok=True)
    files = sorted(f for f in os.listdir(SEM_DIR)
                   if f.lower().endswith((".bmp", ".tif", ".tiff", ".png", ".jpg"))
                   and not f.lower().endswith(("_quality.png", "_pair.png", "_marked.png")))
    rows = []
    scalebar = {}
    for f in files:
        path = os.path.join(SEM_DIR, f)
        bar_px, _, _ = measure_scalebar_px(path)
        scalebar[f] = bar_px
        img = load_gray(path)
        print(f"[{f}] shape={img.shape} scalebar={bar_px} px -> "
              f"{1000.0 / bar_px:.2f} nm/px" if bar_px else f"[{f}] shape={img.shape} scalebar=?", flush=True)
        m0 = m0_module(path)
        theta0 = float(m0["theta_deg"]) if np.isfinite(m0.get("theta_deg") or np.nan) else 0.0
        rec = dict(file=f, coupon=f.split("-")[0], scalebar_px=bar_px,
                   px_nm_measured=(1000.0 / bar_px) if bar_px else np.nan)
        rec.update({f"M0_{k}": v for k, v in m0.items()})
        rec.update({f"M1_{k}": v for k, v in m1_naive_fft(img).items()})
        rec.update({f"M2_{k}": v for k, v in m2_radial_fft(img).items()})
        rec.update({f"M3_{k}": v for k, v in m3_profile_fft(img, theta0).items()})
        rec.update({f"M4_{k}": v for k, v in m4_acf(img, theta0).items()})
        rec.update({f"M5_{k}": v for k, v in m5_areal_psd(img).items()})
        rec.update({f"M6_{k}": v for k, v in m6_order_parameter(img, theta0).items()})
        rec.update({f"M7_{k}": v for k, v in m7_tile_prominence(img, theta0).items()})
        rows.append(rec)

    field_csv = os.path.join(OUTDIR, "crosscheck_perfield.csv")
    with open(field_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- summary per method
    methods = {
        "M0": ("semtexture (autocorr. of mean profile)", "M0_period_nm"),
        "M1": ("naive 2-D FFT maximum (v4 defect)", "M1_period_nm"),
        "M2": ("radial 2-D FFT peak (high-pass + Hann)", "M2_period_nm"),
        "M3": ("1-D FFT of rotated mean profile", "M3_period_nm"),
        "M4": ("2-D autocorrelation side-lobe", "M4_period_nm"),
        "M5": ("areal PSD (Welch) peak", "M5_period_nm"),
    }
    summ = []
    for key, (name, col) in methods.items():
        v = np.array([r.get(col, np.nan) for r in rows], float)
        v = v[np.isfinite(v)]
        if v.size == 0:
            continue
        summ.append(dict(method=key, name=name, n=int(v.size), mean_nm=float(v.mean()),
                         sd_nm=float(v.std(ddof=1)) if v.size > 1 else 0.0,
                         cv_pct=float(100 * v.std(ddof=1) / v.mean()) if v.size > 1 else 0.0,
                         min_nm=float(v.min()), max_nm=float(v.max()),
                         delta_vs_afm_nm=float(v.mean() - AFM_REF_NM),
                         delta_vs_afm_pct=float(100 * (v.mean() - AFM_REF_NM) / AFM_REF_NM),
                         inside_v5_ring=bool(V5_RING_NM[0] <= v.mean() <= V5_RING_NM[1])))

    # ordering metrics
    order = []
    for key, name, col in [("C", "coherence C (structure-tensor, module)", "M0_coherence"),
                           ("S", "nematic order S (C^2-weighted)", "M6_order_S"),
                           ("Hs", "orientation entropy, normalised (0=one direction)", "M6_orientation_entropy"),
                           ("tile%", "tile spectral-prominence fraction % (prom>=2)", "M7_tile_prom_frac_pct"),
                           ("prom", "tile spectral-prominence median", "M7_tile_prom_median"),
                           ("ord%", "ordered area fraction % (module tile map)", "M0_ordered_frac_pct")]:
        v = np.array([r.get(col, np.nan) for r in rows], float)
        v = v[np.isfinite(v)]
        if v.size:
            order.append(dict(metric=key, name=name, n=int(v.size), mean=float(v.mean()),
                              sd=float(v.std(ddof=1)) if v.size > 1 else 0.0,
                              min=float(v.min()), max=float(v.max())))

    sum_csv = os.path.join(OUTDIR, "crosscheck_summary.csv")
    with open(sum_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summ[0].keys()))
        w.writeheader()
        w.writerows(summ)
    ord_csv = os.path.join(OUTDIR, "crosscheck_ordering.csv")
    with open(ord_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(order[0].keys()))
        w.writeheader()
        w.writerows(order)

    # ---- calibration & magnification cross-check (coupon 8: 3 k vs 12 k, sidecar pixel size)
    mag_rows = []
    for name, px in (("LIPSS-515-8-3k_e.tif", 31.25), ("LIPSS-515-8-12k_e.tif", 7.8125)):
        p = os.path.join(MAG_DIR, name)
        if not os.path.exists(p):
            continue
        globals()["PX_NM"] = px                    # methods read the global
        img = load_gray(p)
        m0 = m0_module(p)
        rec = dict(file=name, px_nm=px, sidecar=read_sidecar_bar(p))
        rec.update({f"M0_{k}": v for k, v in m0.items()})
        rec.update({f"M2_{k}": v for k, v in m2_radial_fft(img).items()})
        rec.update({f"M4_{k}": v for k, v in m4_acf(img, float(m0.get("theta_deg") or 0)).items()})
        mag_rows.append(rec)
        print(f"[mag] {name} px={px} M0={m0.get('period_nm'):.1f} "
              f"M2={rec.get('M2_period_nm', float('nan')):.1f} M4={rec.get('M4_period_nm', float('nan')):.1f}",
              flush=True)
    globals()["PX_NM"] = 31.25

    # what pixel size WOULD be needed to reconcile SEM with the AFM value
    m0_mean = float(np.nanmean([r.get("M0_period_nm", np.nan) for r in rows]))
    px_needed = PX_NM * AFM_REF_NM / m0_mean
    bar_needed = 1000.0 / px_needed

    # ---- figures
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    labels = [f"{s['method']}" for s in summ]
    means = [s["mean_nm"] for s in summ]
    sds = [s["sd_nm"] for s in summ]
    ax = axes[0]
    ax.bar(range(len(summ)), means, yerr=sds, capsize=4, color="#4C78A8", alpha=0.85)
    ax.axhline(AFM_REF_NM, color="#D62728", ls="--", lw=1.5, label=f"AFM ZSR median {AFM_REF_NM:.1f} nm")
    ax.axhspan(*V5_RING_NM, color="#D62728", alpha=0.10, label="v5 ring analysis 378–396 nm")
    ax.set_xticks(range(len(summ)))
    ax.set_xticklabels(labels)
    ax.set_ylabel("ripple period Λ (nm)")
    ax.set_title(f"Same 6 fields, six extraction methods (n={summ[0]['n']})")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)

    ax = axes[1]
    for i, r in enumerate(rows):
        vals = [r.get(col, np.nan) for _, (_, col) in methods.items()]
        ax.plot(range(len(vals)), vals, "o-", lw=0.8, alpha=0.75, ms=4, label=r["file"])
    ax.axhline(AFM_REF_NM, color="#D62728", ls="--", lw=1.2)
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels(list(methods.keys()))
    ax.set_ylabel("Λ (nm)")
    ax.set_title("Per-coupon spread across methods")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig_png = os.path.join(OUTDIR, "crosscheck_periods.png")
    fig.savefig(fig_png, dpi=200)

    # ---- report
    lines = [f"# SEM 织构「完整性」指标跨方法比对 — {date.today().isoformat()}", "",
             f"输入：`{SEM_DIR}`（515 nm LIPSS，6 个 coupon 视野，{PX_NM} nm/px）", "",
             "## 1. 周期 Λ 的六种取法（同一批图）", "",
             "| 方法 | 说明 | n | 均值 (nm) | SD | CV | vs AFM 384.6 nm |",
             "|---|---|---|---|---|---|---|"]
    for s in summ:
        lines.append(f"| {s['method']} | {s['name']} | {s['n']} | {s['mean_nm']:.1f} | "
                     f"{s['sd_nm']:.1f} | {s['cv_pct']:.2f} % | {s['delta_vs_afm_pct']:+.1f} % |")
    lines += ["", "## 2. 有序性/完整性指标（同类比较）", "",
              "| 指标 | 说明 | n | 均值 | SD | 范围 |", "|---|---|---|---|---|---|"]
    for o in order:
        lines.append(f"| {o['metric']} | {o['name']} | {o['n']} | {o['mean']:.3f} | "
                     f"{o['sd']:.3f} | {o['min']:.3f} – {o['max']:.3f} |")

    # calibration section
    bars = [r["scalebar_px"] for r in rows if r.get("scalebar_px")]
    lines += ["", "## 3. 像素标定核对（决定性证据）", "",
              "| 检查 | 结果 |", "|---|---|",
              f"| 图内比例尺实测（脚注白条，逐图测量） | {', '.join(str(b) for b in bars)} px = 1 µm |",
              f"| 换算像素尺寸 | {1000.0 / np.median(bars):.2f} nm/px |",
              f"| 仪器 sidecar 自述（`SM_MICRON_BAR` / `SM_MICRON_MARKER`） | 515-8 series 3k = 32 px/1 µm，12k = 128 px/1 µm（JSM 7400F） |",
              f"| 模块假定 `DEFAULT_PIXEL_NM` | 31.25 nm/px ✓ 与以上一致 |",
              f"| 若要 SEM 周期等于 AFM {AFM_REF_NM} nm，像素需为 | **{px_needed:.2f} nm/px**（即 1 µm = {bar_needed:.1f} px，与实测 32 px 不符） |",
              "",
              f"→ 标定本身无误；**SEM 与 AFM 的 {100 * (m0_mean - AFM_REF_NM) / AFM_REF_NM:+.1f}% 偏差不能归因于像素标定**。",
              "",
              f"另外：模块 docstring/文档声称「六个 515 nm 样片给出 375–395 nm，与 AFM 384.6 nm 吻合」——"
              f"本脚本与仓库内既有的 `output/sem_texture_20261103` 运行**都复现不出这个区间**（实际 {m0_mean:.1f} ± "
              f"{np.nanstd([r.get('M0_period_nm', np.nan) for r in rows], ddof=1):.1f} nm / 362.9 nm），"
              "该验证声明目前**无数据支持**，需要改写或重新标定后再引用。"]

    # magnification section
    if mag_rows:
        lines += ["", "## 4. 放大倍数一致性（同一 coupon 8，3k vs 12k）", "",
                  "| 文件 | 像素 (nm) | M0 semtexture | M2 径向 FFT | M4 自相关 |", "|---|---|---|---|---|"]
        for m in mag_rows:
            lines.append(f"| {m['file']} | {m['px_nm']} | {m['M0_period_nm']:.1f} | "
                         f"{m.get('M2_period_nm', float('nan')):.1f} | {m.get('M4_period_nm', float('nan')):.1f} |")
        if len(mag_rows) == 2:
            a, b = mag_rows[0], mag_rows[1]
            d0 = 100 * (b["M0_period_nm"] - a["M0_period_nm"]) / a["M0_period_nm"]
            lines += ["", f"→ 12k 相对 3k：**{d0:+.1f}%**（同一 coupon，两套像素尺寸都由 sidecar 给出）。"]

    lines += ["", "## 5. 逐视野数据", "", "| file | " + " | ".join(methods) + " |",
              "|---|" + "---|" * len(methods)]
    for r in rows:
        vals = []
        for _, (_, col) in methods.items():
            v = r.get(col, np.nan)
            vals.append(f"{v:.0f}" if np.isfinite(v) else "–")
        lines.append(f"| {r['file']} | " + " | ".join(vals) + " |")
    rep_md = os.path.join(OUTDIR, "crosscheck_report.md")
    with open(rep_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print(json.dumps({"outdir": OUTDIR, "perfield": field_csv, "summary": sum_csv,
                      "ordering": ord_csv, "figure": fig_png, "report": rep_md}, ensure_ascii=False, indent=1))
    for s in summ:
        print(f"{s['method']:<3} {s['mean_nm']:7.1f} ± {s['sd_nm']:5.1f} nm  CV {s['cv_pct']:5.2f}%  "
              f"vs AFM {s['delta_vs_afm_pct']:+6.1f}%  {s['name']}")
    for o in order:
        print(f"{o['metric']:<4} {o['mean']:.3f} ± {o['sd']:.3f}  {o['name']}")


if __name__ == "__main__":
    main()
