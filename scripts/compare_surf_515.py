# -*- coding: utf-8 -*-
"""
compare_surf_515.py — 515 钢样品 AFM: Python(自研) vs Gwyddion 内核 全量对比
每个 .ibw 三路数值:
  py_raw     = surfmetrics Python (raw, 不 level)
  gwy_raw    = Gwyddion 内核统计 (raw)
  gwy_level  = Gwyddion 内核 (平面扣除后)
输出: <out>/surf_515_comparison.csv + 控制台汇总
用法: python compare_surf_515.py
"""
import os, sys, glob, csv
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from labtoolbox.surfmetrics.surfmetrics import load_heightmap, surface_metrics, gwy_batch_wsl

BASE = r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_Antibacterial Surfaces\AFM Steel Samples\515 samples"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "surf_515_compare")


def main():
    os.makedirs(OUT, exist_ok=True)
    ibws = sorted(glob.glob(os.path.join(BASE, "*", "*.ibw")))
    print("找到 %d 个 .ibw" % len(ibws))

    print("跑 Gwyddion raw...")
    g_raw = {r["file"]: r for r in gwy_batch_wsl(ibws, level=False)}
    print("跑 Gwyddion level...")
    g_lvl = {r["file"]: r for r in gwy_batch_wsl(ibws, level=True)}

    rows = []
    for p in ibws:
        name = os.path.basename(p)
        z, px_h, py_h = load_heightmap(p)
        px = px_h if px_h else None
        if px:
            m = surface_metrics(z, px, px)
        else:
            m = {"Sa_nm": None, "Sq_nm": None, "Sz_nm": None}
        gr = g_raw.get(name, {})
        gl = g_lvl.get(name, {})
        rows.append({
            "file": name,
            "Sa_py_raw": m.get("Sa_nm"), "Sq_py_raw": m.get("Sq_nm"), "Sz_py_raw": m.get("Sz_nm"),
            "Sa_gwy_raw": gr.get("Sa_nm"), "Sq_gwy_raw": gr.get("Sq_nm"), "Sz_gwy_raw": gr.get("Sz_nm"),
            "Sa_gwy_lvl": gl.get("Sa_nm"), "Sq_gwy_lvl": gl.get("Sq_nm"), "Sz_gwy_lvl": gl.get("Sz_nm"),
            "ch_gwy": gl.get("channel"),
        })
    df = pd.DataFrame(rows)
    df["d_py_vs_gwy_raw_pct"] = ((df["Sa_gwy_raw"] - df["Sa_py_raw"]) / df["Sa_py_raw"] * 100).round(3)
    df["d_level_pct"] = ((df["Sa_gwy_lvl"] - df["Sa_gwy_raw"]) / df["Sa_gwy_raw"] * 100).round(1)
    df["d_level_abs"] = (df["Sa_gwy_lvl"] - df["Sa_gwy_raw"]).round(2)
    out_csv = os.path.join(OUT, "surf_515_comparison.csv")
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 220)
    show = df[["file", "Sa_py_raw", "Sa_gwy_raw", "Sa_gwy_lvl",
               "d_py_vs_gwy_raw_pct", "d_level_abs", "d_level_pct"]].copy()
    show.columns = ["file", "Sa_py", "Sa_gwy", "Sa_lvl", "py-vs-gwy%", "lvl Δ(nm)", "lvl Δ%"]
    print(show.to_string(index=False))

    print()
    print("汇总:")
    print("  Python vs Gwyddion(raw) Sa 一致率: %.1f%% (mean |Δ|%% = %.3f%%)" % (
        (df["d_py_vs_gwy_raw_pct"].abs() < 0.01).mean() * 100,
        df["d_py_vs_gwy_raw_pct"].abs().mean()))
    print("  level 前后 Sa: mean Δ = %.2f nm (%.1f%%), |Δ|>1nm 的文件 %d 个" % (
        df["d_level_abs"].mean(), df["d_level_pct"].mean(),
        (df["d_level_abs"].abs() > 1).sum()))
    big = df[df["d_level_abs"].abs() > 1]
    if len(big):
        print("  ⚠️ level 显著改变的文件:")
        for _, r in big.iterrows():
            print("    %s: Sa %.2f → %.2f nm (%.1f%%)" % (
                r["file"], r["Sa_gwy_raw"], r["Sa_gwy_lvl"], r["d_level_pct"]))
    print("明细:", out_csv)


if __name__ == "__main__":
    main()
