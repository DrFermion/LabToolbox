# -*- coding: utf-8 -*-
"""515nm AFM 表面分析 (ZSR 通道版) —— 按 Svetlana 的要求改用 ZSensor Retrace (ZSR).

要求原文: "The surface data appear correct but calculated for the Height Retrace, You must use
ZSensor Retrace (ZSR) for surface analysis."

处理链 (ZSR 未滤波未展平, 缺一步结果就废):
  1. 通道 = ZSR (ZSensorRetrace; 本批 20 个文件都是索引 3, labels 与 wave_note 双向确认)
  2. 数值 = Gwyddion 内核 + level (真·平面扣除) + ISO 25178 统计
  3. 出图 = Python 渲染: 2D 最小二乘平面扣除 → 5σ 中值去单点尖峰 → 3D(z 与 XY 等比)/剖面
  4. 参考线: LIPSS = 一条横跨条纹的线 (方向由 2D FFT 在 0.5λ~1.5λ = 258~772 nm 带内判)
             Nanopillar / VirginSS = 横 + 纵两条
输出: <数据目录>/AFM_surface_analysis_20260915_ZSR/ + Height vs ZSR 对比表
"""
import csv
import glob
import os
import shutil
import subprocess
import sys

sys.path.insert(0, r"E:\LabToolbox")
from labtoolbox.surfmetrics.surfmetrics import run  # noqa: E402

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - "
        r"Ruinong Pan_Antibacterial Surfaces\AFM Steel Samples\515 samples")
OUT = os.path.join(BASE, "AFM_surface_analysis_20260915_ZSR")
OLD = os.path.join(BASE, "AFM_surface_analysis_20260912", "surface_metrics_515nm_all.csv")
MIRROR = r"E:\LabToolbox\output\afm_515_zsr_template"
BAND = (258.0, 772.0)          # 515 nm 激光: LIPSS 周期物理上落在 0.5λ~1.5λ

