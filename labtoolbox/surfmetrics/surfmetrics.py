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


_CJK_READY = False


def _setup_cjk_font():
    """让图里的中文正常显示 (matplotlib 默认字体没有汉字 → 出豆腐块)."""
    global _CJK_READY
    if _CJK_READY:
        return
    import matplotlib
    from matplotlib import font_manager
    try:
        available = {f.name for f in font_manager.fontManager.ttflist}
    except Exception:  # noqa: BLE001
        return
    for cand in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC"):
        if cand in available:
            matplotlib.rcParams["font.sans-serif"] = [cand, "DejaVu Sans"]
            matplotlib.rcParams["axes.unicode_minus"] = False
            break
    _CJK_READY = True


def plot3d(z, px, py, out, title=None, z_mode="auto"):
    """单文件 3D 表面图. z: nm; px/py: nm/px.

    z_mode 高度轴显示模式:
      "auto"  (默认) — XY 严格按物理比例 (px:py), z 显示为 xy 平均尺度的 ~25%,
                       形貌起伏清晰可读 (学术图惯例, z 轻微夸大但标注真实 nm 刻度)
      "real"  — z 与 XY 完全同比例 (1 nm = 0.001 µm), 实际结构全等比,
                起伏可能非常扁 (真实物理比例)
      数值    — 手动 z 放大系数 k (k=1.0 即 real)
    """
    import matplotlib
    matplotlib.use("Agg")
    _setup_cjk_font()
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    h, w = z.shape
    xr = (w - 1) * px / 1000.0          # µm
    yr = (h - 1) * (py or px) / 1000.0  # µm
    zr = float(np.ptp(z))               # nm
    k = 1.0
    if z_mode == "auto":
        if zr > 0:
            k = max(0.25 * (xr + yr) / 2.0 / (zr / 1000.0), 1.0)
    elif z_mode == "real":
        k = 1.0
    else:
        k = float(z_mode)
    X, Y = np.meshgrid(np.arange(w) * px / 1000.0, np.arange(h) * (py or px) / 1000.0)
    m = surface_metrics(z, px, py or px)
    fig = plt.figure(figsize=(9, 6.5))
    ax = fig.add_subplot(111, projection="3d")
    surf = ax.plot_surface(X, Y, z, cmap="viridis", linewidth=0,
                           antialiased=True, rstride=1, cstride=1)
    # 横纵轴 (X/Y) 严格按物理尺寸比例 + z 按显示模式; z 数据轴保持真实 nm
    ax.set_box_aspect((xr, yr, zr / 1000.0 * k))
    ax.set_xlabel("X (µm)")
    ax.set_ylabel("Y (µm)")
    ax.set_zlabel("Height (nm)")
    t = title or (f"Sa={m['Sa_nm']:.2f} nm, Sq={m['Sq_nm']:.2f} nm, "
                  f"Sz={m['Sz_nm']:.1f} nm, Sdr={m['Sdr_pct']:.2f}%")
    if z_mode != "auto":
        t += f"  [z ×{k:.2g}]"
    ax.set_title(t, fontsize=10)
    fig.colorbar(surf, shrink=0.6, label="Height (nm)")
    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def plot_profiles(z, px, py, out, row=None, col=None, title=None, z_mode="real"):
    """参考线剖面图: 左 = 3D 形貌 (z 与 XY 同比例, 横/纵两条参考线用虚线标出), 右 = 沿这两条线的深度曲线.

    三维图看整体形貌, 剖面图才是"标尺"——起伏的真实幅度 (P-V) 和周期性只有一条线量得出来。
    row/col: 参考线所在的行/列索引 (默认取正中); z: nm; px/py: nm/px。
    """
    import matplotlib
    matplotlib.use("Agg")
    _setup_cjk_font()
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    h, w = z.shape
    pyv = py or px
    row = h // 2 if row is None else max(0, min(h - 1, int(row)))
    col = w // 2 if col is None else max(0, min(w - 1, int(col)))
    xr = (w - 1) * px / 1000.0          # µm
    yr = (h - 1) * pyv / 1000.0         # µm
    zr = float(np.ptp(z))               # nm
    k = 1.0
    if z_mode == "auto":
        if zr > 0:
            k = max(0.25 * (xr + yr) / 2.0 / (zr / 1000.0), 1.0)
    elif z_mode != "real":
        k = float(z_mode)
    X, Y = np.meshgrid(np.arange(w) * px / 1000.0, np.arange(h) * pyv / 1000.0)
    m = surface_metrics(z, px, pyv)
    fig = plt.figure(figsize=(13.5, 5.4))

    # ── 左: 3D, z 与 XY 同比例 ──
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    surf = ax.plot_surface(X, Y, z, cmap="viridis", linewidth=0,
                           antialiased=True, rstride=1, cstride=1)
    lift = max(zr, 1e-9) * 0.04      # 参考线抬离表面一点, 免得被形貌盖住
    ax.plot(X[row, :], Y[row, :], z[row, :] + lift, color="#0072B2", ls="--", lw=1.6)
    ax.plot(X[:, col], Y[:, col], z[:, col] + lift, color="#D55E00", ls="--", lw=1.6)
    ax.set_box_aspect((xr, yr, zr / 1000.0 * k))
    ax.set_xlabel("X (µm)")
    ax.set_ylabel("Y (µm)")
    ax.set_zlabel("Height (nm)")
    scale_tag = "z 与 XY 同比例" if (z_mode == "real" or abs(k - 1.0) < 1e-9) else f"z ×{k:.3g}"
    ax.set_title(f"{title or '3D surface'}  [{scale_tag}]", fontsize=10)
    ax.view_init(elev=42, azim=-60)
    fig.colorbar(surf, ax=ax, shrink=0.6, pad=0.08, label="Height (nm)")

    # ── 右: 沿两条参考线的深度曲线 ──
    ax2 = fig.add_subplot(1, 2, 2)
    xh = np.arange(w) * px / 1000.0
    yv = np.arange(h) * pyv / 1000.0
    zh = z[row, :]
    zv = z[:, col]
    ax2.plot(xh, zh, color="#0072B2", lw=1.3, label=f"横线  Y = {Y[row, 0]:.2f} µm")
    ax2.plot(yv, zv, color="#D55E00", lw=1.3, label=f"纵线  X = {X[0, col]:.2f} µm")
    ax2.axhline(float(zh.mean()), color="#0072B2", lw=0.6, ls=":", alpha=0.55)
    ax2.axhline(float(zv.mean()), color="#D55E00", lw=0.6, ls=":", alpha=0.55)
    ax2.set_xlabel("Distance (µm)")
    ax2.set_ylabel("Height (nm)")
    ax2.set_title(f"沿参考线的深度曲线   Sa={m['Sa_nm']:.2f} nm | "
                  f"横线 P-V {np.ptp(zh):.1f} nm | 纵线 P-V {np.ptp(zv):.1f} nm", fontsize=10)
    ax2.grid(alpha=0.25)
    ax2.legend(fontsize=9, loc="best")

    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def plot_grid(files_data, out, title=None, z_mode="auto"):
    """多文件 3D 网格图 (≤9 个); XY 等比例, z_mode 同 plot3d"""
    import matplotlib
    matplotlib.use("Agg")
    _setup_cjk_font()
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    n = len(files_data)
    cols = 3 if n > 4 else (2 if n > 1 else 1)
    rows = int(np.ceil(n / cols))
    fig = plt.figure(figsize=(6 * cols, 5 * rows))
    for idx, (name, z, px, m) in enumerate(files_data):
        ax = fig.add_subplot(rows, cols, idx + 1, projection="3d")
        h, w = z.shape
        py = px  # 网格数据统一按 px (方形扫描); 非方形用 px 近似
        xr = (w - 1) * px / 1000.0
        yr = (h - 1) * py / 1000.0
        zr = float(np.ptp(z))
        k = 1.0
        if z_mode == "auto":
            if zr > 0:
                k = max(0.25 * (xr + yr) / 2.0 / (zr / 1000.0), 1.0)
        elif z_mode != "real":
            k = float(z_mode)
        X, Y = np.meshgrid(np.arange(w) * px / 1000.0, np.arange(h) * py / 1000.0)
        surf = ax.plot_surface(X, Y, z, cmap="viridis", linewidth=0,
                               antialiased=True, rstride=1, cstride=1)
        ax.set_box_aspect((xr, yr, zr / 1000.0 * k))
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


