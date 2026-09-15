# -*- coding: utf-8 -*-
"""收尾 ZSR 交付: 修对比表名字匹配 + 写质量/剔除说明 + 给 VirginSS-4 的 3D 图打 [excluded] 标."""
import csv
import os
import re
import sys

import numpy as np

sys.path.insert(0, r"E:\LabToolbox")
from labtoolbox.surfmetrics.surfmetrics import (load_heightmap, plane_subtract,  # noqa: E402
                                                despike_z, plot3d, surface_metrics)

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - "
        r"Ruinong Pan_Antibacterial Surfaces\AFM Steel Samples\515 samples")
OUT = os.path.join(BASE, "AFM_surface_analysis_20260915_ZSR")
OLD = os.path.join(BASE, "AFM_surface_analysis_20260912", "surface_metrics_515nm_all.csv")


def key(name):
    """文件名归一化: 去掉 ' (HtR)'、空白、大小写差异."""
    n = re.sub(r"\s*\([A-Za-z]+\)\s*$", "", str(name)).strip()
    return n.lower().replace(" ", "")


def main():
    old = {}
    with open(OLD, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            old[key(r["file"])] = r

    rows = []
    with open(os.path.join(OUT, "surface_metrics_515nm_ZSR_all.csv"), encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    cmp_path = os.path.join(OUT, "height_vs_zsr.csv")
    with open(cmp_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["group", "file", "Sa_height", "Sa_ZSR", "Sa_change_pct", "Sq_height", "Sq_ZSR",
                    "Sz_height", "Sz_ZSR", "Sdr_height", "Sdr_ZSR", "note"])
        for r in sorted(rows, key=lambda x: (x["group"], x["file"])):
            o = old.get(key(r["file"]), {})

            def num(d, k):
                try:
                    return float(str(d.get(k, "")).strip())
                except Exception:
                    return float("nan")
            sh, sz_ = num(o, "Sa_nm"), num(r, "Sa_nm")
            note = ""
            if "VirginSS-4" in r["file"]:
                note = "单点大凸起 (真实颗粒/夹杂?) → 按惯例标 excluded"
            elif "VirginSS-8" in r["file"]:
                note = "unflattened + 多处尖峰, ZSR 下 Sa 升高 → 待确认是否剔除"
            elif "VirginSS-7" in r["file"]:
                note = "unflattened, ZSR 下 Sa 略升"
            w.writerow([r["group"], r["file"],
                        f"{sh:.2f}" if sh == sh else "", f"{sz_:.2f}" if sz_ == sz_ else "",
                        f"{(sz_ - sh) / sh * 100:.1f}" if (sh == sh and sh) else "",
                        f"{num(o,'Sq_nm'):.2f}" if num(o, "Sq_nm") == num(o, "Sq_nm") else "",
                        f"{num(r,'Sq_nm'):.2f}",
                        f"{num(o,'Sz_nm'):.1f}" if num(o, "Sz_nm") == num(o, "Sz_nm") else "",
                        f"{num(r,'Sz_nm'):.1f}",
                        f"{num(o,'Sdr_pct'):.2f}" if num(o, "Sdr_pct") == num(o, "Sdr_pct") else "",
                        f"{num(r,'Sdr_pct'):.2f}", note])

    # --- VirginSS-4: 重新出 3D 图, 标题带 [excluded] ---
    f4 = os.path.join(BASE, "260825_SZ", "VirginSS-4_512 points.ibw")
    if os.path.exists(f4):
        z, px, py = load_heightmap(f4, channel="zsr")
        z = despike_z(plane_subtract(z))[0]
        m = surface_metrics(z, px, py or px)
        png = os.path.join(OUT, "VirginSS", "VirginSS-4_512 points_3D.png")
        plot3d(z, px, py or px, png, z_mode="real",
               title=f"VirginSS-4_512 points  3D surface (ZSR)  [excluded: single large bump]  "
                     f"Sa={m['Sa_nm']:.1f} nm")
        print("已重出 VirginSS-4 的 3D 图 (带 [excluded]):", png)

    # --- README 补质量说明 ---
    rd = os.path.join(OUT, "README.md")
    txt = open(rd, encoding="utf-8").read()
    extra = """
## 质量说明与剔除（QC）

ZSR 未滤波，缺陷会真实地留在数据里 —— 以下三个 VirginSS 面按人工 QC（3D 图）标注，**数值行保留**便于追溯：

| 文件 | ZSR Sa | Height Sa | 判读 | 处理 |
|---|---|---|---|---|
| VirginSS-4_512 points | **41.27 nm** | 10.20 nm | 一处**大块凸起**（数百像素宽，5σ 中值滤波去不掉）——真实颗粒/夹杂物可能性大，与前次 ZS 分析结论一致（当时 Sa≈41 nm） | 标 **excluded**（3D 图标题带标记），组内汇总不含它 |
| VirginSS-8_512points-unflattened | 12.46 nm | 4.54 nm | unflattened 数据 + **多处上下尖峰** | 保留但标注，待导师/主人确认是否剔除 |
| VirginSS-7_256points-unflattened | 7.61 nm | 4.54 nm | unflattened，ZSR 下 Sa 略升 | 保留但标注 |

其余 VirginSS（1/2/3/5/6）ZSR 与 Height 一致（±0.5 nm，2.9–3.9 nm），可作为对照基准。
"""
    if "质量说明与剔除" not in txt:
        txt = txt.rstrip() + "\n" + extra
        open(rd, "w", encoding="utf-8").write(txt)
        print("README 已补质量说明")
    print("对比表已重写:", cmp_path)


if __name__ == "__main__":
    main()
