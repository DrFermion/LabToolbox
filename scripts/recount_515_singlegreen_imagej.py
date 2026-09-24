# -*- coding: utf-8 -*-
"""
recount_515_singlegreen_imagej.py — 515nm 单绿染 (SYTO9 单染, 无 PI) 总菌计数 (ImageJ 引擎)

数据集: Live_Dead Bacteria Test/515-singlegreen/
  结构: <species>/<repeat>/<time>/<region>-<n>.tif
  species ∈ {E.coli, S.aureus};  repeat ∈ {repeat 1..3};  time ∈ {3h, 6h, 8h, 24h}
  region ∈ {c=control, 1=LIPSS, 2=Nanopillar} (同一块样品的三个处理区)
单绿染 = 只染 SYTO9 无 PI → 计的是总附着菌数 (不分死活)。

文件名无 -g/-r 后缀 → 复制为 {region}-{n}-g.tif 强制宏走绿通道, 计数后映射回原名。
方法学与 ss-control / 515nm 一致: 自适应阈值 (背景众数+40) + Analyze Particles 3-500px。
视野面积 (40X): 46946.10 µm² → density [cells/cm²] = count/µm² × 1e8。

筛查政策 (2026-09-24, 本数据集专用 — 与 ss-control 的强制 k=5×MAD 修剪不同):
  · 剔除: 仅阈值失效图 (直方图众数 bg≥250 → bg+40>255, count=0 为假零), 例 S.aureus/24h/2-3。
  · MAD 只作诊断列 (mad_mult / mad_flag), 不强制剔除 —— 本数据集多组视野高度均匀
    (5×MAD 低至中位数的 5~15%, 强制修剪会丢掉 ±15% 内的正常视野, 如 8h LIPSS 组);
    且经 QC 与几何诊断, 被标记视野均未见伪影特征 (尺寸分布正常, 大团块在同组未标记视野同样存在)。
  · 融合度诊断 (big_frac/cover_pct) 由 diagnose_515_singlegreen.py 单独输出:
    大团块 (>500px) 占比高的组, 计数是下界, 报告已注明。

输出 (BASE/imagej_counts/):
  singlegreen_raw.csv                逐视野 (含 mad_mult/mad_flag/excluded/exclude_reason)
  singlegreen_summary_by_region.csv  species×repeat×time×region 汇总 (剔除饱和图后)
  qc/<species>/<repeat>/<time>/<region>-<n>_qc.png

用法:
  python recount_515_singlegreen_imagej.py                 # 全量
  python recount_515_singlegreen_imagej.py --filter "E.coli/repeat 1/3h" --smoke
"""
import os
import re
import csv
import glob
import shutil
import argparse
import subprocess
import tempfile

import numpy as np
import pandas as pd
import tifffile

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_"
        r"Antibacterial Surfaces\Live_Dead Bacteria Test\515-singlegreen")
AREA_UM2 = 46946.10
SPECIES = ("E.coli", "S.aureus")
REPEATS = ("repeat 1", "repeat 2", "repeat 3")
TIMES = ("3h", "6h", "8h", "24h")
REGIONS = ("c", "1", "2")                     # 样品上的三个处理区
REGION_LABEL = {"c": "control", "1": "LIPSS", "2": "Nanopillar"}
MAD_K = 5.0
SATURATION_BG = 250   # 直方图众数 ≥ 此值 → bg+40 阈值失效

IMAGEJ_DIR = r"F:/ImageJ/ImageJ"
MACRO_INST = os.path.join(IMAGEJ_DIR, "macros", "count_livedead.ijm")
MACRO_REPO = r"E:/LabToolbox/scripts/imagej/count_livedead.ijm"
JAVA = os.path.join(IMAGEJ_DIR, "jre", "bin", "java.exe")
IJ_JAR = os.path.join(IMAGEJ_DIR, "ij.jar")

FNAME_RE = re.compile(r"^([c12])-(\d+)\.tif$", re.IGNORECASE)


def macro_path():
    if os.path.exists(MACRO_INST):
        return MACRO_INST
    if os.path.exists(MACRO_REPO):
        return MACRO_REPO
    raise FileNotFoundError(f"ImageJ 宏不存在: {MACRO_INST} / {MACRO_REPO}")


