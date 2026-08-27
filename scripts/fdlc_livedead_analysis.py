# -*- coding: utf-8 -*-
"""
F-DLC LIVE/DEAD 荧光计数分析 (LabToolbox 版)
=============================================
输入: Live_Dead Bacteria Test/F-DLC/ 文件夹下的计数 csv
  F-DLC/{2%F-DLC|5%F-DLC|8%F-DLC}/{日期}/live_dead_counts_*.csv
  文件名: {time}-{g|r}{num}.tif  (time=1/3/5h), c{time}-{g|r}{num}.tif = Control
  配对: g 图绿通道=活菌, r 图红通道=死菌 (同一 time+num 为一对视野)
口径: 与 F-DLC_stats_fixed.R 一致
  - 每重复 5 视野取平均 -> 每组每时间 n=重复数 (Control 跨浓度合并)
  - CFU/cm² 换算: count * 1e8 / 46946.10
  - log10 转换后双因素 ANOVA (Group × Time), 逐时间点 one-way + Tukey
输出: summary / anova / tukey 表格 + 堆叠柱状图
"""
import os
import re
import glob
import sys

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd

# 复用 labtoolbox 工具
sys.path.insert(0, r"E:\LabToolbox")
from labtoolbox.common.io_utils import ensure_output_dir, save_csv, save_figure

AREA_UM2 = 46946.10
SCALE = 1e8 / AREA_UM2  # count -> CFU/cm²
FNAME_RE = re.compile(r"^c?(\d+)-([gr])(\d+)$", re.IGNORECASE)
GROUPS = ["Control", "2% F-DLC", "5% F-DLC", "8% F-DLC"]
TIMES = ["1h", "3h", "5h"]


def parse_fname(fname):
    m = FNAME_RE.match(os.path.splitext(fname)[0].strip())
    if not m:
        return None
    time = f"{m.group(1)}h"
    ch = m.group(2).lower()
    num = int(m.group(3))
    ctrl = fname.strip().lower().startswith("c")
    return time, ch, num, ctrl


def load_all_csvs(base):
    """读取 F-DLC 全部计数 csv, 配对 g/r, 返回长表。"""
    rows = []
    skipped = []
    for grp_dir in ["2%F-DLC", "5%F-DLC", "8%F-DLC"]:
        group = {"2%F-DLC": "2% F-DLC", "5%F-DLC": "5% F-DLC", "8%F-DLC": "8% F-DLC"}[grp_dir]
        for csv_path in sorted(glob.glob(os.path.join(base, grp_dir, "*", "*.csv"))):
            rep = os.path.basename(os.path.dirname(csv_path))
            df = pd.read_csv(csv_path)
            df.columns = [c.strip() for c in df.columns]
            live_col, dead_col = df.columns[1], df.columns[2]
            # 按 (ctrl, time, num) 配对 g/r
            pairs = {}
            for _, r in df.iterrows():
                fname = str(r.iloc[0]).strip()
                parsed = parse_fname(fname)
                if not parsed:
                    skipped.append(f"{grp_dir}/{rep}: {fname!r}")
                    continue
                time, ch, num, ctrl = parsed
                pairs.setdefault((ctrl, time, num), {})[ch] = (r[live_col], r[dead_col])
            for (ctrl, time, num), chd in sorted(pairs.items()):
                if "g" not in chd or "r" not in chd:
                    skipped.append(f"{grp_dir}/{rep}: ({time},{num}) 缺 {'g' if 'g' not in chd else 'r'} 通道")
                    continue
                g_live, g_dead = chd["g"]
                r_live, r_dead = chd["r"]
                rows.append({
                    "group": "Control" if ctrl else group,
                    "source": grp_dir,
                    "time": time, "rep": rep, "area": num,
                    "live": g_live, "dead": r_dead,
                    "total": g_live + r_dead,
                })
    raw = pd.DataFrame(rows)
    return raw, skipped


