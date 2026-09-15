# -*- coding: utf-8 -*-
"""check_figure_layout.py — 图形排版自检: 把三类图 (3D / 参考线剖面 / 网格) 画出来,
把所有可见 Text 的包围盒两两比对, 直接报"哪两段文字重叠了多少像素"。

为什么用代码量而不是肉眼看: matplotlib 3D + colorbar 的标签位置靠经验, 眼睛容易漏;
实测踩过的坑 (2026-09-15) —— z 轴标签与 colorbar 刻度挤在一处、两行长标题压到左 panel 的
colorbar、图例盖住剖面曲线的峰、网格图每格一排 z 刻度数字互相叠 (144 对重叠)。
判据: 重叠对数应为 0 (画布外的文字不计, 3D 会画一份镜像刻度在画布外)。

用法: python scripts/check_figure_layout.py [通道, 默认 zsr]
"""
import glob
import itertools
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from labtoolbox.surfmetrics.surfmetrics import (load_heightmap, plane_subtract,  # noqa: E402
                                                despike_z, plot3d, plot_grid,
                                                plot_profiles, profile_lines_for,
                                                surface_metrics)

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - "
        r"Ruinong Pan_Antibacterial Surfaces\AFM Steel Samples\515 samples")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "_layout_probe")
CHANNEL = sys.argv[1] if len(sys.argv) > 1 else "zsr"

_orig_close = plt.close
plt.close = lambda *a, **k: None


def load(rel):
    z, px, py = load_heightmap(BASE + rel, channel=CHANNEL)
    if CHANNEL == "zsr":
        z = despike_z(plane_subtract(z))[0]
    return z, (px or 10.0), (py or px or 10.0)


def overlaps(tag):
    fig = plt.gcf()
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W, H = fig.canvas.get_width_height()
    items = []
    for t in fig.findobj(matplotlib.text.Text):
        if not t.get_visible() or not (t.get_text() or "").strip():
            continue
        bb = t.get_window_extent(renderer=r)
        if bb.width <= 0 or bb.height <= 0:
            continue
        if bb.x1 < 0 or bb.y1 < 0 or bb.x0 > W or bb.y0 > H:
            continue                      # 画布外的镜像标签不算
        items.append((t.get_text().replace("\n", "⏎")[:46], bb))
    bad = 0
    for (t1, b1), (t2, b2) in itertools.combinations(items, 2):
        ox = min(b1.x1, b2.x1) - max(b1.x0, b2.x0)
        oy = min(b1.y1, b2.y1) - max(b1.y0, b2.y0)
        if ox > 1 and oy > 1:
            bad += 1
            print(f"   ❌ {ox:.0f}×{oy:.0f}px: {t1!r} ↔ {t2!r}")
    print(f"[{tag}] 可见文本 {len(items)} 个 → 重叠对 {bad} "
          f"{'✅' if bad == 0 else '⚠️ 需要调整排版'}")
    plt.close = lambda *a, **k: None
    return bad


def main():
    os.makedirs(OUT, exist_ok=True)
    total = 0
    z, px, py = load(r"\260827_SZ\515LIPSS-5x5_area1.ibw")
    plot3d(z, px, py, os.path.join(OUT, "3d.png"), z_mode="real", title="layout probe (3D)")
    total += overlaps("plot3d")

    lines, _info = profile_lines_for(z, px, py, "cross", stripe_band=(258.0, 772.0))
    plot_profiles(z, px, py, os.path.join(OUT, "profile.png"), title="layout probe", z_mode="real", lines=lines)
    total += overlaps("plot_profiles")

    grid = []
    for rel in sorted(glob.glob(BASE + r"\260901_SZ\*NP*.ibw"))[:6]:
        zg, pxg, pyg = load(rel[len(BASE):])
        grid.append((os.path.basename(rel).rsplit(".", 1)[0], zg, pxg, surface_metrics(zg, pxg, pyg)))
    plot_grid(grid, os.path.join(OUT, "grid.png"), title="layout probe (grid)", z_mode="real")
    total += overlaps("plot_grid")

    print(f"\n合计重叠对: {total} {'✅ 排版干净' if total == 0 else '⚠️'}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
