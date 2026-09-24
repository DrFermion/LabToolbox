# -*- coding: utf-8 -*-
"""
bsa_sample_level_weighting.py — BSA 蛋白吸附预测: 三个区间面积加权 → "整片"数值 (任务①)

输入: xdlvo_515nm_dG.csv 的表面能序列 (Control/LIPSS/Nanopillar × 天数)
     + BSA 参数 (PMC4286104) → van Oss ΔG_ADH + Derjaguin 接触能量 (kT/蛋白)
输出: 逐区间 × 逐天 CSV; 面积加权 (默认等面积三分, 另给两组敏感性情景) 汇总 CSV + 图.
⚠️ 面积分数为假设值 (等分), 拿到真实分区尺寸后一改即重算.
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, r"E:\LabToolbox")
from labtoolbox.xdlvo.xdlvo import delta_g, SurfaceEnergy              # noqa: E402

OUT = r"E:\LabToolbox\output\bsa_sample_level_20260924"
os.makedirs(OUT, exist_ok=True)
DG_CSV = r"E:\LabToolbox\output\xdlvo_515nm_20260912\xdlvo_515nm_dG.csv"
KT = 1.380649e-23 * 298.15
NM = 1e-9
H0 = 0.158 * NM
LAM = 0.6 * NM

BSA = SurfaceEnergy(40.6, 1.16, 20.03, 2 * np.sqrt(1.16 * 20.03), 40.6 + 2 * np.sqrt(1.16 * 20.03))
R_BSA = 3.5

SCENARIOS = {
    "equal thirds": {"Control 316L": 1 / 3, "LIPSS": 1 / 3, "Nanopillar": 1 / 3},
    "control-heavy": {"Control 316L": 0.50, "LIPSS": 0.25, "Nanopillar": 0.25},
    "treated-heavy": {"Control 316L": 0.20, "LIPSS": 0.40, "Nanopillar": 0.40},
}


def u_contact_kT(dG):
    R = R_BSA * NM
    u = (2 * np.pi * R * dG["LW"] * 1e-3 * H0 + 2 * np.pi * R * LAM * dG["AB"] * 1e-3)
    return u / KT


def main():
    raw = pd.read_csv(DG_CSV, encoding="utf-8-sig")
    surf = raw.drop_duplicates(["surface", "day"])[["surface", "day", "gamma_LW", "gamma_plus", "gamma_minus"]]

    rows = []
    for _, r in surf.iterrows():
        se = SurfaceEnergy(r["gamma_LW"], r["gamma_plus"], r["gamma_minus"],
                           2 * np.sqrt(r["gamma_plus"] * r["gamma_minus"]),
                           r["gamma_LW"] + 2 * np.sqrt(r["gamma_plus"] * r["gamma_minus"]))
        dg = delta_g(se, BSA, 0.15)
        rows.append({"surface": r["surface"], "day": r["day"],
                     "gamma_minus": r["gamma_minus"],
                     "dG_LW": dg["LW"], "dG_AB": dg["AB"], "dG_ADH": dg["ADH"],
                     "U_contact_kT": u_contact_kT(dg)})
    per = pd.DataFrame(rows).sort_values(["surface", "day"])
    per.to_csv(os.path.join(OUT, "bsa_per_zone_by_day.csv"), index=False, encoding="utf-8-sig")

    # 只在三天数齐备的天数上做加权
    piv = per.pivot_table(index="day", columns="surface", values="dG_ADH")
    piv = piv.dropna()
    wrows = []
    for day, r in piv.iterrows():
        d = {"day": day, "dG_Control": r["Control 316L"], "dG_LIPSS": r["LIPSS"], "dG_Nanopillar": r["Nanopillar"]}
        for sname, w in SCENARIOS.items():
            d[f"dG_weighted[{sname}]"] = sum(w[s] * r[s] for s in w)
        wrows.append(d)
    wdf = pd.DataFrame(wrows)
    wdf.to_csv(os.path.join(OUT, "bsa_sample_level_weighted.csv"), index=False, encoding="utf-8-sig")

    # 图: 三区间 ΔG vs 天 + 加权线 (等分)
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    colors = {"Control 316L": "#7F7F7F", "LIPSS": "#4C72B0", "Nanopillar": "#8172B3"}
    labels = {"Control 316L": "Control", "LIPSS": "LIPSS", "Nanopillar": "Nanopillar"}
    for s in ("Control 316L", "LIPSS", "Nanopillar"):
        ax.plot(per[per.surface == s]["day"], per[per.surface == s]["dG_ADH"], "-o", ms=3,
                color=colors[s], label=labels[s])
    ax.plot(wdf["day"], wdf["dG_weighted[equal thirds]"], "-", color="black", lw=2.2,
            label="area-weighted (equal thirds)")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("Day after laser processing")
    ax.set_ylabel("BSA contact free energy  ΔG_ADH  (mJ/m²)")
    ax.set_title("BSA adsorption tendency on the 515 nm coupon — zone values and area-weighted sample value\n"
                 "(positive = repulsive / barrier;  negative = attractive;  equal-area weighting assumed)",
                 fontsize=10.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=9)
    ax.tick_params(direction="in")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_bsa_sample_level_vs_day.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

    print("逐区间数据:", os.path.join(OUT, "bsa_per_zone_by_day.csv"))
    print("加权汇总:", os.path.join(OUT, "bsa_sample_level_weighted.csv"))
    print(wdf.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