def build_rep_df(raw):
    """每 (group, time, rep) 5 视野取平均 -> 每重复一行。"""
    rep = raw.groupby(["group", "source", "time", "rep"])[["live", "dead"]].mean().reset_index()
    rep["total"] = rep["live"] + rep["dead"]
    rep["live_cm2"] = rep["live"] * SCALE
    rep["dead_cm2"] = rep["dead"] * SCALE
    rep["total_cm2"] = rep["total"] * SCALE
    rep["logLive"] = np.log10(rep["live_cm2"] + 1)
    rep["logTotal"] = np.log10(rep["total_cm2"] + 1)
    return rep


def summary_table(rep):
    """每组×时间 均值±SD (CFU/cm²), 死亡率, n。"""
    out = []
    for (g, t), sub in rep.groupby(["group", "time"]):
        out.append({
            "group": g, "time": t, "n": len(sub),
            "live_mean": sub["live_cm2"].mean(),
            "live_sd": sub["live_cm2"].std(ddof=1) if len(sub) > 1 else np.nan,
            "dead_mean": sub["dead_cm2"].mean(),
            "dead_sd": sub["dead_cm2"].std(ddof=1) if len(sub) > 1 else np.nan,
            "total_mean": sub["total_cm2"].mean(),
            "total_sd": sub["total_cm2"].std(ddof=1) if len(sub) > 1 else np.nan,
            "dead_rate": sub["dead"].sum() / (sub["live"].sum() + sub["dead"].sum()),
            "viability_pct": sub["live"].sum() / (sub["live"].sum() + sub["dead"].sum()) * 100,
        })
    return pd.DataFrame(out)


def two_way_anova(rep, value_col, groups, times):
    """双因素 ANOVA: log10(value) ~ Group * Time (Type III)。"""
    from statsmodels.formula.api import ols
    import statsmodels.api as sm
    data = rep[rep["group"].isin(groups) & rep["time"].isin(times)].copy()
    data["group"] = pd.Categorical(data["group"], categories=groups, ordered=False)
    data["time"] = pd.Categorical(data["time"], categories=times, ordered=False)
    model = ols(f"{value_col} ~ C(group) * C(time)", data=data).fit()
    aov = sm.stats.anova_lm(model, typ=3)
    return aov.reset_index().rename(columns={"index": "factor"})


def per_time_anova_tukey(rep, value_col, groups, times):
    """逐时间点 one-way ANOVA + Tukey (返回每个时间点的结果行)。"""
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    out = []
    for t in times:
        sub = rep[(rep["time"] == t) & (rep["group"].isin(groups))].copy()
        if sub["group"].nunique() < 2:
            continue
        import scipy.stats as st
        grps = [sub.loc[sub["group"] == g, value_col].dropna() for g in groups if g in sub["group"].values]
        grps = [g for g in grps if len(g) > 0]
        if len(grps) < 2:
            continue
        f, p = st.f_oneway(*grps)
        # Tukey 仅对 ≥3 组做
        tuk_rows = []
        if len(grps) >= 3:
            tuk = pairwise_tukeyhsd(sub[value_col], sub["group"])
            for row in tuk.summary().data[1:]:
                tuk_rows.append({
                    "pair": f"{row[0]}-{row[1]}",
                    "meandiff": row[2], "p_adj": row[3],
                })
        out.append({"time": t, "n_groups": len(grps), "F": f, "p": p, "tukey": tuk_rows})
    return out


def sig_stars(p):
    if p is None or p >= 0.05:
        return "ns"
    if p < 0.0001:
        return "****"
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    return "*"