def exposure_seconds(p):
    """从 ImageDescription 提取曝光秒数 (Exposure: 000 : 00 : 00 . 800 : 012 -> 0.8)"""
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
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)
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
    """复制 {region}-{n}.tif -> {region}-{n}-g.tif 到临时目录, 跑 ImageJ, 返回 (rows, mapping)"""
    tmp = tempfile.mkdtemp(prefix="sgreen_")
    mapping = {}
    files = sorted(
        (p for p in glob.glob(os.path.join(time_dir, "*.tif")) if FNAME_RE.match(os.path.basename(p))),
        key=lambda p: (REGIONS.index(FNAME_RE.match(os.path.basename(p)).group(1).lower()),
                       int(FNAME_RE.match(os.path.basename(p)).group(2))),
    )
    for p in files:
        m = FNAME_RE.match(os.path.basename(p))
        region, num = m.group(1).lower(), int(m.group(2))
        dst = os.path.join(tmp, f"{region}-{num}-g.tif")
        shutil.copy2(p, dst)
        mapping[f"{region}-{num}-g.tif"] = (os.path.basename(p), p, region, num)
    os.makedirs(qc_dir, exist_ok=True)
    # 清理上次遗留的 QC 图, 防止重跑时重命名冲突
    for fn in os.listdir(qc_dir):
        if fn.endswith("_qc.png"):
            try:
                os.remove(os.path.join(qc_dir, fn))
            except OSError:
                pass
    try:
        rows = run_imagej(tmp, out_csv, qc_dir)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # QC 图重命名: <region>-<n>-g_qc.png -> <region>-<n>_qc.png
    for fn in os.listdir(qc_dir):
        m = re.match(r"^([c12])-(\d+)-g_qc\.png$", fn, re.IGNORECASE)
        if m:
            os.replace(os.path.join(qc_dir, fn),
                       os.path.join(qc_dir, f"{m.group(1).lower()}-{m.group(2)}_qc.png"))
    return rows, mapping


