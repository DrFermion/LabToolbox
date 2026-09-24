# -*- coding: utf-8 -*-
"""
diagnose_515_singlegreen.py — 515nm 单绿染计数的几何诊断 (计数的独立 QC 工具)

对每张图用与 ImageJ 宏相同的阈值 (背景众数+40) 做连通域分析, 输出:
  · n3_500   : 3-500px 连通域个数 —— 应与 ImageJ count 逐张一致 (一致性自检)
  · big_frac : 阈值信号中位于 >500px 大团块的比例 —— 高 = 菌团融合, 计数被低估的风险
  · cover_pct: 阈值像素占视野比例 —— 视野负载的直观量 (密集视野饱和时不可数)

输出: imagej_counts/singlegreen_geometry.csv (逐视野) + 控制台组汇总
注意: 这是排查/诊断工具 (与计数交付并行使用), 不参与出数决策 —— 计数以 ImageJ 为准。
"""
import os
import re
import glob
import numpy as np
import pandas as pd
import tifffile
from scipy import ndimage

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_"
        r"Antibacterial Surfaces\Live_Dead Bacteria Test\515-singlegreen")
OUT = os.path.join(BASE, "imagej_counts")
RAW = os.path.join(OUT, "singlegreen_raw.csv")
FNAME_RE = re.compile(r"^([c12])-(\d+)\.tif$", re.IGNORECASE)


def main():
    rows = []
    for sp in ("E.coli", "S.aureus"):
        for rep in ("repeat 1", "repeat 2", "repeat 3"):
            for tp in ("3h", "6h", "8h", "24h"):
                for p in sorted(glob.glob(os.path.join(BASE, sp, rep, tp, "*.tif"))):
                    fn = os.path.basename(p)
                    m = FNAME_RE.match(fn)
                    if not m:
                        continue
                    a = tifffile.imread(p)
                    g = a[..., 1] if a.ndim == 3 else a
                    mode = int(np.bincount(g.ravel(), minlength=256).argmax())
                    th = min(mode + 40, 255)
                    mask = g >= th if mode < 250 else np.zeros_like(g, bool)
                    if mask.any():
                        lab, _ = ndimage.label(mask, structure=np.ones((3, 3), int))
                        sizes = np.bincount(lab.ravel())[1:]
                        small = sizes[(sizes >= 3) & (sizes <= 500)]
                        big = sizes[sizes > 500]
                        n_small, n_big = int(len(small)), int(len(big))
                        big_px = int(big.sum()) if len(big) else 0
                        tot_px = int(mask.sum())
                    else:
                        n_small = n_big = big_px = tot_px = 0
                    rows.append({
                        "species": sp, "repeat": rep, "time": tp,
                        "region": m.group(1).lower(), "num": int(m.group(2)),
                        "mode": mode, "th": th, "n3_500": n_small, "n_big": n_big,
                        "big_px": big_px, "tot_px": tot_px,
                        "big_frac": round(big_px / tot_px, 3) if tot_px else np.nan,
                        "cover_pct": round(tot_px / g.size * 100, 2),
                    })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "singlegreen_geometry.csv"), index=False, encoding="utf-8-sig")
    print(f"已保存: {os.path.join(OUT, 'singlegreen_geometry.csv')} ({len(df)} 行)")

    # 与 ImageJ 计数一致性自检
    if os.path.exists(RAW):
        ij = pd.read_csv(RAW, encoding="utf-8-sig")
        mg = df.merge(ij[["species", "repeat", "time", "region", "num", "count", "excluded"]],
                      on=["species", "repeat", "time", "region", "num"], how="left")
        mg = mg[~mg["excluded"].fillna(False)]
        d = (mg["n3_500"] - mg["count"]).abs()
        print(f"与 ImageJ 计数对照: {len(mg)} 张, |Δ|>3 的 {int((d > 3).sum())} 张, max|Δ|={d.max():.0f}")

    print("\n=== 组级诊断: big_frac (融合占比) / cover_pct (负载) 均值 ===")
    g = df.groupby(["species", "time", "region"]).agg(
        big_frac_mean=("big_frac", "mean"),
        big_frac_max=("big_frac", "max"),
        cover_mean=("cover_pct", "mean"),
        cover_max=("cover_pct", "max"),
    ).round(3)
    print(g.to_string())


if __name__ == "__main__":
    main()
