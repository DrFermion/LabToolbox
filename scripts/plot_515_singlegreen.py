# -*- coding: utf-8 -*-
"""
plot_515_singlegreen.py — 515nm 单绿染总菌计数: 汇总图 + 统计检验 (BH 校正) + 融合度诊断图

数据源:
  imagej_counts/singlegreen_raw.csv          (计数, 含 excluded 列)
  imagej_counts/singlegreen_geometry.csv     (几何诊断, big_frac/cover_pct — 可选)
图:
  singlegreen_by_region.png            两种菌 × 4 时间点 × 3 区域 (control/LIPSS/Nanopillar)
                                       柱=mean±SD cells/cm², 散点=各视野
  singlegreen_reduction_vs_control.png 相对 control 的变化率 (%) + BH 校正显著性
  singlegreen_merge_diagnostic.png     >500px 融合团块占信号比例 (计数低估风险诊断)
统计:
  singlegreen_stats.csv  每组 n/mean/sd + 两两 Mann-Whitney + BH 校正 + 相对 control 变化率
颜色: 中性灰/蓝/紫 (红绿只用于死活语义, 此处不碰)
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from scipy import stats

try:
    from statsmodels.stats.multitest import multipletests
    HAVE_SM = True
except Exception:
    HAVE_SM = False

for fp in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
    if os.path.exists(fp):
        font_manager.fontManager.addfont(fp)
        break

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_"
        r"Antibacterial Surfaces\Live_Dead Bacteria Test\515-singlegreen")
OUT = os.path.join(BASE, "imagej_counts")
RAW = os.path.join(OUT, "singlegreen_raw.csv")
GEO = os.path.join(OUT, "singlegreen_geometry.csv")

SPECIES = ["E.coli", "S.aureus"]
SP_LABEL = {"E.coli": "E. coli", "S.aureus": "S. aureus"}
TIMES = ["3h", "6h", "8h", "24h"]
REGIONS = [("c", "control", "#7F7F7F"), ("1", "LIPSS", "#4C72B0"), ("2", "Nanopillar", "#8172B3")]


def stars(p):
    if not np.isfinite(p):
        return ""
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"


def main():
    df = pd.read_csv(RAW, encoding="utf-8-sig")
    excluded = df["excluded"].fillna(False).astype(bool)
    clean = df[~excluded].copy()
    print(f"读入 {len(df)} 视野, 剔除饱和图 {int(excluded.sum())} → 干净 {len(clean)} 视野")

    # ---------- 统计 ----------
    rows = []
    for sp in SPECIES:
        for t in TIMES:
            sub = clean[(clean["species"] == sp) & (clean["time"] == t)]
            d = {}
            for r, lab, _ in REGIONS:
                v = sub[sub["region"] == r]["total_per_cm2"].values
                d[f"n_{lab}"] = len(v)
                d[f"mean_{lab}"] = v.mean() if len(v) else np.nan
                d[f"sd_{lab}"] = v.std(ddof=1) if len(v) > 1 else np.nan
            g = {r: sub[sub["region"] == r]["count"].values for r, _, _ in REGIONS}

            def pv(a, b):
                if len(a) < 2 or len(b) < 2:
                    return np.nan
                return stats.mannwhitneyu(a, b, alternative="two-sided")[1]

            d["p_control_vs_LIPSS"] = pv(g["c"], g["1"])
            d["p_control_vs_Nanopillar"] = pv(g["c"], g["2"])
            d["p_LIPSS_vs_Nanopillar"] = pv(g["1"], g["2"])
            d["reduction_LIPSS_pct"] = ((d["mean_LIPSS"] - d["mean_control"]) / d["mean_control"] * 100
                                        if d["mean_control"] else np.nan)
            d["reduction_Nanopillar_pct"] = ((d["mean_Nanopillar"] - d["mean_control"]) / d["mean_control"] * 100
                                             if d["mean_control"] else np.nan)
            rows.append({"species": sp, "time": t, **d})
    stat_df = pd.DataFrame(rows)

    pcols = ["p_control_vs_LIPSS", "p_control_vs_Nanopillar", "p_LIPSS_vs_Nanopillar"]
    flat = stat_df[pcols].values.ravel()
    mask = ~np.isnan(flat)
    if HAVE_SM and mask.any():
        adj = np.full_like(flat, np.nan, dtype=float)
        adj[mask] = multipletests(flat[mask], method="fdr_bh")[1]
        adj = adj.reshape(stat_df[pcols].shape)
        for j, c in enumerate(pcols):
            stat_df[c + "_BH"] = adj[:, j]
    else:
        for c in pcols:
            stat_df[c + "_BH"] = stat_df[c]
    stat_df.to_csv(os.path.join(OUT, "singlegreen_stats.csv"), index=False, encoding="utf-8-sig")
    print("\n统计表 (BH 校正):")
    print(stat_df[["species", "time", "reduction_LIPSS_pct", "reduction_Nanopillar_pct",
                   "p_control_vs_LIPSS_BH", "p_control_vs_Nanopillar_BH"]].round(3).to_string(index=False))

    # ---------- Fig 1: 按区域 ----------
    fig, axes = plt.subplots(2, 1, figsize=(7.4, 8.6))
    rng = np.random.default_rng(7)
    for ax, sp in zip(axes, SPECIES):
        width = 0.24
        x = np.arange(len(TIMES))
        for j, (r, lab, col) in enumerate(REGIONS):
            means, sds = [], []
            for t in TIMES:
                v = clean[(clean.species == sp) & (clean.time == t) & (clean.region == r)]["total_per_cm2"].values
                means.append(v.mean() if len(v) else np.nan)
                sds.append(v.std(ddof=1) if len(v) > 1 else 0)
                pos = x[TIMES.index(t)] + (j - 1) * width
                if len(v):
                    ax.scatter(np.full(len(v), pos) + rng.uniform(-0.045, 0.045, len(v)), v,
                               s=10, c="black", alpha=0.4, zorder=3, linewidths=0)
            ax.bar(x + (j - 1) * width, means, yerr=sds, capsize=3, width=width,
                   color=col, edgecolor="black", linewidth=0.7, error_kw=dict(elinewidth=1.0),
                   label=lab)
        st = stat_df[stat_df.species == sp].set_index("time")
        ymax = 0.0
        for t in TIMES:
            top = max(st.loc[t, f"mean_{lab}"] + (st.loc[t, f"sd_{lab}"] if np.isfinite(st.loc[t, f"sd_{lab}"]) else 0)
                      for _, lab, _ in REGIONS if np.isfinite(st.loc[t, f"mean_{lab}"]))
            ymax = max(ymax, top)
        ax.set_ylim(0, ymax * 1.22)
        # 星号贴在各自柱顶 (而不是漂浮在统一高度), 避免与图例/相邻元素相碰
        for i, t in enumerate(TIMES):
            for j, pcol in ((1, "p_control_vs_LIPSS_BH"), (2, "p_control_vs_Nanopillar_BH")):
                p = st.loc[t, pcol]
                if np.isfinite(p) and p < 0.05:
                    lab2 = REGIONS[j][1]
                    top2 = st.loc[t, f"mean_{lab2}"] + (st.loc[t, f"sd_{lab2}"]
                                                        if np.isfinite(st.loc[t, f"sd_{lab2}"]) else 0)
                    ax.text(i + (j - 1) * width, top2 + 0.022 * ymax, stars(p),
                            ha="center", va="bottom", fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels(TIMES, fontsize=11)
        ax.set_ylabel("Total attached bacteria (cells/cm$^2$)", fontsize=11)
        ax.set_title(f"{SP_LABEL[sp]} — 515 nm single green stain (repeat 1,\nSYTO9 only → total attached count)",
                     fontsize=11, fontweight="bold")
        ax.tick_params(direction="in")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(frameon=False, fontsize=9,
                  loc=("upper right" if sp == "E.coli" else "upper left"))
        ax.ticklabel_format(style="sci", scilimits=(0, 0), axis="y")
    fig.tight_layout(h_pad=3.0)
    p1 = os.path.join(OUT, "singlegreen_by_region.png")
    fig.savefig(p1, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("已保存:", p1)

    # ---------- Fig 2: 相对 control 变化率 ----------
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 4.8), sharey=True)
    up_max, dn_min = 0.0, 0.0
    for ax, sp in zip(axes, SPECIES):
        width = 0.36
        x = np.arange(len(TIMES))
        st = stat_df[stat_df.species == sp].set_index("time")
        for j, (lab, col, pcol) in enumerate((
                ("LIPSS", "#4C72B0", "p_control_vs_LIPSS_BH"),
                ("Nanopillar", "#8172B3", "p_control_vs_Nanopillar_BH"))):
            vals = [st.loc[t, f"reduction_{lab}_pct"] for t in TIMES]
            ps = [st.loc[t, pcol] for t in TIMES]
            pos = x + (j - 0.5) * width
            ax.bar(pos, vals, width=width, color=col, edgecolor="black", linewidth=0.7, label=lab)
            for xi, v, p in zip(pos, vals, ps):
                if np.isfinite(v):
                    # 标签横向向外错开 + 显著星与数值标签分层, 防止相邻标签相碰
                    xl = xi + (j - 0.5) * 0.11
                    ax.text(xl, v + (2.5 if v >= 0 else -2.5), f"{v:+.0f}%", ha="center",
                            va="bottom" if v >= 0 else "top", fontsize=8.5)
                    if np.isfinite(p) and p < 0.05:
                        ax.text(xl, v + (10 if v >= 0 else -10), stars(p), ha="center",
                                va="bottom" if v >= 0 else "top", fontsize=11)
                    up_max = max(up_max, v + (22 if v >= 0 else 0))
                    dn_min = min(dn_min, v - (22 if v < 0 else 0))
        ax.axhline(0, color="black", lw=0.9)
        ax.set_xticks(x)
        ax.set_xticklabels(TIMES, fontsize=11)
        ax.set_title(SP_LABEL[sp], fontsize=12, fontweight="bold")
        ax.tick_params(direction="in")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].set_ylim(dn_min - 12, up_max + 12)
    axes[0].set_ylabel("Change vs control (% of control density)", fontsize=11)
    axes[0].legend(frameon=False, fontsize=9, loc="best")
    fig.suptitle("515 nm single green stain — change vs control region "
                 "(negative = fewer attached bacteria)\nrepeat 1 · BH-adjusted Mann-Whitney: * p<0.05, ** p<0.01",
                 fontsize=10.5, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    p2 = os.path.join(OUT, "singlegreen_reduction_vs_control.png")
    fig.savefig(p2, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("已保存:", p2)

    # ---------- Fig 3: 融合度诊断 ----------
    if os.path.exists(GEO):
        geo = pd.read_csv(GEO, encoding="utf-8-sig")
        fig, axes = plt.subplots(2, 1, figsize=(7.4, 7.4))
        for ax, sp in zip(axes, SPECIES):
            width = 0.24
            x = np.arange(len(TIMES))
            for j, (r, lab, col) in enumerate(REGIONS):
                vals = []
                for t in TIMES:
                    v = geo[(geo.species == sp) & (geo.time == t) & (geo.region == r)]["big_frac"].values
                    vals.append(np.nanmean(v) if len(v) else np.nan)
                ax.bar(x + (j - 1) * width, vals, width=width, color=col,
                       edgecolor="black", linewidth=0.7, label=lab)
            ax.set_xticks(x)
            ax.set_xticklabels(TIMES, fontsize=11)
            ax.set_ylim(0, 1.0)
            ax.set_ylabel("Fraction of signal in\n>500 px merged clumps", fontsize=11)
            ax.set_title(f"{SP_LABEL[sp]} — merged-clump diagnostic "
                         "(high = counts are lower bounds)", fontsize=11, fontweight="bold")
            ax.tick_params(direction="in")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.legend(frameon=False, fontsize=9, loc="upper left")
        fig.tight_layout(h_pad=2.2)
        p3 = os.path.join(OUT, "singlegreen_merge_diagnostic.png")
        fig.savefig(p3, dpi=200, bbox_inches="tight")
        plt.close(fig)
        print("已保存:", p3)
    else:
        print("(无 geometry CSV, 跳过诊断图)")


if __name__ == "__main__":
    main()
