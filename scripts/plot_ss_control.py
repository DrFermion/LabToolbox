# -*- coding: utf-8 -*-
"""
plot_ss_control.py — ss-control 单绿染总菌柱状图 (mean ± SD, 标 P 值)

数据源: ss-control/imagej_counts/ss_control_raw.csv (含 repeat/time/outlier 列)
纵轴: total bacteria (cells/cm²) — 40X 视野面积 46946.10 µm² 归一化
检验: 3h vs 5h Mann-Whitney U (非参数, 小样本偏态稳健) + Welch t-test
颜色: 中性蓝紫 (不碰红/绿 — 红绿只表示死活, 见 livedead 技能硬规则)

输出:
  ss_control_bar.png            3 个 repeat 合并的 3h vs 5h
  ss_control_bar_by_repeat.png  逐 repeat 分组 (每 repeat 两根柱 + 视野散点)
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from scipy import stats

# 中文字体 (备用, 本图用英文标签)
for fp in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
    if os.path.exists(fp):
        font_manager.fontManager.addfont(fp)
        break

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_"
        r"Antibacterial Surfaces\Live_Dead Bacteria Test\ss-control")
RAW = os.path.join(BASE, "imagej_counts", "ss_control_raw.csv")
OUT_POOLED = os.path.join(BASE, "imagej_counts", "ss_control_bar.png")
OUT_BYREP = os.path.join(BASE, "imagej_counts", "ss_control_bar_by_repeat.png")

ORDER = ["3h", "5h"]
COLORS = ["#4C72B0", "#8172B3"]   # 蓝 / 紫 (中性, 非红绿)
REP_COLORS = ["#4C72B0", "#55A868", "#8172B3"]  # 每个 repeat 一色 (绿仅作图例区分, 非死活语义)


def stars(p):
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


def stat_pair(a, b):
    if len(a) < 2 or len(b) < 2:
        return np.nan, np.nan
    _, p_mw = stats.mannwhitneyu(a, b, alternative="two-sided")
    _, p_t = stats.ttest_ind(a, b, equal_var=False)
    return p_mw, p_t


def plot_pooled(df):
    means, sds, ns = [], [], []
    for t in ORDER:
        dens = df[df["time"] == t]["total_per_cm2"].values
        means.append(dens.mean())
        sds.append(dens.std(ddof=1))
        ns.append(len(dens))
    p_mw, p_t = stat_pair(df[df["time"] == "3h"]["count"].values,
                          df[df["time"] == "5h"]["count"].values)

    fig, ax = plt.subplots(figsize=(4.6, 5.4))
    x = np.arange(len(ORDER))
    ax.bar(x, means, yerr=sds, capsize=6, width=0.55,
           color=COLORS, edgecolor="black", linewidth=0.8,
           error_kw=dict(elinewidth=1.2))
    # 单个视野散点 (半透明黑点, 显示分布)
    for i, t in enumerate(ORDER):
        v = df[df["time"] == t]["total_per_cm2"].values
        ax.scatter(np.full(len(v), i) + np.random.uniform(-0.13, 0.13, len(v)), v,
                   s=12, c="black", alpha=0.45, zorder=3, linewidths=0)

    ax.set_ylabel("Total bacteria (cells/cm$^2$)", fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{t}\n(n = {n})" for t, n in zip(ORDER, ns)], fontsize=13)
    ax.set_title("SS-control: total attached bacteria\n(single green stain, 3 repeats pooled)",
                 fontsize=12, fontweight="bold")
    ax.tick_params(direction="in")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ymax = max(m + s for m, s in zip(means, sds))
    ax.set_ylim(0, ymax * 1.35)
    bar_y, line_y = ymax * 1.06, ymax * 1.14
    ax.plot([x[0], x[0], x[1], x[1]], [bar_y, line_y, line_y, bar_y], lw=1.2, c="black")
    label = f"p = {p_mw:.4g} {stars(p_mw)}" if np.isfinite(p_mw) else "p = n/a"
    ax.text((x[0] + x[1]) / 2, line_y, label, ha="center", va="bottom", fontsize=12)
    ax.text(0.02, 0.98,
            (f"Mann-Whitney U: p = {p_mw:.4g}\nWelch t-test: p = {p_t:.4g}"
             if np.isfinite(p_mw) else "insufficient n"),
            transform=ax.transAxes, ha="left", va="top", fontsize=9, color="0.35")

    plt.tight_layout()
    plt.savefig(OUT_POOLED, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("已保存:", OUT_POOLED)
    print(f"  3h: {means[0]:.0f} ± {sds[0]:.0f} cells/cm² (n={ns[0]})")
    print(f"  5h: {means[1]:.0f} ± {sds[1]:.0f} cells/cm² (n={ns[1]})")
    print(f"  Mann-Whitney U p={p_mw:.4g}  Welch t p={p_t:.4g}")


def plot_by_repeat(df):
    reps = sorted(df["repeat"].unique())
    fig, ax = plt.subplots(figsize=(7.6, 5.4))
    width = 0.26
    x = np.arange(len(reps))
    ymax = 0.0
    for j, t in enumerate(ORDER):
        means, sds, ns = [], [], []
        for rep in reps:
            dens = df[(df["repeat"] == rep) & (df["time"] == t)]["total_per_cm2"].values
            means.append(dens.mean() if len(dens) else np.nan)
            sds.append(dens.std(ddof=1) if len(dens) > 1 else 0)
            ns.append(len(dens))
        pos = x + (j - 0.5) * width
        ax.bar(pos, means, yerr=sds, capsize=4, width=width,
               color=COLORS[j], edgecolor="black", linewidth=0.7,
               error_kw=dict(elinewidth=1.1), label=t)
        for i, rep in enumerate(reps):
            v = df[(df["repeat"] == rep) & (df["time"] == t)]["total_per_cm2"].values
            ax.scatter(np.full(len(v), pos[i]) + np.random.uniform(-0.03, 0.03, len(v)), v,
                       s=9, c="black", alpha=0.4, zorder=3, linewidths=0)
        ymax = max(ymax, max(m + s for m, s in zip(means, sds)))

    # 每个 repeat 上方的显著性 (3h vs 5h)
    for i, rep in enumerate(reps):
        a = df[(df["repeat"] == rep) & (df["time"] == "3h")]["count"].values
        b = df[(df["repeat"] == rep) & (df["time"] == "5h")]["count"].values
        p, _ = stat_pair(a, b)
        if np.isfinite(p):
            ax.text(x[i], ymax * 1.05, f"{stars(p)}\np={p:.3g}",
                    ha="center", va="bottom", fontsize=9)

    ax.set_ylabel("Total bacteria (cells/cm$^2$)", fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r}\n(3h n={len(df[(df['repeat']==r)&(df['time']=='3h')])}, "
                        f"5h n={len(df[(df['repeat']==r)&(df['time']=='5h')])})" for r in reps],
                       fontsize=10)
    ax.set_title("SS-control: total attached bacteria by repeat\n(single green stain)",
                 fontsize=12, fontweight="bold")
    ax.set_ylim(0, ymax * 1.28)
    ax.tick_params(direction="in")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(title="Incubation", frameon=False, loc="upper right")

    plt.tight_layout()
    plt.savefig(OUT_BYREP, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("已保存:", OUT_BYREP)


def main():
    df = pd.read_csv(RAW, encoding="utf-8-sig")
    clean = df[~df["outlier"]].copy()
    print(f"读入 {len(df)} 视野, 剔除离群值 {int(df['outlier'].sum())} → 干净 {len(clean)} 视野")
    plot_pooled(clean)
    plot_by_repeat(clean)


if __name__ == "__main__":
    main()
