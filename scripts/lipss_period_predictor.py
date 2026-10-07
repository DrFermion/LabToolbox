# -*- coding: utf-8 -*-
"""LIPSS period predictor — Sipe efficacy factor (via lipss_sipe) + SPP estimate.

Demo material: austenitic stainless steel (Avesta 832 MV ~ SS316),
optical constants from Karlsson & Ribbing, J. Appl. Phys. 53, 6340 (1982)
(via refractiveindex.info, data extracted from figure).

Usage:  python lipss_period_predictor.py [--npts 181] [--out DIR]
Outputs: eta maps (PNG) + peaks (CSV + console) in the output directory.
"""
import os
import sys
import time
import argparse
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lipss_sipe.core import compute_eta_array

plt.rcParams.update({
    "font.size": 10, "font.weight": "normal", "axes.labelweight": "normal",
    "axes.titleweight": "normal", "figure.titleweight": "normal",
    "lines.linewidth": 1.5, "axes.linewidth": 1.0,
    "xtick.labelsize": 9, "ytick.labelsize": 9,
})

# --- stainless steel n,k (wavelength in um, n, k), 0.28-1.12 um ---
NK = [
    (0.28, 1.3009, 2.0018),
    (0.30, 1.3241, 2.1379),
    (0.32, 1.3575, 2.2793),
    (0.34, 1.3950, 2.4165),
    (0.36, 1.4354, 2.5447),
    (0.38, 1.4786, 2.6681),
    (0.40, 1.5249, 2.7925),
    (0.42, 1.5762, 2.9240),
    (0.44, 1.6386, 3.0555),
    (0.46, 1.7169, 3.1785),
    (0.48, 1.7921, 3.2933),
    (0.50, 1.8636, 3.4010),
    (0.52, 1.9349, 3.5072),
    (0.54, 2.0072, 3.6166),
    (0.56, 2.0807, 3.7298),
    (0.58, 2.1557, 3.8451),
    (0.60, 2.2325, 3.9594),
    (0.62, 2.3122, 4.0504),
    (0.64, 2.3962, 4.1378),
    (0.66, 2.4839, 4.2261),
    (0.68, 2.5731, 4.3155),
    (0.70, 2.6617, 4.4066),
    (0.72, 2.7493, 4.5077),
    (0.74, 2.8446, 4.6053),
    (0.76, 2.9377, 4.7102),
    (0.78, 3.0323, 4.8118),
    (0.80, 3.1267, 4.9164),
    (0.82, 3.2257, 5.0188),
    (0.84, 3.3140, 5.1214),
    (0.86, 3.4028, 5.2264),
    (0.88, 3.4930, 5.3245),
    (0.90, 3.5773, 5.4280),
    (0.92, 3.6643, 5.5350),
    (0.94, 3.7508, 5.6390),
    (0.96, 3.8331, 5.7480),
    (0.98, 3.9166, 5.8500),
    (1.00, 3.9957, 5.9480),
    (1.02, 4.0716, 6.0510),
    (1.04, 4.1414, 6.1540),
    (1.06, 4.2142, 6.2610),
    (1.08, 4.2850, 6.3700),
    (1.10, 4.3600, 6.4790),
    (1.12, 4.4410, 6.5880),
]

F_FACTOR = 0.1     # roughness filling factor
S_FACTOR = 0.4     # roughness shape factor
ANGLE_DEG = 0.0    # angle of incidence


def eps_at(lam_nm):
    lam_um = lam_nm / 1000.0
    arr = np.array(NK)
    n = float(np.interp(lam_um, arr[:, 0], arr[:, 1]))
    k = float(np.interp(lam_um, arr[:, 0], arr[:, 2]))
    return (n + 1j * k) ** 2, n, k


def lam_spp_ratio(eps):
    """SPP-based estimate of Lambda/lambda0 (Sipe 1983; air interface)."""
    return 1.0 / np.real(np.sqrt(eps / (eps + 1.0)))


