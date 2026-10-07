# -*- coding: utf-8 -*-
"""Figure 4 for the laser-textured antibacterial surfaces review:
predictive calculations for austenitic stainless steel at 515 nm.
(a) Sipe efficacy-factor map (room-temperature optical constants).
(b) Predicted period vs assumed surface permittivity (effective-state inversion).

Output: fig4_predictive_models_{en,zh}.png/pdf in <output_dir>/figures/
Requires: lipss_sipe (pip install "git+https://github.com/tjalb/lipss_sipe.git"), numpy, matplotlib.
Usage: python make_review_fig4_predictive.py [output_dir]
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lipss_sipe.core import compute_eta_array

OUTDIR = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:\Users\PC\AppData\Local\hermes\cache\scratch\review_20261007\build"
FIGDIR = os.path.join(OUTDIR, "figures")
os.makedirs(FIGDIR, exist_ok=True)

# stainless steel n,k (wavelength in um, n, k) — Karlsson & Ribbing 1982
NK = [
    (0.28, 1.3009, 2.0018), (0.30, 1.3241, 2.1379), (0.32, 1.3575, 2.2793),
    (0.34, 1.3950, 2.4165), (0.36, 1.4354, 2.5447), (0.38, 1.4786, 2.6681),
    (0.40, 1.5249, 2.7925), (0.42, 1.5762, 2.9240), (0.44, 1.6386, 3.0555),
    (0.46, 1.7169, 3.1785), (0.48, 1.7921, 3.2933), (0.50, 1.8636, 3.4010),
    (0.52, 1.9349, 3.5072), (0.54, 2.0072, 3.6166), (0.56, 2.0807, 3.7298),
    (0.58, 2.1557, 3.8451), (0.60, 2.2325, 3.9594), (0.62, 2.3122, 4.0504),
    (0.64, 2.3962, 4.1378), (0.66, 2.4839, 4.2261), (0.68, 2.5731, 4.3155),
    (0.70, 2.6617, 4.4066), (0.72, 2.7493, 4.5077), (0.74, 2.8446, 4.6053),
    (0.76, 2.9377, 4.7102), (0.78, 3.0323, 4.8118), (0.80, 3.1267, 4.9164),
    (0.82, 3.2257, 5.0188), (0.84, 3.3140, 5.1214), (0.86, 3.4028, 5.2264),
    (0.88, 3.4930, 5.3245), (0.90, 3.5773, 5.4280), (0.92, 3.6643, 5.5350),
    (0.94, 3.7508, 5.6390), (0.96, 3.8331, 5.7480), (0.98, 3.9166, 5.8500),
    (1.00, 3.9957, 5.9480), (1.02, 4.0716, 6.0510), (1.04, 4.1414, 6.1540),
    (1.06, 4.2142, 6.2610), (1.08, 4.2850, 6.3700), (1.10, 4.3600, 6.4790),
    (1.12, 4.4410, 6.5880),
]

F_FACTOR, S_FACTOR = 0.1, 0.4
LAM = 515.0


def eps_at(lam_nm):
    lam_um = lam_nm / 1000.0
    arr = np.array(NK)
    n = float(np.interp(lam_um, arr[:, 0], arr[:, 1]))
    k = float(np.interp(lam_um, arr[:, 0], arr[:, 2]))
    return (n + 1j * k) ** 2


def peak_period(kk, ETA, lam):
    KX, KY = np.meshgrid(kk, kk, indexing="ij")
    R = np.sqrt(KX ** 2 + KY ** 2)
    work = ETA.copy()
    work[R < 0.6] = -np.inf
    work[~np.isfinite(work)] = -np.inf
    i, j = np.unravel_index(np.argmax(work), work.shape)
    kp = float(np.sqrt(kk[i] ** 2 + kk[j] ** 2))
    return kp, lam / kp, i, j


def main():
    kx = np.linspace(-1.8, 1.8, 151)
    ETA = compute_eta_array(kx, kx, "spol", 0.0, eps_at(LAM), F_FACTOR, S_FACTOR)
    kpeak, lampeak, i, j = peak_period(kx, ETA, LAM)
    print("map peak:", round(kpeak, 3), "->", round(lampeak, 1))

    eps_pairs = [(-8.44, 13.35), (-6.0, 8.0), (-4.5, 5.0), (-3.5, 3.5),
                 (-2.8, 2.5), (-2.3, 1.5)]
    kxs = np.linspace(-1.8, 1.8, 121)
    per = []
    for e1, e2 in eps_pairs:
        E2 = compute_eta_array(kxs, kxs, "spol", 0.0, complex(e1, e2), F_FACTOR, S_FACTOR)
        _, pp, _, _ = peak_period(kxs, E2, LAM)
        per.append(pp)
        print("eps", e1, e2, "->", round(pp, 1))
    eps1 = np.array([p[0] for p in eps_pairs])
    per = np.array(per)
    idx = np.argsort(per)
    xc = float(np.interp(385.5, per[idx], eps1[idx]))
    print("crossing at Re(eps) =", round(xc, 2))

    for lang in ("en", "zh"):
        if lang == "en":
            plt.rcParams.update({"font.family": "sans-serif",
                                 "font.sans-serif": ["Arial", "DejaVu Sans"],
                                 "font.size": 9})
            L = dict(t1="(a)  Efficacy factor — steel, 515 nm",
                     t2="(b)  Period vs assumed surface permittivity",
                     cbar="η",
                     ann=f"peak κ = {kpeak:.2f}\n→ Λ = {lampeak:.0f} nm (0.98 λ)",
                     x2="Assumed Re(ε) of the surface",
                     y2="Predicted period Λ (nm)",
                     meas="reported on 316L: 385 nm (0.75 λ)",
                     eff="ε_eff ≈ −2.3")
        else:
            plt.rcParams.update({"font.family": "sans-serif",
                                 "font.sans-serif": ["Microsoft YaHei", "DejaVu Sans"],
                                 "font.size": 9})
            L = dict(t1="(a) 效率因子 η——钢，515 nm",
                     t2="(b) 预测周期与假定表面介电常数",
                     cbar="η",
                     ann=f"峰值 κ = {kpeak:.2f}\n→ Λ = {lampeak:.0f} nm（0.98 λ）",
                     x2="假定的表面 Re(ε)",
                     y2="预测周期 Λ（nm）",
                     meas="316L 实测：385 nm（0.75 λ）",
                     eff="ε_eff ≈ −2.3")

        fig = plt.figure(figsize=(6.1, 3.15))
        ax1 = fig.add_axes([0.065, 0.20, 0.30, 0.62])
        cax = fig.add_axes([0.366, 0.20, 0.015, 0.62])
        ax2 = fig.add_axes([0.55, 0.20, 0.415, 0.62])

        im = ax1.pcolormesh(kx, kx, ETA.T, cmap="inferno", shading="auto")
        ax1.plot(kx[i], kx[j], "o", ms=7, mfc="none", mec="cyan", mew=1.8)
        ax1.annotate(L["ann"], xy=(kx[i], kx[j]), xytext=(-1.72, 1.32),
                     fontsize=7.6, color="#3F4A54",
                     bbox=dict(fc="white", ec="none", alpha=0.7, pad=1.2),
                     arrowprops=dict(arrowstyle="->", color="#6B7680", lw=0.8))
        ax1.set_xlabel("κx", fontsize=9)
        ax1.set_ylabel("κy", fontsize=9)
        ax1.set_title(L["t1"], fontsize=9)
        ax1.set_aspect("equal")
        ax1.set_xticks([-1, 0, 1])
        ax1.set_yticks([-1, 0, 1])
        ax1.tick_params(labelsize=8)
        fig.colorbar(im, cax=cax, label=L["cbar"])

        ax2.plot(eps1, per, "o-", color="#2F6FD0", lw=1.6, ms=5)
        ax2.axhline(385.5, color="#E4572E", ls="--", lw=1.2)
        ax2.text(-8.3, 392, L["meas"], color="#E4572E", fontsize=8)
        ax2.plot([xc], [385.5], "o", ms=6, color="#E4572E")
        ax2.text(xc, 397, L["eff"], color="#E4572E", fontsize=8, ha="center", va="bottom")
        ax2.set_xlabel(L["x2"], fontsize=9)
        ax2.set_ylabel(L["y2"], fontsize=9)
        ax2.set_title(L["t2"], fontsize=9)
        ax2.tick_params(labelsize=8)
        ax2.grid(alpha=0.3)
        ax2.set_ylim(368, 520)

        for ext in ("png", "pdf"):
            fig.savefig(os.path.join(FIGDIR, f"fig4_predictive_models_{lang}.{ext}"), dpi=300)
        plt.close(fig)
        print("saved fig4", lang)


if __name__ == "__main__":
    main()