def _win2wsl(path):
    """Windows 路径 F:\\x\\y → WSL /mnt/f/x/y"""
    p = path.replace("\\", "/")
    drive = p[0].lower()
    return "/mnt/" + drive + p[2:]


def gwy_batch_wsl(paths, level=True, channel=None, timeout=600):
    """调 WSL Gwyddion 内核批处理 (pygwy)。返回 [{file, channel, mean_nm,
    Sa_nm, Sq_nm, Sz_nm, skew, kurt}]. 依赖: WSL Ubuntu + /usr/local/bin/gwy_batch.py
    (见 labtoolbox 技能 references/gwyddion-pygwy-wsl-batch.md)
    """
    import subprocess, tempfile, csv as _csv
    # gwy_batch.py 收单文件/目录 → 逐文件循环 (每次 ~2-4s JVM/模块启动)
    rows = []
    for p in paths:
        wp = _win2wsl(os.path.abspath(p))
        fd, tmp = tempfile.mkstemp(suffix=".csv", prefix="gwy_")
        os.close(fd)
        tmp_win = tmp.replace("\\", "/")
        tmp_wsl = _win2wsl(tmp_win)   # C:/... → /mnt/c/...
        cmd = ["wsl", "-d", "Ubuntu", "-u", "root", "--", "bash", "-lc",
               "/usr/local/bin/gwy_batch.py '%s' %s %s -o '%s' 2>/dev/null"
               % (wp, "--level" if level else "--raw",
                  ("--channel %d" % channel) if channel is not None else "",
                  "/root/" + os.path.basename(tmp))]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, env=dict(os.environ))
        # 拷回 Windows 临时路径 (WSL 侧须用 /mnt/... 路径)
        subprocess.run(["wsl", "-d", "Ubuntu", "-u", "root", "--", "bash", "-lc",
                        "cp '/root/%s' '%s'" % (os.path.basename(tmp), tmp_wsl)],
                       capture_output=True, timeout=60)
        if os.path.exists(tmp):
            with open(tmp, encoding="utf-8") as f:
                for r in _csv.DictReader(f):
                    rows.append({
                        "file": r["file"], "channel": r["channel"],
                        "mean_nm": float(r["mean_nm"]), "Sa_nm": float(r["Sa_nm"]),
                        "Sq_nm": float(r["Sq_nm"]), "Sz_nm": float(r["Sz_nm"]),
                        "skew": float(r["skew"]), "kurt": float(r["kurt"]),
                    })
            os.unlink(tmp)
        if not rows or rows[-1].get("file") != os.path.basename(p):
            raise RuntimeError("gwy_batch 无输出: %s (err: %s)"
                               % (p, (proc.stderr + proc.stdout)[-300:]))
    return rows


