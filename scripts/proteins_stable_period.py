# -*- coding: utf-8 -*-
"""proteins_stable_period.py — 两个端态汇总（新鲜 day 0 / 最终稳定期 day 49–73）。

主人 2026-09-30 要求：报告只看"新鲜"与"最后稳定期"，不展开中间老化过程。
本脚本：
  - 从 protein_surface_matrix.csv 汇总稳定期（第 49/58/65/73 天, n=4）的 mean ± SD → protein_stable_period.csv
  - 用"稳定期平均表面能"重算细菌对裸面/条件膜的黏附，替代按单日 day 58 → bacteria_on_films_stable.csv
  - 覆盖重制 fig1（新鲜 vs 稳定期均值±SD）与 fig3（稳定期用平均表面能）
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, r"E:\LabToolbox")
from labtoolbox.xdlvo.xdlvo import SurfaceEnergy, delta_g, interaction_energy  # noqa: E402

OUT = r"E:\LabToolbox\output\proteins_environments_20260930"
SFE = r"E:\LabToolbox\output\xdlvo_515nm_20260912\xdlvo_515nm_dG.csv"
STABLE = [49, 58, 65, 73]
I_M, T_K = 0.15, 310.15
H0 = 0.158e-9
LAM = 0.6e-9
KT = 1.380649e-23 * T_K

PROT_ORDER = ["Albumin (BSA A)", "Albumin (BSA B)", "Fibrinogen (human)", "Fibronectin (human)"]
SURF_ORDER = ["LIPSS", "Nanopillar", "Control 316L"]
PROT_PARAMS = {
    "Albumin (BSA A)": ((40.60, 1.16, 20.03), 3.5, -13.0),
    "Albumin (BSA B)": ((43.22, 1.065, 47.68), 3.5, -13.0),
    "Fibrinogen (human)": ((37.6, 0.1, 38.0), 5.0, -20.0),
    "Fibronectin (human)": ((29.5, 3.9, 52.1), 5.0, -15.0),
}
BACT = {"S. aureus 12600": ((31.56, 0.43, 68.32), 450.0),
        "E. coli F1693": ((35.60, 0.14, 67.68), 450.0)}
FILMS = {"Albumin (BSA A) film": (40.60, 1.16, 20.03),
         "Albumin (BSA B) film": (43.22, 1.065, 47.68),
         "Fibrinogen (human) film": (37.6, 0.1, 38.0),
         "Fibronectin (human) film": (29.5, 3.9, 52.1)}
COLORS = ["#1f4e79", "#85c1e9", "#e07b39", "#4c9f70"]


def se(t):
    return SurfaceEnergy(t[0], t[1], t[2], 2 * np.sqrt(t[1] * t[2]), t[0] + 2 * np.sqrt(t[1] * t[2]))


def contact_barrier_kT(dg, R_nm):
    """Derjaguin 接触能量（与主脚本同一口径）。"""
    return 2 * np.pi * (R_nm * 1e-9) * (dg['LW'] * 1e-3 * H0 + LAM * dg['AB'] * 1e-3) / KT


sfe = pd.read_csv(SFE, encoding="utf-8-sig").drop_duplicates(subset=["surface", "day"])
mat = pd.read_csv(os.path.join(OUT, "protein_surface_matrix.csv"), encoding="utf-8-sig")


def surf_se(surface, day):
    r = sfe[(sfe.surface == surface) & (sfe.day == day)].iloc[0]
    return se((r.gamma_LW, r.gamma_plus, r.gamma_minus))


def stable_se(surface):
    q = sfe[(sfe.surface == surface) & (sfe.day.isin(STABLE))]
    return se((q.gamma_LW.mean(), q.gamma_plus.mean(), q.gamma_minus.mean()))


# ---------- 1) 稳定期统计
sta = (mat[mat.day.isin(STABLE)]
       .groupby(["surface", "protein"])[["dG_LW", "dG_AB", "dG_ADH", "barrier_kT"]]
       .agg(["mean", "std"]))
sta.columns = [f"{a}_{b}" for a, b in sta.columns]
sta = sta.reset_index()[["surface", "protein",
                         "dG_LW_mean", "dG_AB_mean", "dG_ADH_mean", "dG_ADH_std",
                         "barrier_kT_mean", "barrier_kT_std"]]
sta["n_days"] = len(STABLE)
sta.round(4).to_csv(os.path.join(OUT, "protein_stable_period.csv"), index=False, encoding="utf-8-sig")
print("protein_stable_period.csv written; n=", len(sta))

# ---------- 2) 细菌 vs 裸面/条件膜（稳定期用平均表面能）
rows = []
for bname, (bt, R) in BACT.items():
    cases = [
        ("bare LIPSS fresh (day 0)", surf_se("LIPSS", 0)),
        ("bare LIPSS stable (days 49-73)", stable_se("LIPSS")),
        ("bare Control fresh (day 0)", surf_se("Control 316L", 0)),
        ("bare Control stable (days 49-73)", stable_se("Control 316L")),
    ] + [(k, se(v)) for k, v in FILMS.items()]
    for label, sub in cases:
        dg = delta_g(sub, se(bt), I_M, T_K, zeta_m=-25.0, zeta_f=-20.0)
        rows.append([bname, label, float(dg['ADH']), float(contact_barrier_kT(dg, R))])
bs = pd.DataFrame(rows, columns=["bacterium", "substrate", "dG_ADH", "barrier_kT"])
bs.round(3).to_csv(os.path.join(OUT, "bacteria_on_films_stable.csv"), index=False, encoding="utf-8-sig")
print(bs.round(1).to_string(index=False))

# ---------- 3) fig1：新鲜 vs 稳定期均值±SD
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), sharey=True)
x = np.arange(len(SURF_ORDER))
w = 0.2
for ax, mode in zip(axes, ("fresh", "stable")):
    for i, prot in enumerate(PROT_ORDER):
        if mode == "fresh":
            vals = [float(mat[(mat.surface == s) & (mat.protein == prot) & (mat.day == 0)].dG_ADH.iloc[0])
                    for s in SURF_ORDER]
            errs = None
            title = "Fresh (day 0)"
        else:
            vals = [float(sta[(sta.surface == s) & (sta.protein == prot)].dG_ADH_mean.iloc[0])
                    for s in SURF_ORDER]
            errs = [float(sta[(sta.surface == s) & (sta.protein == prot)].dG_ADH_std.iloc[0])
                    for s in SURF_ORDER]
            title = "Final stable period (days 49-73, mean ± SD, n=4)"
        ax.bar(x + (i - 1.5) * w, vals, w, color=COLORS[i], label=prot,
               yerr=errs, capsize=2.5, error_kw=dict(lw=0.8, ecolor="#555555"))
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(SURF_ORDER)
    ax.set_title(title, fontsize=10)
    ax.set_ylabel("ΔG_ADH  (mJ m$^{-2}$)")
    ax.grid(axis="y", alpha=0.25)
axes[0].legend(fontsize=8, frameon=False)
fig.suptitle("Protein adhesion free energy on 515 nm laser-textured 316L — body-fluid conditions (37 °C, 0.15 M)",
             fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig(os.path.join(OUT, "fig1_dGADH_matrix.png"), dpi=300)
plt.close(fig)
print("fig1 rewritten")

# ---------- 4) fig3：U(h) —— 左=day 0，右=稳定期（平均表面能）
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), sharey=True)
for ax, (label, mse) in zip(axes, [("day 0  (fresh)", surf_se("LIPSS", 0)),
                                   ("stable period  (days 49-73)", stable_se("LIPSS"))]):
    for i, prot in enumerate(PROT_ORDER):
        (g, R, z) = PROT_PARAMS[prot]
        dg = delta_g(mse, se(g), I_M, T_K, zeta_m=-25.0, zeta_f=z)
        prof = interaction_energy(mse, se(g), dg, R, I_M, T_K, zeta_m=-25.0, zeta_f=z)
        ax.plot(np.asarray(prof["h"], dtype=float), np.asarray(prof["TOT"], dtype=float),
                "-", lw=1.6, color=COLORS[i], label=prot)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xscale("log")
    ax.set_xlim(0.1, 30)
    ax.set_ylim(-220, 180)
    ax.set_xlabel("Separation distance  h (nm, log scale)")
    ax.set_title(f"LIPSS — {label}", fontsize=10)
    ax.grid(alpha=0.25, which="both")
axes[0].set_ylabel("Interaction energy  U(h)  (kT)")
axes[0].legend(fontsize=8, frameon=False)
fig.suptitle("U(h) profiles on LIPSS in body-fluid conditions (37 °C, 0.15 M)", fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig(os.path.join(OUT, "fig3_uh_profiles.png"), dpi=300)
plt.close(fig)
print("fig3 rewritten")

# ---------- 5) 摘要数字
li = sta[(sta.surface == "LIPSS") & (sta.protein == "Fibrinogen (human)")]
print("\n稳定期汇总（ΔG_ADH mJ/m² / 势垒 kT）:")
print(sta.round(2).to_string(index=False))
print("\nLIPSS 稳定期表面能:", stable_se("LIPSS"))
print("\n关键区间: ΔG_ADH 均值范围",
      f"{sta.dG_ADH_mean.min():.2f} … {sta.dG_ADH_mean.max():.2f} mJ/m²",
      "| 势垒均值范围", f"{sta.barrier_kT_mean.min():.1f} … {sta.barrier_kT_mean.max():.1f} kT")
print("DONE")