def top_peaks(kx, ky, ETA, rmin=0.6, n=6):
    """Find the n strongest local maxima of ETA inside radius rmin."""
    KX, KY = np.meshgrid(kx, ky, indexing="ij")
    R = np.sqrt(KX ** 2 + KY ** 2)
    work = ETA.copy()
    work[R < rmin] = -np.inf
    work[~np.isfinite(work)] = -np.inf
    peaks = []
    for _ in range(n):
        idx = np.unravel_index(np.argmax(work), work.shape)
        i, j = idx
        # suppress neighbourhood
        i0, i1 = max(0, i - 8), min(work.shape[0], i + 9)
        j0, j1 = max(0, j - 8), min(work.shape[1], j + 9)
        val = work[i, j]
        if not np.isfinite(val):
            break
        kxm, kym = kx[i], ky[j]
        peaks.append((float(kxm), float(kym), float(np.sqrt(kxm**2 + kym**2)),
                      float(np.degrees(np.arctan2(kym, kxm))), float(val)))
        work[i0:i1, j0:j1] = -np.inf
    return peaks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npts", type=int, default=181)
    ap.add_argument("--out", type=str,
                    default=r"E:\LabToolbox\output\lipss_predict_20261007")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    kx = np.linspace(-1.8, 1.8, args.npts)
    ky = np.linspace(-1.8, 1.8, args.npts)
    lams = (515, 1030, 343)
    summary = []
    store = {}

    for lam in lams:
        eps, n, k = eps_at(lam)
        ratio_spp = lam_spp_ratio(eps)
        print(f"=== {lam} nm: n={n:.3f}, k={k:.3f}, eps={eps.real:.2f}{eps.imag:+.2f}j | "
              f"SPP estimate Lambda/lambda = {ratio_spp:.3f} -> {ratio_spp*lam:.0f} nm")
        for pol in ("spol", "ppol"):
            t0 = time.time()
            ETA = compute_eta_array(kx, ky, pol, np.deg2rad(ANGLE_DEG), eps,
                                    F_FACTOR, S_FACTOR)
            dt = time.time() - t0
            peaks = top_peaks(kx, ky, ETA)
            p = peaks[0]
            print(f"  [{pol}] {dt:.1f}s | top peak: kappa=({p[0]:+.3f},{p[1]:+.3f}) "
                  f"|k|={p[2]:.3f} angle={p[3]:.1f} deg eta={p[4]:.1f} "
                  f"-> Lambda = {lam/p[2]:.1f} nm")
            for q in peaks[1:4]:
                print(f"          next: kappa=({q[0]:+.3f},{q[1]:+.3f}) |k|={q[2]:.3f} "
                      f"angle={q[3]:.1f} eta={q[4]:.1f} -> Lambda = {lam/q[2]:.1f} nm")
            summary.append((lam, pol, p[2], lam / p[2], p[3], p[4]))
            store[(lam, pol)] = (ETA.copy(), p)
            # save map figure
            fig, ax = plt.subplots(figsize=(5.2, 4.4))
            im = ax.pcolormesh(kx, ky, ETA.T, cmap="inferno", shading="auto")
            ax.plot(p[0], p[1], "o", ms=8, mfc="none", mec="cyan", mew=2)
            ax.set_xlabel(r"$\kappa_x$", fontsize=11)
            ax.set_ylabel(r"$\kappa_y$", fontsize=11)
            ax.set_title(f"steel, {lam} nm, {pol}, $\\theta$={ANGLE_DEG:.0f}$^\\circ$\n"
                         f"peak $|\\kappa|$={p[2]:.3f} -> $\\Lambda$={lam/p[2]:.0f} nm",
                         fontsize=10)
            fig.colorbar(im, ax=ax, label=r"efficacy factor $\eta$")
            fig.tight_layout()
            fp = os.path.join(args.out, f"eta_{lam}nm_{pol}.png")
            fig.savefig(fp, dpi=170)
            plt.close(fig)

    # combined summary figure (s-polarization at the three wavelengths)
    fig, axs = plt.subplots(1, 3, figsize=(11.5, 3.9))
    im = None
    for axx, lam in zip(axs, lams):
        ETA, p = store[(lam, "spol")]
        im = axx.pcolormesh(kx, ky, ETA.T, cmap="inferno", shading="auto")
        axx.plot(p[0], p[1], "o", ms=9, mfc="none", mec="cyan", mew=2)
        axx.set_xlabel(r"$\kappa_x = k_x\lambda/2\pi$")
        if lam == 515:
            axx.set_ylabel(r"$\kappa_y$")
        axx.set_title(f"{lam} nm  |  peak $\kappa$ = {p[2]:.2f}  ->  "
                      f"$\Lambda$ = {lam/p[2]:.0f} nm ({(lam/p[2])/lam:.2f}$\lambda$)",
                      fontsize=10)
        axx.set_aspect("equal")
    fig.colorbar(im, ax=axs, shrink=0.85, label=r"efficacy factor $\eta$")
    fig.suptitle("Sipe efficacy factor - austenitic stainless steel (n,k: Karlsson and Ribbing 1982), "
                 r"$	heta=0^\circ$, s-pol", y=0.99, fontsize=10)
    fig.tight_layout(rect=(0, 0, 0.94, 0.94))
    fig.savefig(os.path.join(args.out, "summary_eta_spol.png"), dpi=170)
    plt.close(fig)

    # peaks CSV
    csvp = os.path.join(args.out, "peaks.csv")
    with open(csvp, "w", encoding="utf-8") as f:
        f.write("lambda_nm,pol,kappa,period_nm,angle_deg,eta\n")
        for row in summary:
            f.write(f"{row[0]},{row[1]},{row[2]:.4f},{row[3]:.1f},{row[4]:.1f},{row[5]:.2f}\n")
    print("outputs in:", args.out)


if __name__ == "__main__":
    main()