def run(file=None, folder=None, channel=None, px=None, py=None, output_dir="output",
        z_mode="real", backend="python", level=True,
        profiles=True, profile_row=None, profile_col=None):
    """统一入口 (CLI/GUI 调用).

    file: 单个高度图文件; folder: 批量处理文件夹内所有 .ibw
    z_mode: 3D 图 z 轴显示模式 — "real" (默认, z 与 XY 同比例, 不做纵向夸张) /
            "auto" (z 显示为 xy 平均尺度的 ~25%, 起伏扁平时看得清楚) / 数值放大系数
    profiles: 是否额外输出"参考线剖面图" (左 3D 等比例 + 横/纵参考线虚线, 右 沿两条线的深度曲线);
              profile_row/profile_col 指定参考线所在的像素行列 (默认取正中)
    backend: "python" (默认, 自研算法) / "gwyddion" (WSL Gwyddion 2.67 内核,
             真·Gwyddion 平面扣除+统计; level=True 时先平面扣除)
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
    if backend == "gwyddion":
        # ---- Gwyddion 内核后端: 数值来自真·Gwyddion (level + 统计) ----
        gwy_rows = gwy_batch_wsl(paths, level=level, channel=channel)
        gwy_by_file = {r["file"]: r for r in gwy_rows}
        for p in paths:
            name = os.path.splitext(os.path.basename(p))[0]
            g = gwy_by_file.get(os.path.basename(p), {})
            z, px_h, py_h = load_heightmap(p, channel=channel)
            if px is None and px_h is not None:
                px, py = px_h, py_h or px_h
            m_py = surface_metrics(z, px, py or px) if px else None
            results.append({
                "file": name, "path": p, "backend": "gwyddion",
                "level": bool(level),
                "Sa_nm": g.get("Sa_nm"), "Sq_nm": g.get("Sq_nm"),
                "Sz_nm": g.get("Sz_nm"), "skew": g.get("skew"),
                "kurt": g.get("kurt"),
                "S3d_um2": m_py["S3d_um2"] if m_py else None,
                "Sproj_um2": m_py["Sproj_um2"] if m_py else None,
                "Sdr_pct": m_py["Sdr_pct"] if m_py else None,
            })
            if px:
                fig_p = os.path.join(out, f"{name}_3D.png")
                src_tag = "(Gwyddion level)" if level else "(Gwyddion raw)"
                plot3d(z, px, py or px, fig_p, z_mode=z_mode,
                       title=f"{name}  3D surface  {src_tag}")
                figures.append(fig_p)
                if profiles:
                    fig_pr = os.path.join(out, f"{name}_profile.png")
                    plot_profiles(z, px, py or px, fig_pr, row=profile_row, col=profile_col,
                                  title=name, z_mode=z_mode)
                    figures.append(fig_pr)
                grid_data.append((name, z, px, {
                    "Sa_nm": g.get("Sa_nm"), "Sq_nm": g.get("Sq_nm"),
                    "Sdr_pct": m_py["Sdr_pct"] if m_py else 0.0}))
            print(f"  {name}: Sa={g.get('Sa_nm')} nm, Sq={g.get('Sq_nm')} nm, "
                  f"Sz={g.get('Sz_nm')} nm  [Gwyddion kernel]")
        csv_path = os.path.join(out, "surface_metrics_summary.csv")
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            wtr = csv.writer(f)
            wtr.writerow(["file", "backend", "level", "Sa_nm", "Sq_nm", "Sz_nm",
                          "skew", "kurt", "S3d_um2", "Sproj_um2", "Sdr_pct"])
            for r in results:
                wtr.writerow([r["file"], r["backend"], r["level"],
                              f"{r['Sa_nm']:.4f}" if r["Sa_nm"] is not None else "",
                              f"{r['Sq_nm']:.4f}" if r["Sq_nm"] is not None else "",
                              f"{r['Sz_nm']:.4f}" if r["Sz_nm"] is not None else "",
                              f"{r['skew']:.4f}" if r.get("skew") is not None else "",
                              f"{r['kurt']:.4f}" if r.get("kurt") is not None else "",
                              f"{r['S3d_um2']:.4f}" if r["S3d_um2"] is not None else "",
                              f"{r['Sproj_um2']:.4f}" if r["Sproj_um2"] is not None else "",
                              f"{r['Sdr_pct']:.4f}" if r["Sdr_pct"] is not None else ""])
        grid_path = None
        if len(grid_data) > 1:
            grid_path = os.path.join(out, "all_3D_grid.png")
            plot_grid(grid_data, grid_path, title="AFM surface analysis (3D)",
                      z_mode=z_mode)
        return {"results": results, "csv": csv_path, "figures": figures,
                "grid": grid_path}

    # ---- Python 自研后端 (原逻辑) ----
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
        plot3d(z, px, py or px, fig_p, title=f"{name}  3D surface", z_mode=z_mode)
        figures.append(fig_p)
        if profiles:
            fig_pr = os.path.join(out, f"{name}_profile.png")
            plot_profiles(z, px, py or px, fig_pr, row=profile_row, col=profile_col,
                          title=name, z_mode=z_mode)
            figures.append(fig_pr)
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
        plot_grid(grid_data, grid_path, title="AFM surface analysis (3D)", z_mode=z_mode)
    return {"results": results, "csv": csv_path, "figures": figures, "grid": grid_path}