def plot_stacked(rep, summary, out_dir, groups, times, anova_live, anova_total, tukey_by_time=None):
    """堆叠柱状图: Control/2%/5%/8% × 1h/3h/5h, CFU/cm², 显著性括号。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for fp in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
        if os.path.exists(fp):
            font_manager.fontManager.addfont(fp)
            break

    plt.rcParams["font.family"] = "Microsoft YaHei"
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(11, 6.2))
    colors_live = "#00ba38"
    colors_dead = "#f8766d"
    n_times = len(times)
    width = 0.32

    x_pos = {}
    for gi, g in enumerate(groups):
        for ti, t in enumerate(times):
            row = summary[(summary["group"] == g) & (summary["time"] == t)]
            if row.empty:
                continue
            r = row.iloc[0]
            x = gi * (n_times + 0.8) + ti * 0.9
            x_pos[(g, t)] = x
            ax.bar(x, r["dead_mean"], width=width, color=colors_dead, edgecolor="black", linewidth=0.6,
                   yerr=r["dead_sd"], error_kw=dict(elinewidth=0.8, capsize=2))
            ax.bar(x, r["live_mean"], width=width, bottom=r["dead_mean"], color=colors_live,
                   edgecolor="black", linewidth=0.6,
                   yerr=r["live_sd"], error_kw=dict(elinewidth=0.8, capsize=2))

    # 显著性括号: 每个时间点, 各 F-DLC 组 vs Control (基于 logLive Tukey p)
    # 从 per_time ANOVA + Tukey 结果取 p_adj
    p_lookup = {}
    if tukey_by_time:
        for pt in tukey_by_time:
            for tr in pt["tukey"]:
                p_lookup[(pt["time"], tr["pair"])] = tr["p_adj"]

    brackets = []
    for t in times:
        for g in ["2% F-DLC", "5% F-DLC", "8% F-DLC"]:
            if (g, t) in x_pos and ("Control", t) in x_pos:
                pair = f"{g}-Control"
                p_adj = p_lookup.get((t, pair))
                brackets.append((t, g, x_pos[("Control", t)], x_pos[(g, t)], p_adj))

    ymax = summary["total_mean"].max() + summary["total_sd"].max()
    if np.isnan(ymax):
        ymax = 1
    step = ymax * 0.10
    used = {}
    for ti, t in enumerate(times):
        level = 0
        for (bt, bg, x1, x2, p_adj) in brackets:
            if bt != t:
                continue
            y = ymax * 1.05 + level * step
            used.setdefault(t, 0)
            used[t] += 1
            level = used[t]
            ax.plot([x1, x2], [y, y], color="black", lw=1.0)
            label = sig_stars(p_adj)
            ax.text((x1 + x2) / 2, y + step * 0.15, label, ha="center",
                    fontsize=10 if label != "ns" else 8, fontweight="bold")

    # 组标签
    for gi, g in enumerate(groups):
        xs = [x for (gg, _), x in x_pos.items() if gg == g]
        if xs:
            ax.text(np.mean(xs), -ymax * 0.09, g, ha="center", fontsize=11, fontweight="bold")

    # ANOVA 标注
    p_live = None
    p_total = None
    if anova_live is not None:
        r = anova_live[anova_live["factor"] == "C(group)"]
        if len(r):
            p_live = r.iloc[0]["PR(>F)"]
    if anova_total is not None:
        r = anova_total[anova_total["factor"] == "C(group)"]
        if len(r):
            p_total = r.iloc[0]["PR(>F)"]
    annot = ""
    if p_live is not None and p_total is not None:
        annot = f"Two-way ANOVA (log10): Group p = {p_total:.2e} (Total), p = {p_live:.2e} (Live)"
    if annot:
        ax.text(0.5, 0.96, annot, transform=ax.transAxes, ha="center",
                fontsize=10, fontstyle="italic")

    ax.set_xticks([])
    ax.set_ylabel("Number of adhered bacteria (CFU/cm²)", fontsize=12)
    ax.set_ylim(0, ymax * 1.7)
    ax.tick_params(direction="in")
    # 时间刻度: 每组下的 1h/3h/5h
    for gi, g in enumerate(groups):
        xs = [x_pos[(g, t)] for t in times if (g, t) in x_pos]
        labels = [t for t in times if (g, t) in x_pos]
        if xs:
            ax.set_xticks(xs, minor=True)
            ax.set_xticklabels(labels, minor=True, fontsize=9)
    ax.legend(handles=[
        plt.Rectangle((0, 0), 1, 1, color=colors_live, label="Live (green)"),
        plt.Rectangle((0, 0), 1, 1, color=colors_dead, label="Dead (red)"),
    ], loc="upper left", frameon=False, fontsize=10)
    plt.tight_layout()
    path = save_figure(fig, os.path.join(out_dir, "F-DLC_livedead_counts.png"), dpi=300)
    plt.close(fig)
    return path, brackets


def main():
    base = r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_Antibacterial Surfaces\Live_Dead Bacteria Test\F-DLC"
    out_dir = ensure_output_dir(r"E:\LabToolbox\output\F-DLC_analysis")

    raw, skipped = load_all_csvs(base)
    print(f"读入配对视野: {len(raw)} 对; 跳过: {len(skipped)} 条")
    for s in skipped:
        print("  ⚠", s)
    raw.to_csv(os.path.join(out_dir, "F-DLC_raw_pairs.csv"), index=False, encoding="utf-8-sig")

    rep = build_rep_df(raw)
    print(f"\n每重复一行 (group×time×rep): {len(rep)} 行")

    # Control 口径: 与 R 脚本一致, 只合并 2%/8% 两个 sheet 的 control (n=6)
    rep_main = rep[~((rep["group"] == "Control") & (rep["source"].isin(["5%F-DLC"])))].copy()
    rep_main = rep_main.drop(columns=["source"])
    # 5% 数据不完整 (2026.8.5 仅部分时间点), 单独存原始行供查看
    rep_5 = rep[rep["group"] == "5% F-DLC"].copy()
    rep_5.to_csv(os.path.join(out_dir, "F-DLC_5percent_rep_data.csv"), index=False, encoding="utf-8-sig")

    summ = summary_table(rep_main)
    summ.to_csv(os.path.join(out_dir, "F-DLC_summary.csv"), index=False, encoding="utf-8-sig")

    # 主分析: 2%/8% (数据完整), Control 合并
    main_groups = ["Control", "2% F-DLC", "8% F-DLC"]
    aov_live = two_way_anova(rep_main, "logLive", main_groups, TIMES)
    aov_total = two_way_anova(rep_main, "logTotal", main_groups, TIMES)
    aov_live.to_csv(os.path.join(out_dir, "F-DLC_ANOVA_Live.csv"), index=False, encoding="utf-8-sig")
    aov_total.to_csv(os.path.join(out_dir, "F-DLC_ANOVA_Total.csv"), index=False, encoding="utf-8-sig")

    per_time = per_time_anova_tukey(rep_main, "logLive", main_groups, TIMES)
    tukey_rows = []
    for pt in per_time:
        for tr in pt["tukey"]:
            tukey_rows.append({"time": pt["time"], **tr})
    pd.DataFrame(tukey_rows).to_csv(os.path.join(out_dir, "F-DLC_Tukey_Live.csv"), index=False, encoding="utf-8-sig")

    fig_path, brackets = plot_stacked(rep_main, summ, out_dir, main_groups, TIMES,
                                      aov_live, aov_total, per_time)

    # 打印结果
    print("\n================ 汇总表 (CFU/cm²) ================")
    disp = summ.copy()
    disp["live"] = disp.apply(lambda r: f"{r['live_mean']:,.0f}±{r['live_sd']:,.0f}", axis=1)
    disp["dead"] = disp.apply(lambda r: f"{r['dead_mean']:,.0f}±{r['dead_sd']:,.0f}", axis=1)
    disp["total"] = disp.apply(lambda r: f"{r['total_mean']:,.0f}±{r['total_sd']:,.0f}", axis=1)
    disp["存活率%"] = disp["viability_pct"].round(1)
    print(disp[["group", "time", "n", "live", "dead", "total", "存活率%"]].to_string(index=False))
    print("\n================ 双因素 ANOVA: logTotal ================")
    print(aov_total.to_string(index=False))
    print("\n================ 双因素 ANOVA: logLive ================")
    print(aov_live.to_string(index=False))
    print("\n================ 逐时间点 ANOVA (logLive) ================")
    for pt in per_time:
        sig = "✅" if pt["p"] < 0.05 else "ns"
        print(f"  {pt['time']}: F={pt['F']:.3f}, p={pt['p']:.4f} {sig}")
        for tr in pt["tukey"]:
            mark = "✅" if tr["p_adj"] < 0.05 else ""
            print(f"      {tr['pair']}: p_adj={tr['p_adj']:.4f} {mark}")
    print(f"\n图: {fig_path}")
    print(f"输出目录: {out_dir}")


if __name__ == "__main__":
    main()
