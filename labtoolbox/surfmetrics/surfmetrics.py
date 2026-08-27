# -*- coding: utf-8 -*-
"""
表面形貌参数模块: AFM/SEM 高度图 → 3D 图 + ISO 25178 粗糙度 (Sa/Sq/Sz) + 表面积 (Sdr)

支持格式:
  - .ibw  (Bruker/Igor AFM 原始数据, 直读; 自动读 ScanSize 校准 + 自动选 Height 通道)
  - .tif/.tiff (高度图)
  - .txt/.csv/.xyz (纯高度矩阵 或 x,y,z 三列)

输出 (ISO 25178 面积参数):
  Sa   算术平均高度  (nm)
  Sq   均方根高度    (nm)
  Sz   最大峰谷差    (nm)
  Sdr  表面积增加率  (%)  = (真实表面积 - 投影面积)/投影面积 * 100
"""
import os
import re
import sys
import csv
import glob

import numpy as np


def load_heightmap(path, channel=None):
    """读取高度图. 返回 (z, px_hint, py_hint); px_hint=None 表示未知需手动指定"""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".tif", ".tiff", ".png"):
        import tifffile
        z = tifffile.imread(path).astype(float)
        if z.ndim == 3:
            z = z[:, :, 0]
        return z, None, None
    if ext == ".ibw":  # Bruker/Igor binary wave — 直读 AFM 数据
        from igor import binarywave
        rec = binarywave.load(path)
        w = rec["wave"]
        data = np.array(w["wData"])
        labels = w.get("labels") or []
        flat = [l for grp in labels for l in (grp if isinstance(grp, list) else [grp])]
        names = [(l.decode("utf-8", errors="ignore") if isinstance(l, bytes) else str(l))
                 for l in flat if l]
        ch_sel = channel
        if data.ndim == 3:
            if ch_sel is None:
                # 优先 Height 通道
                for i, nm in enumerate(names):
                    if "height" in nm.lower():
                        ch_sel = i
                        break
                if ch_sel is None:
                    stds = [float(data[:, :, i].std()) for i in range(data.shape[2])]
                    alive = [i for i, s in enumerate(stds) if s > 1e-9]
                    if alive:
                        ch_sel = alive[0]
                        print(f"⚠️  未找到高度通道, 使用首个有数据通道 "
                              f"{names[ch_sel] if ch_sel < len(names) else ch_sel} (非高度, 结果仅作形貌参考)")
                    else:
                        raise ValueError("所有通道均无数据")
            z = data[:, :, ch_sel].astype(float)
            nm = names[ch_sel] if ch_sel < len(names) else f"ch{ch_sel}"
            # Bruker .ibw 高度通道原始单位是"米" → 按量级自动转 nm
            sd = float(z.std())
            if 1e-12 < sd < 1e-4:
                z = z * 1e9
                print(f"    通道: {nm} (单位 m → 已转 nm, std={sd:.2e}m = {z.std():.2f}nm)")
            else:
                print(f"    通道: {nm} (std={sd:.2f}, 视为已用 nm 或相对单位)")
            if z.std() < 1e-3:
                raise ValueError(f"{nm} 通道转换后仍无有效高度数据")
        else:
            z = data.astype(float)
        note = (w.get("note") or b"").decode("utf-8", errors="ignore")
        m = re.search(r"ScanSize:\s*([0-9.eE+-]+)", note)
        px = py = None
        if m:
            scan_m = float(m.group(1))  # 米
            n = max(z.shape)
            px = py = scan_m * 1e9 / n  # nm/px
        return z, px, py
    data = np.loadtxt(path, ndmin=2)
    if data.shape[1] == 3:  # x,y,z 三列 → 转矩阵
        xs = np.unique(data[:, 0])
        ys = np.unique(data[:, 1])
        z = data[:, 2].reshape(len(ys), len(xs))
        return z, None, None
    return data, None, None  # 纯高度矩阵


def surface_metrics(z, px, py):
    """z: 高度矩阵 (nm), px/py: 像素尺寸 (nm). 返回 dict"""
    z = z.astype(float)
    zc = z - z.mean()
    Sa = float(np.abs(zc).mean())
    Sq = float(np.sqrt((zc ** 2).mean()))
    Sz = float(z.max() - z.min())
    # --- Sdr: 相邻像素三角剖分 (ISO 25178 标准做法) ---
    h, w = z.shape
    dz10 = z[1:, :-1] - z[:-1, :-1]  # 向右高度差
    dz01 = z[:-1, 1:] - z[:-1, :-1]  # 向下高度差
    dz11 = z[1:, 1:] - z[:-1, :-1]   # 对角高度差
    a1 = np.stack([np.full_like(dz10, px), np.zeros_like(dz10), dz10], -1)
    b1 = np.stack([np.full_like(dz11, px), np.full_like(dz11, py), dz11], -1)
    a2 = np.stack([np.zeros_like(dz01), np.full_like(dz01, py), dz01], -1)
    b2 = np.stack([np.full_like(dz11, px), np.full_like(dz11, py), dz11], -1)

    def tri_area(a, b):
        c = np.cross(a, b)
        return 0.5 * np.sqrt((c ** 2).sum(-1))

    S3d = float((tri_area(a1, b1) + tri_area(a2, b2)).sum())
    Sproj = (h - 1) * (w - 1) * px * py
    Sdr = (S3d / Sproj - 1.0) * 100.0
    return {"Sa_nm": Sa, "Sq_nm": Sq, "Sz_nm": Sz,
            "S3d_um2": S3d / 1e6, "Sproj_um2": Sproj / 1e6, "Sdr_pct": Sdr}


