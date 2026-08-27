# -*- coding: utf-8 -*-
"""
F-DLC LIVE/DEAD 荧光图像重新计数 (2026-08-25)
=============================================
主人指示: 忽略旧 CSV (live_dead_counts_*.csv), 直接从原始 .tif 重新计数。

文件夹结构:
  F-DLC/{浓度%F-DLC}/{日期}/xxx.tif       (每个日期文件夹 = 1 个 repeat)
文件名格式: {前缀}-{g|r}{视场}.tif
  前缀: 1/3/5 = 1h/3h/5h;  c1/c3/c5 = Control 对应时间点
  通道: g = 绿 (活菌), r = 红 (死菌);  视场: 1-5

配对逻辑: 同一 (时间, 视场) 的 g/r 图是同一视野两通道
  live = g 图绿色通道计数,  dead = r 图红色通道计数

统计口径 (对齐 F-DLC_stats_fixed.R):
  每个 repeat 的 5 个视场取平均 → rep 级数据
  双因素 ANOVA: log10(live+1) / log10(total+1) ~ Group * Time
  逐时间点单因素 ANOVA + Tukey (Control vs 各浓度, 用 logLive)
  换算 CFU/cm²: area_um2 = 46946.10 µm², scale = 1e8/area_um2
"""
import os
import re
import sys
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
sys.path.insert(0, r"E:\LabToolbox")

from labtoolbox.livedead_cellcounter.cellcounter import CellCounterEngine

ROOT = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - "
        r"Ruinong Pan_Antibacterial Surfaces\Live_Dead Bacteria Test\F-DLC")
OUT = r"E:\LabToolbox\output\F-DLC_recount_20260825"
AREA_UM2 = 46946.10
SCALE = 1e8 / AREA_UM2

# 计数参数: 2%F-DLC 真实图实测宽松参数 (见 labtoolbox 技能)
ENGINE_KW = dict(min_size=4, min_roundness=0.4, green_thresh=15,
                 red_thresh=15, min_channel_ratio=1.0)

# 2026.8.5 只有 1h 有效数据 (2-*/3-* 是废弃文件, xlsx 中对应 3h/5h 全空)
DATE_PREFIX_OVERRIDE = {"2026.8.5": {"1", "c1"}}

TIME_MAP = {"1": "1h", "3": "3h", "5": "5h"}
FILE_RE = re.compile(r"^(c?)([135])-(g|r)(\d+)\.tif$", re.I)


def parse_fname(fname):
    m = FILE_RE.match(fname.lower())
    if not m:
        return None
    ctrl, t, ch, field = m.group(1) == "c", m.group(2), m.group(3), int(m.group(4))
    return ctrl, TIME_MAP[t], ch, field


