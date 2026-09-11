# -*- coding: utf-8 -*-
"""
recount_ss_control_imagej.py — ss-control 单绿染总菌计数 (ImageJ 引擎) + MAD 离群值筛选 + QC 排查图

背景 (2026-09-10 首版, 2026-09-11 扩展到多 repeat):
LIVE/DEAD 实验的 ss-control (不锈钢对照, SS control)。
此实验只使用单绿色染剂 (SYTO9 单染, 无 PI), 染色所有细菌 → 统计总菌数 (不分死活)。
文件名是纯数字 {n}.tif (无 -g/-r 通道后缀), 信号在绿色通道 (R/B 通道几乎无信号,
但 Rmax=255 为噪点像素, 会骗过宏的"命名通道"判断)。

方案: 临时把 {n}.tif 复制为 {n}-g.tif 让宏走绿色通道, 计数后映射回原文件名。
方法学: 与 515nm 一致 — 自适应阈值 (背景众数+40) + Analyze Particles 3-500px。
视野面积 (40X): 46946.10 µm² → 密度 cells/cm² = count/µm² × 1e8。

QC 排查图: 宏参数第 3 行 = qcDir → 每张被计数图存 <stem>_qc.png (绿 LUT 底色 +
蓝色圈 + 蓝编号标每个被计数粒子), 用于人工排查 0/漏数/多圈。

离群值筛选: 每个 repeat × 时间点组内, |x - median| > k × MAD 的视野标记为离群值踢出
(MAD = median absolute deviation, 稳健; k 默认 5)。

输出: ss-control/imagej_counts/
  ss_control_raw.csv            逐视野计数 (repeat/time/num/count/曝光/outlier/mad_mult)
  ss_control_summary.csv        按时间点汇总 (3 个 repeat 合并, 剔除离群值后)
  ss_control_summary_by_repeat.csv  按 repeat × 时间点汇总
  qc/<repeat>/<time>/<n>_qc.png 每张图的 QC 排查图
"""
import os
import re
import csv
import glob
import shutil
import subprocess
import tempfile

import numpy as np
import pandas as pd
import tifffile

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_"
        r"Antibacterial Surfaces\Live_Dead Bacteria Test\ss-control")
AREA_UM2 = 46946.10
OUT = os.path.join(BASE, "imagej_counts")
QC_ROOT = os.path.join(OUT, "qc")
REPEATS = ("repeat 1", "repeat 2", "repeat 3")
TIMES = ("3h", "5h")
MAD_K = 5.0  # 离群值阈值: |x - median| > k * MAD

IMAGEJ_DIR = r"F:/ImageJ/ImageJ"
MACRO_INST = os.path.join(IMAGEJ_DIR, "macros", "count_livedead.ijm")
MACRO_REPO = r"E:/LabToolbox/scripts/imagej/count_livedead.ijm"
JAVA = os.path.join(IMAGEJ_DIR, "jre", "bin", "java.exe")
IJ_JAR = os.path.join(IMAGEJ_DIR, "ij.jar")


def macro_path():
    if os.path.exists(MACRO_INST):
        return MACRO_INST
    if os.path.exists(MACRO_REPO):
        return MACRO_REPO
    raise FileNotFoundError(f"ImageJ 宏不存在: {MACRO_INST} / {MACRO_REPO}")


def exposure_seconds(p):
    """从 ImageDescription 提取曝光秒数 (Exposure: 000 : 00 : 01 . 200 : 012 -> 1.2)"""
    t = tifffile.TiffFile(p)
    d = t.pages[0].tags.get("ImageDescription")
    t.close()
    v = d.value if d else ""
    m = re.search(r"Exposure:\s*000 : 00 : (\d+) \. (\d+)", v)
    return float(f"{m.group(1)}.{m.group(2)}") if m else np.nan