def plot3d(z, px, py, out, title=None):
    """单文件 3D 表面图. z: nm; px/py: nm"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    h, w = z.shape
    X, Y = np.meshgrid(np.arange(w) * px / 1000.0, np.arange(h) * py / 1000.0)
    m = surface_metrics(z, px, py)
    fig = plt.figure(figsize=(9, 6.5))
    ax = fig.add_subplot(111, projection="3d")
    surf = ax.plot_surface(X, Y, z, cmap="viridis", linewidth=0,
                           antialiased=True, rstride=1, cstride=1)
    ax.set_xlabel("X (µm)")
    ax.set_ylabel("Y (µm)")
    ax.set_zlabel("Height (nm)")
    t = title or (f"Sa={m['Sa_nm']:.2f} nm, Sq={m['Sq_nm']:.2f} nm, "
                  f"Sz={m['Sz_nm']:.1f} nm, Sdr={m['Sdr_pct']:.2f}%")
    ax.set_title(t, fontsize=10)
    fig.colorbar(surf, shrink=0.6, label="Height (nm)")
    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def plot_grid(files_data, out, title=None):
    """多文件 3D 网格图 (≤9 个)"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    n = len(files_data)
    cols = 3 if n > 4 else (2 if n > 1 else 1)
    rows = int(np.ceil(n / cols))
    fig = plt.figure(figsize=(6 * cols, 5 * rows))
    for idx, (name, z, px, m) in enumerate(files_data):
        ax = fig.add_subplot(rows, cols, idx + 1, projection="3d")
        h, w = z.shape
        X, Y = np.meshgrid(np.arange(w) * px / 1000.0, np.arange(h) * px / 1000.0)
        surf = ax.plot_surface(X, Y, z, cmap="viridis", linewidth=0,
                               antialiased=True, rstride=1, cstride=1)
        ax.set_title(f"{name}\nSa={m['Sa_nm']:.2f} nm | Sq={m['Sq_nm']:.2f} nm | "
                     f"Sdr={m['Sdr_pct']:.2f}%", fontsize=8)
        ax.set_xlabel("µm"); ax.set_ylabel("µm"); ax.set_zlabel("nm")
        ax.tick_params(labelsize=6)
    if title:
        fig.suptitle(title, fontsize=13)
    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def run(file=None, folder=None, channel=None, px=None, py=None, output_dir="output"):
    """统一入口 (CLI/GUI 调用).

    file: 单个高度图文件; folder: 批量处理文件夹内所有 .ibw
    返回 dict: {"results": [...], "csv": path, "figures": [...], "grid": path|None}
    """
    from labtoolbox.common.io_utils import ensure_output_dir
    out = ensure_output_dir(output_dir)
    paths = []
    if folder:
        paths = sorted(glob.glob(os.path.join(folder, "*.ibw")))
        if not paths:
            paths = sorted(glob.glob(os.path.join(folder, "*.tif")))
        if not paths:
            raise FileNotFoundError(f"文件夹内未找到 .ibw/.tif 文件: {folder}")
    elif file:
        paths = [file]
    else:
        raise ValueError("必须提供 file 或 folder")
    if not paths:
        raise FileNotFoundError("未找到输入文件")

    results, figures, grid_data = [], [], []
    for p in paths:
        name = os.path.splitext(os.path.basename(p))[0]
        z, px_h, py_h = load_heightmap(p, channel=channel)
        if px is None and px_h is not None:
            px, py = px_h, py_h or px_h
        if px is None:
            raise ValueError(f"像素尺寸未知: {name} — 请用 --px/px 指定 (nm)")
        m = surface_metrics(z, px, py or px)
        results.append({"file": name, "path": p, **m})
        fig_p = os.path.join(out, f"{name}_3D.png")
        plot3d(z, px, py or px, fig_p, title=f"{name}  3D surface")
        figures.append(fig_p)
        grid_data.append((name, z, px, m))
        print(f"  {name}: Sa={m['Sa_nm']:.2f} nm, Sq={m['Sq_nm']:.2f} nm, "
              f"Sz={m['Sz_nm']:.1f} nm, Sdr={m['Sdr_pct']:.3f}%")

    csv_path = os.path.join(out, "surface_metrics_summary.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        wtr = csv.writer(f)
        wtr.writerow(["file", "Sa_nm", "Sq_nm", "Sz_nm", "S3d_um2", "Sproj_um2", "Sdr_pct"])
        for r in results:
            wtr.writerow([r["file"], f"{r['Sa_nm']:.4f}", f"{r['Sq_nm']:.4f}",
                          f"{r['Sz_nm']:.4f}", f"{r['S3d_um2']:.4f}",
                          f"{r['Sproj_um2']:.4f}", f"{r['Sdr_pct']:.4f}"])

    grid_path = None
    if len(grid_data) > 1:
        grid_path = os.path.join(out, "all_3D_grid.png")
        plot_grid(grid_data, grid_path, title="AFM surface analysis (3D)")
    return {"results": results, "csv": csv_path, "figures": figures, "grid": grid_path}