def main():
    engine = CellCounterEngine(**ENGINE_KW)
    os.makedirs(OUT, exist_ok=True)

    rows = []
    skipped_files = []
    total_imgs = 0
    done = 0
    raw_csv_path = os.path.join(OUT, "livedead_raw_counts.csv")
    use_cache = os.path.exists(raw_csv_path) and os.path.getsize(raw_csv_path) > 0

    if use_cache:
        print(f"[缓存] 复用已有原始计数: {raw_csv_path}")

    conc_dirs = sorted([d for d in os.listdir(ROOT)
                        if os.path.isdir(os.path.join(ROOT, d))])
    for conc in conc_dirs:
        conc_path = os.path.join(ROOT, conc)
        date_dirs = sorted([d for d in os.listdir(conc_path)
                            if os.path.isdir(os.path.join(conc_path, d))])
        for rep_i, date in enumerate(date_dirs, start=1):
            date_path = os.path.join(conc_path, date)
            allow = DATE_PREFIX_OVERRIDE.get(date)
            imgs = {}
            for fname in sorted(os.listdir(date_path)):
                if not fname.lower().endswith(".tif"):
                    continue
                parsed = parse_fname(fname)
                if not parsed:
                    skipped_files.append((conc, date, fname))
                    continue
                ctrl, t, ch, field = parsed
                prefix = fname.split("-")[0].lower()
                if allow and prefix not in allow:
                    skipped_files.append((conc, date, fname))
                    continue
                key = (ctrl, t, field)
                imgs.setdefault(key, {})[ch] = os.path.join(date_path, fname)
                total_imgs += 1

            if use_cache:
                continue
            for (ctrl, t, field), ch_imgs in sorted(imgs.items()):
                g_img = ch_imgs.get("g")
                r_img = ch_imgs.get("r")
                live = dead = np.nan
                if g_img:
                    live = engine.count_live_dead(g_img)["green"]
                if r_img:
                    dead = engine.count_live_dead(r_img)["red"]
                done += 1
                if done % 50 == 0:
                    print(f"  [进度] {done} 对 / 总计约 {len(imgs) * len(conc_dirs)} 对", flush=True)
                rows.append({
                    "concentration": conc, "date": date, "repeat": rep_i,
                    "time": t, "condition": "Control" if ctrl else "F-DLC",
                    "field": field,
                    "g_image": os.path.basename(g_img) if g_img else "",
                    "r_image": os.path.basename(r_img) if r_img else "",
                    "live": live, "dead": dead,
                })

    if use_cache:
        raw = pd.read_csv(raw_csv_path)
    else:
        raw = pd.DataFrame(rows)
    raw["total"] = raw["live"] + raw["dead"]
    raw["dead_rate"] = raw["dead"] / raw["total"].replace(0, np.nan)
    raw["group"] = np.where(raw["condition"] == "Control", "Control",
                            raw["concentration"].str.replace("%F-DLC", "% F-DLC", regex=False))

    print(f"\n共处理 {len(raw)} 个视野对, 跳过 {len(skipped_files)} 个非标准文件: {skipped_files}")
    print(raw.groupby(["group", "time"]).size().unstack(fill_value=0))

    raw.to_csv(raw_csv_path, index=False, encoding="utf-8-sig")

    # ===== rep 级: 每个 repeat 的 5 个视场取平均 =====
    rep_df = (raw.dropna(subset=["live", "dead"])
              .groupby(["concentration", "date", "repeat", "time", "condition"])
              [["live", "dead", "total"]].mean().reset_index())
    rep_df["group"] = np.where(rep_df["condition"] == "Control", "Control",
                               rep_df["concentration"].str.replace("%F-DLC", "% F-DLC", regex=False))
    for c in ["live", "dead", "total"]:
        rep_df[f"{c}_cm2"] = rep_df[c] * SCALE
        rep_df[f"log10_{c}"] = np.log10(rep_df[f"{c}_cm2"] + 1)

    # ===== 汇总表 (field 级) =====
    summ = (raw.dropna(subset=["live", "dead"])
            .groupby(["group", "time"])
            .agg(n_fields=("live", "count"),
                 n_repeats=("repeat", "nunique"),
                 live_mean=("live", "mean"), live_sd=("live", "std"),
                 dead_mean=("dead", "mean"), dead_sd=("dead", "std"),
                 total_mean=("total", "mean"), total_sd=("total", "std"),
                 live_pooled=("live", "sum"), dead_pooled=("dead", "sum"))
            .reset_index())
    summ["viability_pct"] = (summ["live_pooled"] /
                             (summ["live_pooled"] + summ["dead_pooled"]) * 100)
    for c in ["live_sd", "dead_sd", "total_sd"]:
        summ[c] = summ[c].fillna(0)

    # rep 级汇总 (CFU/cm²)
    summ_cm2 = (rep_df.groupby(["group", "time"])
                .agg(n=("repeat", "count"),
                     live_cm2_mean=("live_cm2", "mean"), live_cm2_sd=("live_cm2", "std"),
                     dead_cm2_mean=("dead_cm2", "mean"), dead_cm2_sd=("dead_cm2", "std"),
                     total_cm2_mean=("total_cm2", "mean"), total_cm2_sd=("total_cm2", "std"))
                .reset_index())
    for c in ["live_cm2_sd", "dead_cm2_sd", "total_cm2_sd"]:
        summ_cm2[c] = summ_cm2[c].fillna(0)

    summ.to_csv(os.path.join(OUT, "livedead_summary.csv"), index=False, encoding="utf-8-sig")
    summ_cm2.to_csv(os.path.join(OUT, "livedead_summary_cm2.csv"), index=False, encoding="utf-8-sig")

    # ===== 统计分析 =====
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
    from statsmodels.stats.multicomp import pairwise_tukeyhsd

    anova_rows = []
    for metric in ["live", "total"]:
        d = rep_df.dropna(subset=[f"log10_{metric}"]).copy()
        d["group"] = pd.Categorical(d["group"])
        d["time"] = pd.Categorical(d["time"])
        model = ols(f"log10_{metric} ~ C(group) * C(time)", data=d).fit()
        aov = sm.stats.anova_lm(model, typ=2).reset_index().rename(columns={"index": "factor"})
        aov.insert(0, "metric", metric)
        anova_rows.append(aov)
    anova_df = pd.concat(anova_rows, ignore_index=True)

    # 逐时间点单因素 ANOVA + Tukey (logLive, Control vs 各浓度)
    tuk_rows = []
    oneway_rows = []
    for t in ["1h", "3h", "5h"]:
        sub = rep_df[rep_df["time"] == t].dropna(subset=["log10_live"])
        grps = [g for g in ["Control", "2% F-DLC", "5% F-DLC", "8% F-DLC"]
                if (sub["group"] == g).any()]
        if len(grps) >= 2:
            from scipy import stats
            f, p = stats.f_oneway(*[sub.loc[sub["group"] == g, "log10_live"] for g in grps])
            oneway_rows.append({"time": t, "metric": "live",
                                "groups": "+".join(grps), "F": f, "p": p})
        if len(grps) >= 3:
            tuk = pairwise_tukeyhsd(sub["log10_live"], sub["group"])
            for row in tuk.summary().data[1:]:
                g1, g2 = row[0], row[1]
                if g1 == "Control" or g2 == "Control":
                    ctrl_g, trt_g = (g1, g2) if g1 == "Control" else (g2, g1)
                    tuk_rows.append({"time": t, "metric": "live",
                                     "control": ctrl_g, "treatment": trt_g,
                                     "meandiff_log10": float(row[2]),
                                     "p_adj": float(row[3])})
    oneway_df = pd.DataFrame(oneway_rows)
    tuk_df = pd.DataFrame(tuk_rows)

    anova_df.to_csv(os.path.join(OUT, "livedead_anova.csv"), index=False, encoding="utf-8-sig")
    oneway_df.to_csv(os.path.join(OUT, "livedead_oneway_anova.csv"), index=False, encoding="utf-8-sig")
    tuk_df.to_csv(os.path.join(OUT, "livedead_tukey_vs_control.csv"), index=False, encoding="utf-8-sig")

    # ===== 柱状图 (CFU/cm², 对齐 R 图) =====
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    groups_order = ["Control", "2% F-DLC", "5% F-DLC", "8% F-DLC"]
    times = ["1h", "3h", "5h"]

    def stars(p):
        if pd.isna(p) or p >= 0.05:
            return "ns"
        if p < 0.0001:
            return "****"
        if p < 0.001:
            return "***"
        if p < 0.01:
            return "**"
        return "*"

    tuk_map = {(r["time"], r["treatment"]): r["p_adj"] for _, r in tuk_df.iterrows()}

    x_pos = {}
    x = 0.0
    for g in groups_order:
        for t in times:
            x_pos[(g, t)] = x
            x += 1.0
        x += 0.8

    fig, ax = plt.subplots(figsize=(11, 6.5))
    colors_live, colors_dead = "#00ba38", "#f8766d"
    bar_w = 0.62

    for g in groups_order:
        for t in times:
            row = summ_cm2[(summ_cm2["group"] == g) & (summ_cm2["time"] == t)]
            if row.empty:
                continue
            r = row.iloc[0]
            xc = x_pos[(g, t)]
            ax.bar(xc, r["dead_cm2_mean"], width=bar_w, color=colors_dead,
                   edgecolor="black", linewidth=0.5)
            ax.bar(xc, r["live_cm2_mean"], width=bar_w, bottom=r["dead_cm2_mean"],
                   color=colors_live, edgecolor="black", linewidth=0.5)
            ax.errorbar(xc, r["dead_cm2_mean"] + r["live_cm2_mean"],
                        yerr=r["total_cm2_sd"], fmt="none", ecolor="black",
                        elinewidth=1, capsize=3)

    # 显著性连线: Control vs 各浓度 (per time, logLive Tukey)
    ymax = summ_cm2["total_cm2_mean"].max() + summ_cm2["total_cm2_sd"].max()
    ytop = ymax * 1.06
    step = ymax * 0.10
    for t in times:
        for trt in ["2% F-DLC", "5% F-DLC", "8% F-DLC"]:
            p = tuk_map.get((t, trt))
            if p is None:
                continue
            x1 = x_pos[("Control", t)] - bar_w / 2
            x2 = x_pos[(trt, t)] + bar_w / 2
            yl = ytop + step * (["2% F-DLC", "5% F-DLC", "8% F-DLC"].index(trt))
            ax.plot([x1, x2], [yl, yl], color="black", lw=1)
            ax.text((x1 + x2) / 2, yl + ymax * 0.02, stars(p),
                    ha="center", fontsize=10, fontweight="bold")

    ax.set_xticks([x_pos[(g, "1h")] + 1.0 for g in groups_order])
    ax.set_xticklabels(groups_order, fontsize=12)
    for g in groups_order:
        for ti, t in enumerate(times):
            ax.text(x_pos[(g, t)], -ymax * 0.06, t, ha="center", fontsize=9)
    ax.set_ylabel("Number of adhered bacteria (CFU/cm²)", fontsize=13)
    ax.set_title("LIVE/DEAD Fluorescence Counts (recounted from raw images, 2026-08-25)",
                 fontsize=13, fontweight="bold")
    ax.tick_params(direction="in")
    ax.set_ylim(-ymax * 0.14, ytop + step * 2.6)
    ax.legend(handles=[
        plt.Rectangle((0, 0), 1, 1, color=colors_live, label="Live (green)"),
        plt.Rectangle((0, 0), 1, 1, color=colors_dead, label="Dead (red)"),
    ], loc="upper right", frameon=False)
    plt.tight_layout()
    fig_path = os.path.join(OUT, "F-DLC_livedead_recount.png")
    fig.savefig(fig_path, dpi=300)
    plt.close(fig)

    print("\n===== 双因素 ANOVA (log10, rep级) =====")
    print(anova_df.to_string(index=False))
    print("\n===== 逐时间点 one-way ANOVA (logLive) =====")
    print(oneway_df.to_string(index=False) if not oneway_df.empty else "空")
    print("\n===== Tukey Control vs 浓度 (logLive) =====")
    print(tuk_df.to_string(index=False) if not tuk_df.empty else "空")
    print(f"\n✅ 完成! 输出目录: {OUT}")
    print(f"   图: {fig_path}")


if __name__ == "__main__":
    main()