def mad_outliers(values, k=MAD_K):
    """返回 (mask, mult): |x - median| > k×MAD; MAD=0 时无标记"""
    values = np.asarray(values, dtype=float)
    med = np.median(values)
    mad = np.median(np.abs(values - med))
    if mad == 0:
        return np.zeros(len(values), dtype=bool), np.zeros(len(values))
    mult = np.abs(values - med) / mad
    return mult > k, mult


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--filter", default=None,
                    help="只处理路径含该子串的目录 (冒烟测试用, 如 'E.coli/repeat 1/3h')")
    ap.add_argument("--smoke", action="store_true",
                    help="冒烟模式: 输出写到 imagej_counts/_smoke/ 不碰正式文件")
    args = ap.parse_args()
    filt = args.filter.replace("\\", "/") if args.filter else None

    out_root = os.path.join(BASE, "imagej_counts", "_smoke" if args.smoke else "")
    qc_root = os.path.join(out_root, "qc")
    os.makedirs(out_root, exist_ok=True)

    all_rows = []
    for sp in SPECIES:
        for rep in REPEATS:
            for tp in TIMES:
                time_dir = os.path.join(BASE, sp, rep, tp)
                rel = f"{sp}/{rep}/{tp}"
                if filt and filt not in rel:
                    continue
                if not os.path.isdir(time_dir) or not glob.glob(os.path.join(time_dir, "*.tif")):
                    print(f"=== {rel}: 目录为空, 跳过 ===")
                    continue
                tag = f"{sp}_{rep.replace(' ', '_')}_{tp}"
                out_csv = os.path.join(out_root, f"_{tag}_imagej.csv")
                qc_dir = os.path.join(qc_root, sp, rep, tp)
                rows, mapping = count_time_dir(time_dir, out_csv, qc_dir)
                n_qc = len([f for f in os.listdir(qc_dir) if f.endswith("_qc.png")])
                print(f"\n=== {rel}: {len(rows)} 张计数, {n_qc} 张 QC 图 ===")
                for r in rows:
                    fn = r["filename"]
                    orig, orig_path, region, num = mapping[fn]
                    exp = exposure_seconds(orig_path)
                    cnt = int(float(r["count"]))
                    bg = int(float(r["bg"]))
                    all_rows.append({
                        "species": sp,
                        "repeat": rep,
                        "time": tp,
                        "region": region,
                        "region_label": REGION_LABEL[region],
                        "num": num,
                        "count": cnt,
                        "chan_used": r["chan_used"],
                        "bg": bg,
                        "thresh": int(float(r["thresh"])),
                        "roi_count": int(float(r["roi_count"])),
                        "exposure_s": exp,
                        "total_per_cm2": cnt / AREA_UM2 * 1e8,
                    })
                    print(f"  {rel}/{orig}: chan={r['chan_used']:<12} count={cnt:>6} "
                          f"exposure={exp:.2f}s  bg={bg}")

    if not all_rows:
        print("没有处理任何目录。")
        return

    df = pd.DataFrame(all_rows)

    # 通道正确性检查
    bad = df[df["chan_used"] != "green"]
    if len(bad):
        print(f"\n⚠️ 警告: {len(bad)} 张图没走 green 通道:")
        print(bad[["species", "repeat", "time", "region", "num", "chan_used", "count"]].to_string(index=False))
    else:
        print("\n✅ 全部走 green 通道")
    leak = df[df["count"] != df["roi_count"]]
    print(f"✅ ROI 一致性: {'全部 count==roi_count' if not len(leak) else f'⚠️ {len(leak)} 张不一致'}")

    # ---- 剔除: 仅阈值失效 (饱和) 图 ----
    df["excluded"] = df["bg"] >= SATURATION_BG
    df["exclude_reason"] = np.where(df["excluded"], "saturated (bg>=250): threshold invalid", "")
    n_sat = int(df["excluded"].sum())
    if n_sat:
        print(f"\n=== 剔除阈值失效图 {n_sat} 张 ===")
        print(df[df["excluded"]][["species", "time", "region", "num", "count", "bg"]].to_string(index=False))

    # ---- MAD 诊断 (不强制剔除) ----
    df["mad_mult"] = 0.0
    df["mad_flag"] = False
    print(f"\n=== MAD 诊断 (|x - median| > {MAD_K}×MAD, 每组内; 仅标注, 不剔除) ===")
    for (sp, rep, tp, rg), grp in df.groupby(["species", "repeat", "time", "region"]):
        mask, mult = mad_outliers(grp["count"].values, k=MAD_K)
        df.loc[grp.index, "mad_mult"] = mult
        df.loc[grp.index, "mad_flag"] = mask
        med = np.median(grp["count"].values)
        mad = np.median(np.abs(grp["count"].values - med))
        outs = grp[mask]
        thr_rel = (MAD_K * mad / med * 100) if med else np.nan
        print(f"{sp}/{rep}/{tp}/{REGION_LABEL[rg]}: n={len(grp)} median={med:.0f} MAD={mad:.0f} "
              f"5×MAD={MAD_K * mad:.0f} ({thr_rel:.0f}% of median) → 标注 {len(outs)} 张")
        for (_, o), m in zip(outs.iterrows(), mult[mask]):
            print(f"    ⚑ {sp}/{tp}/{o['region']}-{o['num']}.tif: count={o['count']} "
                  f"(偏差 {o['count'] - med:+.0f} = {m:.1f}×MAD)")

    raw_csv = os.path.join(out_root, "singlegreen_raw.csv")
    df.to_csv(raw_csv, index=False, encoding="utf-8-sig")
    clean = df[~df["excluded"]]

    # 汇总: species × repeat × time × region (剔除饱和图后)
    if len(clean):
        by_grp = clean.groupby(["species", "repeat", "time", "region", "region_label"]).agg(
            n=("count", "count"),
            count_mean=("count", "mean"),
            count_sd=("count", "std"),
            cm2_mean=("total_per_cm2", "mean"),
            cm2_sd=("total_per_cm2", "std"),
        ).reset_index()
        raw_n = df.groupby(["species", "repeat", "time", "region"]).size().rename("n_raw").reset_index()
        ex_n = df.groupby(["species", "repeat", "time", "region"])["excluded"].sum().rename("n_excluded").reset_index()
        by_grp = by_grp.merge(raw_n, on=["species", "repeat", "time", "region"], how="left")
        by_grp = by_grp.merge(ex_n, on=["species", "repeat", "time", "region"], how="left")
        by_grp = by_grp[["species", "repeat", "time", "region", "region_label",
                         "n", "n_excluded", "count_mean", "count_sd", "cm2_mean", "cm2_sd"]]
        by_grp.to_csv(os.path.join(out_root, "singlegreen_summary_by_region.csv"),
                      index=False, encoding="utf-8-sig")
        print("\n按 species × repeat × time × region 汇总 (总菌数, 饱和图已剔除):")
        print(by_grp.round(1).to_string(index=False))
    else:
        print("⚠️ 没有可用数据!")

    print(f"\n输出目录: {out_root}")
    print("  singlegreen_raw.csv / singlegreen_summary_by_region.csv")
    print("  qc/<species>/<repeat>/<time>/<region>-<n>_qc.png")


if __name__ == "__main__":
    main()
