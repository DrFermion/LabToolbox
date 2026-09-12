# -*- coding: utf-8 -*-
"""验证新模板的参考线选择: LIPSS 单条跨纹线 (FFT 定向) / NP 横纵两条.

铁证: 跨纹线的剖面自己再做个 FFT —— 周期应与整图 FFT 判出的周期一致;
而沿纹线(平行条纹)的剖面则看不到这个周期. 三者对上才说明线真的横跨了条纹.
"""
import os
import sys

import numpy as np

sys.path.insert(0, r"E:\LabToolbox")
from labtoolbox.surfmetrics.surfmetrics import (load_heightmap, stripe_orientation,  # noqa: E402
                                                _sample_line, profile_lines_for, plot_profiles)

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - "
        r"Ruinong Pan_Antibacterial Surfaces\AFM Steel Samples\515 samples")
OUT = r"E:\LabToolbox\output\afm_515_newtemplate_probe"
os.makedirs(OUT, exist_ok=True)

FILES = [
    ("LIPSS", os.path.join(BASE, "260827_SZ", "515LIPSS-5x5_area1.ibw")),
    ("LIPSS", os.path.join(BASE, "260827_SZ", "515LIPSS-10x10_area2.ibw")),
    ("NP", os.path.join(BASE, "260901_SZ", "515 NP-10x10-area1.ibw")),
]


def prof_period(dist_um, hgt_nm):
    """剖面自己的周期 (去线性趋势 + 汉宁窗 → FFT 峰)."""
    y = hgt_nm - np.polyval(np.polyfit(dist_um, hgt_nm, 1), dist_um)
    y = y * np.hanning(len(y))
    sp = np.abs(np.fft.rfft(y))
    fr = np.fft.rfftfreq(len(y), d=(dist_um[1] - dist_um[0]) * 1000.0)   # 1/nm
    sp[0:2] = 0
    i = int(np.argmax(sp))
    return (1.0 / fr[i]) if fr[i] > 0 else float("nan"), float(sp[i] / (np.median(sp[sp > 0]) or 1))


for group, path in FILES:
    name = os.path.splitext(os.path.basename(path))[0]
    z, px, py = load_heightmap(path)
    py = py or px
    st = stripe_orientation(z, px, py)
    print(f"\n===== {name}  ({group}) =====")
    print(f"  扫描 {z.shape[1]}x{z.shape[0]} px, px={px:.2f} nm  →  "
          f"{(z.shape[1] - 1) * px / 1000:.2f} x {(z.shape[0] - 1) * py / 1000:.2f} µm")
    print(f"  2D FFT: 条纹走向 {st['ridge_deg']:+.1f}°  跨纹线方向 {st['cross_deg']:+.1f}°  "
          f"周期 {st['period_nm']:.0f} nm  峰/中位 = {st['strength']:.1f}")

    mode = "cross" if group == "LIPSS" else "hv"
    lines, info = profile_lines_for(z, px, py, mode)
    print(f"  → 参考线: mode={info['profile_mode']} 共 {info['line_count']} 条: "
          + " | ".join(l.get("label", "").replace("\n", " ") for l in lines))

    # 铁证: 跨纹 vs 沿纹 剖面的周期
    d_cross, h_cross, *_ = _sample_line(z, px, py, {"kind": "angle", "deg": st["cross_deg"]})
    d_ridge, h_ridge, *_ = _sample_line(z, px, py, {"kind": "angle", "deg": st["ridge_deg"]})
    pc, sc = prof_period(d_cross, h_cross)
    pr, sr = prof_period(d_ridge, h_ridge)
    print(f"  横跨条纹的剖面: 周期 {pc:.0f} nm (谱峰/中位 {sc:.1f})   P-V {np.ptp(h_cross):.1f} nm")
    print(f"  沿条纹的剖面:   周期 {pr:.0f} nm (谱峰/中位 {sr:.1f})   P-V {np.ptp(h_ridge):.1f} nm")

    fig = os.path.join(OUT, f"{name}_profile.png")
    plot_profiles(z, px, py, fig, title=name, z_mode="real", lines=lines)
    print(f"  图: {fig}  ({os.path.getsize(fig) // 1024} KB)")
print("\nprobe done")