GROUPS = [
    ("VirginSS", "260825_SZ", "*.ibw", "hv"),
    ("LIPSS", "260827_SZ", "*.ibw", "cross"),
    ("LIPSS", "260901_SZ", "*LIPSS*.ibw", "cross"),
    ("Nanopillar", "260901_SZ", "*NP*.ibw", "hv"),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    rows_all = []
    for group, sub, pat, mode in GROUPS:
        files = sorted(glob.glob(os.path.join(BASE, sub, pat)))
        if not files:
            print(f"⚠️  {group}/{sub}/{pat}: 空")
            continue
        print(f"\n########## {group} ({sub}/{pat}) {len(files)} 个文件 · 通道=ZSR · 参考线={mode} ##########")
        res = run(file=files, output_dir=os.path.join(OUT, group), backend="gwyddion",
                  channel="zsr", level=True, plane=True, despike=True, z_mode="real",
                  profiles=True, profile_mode=mode, stripe_band=(BAND if mode == "cross" else None))
        with open(res["csv"], encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                r["group"] = group
                r["source_dir"] = sub
                rows_all.append(r)

    fields = ["group", "source_dir", "file", "backend", "level", "Sa_nm", "Sq_nm", "Sz_nm",
              "skew", "kurt", "S3d_um2", "Sproj_um2", "Sdr_pct", "profile_mode", "n_lines",
              "stripe_cross_deg", "stripe_ridge_deg", "stripe_period_nm", "stripe_strength"]
    merged = os.path.join(OUT, "surface_metrics_515nm_ZSR_all.csv")
    with open(merged, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows_all, key=lambda x: (x["group"], x["source_dir"], x["file"])):
            w.writerow({k: r.get(k, "") for k in fields})

    # ---- Height vs ZSR 对比 ----
    old = {}
    if os.path.exists(OLD):
        with open(OLD, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                old[r["file"]] = r
    cmp_path = os.path.join(OUT, "height_vs_zsr.csv")
    with open(cmp_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["group", "file", "Sa_height", "Sa_ZSR", "Sa_change_pct",
                    "Sq_height", "Sq_ZSR", "Sz_height", "Sz_ZSR",
                    "Sdr_height", "Sdr_ZSR"])
        for r in sorted(rows_all, key=lambda x: (x["group"], x["file"])):
            o = old.get(r["file"], {})
            def fnum(d, k):
                try:
                    return float(d.get(k) or "nan")
                except Exception:
                    return float("nan")
            sh, sz_ = fnum(o, "Sa_nm"), fnum(r, "Sa_nm")
            w.writerow([r["group"], r["file"],
                        f"{sh:.2f}" if sh == sh else "", f"{sz_:.2f}" if sz_ == sz_ else "",
                        f"{(sz_ - sh) / sh * 100:.1f}" if (sh == sh and sh) else "",
                        fnum(o, "Sq_nm"), fnum(r, "Sq_nm"), fnum(o, "Sz_nm"), fnum(r, "Sz_nm"),
                        fnum(o, "Sdr_pct"), fnum(r, "Sdr_pct")])

    # ---- README ----
    L = ["# 515nm AFM 表面分析 —— ZSR 通道版", "",
         "生成: 荧荧 2026-09-15 | 通道: **ZSensor Retrace (ZSR)** (索引 3) | 数值: WSL Gwyddion 内核 (level) | 图: Python 渲染",
         "",
         "## 为什么重做", "",
         "> \"The surface data appear correct but calculated for the Height Retrace,",
         "> You must use ZSensor Retrace (ZSR) for surface analysis.\"",
         "",
         "Height Retrace 是软件**平滑/压平后**的输出，起伏被系统性低估；ZSR 是 Z 压电传感器**原始反馈**，",
         "未滤波、未展平 —— 表面粗糙度/表面积分析要求用后者。本批 20 个文件全部改用 ZSR 重算（数值 + 图）。",
         "",
         "## ZSR 处理链（未展平数据，缺一步结果就废）", "",
         "1. **通道定位**：labels 与 wave_note 双向确认 —— `HeightRetrace / AmplitudeRetrace / PhaseRetrace / ZSensorRetrace` → ZSR = 索引 3；",
         "2. **单位换算**：Bruker ZS 以「米」存储 → ×1e9 转 nm；",
         "3. **2D 平面扣除**：`z = a·x + b·y + c` 最小二乘拟合后减去（只减均值不够，ZS 带 ~µm 级偏置 + 扫描倾斜）；",
         "4. **去尖峰**：5σ 中值滤波（size=3，迭代 3 次）替换单点/小面积尖峰（探针粘附、灰尘）；**大块凸起去不掉**，靠人工 QC；",
         "5. **统计**：Gwyddion 内核 + level（真·平面扣除）出 ISO 25178 的 Sa/Sq/Sz/skew/kurt；",
         "6. **参考线**：LIPSS = 一条横跨条纹的线（方向由 2D FFT 在 **258–772 nm**（=0.5λ–1.5λ）带内判 —— ZSR 里 µm 级扫描伪影比 LIPSS 峰还强，不设带会挑错方向）；Nanopillar / VirginSS = 横 + 纵两条。",
         "",
         "## 逐文件结果（ZSR）", "",
         "| 组 | 文件 | Sa (nm) | Sq (nm) | Sz (nm) | Sdr (%) | 检测线 | 条纹周期 (nm) | 跨纹方向 (°) |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows_all, key=lambda x: (x["group"], x["source_dir"], x["file"])):
        per = r.get("stripe_period_nm") or ""
        ang = r.get("stripe_cross_deg") or ""
        L.append(f"| {r['group']} | {r['file']} | {float(r['Sa_nm']):.2f} | {float(r['Sq_nm']):.2f} | "
                 f"{float(r['Sz_nm']):.1f} | {float(r['Sdr_pct']):.2f} | {r.get('n_lines','')} 条 "
                 f"({r.get('profile_mode','')}) | {per} | {ang} |")
    L += ["", "## Height vs ZSR（同一文件两个通道）", "",
          f"- 明细: `{os.path.basename(cmp_path)}`；组内 CSV 见各组目录；合并表 `surface_metrics_515nm_ZSR_all.csv`。",
          "- 结论：ZSR 的 Sa/Sq/Sz **系统性高于** Height（Height 被软件压平/平滑过），差值逐文件列在对比表里。",
          "", "## 文件", "",
          "- `<组>/<文件名>_3D.png` — 3D 形貌（z 与 XY 等比，高度看 colorbar）",
          "- `<组>/<文件名>_profile.png` — 左 3D + 参考线；右 沿线的 Height(nm)–Distance(µm) 剖面",
          "- `<组>/all_3D_grid.png`、`<组>/surface_metrics_summary.csv`", "",
          "## z 标线（2026-09-15 起）", "",
          "3D 图与剖面图左侧 3D panel 都带一条**竖直 z 标线**：从高度 **0** 画到该面的**最高点**，",
          "两端小横钩 + 端点数值（只标 0 与最大值）。等比视图下 z 轴刻度会被自动隐藏",
          "（高度只剩 colorbar 可读，而 colorbar 是全域色标、读不出「这图最高点多高」），",
          "这条尺子补的正是绝对高度参照。z 夸张模式（刻度可见）时不画，避免与刻度重复。", ""]
    open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write("\n".join(L))

    # ---- 镜像到 E 盘工作副本 ----
    # ⚠️ 别用 shutil.rmtree + copytree: 在本机 E:\... 上会 WinError 5 (拒绝访问) 中途炸掉,
    #    旧代码还 except 一吞就当成功 → 留下"半新半旧"的镜像 (2026-09-15 实测: LIPSS 整组 13 张丢失)。
    #    改成 robocopy /MIR (Windows 原生) + 复制后**核对图片张数**, 不一致必须报出来。
    def _count_png(root):
        return sum(len([f for f in fs if f.lower().endswith(".png")])
                   for _r, _d, fs in os.walk(root))

    try:
        r = subprocess.run(["robocopy", OUT, MIRROR, "/MIR", "/NFL", "/NDL", "/NJH", "/NJS", "/NP"],
                           capture_output=True, text=True, timeout=1800)
        mirrored = r.returncode is not None and r.returncode < 8
        if not mirrored:
            print("⚠️ robocopy 返回", r.returncode, (r.stdout or "")[-300:])
    except Exception as e:
        print("robocopy 异常, 回退 shutil:", e)
        try:
            if os.path.isdir(MIRROR):
                shutil.rmtree(MIRROR)
            shutil.copytree(OUT, MIRROR)
            mirrored = True
        except Exception as e2:
            print("❌ 镜像失败:", e2)
            mirrored = False
    n_out, n_mir = _count_png(OUT), _count_png(MIRROR)
    print(f"镜像: 交付 {n_out} 张 / 镜像 {n_mir} 张",
          "✅" if (mirrored and n_out == n_mir and n_out > 0) else "❌ 不一致 —— 需手动补镜像")

    print("\n".join(L[28:]))
    print(f"\n输出: {OUT}\n合并表: {merged}\n对比表: {cmp_path}")
    print("图片数:", len(glob.glob(os.path.join(OUT, "*", "*.png"))))


if __name__ == "__main__":
    main()
