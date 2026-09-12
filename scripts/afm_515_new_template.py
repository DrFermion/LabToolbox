# -*- coding: utf-8 -*-
"""515nm AFM: 按新模板出图 (LIPSS 一条横跨条纹的检测线 / Nanopillar 横纵两条).

- 数据: F:\\...\\AFM Steel Samples\\515 samples\\(260825_SZ|260827_SZ|260901_SZ)\\
- 口径: Gwyddion 内核 (level 平面扣除 + ISO 25178 统计), 3D 图 z 与 XY 等比 (期刊口径)
- 参考线: LIPSS → 一条, 方向由 2D FFT 定 (横跨条纹); Nanopillar / VirginSS → 横 + 纵两条
- 输出: <数据目录>\\AFM_surface_analysis_20260912\\{VirginSS,LIPSS,Nanopillar}\\ + 合并 CSV + README
"""
import csv
import glob
import os
import shutil
import sys

sys.path.insert(0, r"E:\LabToolbox")
from labtoolbox.surfmetrics.surfmetrics import run  # noqa: E402

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - "
        r"Ruinong Pan_Antibacterial Surfaces\AFM Steel Samples\515 samples")
OUT = os.path.join(BASE, "AFM_surface_analysis_20260912")
MIRROR = r"E:\LabToolbox\output\afm_515_newtemplate"

GROUPS = [
    ("VirginSS", "260825_SZ", "*.ibw", "hv"),
    ("LIPSS", "260827_SZ", "*.ibw", "cross"),
    ("LIPSS", "260901_SZ", "*LIPSS*.ibw", "cross"),
    ("Nanopillar", "260901_SZ", "*NP*.ibw", "hv"),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    merged, all_rows = [], []
    for group, sub, pat, mode in GROUPS:
        files = sorted(glob.glob(os.path.join(BASE, sub, pat)))
        if not files:
            print(f"⚠️  {group}/{sub}/{pat}: 没有文件")
            continue
        print(f"\n########## {group} ({sub}, {pat}) — {len(files)} 个文件, 参考线模式={mode} ##########")
        out_dir = os.path.join(OUT, group)
        res = run(file=files, output_dir=out_dir, backend="gwyddion", level=True,
                  z_mode="real", profiles=True, profile_mode=mode)
        with open(res["csv"], encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            r["group"] = group
            r["source_dir"] = sub
            all_rows.append(r)
        merged.append((group, res))

    # ---- 合并 CSV (含分组列) ----
    fields = ["group", "source_dir", "file", "backend", "level", "Sa_nm", "Sq_nm", "Sz_nm",
              "skew", "kurt", "S3d_um2", "Sproj_um2", "Sdr_pct", "profile_mode", "n_lines",
              "stripe_cross_deg", "stripe_ridge_deg", "stripe_period_nm", "stripe_strength"]
    merged_csv = os.path.join(OUT, "surface_metrics_515nm_all.csv")
    with open(merged_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in sorted(all_rows, key=lambda x: (x["group"], x["source_dir"], x["file"])):
            w.writerow({k: r.get(k, "") for k in fields})

    # ---- 控制台汇总 + README ----
    lines = ["# 515nm AFM 表面分析 (新模板)", "",
             "生成: 荧荧 2026-09-12 | 内核: WSL Gwyddion (level 平面扣除 + ISO 25178) | 图: Python 渲染",
             "",
             "## 参考线规则 (本次要求)", "",
             "| 组 | 检测线 | 说明 |", "|---|---|---|",
             "| LIPSS | **1 条** | 方向由高度图 2D FFT 自动定, **横跨条纹** (垂直于脊线), 剖面里能读出周期 |",
             "| Nanopillar | **2 条** | 横 (沿 X) + 纵 (沿 Y), 各取正中一行/一列 |",
             "| VirginSS | 2 条 | 各向同性对照面, 无周期性, 沿用横纵两条 |",
             "",
             "## 逐文件结果", "",
             "| 组 | 文件 | Sa (nm) | Sq (nm) | Sz (nm) | Sdr (%) | 检测线 | 条纹周期 (nm) | 跨纹线方向 (°) |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(all_rows, key=lambda x: (x["group"], x["source_dir"], x["file"])):
        per = r.get("stripe_period_nm") or ""
        ang = r.get("stripe_cross_deg") or ""
        lines.append(f"| {r['group']} | {r['file']} | {float(r['Sa_nm']):.2f} | {float(r['Sq_nm']):.2f} | "
                     f"{float(r['Sz_nm']):.1f} | {float(r['Sdr_pct']):.2f} | "
                     f"{r.get('n_lines','')} 条 ({r.get('profile_mode','')}) | {per} | {ang} |")
    lines += ["", "## 文件", "",
              "- `<组>/<文件名>_3D.png` — 3D 形貌, z 与 XY **等比** (高度看 colorbar)",
              "- `<组>/<文件名>_profile.png` — 左: 3D + 参考线 (虚线, 标注方向/位置); 右: 沿线的 Height(nm)-Distance(µm) 剖面",
              "- `<组>/surface_metrics_summary.csv` — 该组 ISO 25178 统计",
              "- `surface_metrics_515nm_all.csv` — 三组合并表 (含检测线方向与周期)",
              "- `<组>/all_3D_grid.png` — 该组 3D 网格总览",
              ""]
    readme = os.path.join(OUT, "README.md")
    open(readme, "w", encoding="utf-8").write("\n".join(lines))

    # ---- 镜像一份到 LabToolbox output (便于在 GUI/仓库里回看) ----
    try:
        if os.path.isdir(MIRROR):
            shutil.rmtree(MIRROR)
        shutil.copytree(OUT, MIRROR)
    except Exception as e:
        print("镜像失败:", e)

    print("\n=== 汇总 ===")
    print("\n".join(lines[13:]))
    print(f"\n输出目录: {OUT}")
    print(f"合并表:   {merged_csv}")
    print(f"README:   {readme}")
    print(f"图片数:   {len(glob.glob(os.path.join(OUT, '*', '*.png')))}")


if __name__ == "__main__":
    main()
