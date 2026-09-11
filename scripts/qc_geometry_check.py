# -*- coding: utf-8 -*-
"""qc_geometry_check.py — 客观校验 QC 图的蓝标记是否落在绿色菌体上
对抽样图: 用同一方法学 (bg+40) 取连通域 → 每个连通域质心周围是否有蓝像素 (圈/编号);
反向: 蓝像素附近是否有绿信号。避免视觉模型幻觉。
"""
import os, re
import numpy as np, cv2
from PIL import Image

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_"
        r"Antibacterial Surfaces\Live_Dead Bacteria Test\ss-control")

CASES = [("repeat 2", "5h", 2), ("repeat 2", "3h", 7), ("repeat 3", "5h", 8)]


def load_tif_gray(path):
    buf = np.fromfile(path, dtype=np.uint8)
    a = cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)
    return a[..., 1] if a.ndim == 3 else a


for rep, tp, num in CASES:
    tif = os.path.join(BASE, rep, tp, f"{num}.tif")
    png = os.path.join(BASE, "imagej_counts", "qc", rep, tp, f"{num}_qc.png")
    g = load_tif_gray(tif)
    u, c = np.unique(g, return_counts=True)
    bg = int(u[np.argmax(c)])
    mask = (g >= bg + 40).astype(np.uint8)
    n, lab, stats, cents = cv2.connectedComponentsWithStats(mask, 8)
    keep = [(i, cents[i]) for i in range(1, n)
            if 3 <= stats[i, cv2.CC_STAT_AREA] <= 500]

    im = np.asarray(Image.open(png).convert("RGB")).astype(int)
    r, gg, b = im[..., 0], im[..., 1], im[..., 2]
    blue = ((b > 150) & (r < 100) & (gg < 100))
    ys, xs = np.nonzero(blue)
    print(f"\n{rep}/{tp}/{num}.tif: 合法连通域 {len(keep)} 个 (CSV count 应等于此值), "
          f"QC 蓝像素 {blue.sum()}, PNG 尺寸 {im.shape[:2]} vs tif {g.shape}")

    if blue.sum() == 0 or not keep:
        print("  跳过 (无标记或无连通域)")
        continue

    # 每个连通域质心附近 (半径 15px) 是否有蓝标记
    covered = 0
    for i, (cx, cy) in keep:
        d = (xs - cx) ** 2 + (ys - cy) ** 2
        if d.min() <= 15 ** 2:
            covered += 1
    # 每个蓝像素 (抽样 500 个) 距最近绿色像素的距离
    gys, gxs = np.nonzero(mask)
    sel = np.random.choice(len(xs), size=min(500, len(xs)), replace=False)
    near = 0
    for k in sel:
        x, y = xs[k], ys[k]
        x0, x1 = max(0, x - 20), min(mask.shape[1], x + 21)
        y0, y1 = max(0, y - 20), min(mask.shape[0], y + 21)
        if mask[y0:y1, x0:x1].any():
            near += 1
    print(f"  连通域被蓝标记覆盖: {covered}/{len(keep)} = {100*covered/len(keep):.1f}%")
    print(f"  抽样蓝像素 20px 内有绿色信号: {near}/{len(sel)} = {100*near/len(sel):.1f}%")
