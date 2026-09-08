# -*- coding: utf-8 -*-
"""
compare_count_backends.py — LIVE/DEAD 计数双引擎全量对比 (OpenCV vs ImageJ)
跑完输出: <out>/compare_raw_pairs.csv (逐配对两引擎 live/dead) + 控制台统计
用法: python compare_count_backends.py
"""
import os, sys, glob, re
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from labtoolbox.livedead_cellcounter.cellcounter import (
    LiveDeadCellCounter, CellCounterEngine, ImageJEngine)

BASE = r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_Antibacterial Surfaces\Live_Dead Bacteria Test"
ROOTS = [os.path.join(BASE, "515nm"), os.path.join(BASE, "515nm-filter_paper")]
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "compare_counters")


def main():
    os.makedirs(OUT, exist_ok=True)
    cv_eng = CellCounterEngine()
    ij_eng = ImageJEngine()
    all_rows = []
    for root in ROOTS:
        if not os.path.isdir(root):
            print("跳过(不存在):", root); continue
        print("=" * 60)
        print("根目录:", root)
        analyzer_cv = LiveDeadCellCounter(engine=cv_eng)
        analyzer_ij = LiveDeadCellCounter(engine=ij_eng)
        structure = analyzer_cv.scan_structure(root)
        df_cv = analyzer_cv.count_all(structure, verbose=False)
        df_ij = analyzer_ij.count_all(structure, verbose=False)
        keys = ["repeat", "time", "area", "num"]
        m = df_cv[keys + ["live", "dead"]].merge(
            df_ij[keys + ["live", "dead"]], on=keys,
            suffixes=("_opencv", "_imagej"))
        m["d_live"] = m["live_imagej"] - m["live_opencv"]
        m["d_dead"] = m["dead_imagej"] - m["dead_opencv"]
        m["root"] = os.path.basename(root)
        all_rows.append(m)
        print(f"  配对: {len(m)} | live 差 mean|Δ|={m['d_live'].abs().mean():.2f} "
              f"max={m['d_live'].abs().max()} | 一致率="
              f"{(m['d_live']==0).mean()*100:.0f}%")
        big = m[m["d_live"].abs() > 50]
        if len(big):
            print(f"  ⚠️ 大差异 (|Δlive|>50) {len(big)} 对, 例如:")
            print(big.head(5).to_string(index=False))
    if all_rows:
        cmp = pd.concat(all_rows, ignore_index=True)
        out_csv = os.path.join(OUT, "compare_raw_pairs.csv")
        cmp.to_csv(out_csv, index=False, encoding="utf-8-sig")
        print()
        print("=" * 60)
        print(f"全量汇总 ({len(cmp)} 配对):")
        print(f"  live:  mean|Δ|={cmp['d_live'].abs().mean():.2f}  "
              f"median|Δ|={cmp['d_live'].abs().median():.1f}  "
              f"max={cmp['d_live'].abs().max()}  "
              f"一致率={(cmp['d_live']==0).mean()*100:.0f}%")
        print(f"  dead:  mean|Δ|={cmp['d_dead'].abs().mean():.2f}  "
              f"max={cmp['d_dead'].abs().max()}")
        # 分组均值对比
        g = cmp.groupby(["root", "repeat", "time", "area"]).agg(
            live_cv=("live_opencv", "mean"), live_ij=("live_imagej", "mean"),
            dead_cv=("dead_opencv", "mean"), dead_ij=("dead_imagej", "mean"),
            n=("live_opencv", "count")).reset_index()
        g.to_csv(os.path.join(OUT, "compare_group_means.csv"),
                 index=False, encoding="utf-8-sig")
        print(f"分组均值表: {os.path.join(OUT, 'compare_group_means.csv')}")
        print(f"逐配对明细: {out_csv}")


if __name__ == "__main__":
    main()