def run_imagej(input_dir, out_csv, qc_dir):
    """直接调用 ImageJ 宏 (3 行 UTF-8 参数文件: inputDir / outputCSV / qcDir)"""
    if os.path.exists(out_csv):  # 宏用 File.append 追加, 必须先清掉旧文件
        os.remove(out_csv)
    macro = macro_path()
    if not os.path.exists(JAVA) or not os.path.exists(IJ_JAR):
        raise FileNotFoundError(f"ImageJ 未安装完整: {IMAGEJ_DIR} (需 ij.jar + jre/bin/java.exe)")
    fd, args_path = tempfile.mkstemp(suffix=".txt", prefix="ij_args_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(input_dir.replace("\\", "/") + "\n")
        f.write(out_csv.replace("\\", "/") + "\n")
        f.write((qc_dir.replace("\\", "/") if qc_dir else "") + "\n")
    env = dict(os.environ, JAVA_TOOL_OPTIONS="-Dfile.encoding=UTF-8")
    cmd = [JAVA, "-cp", IJ_JAR, "ij.ImageJ", "-batch", macro, args_path]
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True,
                              text=True, timeout=1800)
    finally:
        try:
            os.unlink(args_path)
        except OSError:
            pass
    if not os.path.exists(out_csv):
        raise RuntimeError("ImageJ 无输出: " + (proc.stderr[-500:] if proc.stderr else ""))
    with open(out_csv, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def count_time_dir(time_dir, out_csv, qc_dir):
    """复制 {n}.tif -> {n}-g.tif 到临时目录, 跑 ImageJ (带 QC), 返回 (rows, mapping)"""
    tmp = tempfile.mkdtemp(prefix="ssctl_")
    mapping = {}
    files = sorted(
        glob.glob(os.path.join(time_dir, "*.tif")),
        key=lambda x: int(re.search(r"(\d+)\.tif$", x).group(1)),
    )
    for p in files:
        n = int(re.search(r"(\d+)\.tif$", p).group(1))
        dst = os.path.join(tmp, f"{n}-g.tif")
        shutil.copy2(p, dst)
        mapping[f"{n}-g.tif"] = (os.path.basename(p), p)
    os.makedirs(qc_dir, exist_ok=True)
    try:
        rows = run_imagej(tmp, out_csv, qc_dir)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # QC 图重命名: {n}-g_qc.png -> {n}_qc.png (映射回原始文件名)
    for fn in os.listdir(qc_dir):
        m = re.match(r"^(\d+)-g_qc\.png$", fn)
        if m:
            os.rename(os.path.join(qc_dir, fn),
                      os.path.join(qc_dir, f"{m.group(1)}_qc.png"))
    return rows, mapping


def mad_outliers(values, k=MAD_K):
    """返回布尔 mask (True=离群值), 及每个值的 MAD 倍数。稳健, 不被离群值本身拉偏。"""
    values = np.asarray(values, dtype=float)
    med = np.median(values)
    mad = np.median(np.abs(values - med))
    if mad == 0:
        return np.zeros(len(values), dtype=bool), np.zeros(len(values))
    mult = np.abs(values - med) / mad
    return mult > k, mult


def main():
    os.makedirs(OUT, exist_ok=True)
    all_rows = []
    for rep in REPEATS:
        for tp in TIMES:
            time_dir = os.path.join(BASE, rep, tp)
            if not os.path.isdir(time_dir) or not glob.glob(os.path.join(time_dir, "*.tif")):
                print(f"\n=== {rep}/{tp}: 目录为空, 跳过 ===")
                continue
            tag = rep.replace(" ", "_")
            out_csv = os.path.join(OUT, f"_{tag}_{tp}_imagej.csv")
            qc_dir = os.path.join(QC_ROOT, rep, tp)
            rows, mapping = count_time_dir(time_dir, out_csv, qc_dir)
            n_qc = len([f for f in os.listdir(qc_dir) if f.endswith("_qc.png")])
            print(f"\n=== {rep}/{tp}: {len(rows)} 张计数, {n_qc} 张 QC 图 ===")
            for r in rows:
                fn = r["filename"]
                orig, orig_path = mapping[fn]
                exp = exposure_seconds(orig_path)
                cnt = int(float(r["count"]))
                all_rows.append({
                    "repeat": rep,
                    "time": tp,
                    "num": int(re.search(r"(\d+)\.tif$", orig).group(1)),
                    "count": cnt,
                    "chan_used": r["chan_used"],
                    "bg": int(float(r["bg"])),
                    "thresh": int(float(r["thresh"])),
                    "roi_count": int(float(r["roi_count"])),
                    "exposure_s": exp,
                    "total_per_cm2": cnt / AREA_UM2 * 1e8,
                })
                print(f"  {rep}/{tp}/{orig}: chan={r['chan_used']:<12} count={cnt:>5} "
                      f"exposure={exp:.1f}s  bg={r['bg']}")
    df = pd.DataFrame(all_rows)

    # 通道正确性检查
    bad = df[df["chan_used"] != "green"]
    if len(bad):
        print(f"\n⚠️ 警告: {len(bad)} 张图没走 green 通道:")
        print(bad[["repeat", "time", "num", "chan_used", "count"]].to_string(index=False))
    else:
        print("\n✅ 全部走 green 通道")

    # ROI 泄漏检查
    leak = df[df["count"] != df["roi_count"]]
    print(f"✅ ROI 一致性: {'全部 count==roi_count' if not len(leak) else f'⚠️ {len(leak)} 张不一致'}")

    # ---- MAD 离群值筛选 (repeat × time 组内) ----
    df["outlier"] = False
    df["mad_mult"] = 0.0
    print(f"\n=== MAD 离群值筛选 (|x - median| > {MAD_K}×MAD, 每个 repeat×time 组内) ===")
    for (rep, t), grp in df.groupby(["repeat", "time"]):
        mask, mult = mad_outliers(grp["count"].values, k=MAD_K)
        df.loc[grp.index, "outlier"] = mask
        df.loc[grp.index, "mad_mult"] = mult
        med = np.median(grp["count"].values)
        mad = np.median(np.abs(grp["count"].values - med))
        outs = grp[mask]
        print(f"{rep}/{t}: n={len(grp)} median={med:.0f} MAD={mad:.0f} "
              f"阈值={MAD_K * mad:.0f} → 踢出 {len(outs)} 张")
        for (_, o), m in zip(outs.iterrows(), mult[mask]):
            print(f"    ❌ {rep}/{t}/{o['num']}.tif: count={o['count']} "
                  f"(偏差 {o['count'] - med:+.0f} = {m:.1f}×MAD)")

    df.to_csv(os.path.join(OUT, "ss_control_raw.csv"), index=False, encoding="utf-8-sig")
    clean = df[~df["outlier"]]

    # 按 repeat × time 汇总
    by_rep = clean.groupby(["repeat", "time"]).agg(
        n=("count", "count"),
        count_mean=("count", "mean"),
        count_sd=("count", "std"),
        cm2_mean=("total_per_cm2", "mean"),
        cm2_sd=("total_per_cm2", "std"),
    ).reset_index()
    # 每个组的原始图数 (用于 n_removed 列)
    raw_n = df.groupby(["repeat", "time"]).size().rename("n_raw").reset_index()
    by_rep = by_rep.merge(raw_n, on=["repeat", "time"], how="left")
    by_rep["n_removed"] = by_rep["n_raw"] - by_rep["n"]
    by_rep = by_rep[["repeat", "time", "n", "n_removed", "count_mean", "count_sd",
                     "cm2_mean", "cm2_sd"]]
    by_rep.to_csv(os.path.join(OUT, "ss_control_summary_by_repeat.csv"),
                  index=False, encoding="utf-8-sig")

    # 合并 3 个 repeat 的时间点汇总
    summ = clean.groupby("time").agg(
        n=("count", "count"),
        count_mean=("count", "mean"),
        count_sd=("count", "std"),
        cm2_mean=("total_per_cm2", "mean"),
        cm2_sd=("total_per_cm2", "std"),
    ).reset_index()
    summ["n_removed"] = df.groupby("time").size().reindex(summ["time"]).values - summ["n"]
    summ = summ[["time", "n", "n_removed", "count_mean", "count_sd", "cm2_mean", "cm2_sd"]]
    summ.to_csv(os.path.join(OUT, "ss_control_summary.csv"),
                index=False, encoding="utf-8-sig")

    print("\n按 repeat × 时间点汇总 (total bacteria, 离群值已剔除):")
    print(by_rep.round(1).to_string(index=False))
    print("\n3 个 repeat 合并汇总:")
    print(summ.round(1).to_string(index=False))

    # 3h vs 5h 统计检验 (干净数据, 合并)
    from scipy import stats
    g3 = clean[clean["time"] == "3h"]["count"].values
    g5 = clean[clean["time"] == "5h"]["count"].values
    u, up = stats.mannwhitneyu(g3, g5, alternative="two-sided")
    t, tp = stats.ttest_ind(g3, g5, equal_var=False)
    print(f"\n合并 3h (n={len(g3)}, mean={g3.mean():.1f}±{g3.std(ddof=1):.1f}) vs "
          f"5h (n={len(g5)}, mean={g5.mean():.1f}±{g5.std(ddof=1):.1f})")
    print(f"Mann-Whitney U: p={up:.4f}   Welch t-test: p={tp:.4f}")

    # 每个 repeat 内部的 3h vs 5h
    print("\n逐 repeat 的 3h vs 5h (Mann-Whitney U):")
    for rep in REPEATS:
        a = clean[(clean["repeat"] == rep) & (clean["time"] == "3h")]["count"].values
        b = clean[(clean["repeat"] == rep) & (clean["time"] == "5h")]["count"].values
        if len(a) > 1 and len(b) > 1:
            _, p = stats.mannwhitneyu(a, b, alternative="two-sided")
            print(f"  {rep}: 3h {a.mean():.1f}±{a.std(ddof=1):.1f} (n={len(a)}) vs "
                  f"5h {b.mean():.1f}±{b.std(ddof=1):.1f} (n={len(b)}) → p={p:.4f}")

    # QC 图计数
    n_qc_total = 0
    for rep in REPEATS:
        for tp in TIMES:
            d = os.path.join(QC_ROOT, rep, tp)
            if os.path.isdir(d):
                n_qc_total += len([f for f in os.listdir(d) if f.endswith("_qc.png")])
    print(f"\nQC 排查图总数: {n_qc_total} 张 (count>0 才生成)")
    print(f"\n输出目录: {OUT}")
    print("  ss_control_raw.csv / ss_control_summary.csv / ss_control_summary_by_repeat.csv")
    print("  qc/<repeat>/<time>/<n>_qc.png")


if __name__ == "__main__":
    main()
