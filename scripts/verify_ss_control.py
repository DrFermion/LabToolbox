# -*- coding: utf-8 -*-
"""verify_ss_control.py — ss-control 计数结果独立校验
1) 打印完整 raw 表 (新 repeat 2/3)
2) 对抽样图跑独立 OpenCV 自适应阈值计数 (ImageJ vs Python 交叉验证)
3) QC PNG 像素校验: 蓝圈/蓝编号存在, 底色通道正确
"""
import os, re, glob
import numpy as np, pandas as pd, cv2
from PIL import Image

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_"
        r"Antibacterial Surfaces\Live_Dead Bacteria Test\ss-control")
OUT = os.path.join(BASE, "imagej_counts")

df = pd.read_csv(os.path.join(OUT, "ss_control_raw.csv"), encoding="utf-8-sig")
print("=== raw 表 (全部 88 视野) ===")
print(df[["repeat", "time", "num", "count", "bg", "thresh", "exposure_s", "outlier"]]
      .to_string(index=False))

# ---- 独立 OpenCV 计数 (自适应阈值 = 背景众数+40, 与 ImageJ 宏同方法学) ----
def py_count(path):
    # 中文路径: cv2.imread 在 Windows 上会静默失败 → 用 fromfile + imdecode
    buf = np.fromfile(path, dtype=np.uint8)
    a = cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)
    if a.ndim == 3:
        a = a[..., 1]  # green 通道 (BGR -> index1=G)
    u, c = np.unique(a, return_counts=True)
    bg = int(u[np.argmax(c)])
    mask = (a >= bg + 40).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    areas = stats[1:, cv2.CC_STAT_AREA]
    return int(((areas >= 3) & (areas <= 500)).sum()), bg

print("\n=== 独立 Python 计数 vs ImageJ (抽样) ===")
sample = []
for rep in ("repeat 1", "repeat 2", "repeat 3"):
    for tp in ("3h", "5h"):
        fs = sorted(glob.glob(os.path.join(BASE, rep, tp, "*.tif")),
                    key=lambda x: int(re.search(r"(\d+)\.tif$", x).group(1)))
        sample += [fs[0], fs[len(fs)//2], fs[-1]]
rows = []
for p in sample:
    rep = os.path.basename(os.path.dirname(os.path.dirname(p)))
    tp = os.path.basename(os.path.dirname(p))
    num = int(re.search(r"(\d+)\.tif$", p).group(1))
    py, bg = py_count(p)
    ij = int(df[(df["repeat"] == rep) & (df["time"] == tp) & (df["num"] == num)]["count"].iloc[0])
    rows.append((rep, tp, num, ij, py, ij - py, bg))
print(pd.DataFrame(rows, columns=["repeat", "time", "num", "imagej", "python", "diff", "bg_py"])
      .to_string(index=False))
d = np.abs([r[5] for r in rows])
print(f"mean|Δ| = {d.mean():.2f}, max|Δ| = {d.max()}")

# ---- QC PNG 像素校验 ----
print("\n=== QC PNG 像素校验 (蓝标记 + 绿色底) ===")
for rep in ("repeat 2", "repeat 3"):
    for tp in ("3h", "5h"):
        d_ = os.path.join(OUT, "qc", rep, tp)
        pngs = sorted(glob.glob(os.path.join(d_, "*_qc.png")))
        nb_list, ng_list = [], []
        for f in pngs:
            im = np.asarray(Image.open(f).convert("RGB")).astype(int)
            r, g, b = im[..., 0], im[..., 1], im[..., 2]
            blue = ((b > 150) & (r < 100) & (g < 100)).sum()
            green = ((g > 80) & (r < 60) & (b < 60)).sum()
            nb_list.append(blue); ng_list.append(green)
        sub = df[(df["repeat"] == rep) & (df["time"] == tp)]
        print(f"{rep}/{tp}: {len(pngs)}/{len(sub)} QC 图, 每张蓝标记像素 "
              f"min={min(nb_list)}~max={max(nb_list)}, 绿底像素 min={min(ng_list)}~max={max(ng_list)}")
        print(f"   覆盖范围检查: 蓝>0 全通过={all(x > 0 for x in nb_list)}, 绿底全>0={all(x > 0 for x in ng_list)}")
