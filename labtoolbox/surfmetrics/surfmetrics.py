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


def _apply_z_ticks(ax, z, xr, yr, zr, k):
    """Set z ticks so the labels stay readable when the z direction is tiny on screen.

    In true-scale / slightly exaggerated views the z extent can be a few per cent of the XY
    extent, and matplotlib's default 5-6 tick labels then overlap into an unreadable smear.
    Returns True when the ticks were dropped (the colour bar carries the height scale).
    """
    ratio = (zr / 1000.0 * k) / max((xr + yr) / 2.0, 1e-9)
    if ratio < 0.10:
        ax.set_zticks([])
        return True
    if ratio < 0.5:
        ax.set_zticks(np.linspace(float(z.min()), float(z.max()), 3))
    return False


def plot3d(z, px, py, out, title=None, z_mode="real"):
    """Single-file 3D surface map. z: nm; px/py: nm per pixel.

    z_mode: "real" (default) = z axis on the same physical scale as XY, no vertical
            exaggeration; "auto" = z shown at ~25% of the XY extent (keeps shallow relief
            readable); a number = manual z magnification factor.
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
    ticks_hidden = _apply_z_ticks(ax, z, xr, yr, zr, k)
    ax.set_xlabel("X (µm)")
    ax.set_ylabel("Y (µm)")
    ax.set_zlabel("Height (nm)")
    t = title or (f"Sa={m['Sa_nm']:.2f} nm, Sq={m['Sq_nm']:.2f} nm, "
                  f"Sz={m['Sz_nm']:.1f} nm, Sdr={m['Sdr_pct']:.2f}%")
    t += ("  [z and XY at the same scale]" if abs(k - 1.0) < 1e-9
          else f"  [z x{k:.2g}]")
    if ticks_hidden:
        t += "  ·  height scale: see colour bar"
    ax.set_title(t, fontsize=10)
    fig.colorbar(surf, shrink=0.6, label="Height (nm)")
    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def _norm_dir(deg):
    """Fold a ruler direction into [-90, 90) — a line has no sense of forward/backward."""
    return ((float(deg) + 90.0) % 180.0) - 90.0


def stripe_orientation(z, px, py):
    """Dominant stripe (LIPSS-like) direction from the 2D FFT of the height map.

    A corrugated surface shows its periodicity along the direction PERPENDICULAR to the ridges,
    so the FFT peak direction is exactly the direction a profile line has to run to cross the
    ripples. Returns:

        {"cross_deg":  ruler direction that crosses the ripples   (deg, CCW from +X, mod 180)
         "ridge_deg":  ridge (stripe) direction = cross_deg + 90
         "period_nm":  stripe period,
         "strength":   peak / median spectral magnitude — how stripe-like the surface is}
    """
    h, w = z.shape
    yy, xx = np.mgrid[0:h, 0:w]
    A = np.column_stack([xx.ravel() / max(w - 1, 1), yy.ravel() / max(h - 1, 1),
                         np.ones(h * w)])
    coef, *_ = np.linalg.lstsq(A, z.ravel(), rcond=None)             # drop the tilt first
    zp = z - (A @ coef).reshape(h, w)
    F = np.fft.fftshift(np.fft.fft2(zp * np.outer(np.hanning(h), np.hanning(w))))
    mag = np.abs(F)
    cy, cx = h // 2, w // 2
    mag[max(0, cy - 2):cy + 3, max(0, cx - 2):cx + 3] = 0            # kill DC + neighbours
    mag[h // 2:, :] = 0                                              # one half plane (symmetric)
    py2, px2 = np.unravel_index(int(np.argmax(mag)), mag.shape)
    alive = mag[mag > 0]
    med = float(np.median(alive)) if alive.size else 1.0
    fx = (px2 - cx) / (w * px)          # cycles/nm along X
    fy = (py2 - cy) / (h * py)          # cycles/nm along Y
    f = float(np.hypot(fx, fy))
    ang = float(np.degrees(np.arctan2(fy, fx)))      # periodicity direction in the XY plane
    return {"cross_deg": _norm_dir(ang),
            "ridge_deg": _norm_dir(ang + 90.0),
            "period_nm": (1.0 / f) if f > 0 else float("nan"),
            "strength": float(mag[py2, px2]) / (med or 1.0)}


def _sample_line(z, px, py, spec):
    """Sample the height map along one reference line.

    spec = {"kind": "row", "pos": <pixel row>}         ruler along X at that row
           {"kind": "col", "pos": <pixel column>}      ruler along Y at that column
           {"kind": "angle", "deg": <deg CCW from +X>} ruler through the image centre

    Returns (dist_um, height_nm, x_um, y_um): distance along the ruler measured from its start,
    the height profile, and the ruler's coordinates on the surface (for the 3D overlay).
    """
    h, w = z.shape
    kind = (spec or {}).get("kind", "row")
    if kind == "row":
        r = max(0, min(h - 1, int(spec.get("pos", h // 2))))
        i = np.arange(w)
        x = i * px / 1000.0
        y = np.full(w, r * py / 1000.0)
        return x - x[0], z[r, :].astype(float), x, y
    if kind == "col":
        c = max(0, min(w - 1, int(spec.get("pos", w // 2))))
        j = np.arange(h)
        x = np.full(h, c * px / 1000.0)
        y = j * py / 1000.0
        return y - y[0], z[:, c].astype(float), x, y

    th = np.radians(float(spec.get("deg", 0.0)))
    xc, yc = (w - 1) * px / 2000.0, (h - 1) * py / 2000.0       # centre, µm
    dx, dy = np.cos(th), np.sin(th)
    lim = []
    for d, c, hi in ((dx, xc, (w - 1) * px / 1000.0), (dy, yc, (h - 1) * py / 1000.0)):
        if abs(d) < 1e-12:
            continue
        lim.append(((hi - c) / d) if d > 0 else ((0.0 - c) / d))
    L = max(0.0, (min(lim) if lim else 0.0) - 0.02 * min((w - 1) * px, (h - 1) * py) / 1000.0)
    step = max(min(px, py) / 1000.0, 1e-6)
    n = int(max(2, min(4000, round(2 * L / step))))             # ~one sample per pixel
    t = np.linspace(-L, L, n)
    xs, ys = xc + t * dx, yc + t * dy
    fi = np.clip(xs * 1000.0 / px, 0, w - 1.001)
    fj = np.clip(ys * 1000.0 / py, 0, h - 1.001)
    i0, j0 = fi.astype(int), fj.astype(int)
    i1, j1 = i0 + 1, j0 + 1
    wi, wj = fi - i0, fj - j0
    hgt = ((1 - wi) * (1 - wj) * z[j0, i0] + wi * (1 - wj) * z[j0, i1]
           + (1 - wi) * wj * z[j1, i0] + wi * wj * z[j1, i1])
    return t - t[0], hgt.astype(float), xs, ys


def plot_profiles(z, px, py, out, row=None, col=None, title=None, z_mode="real", lines=None):
    """Reference-line profile figure (English only).

    Left  = 3D topography at true z/XY scale with the reference line(s) drawn on the surface and
            labelled with their orientation and position.
    Right = depth profiles measured along those same lines, in matching colours.

    lines=None reproduces the classic two-line figure (H-line along X + V-line along Y, through
    the centre or through ``row``/``col``). Pass ``lines`` to choose the rulers explicitly:

        [{"kind": "angle", "deg": 78.0}]                             # ONE ruler crossing the
                                                                     # ripples (LIPSS)
        [{"kind": "row", "pos": 256}, {"kind": "col", "pos": 256}]   # H + V (isotropic / NP)

    A line is the ruler: peak-to-valley amplitude and the periodicity of a surface are only
    measurable along a profile, while the 3D view shows the overall morphology.
    """
    import matplotlib
    matplotlib.use("Agg")
    _setup_cjk_font()
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    h, w = z.shape
    pyv = py or px
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

    if lines is None:
        r = h // 2 if row is None else max(0, min(h - 1, int(row)))
        c = w // 2 if col is None else max(0, min(w - 1, int(col)))
        lines = [{"kind": "row", "pos": r, "label": f"H-line (along X)\n Y = {r * pyv / 1000.0:.2f} µm"},
                 {"kind": "col", "pos": c, "label": f"V-line (along Y)\n X = {c * px / 1000.0:.2f} µm"}]
    PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7"]

    fig = plt.figure(figsize=(13.5, 5.4))
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    surf = ax.plot_surface(X, Y, z, cmap="viridis", linewidth=0,
                           antialiased=True, rstride=1, cstride=1)
    lift = max(zr, 1e-9) * 0.04      # lift the rulers off the surface so the relief hides nothing
    profiles = []
    for n, spec in enumerate(lines):
        dist, hgt, xs, ys = _sample_line(z, px, pyv, spec)
        col_ = PALETTE[n % len(PALETTE)]
        ax.plot(xs, ys, hgt + lift, color=col_, ls="--", lw=1.7)
        ax.text(xs[0], ys[0], hgt[0] + lift, " " + spec.get("label", f"line {n + 1}"),
                color=col_, fontsize=7.5, zorder=10)
        profiles.append((col_, spec.get("label", f"line {n + 1}").replace("\n", "   "), dist, hgt))
    ax.set_box_aspect((xr, yr, zr / 1000.0 * k))
    ticks_hidden = _apply_z_ticks(ax, z, xr, yr, zr, k)
    ax.set_xlabel("X (µm)")
    ax.set_ylabel("Y (µm)")
    ax.set_zlabel("Height (nm)")
    scale_tag = "z and XY at the same scale" if abs(k - 1.0) < 1e-9 else f"z x{k:.3g}"
    if ticks_hidden:
        scale_tag += "  ·  height scale: see colour bar"
    ax.set_title(f"{title or '3D surface'}   [{scale_tag}]", fontsize=10)
    ax.view_init(elev=42, azim=-60)
    fig.colorbar(surf, ax=ax, shrink=0.6, pad=0.08, label="Height (nm)")

    ax2 = fig.add_subplot(1, 2, 2)
    for col_, label, dist, hgt in profiles:
        ax2.plot(dist, hgt, color=col_, lw=1.3, label=label)
        ax2.axhline(float(hgt.mean()), color=col_, lw=0.6, ls=":", alpha=0.55)
    ax2.set_xlabel("Distance (µm)")
    ax2.set_ylabel("Height (nm)")
    pv = "  |  ".join(f"{lbl.split('   ')[0]} P-V {np.ptp(hgt):.1f} nm"
                      for _c, lbl, _d, hgt in profiles)
    ax2.set_title(f"Depth profiles along the reference line(s)    Sa = {m['Sa_nm']:.2f} nm    {pv}",
                  fontsize=10)
    ax2.grid(alpha=0.25)
    ax2.legend(fontsize=9, loc="best")

    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def profile_lines_for(z, px, py, mode="hv", stripe_angle=None, row=None, col=None):
    """Decide which ruler(s) a figure gets, and describe them.

    mode: "hv"    = H-line + V-line (isotropic surfaces, nanopillar grids)
          "cross" = ONE line crossing the ripples (LIPSS) — direction from the 2D FFT,
                    or from ``stripe_angle`` when given
          "auto"  = "cross" when the surface really is corrugated (FFT peak stands out),
                    otherwise "hv"
    Returns (lines, info) — info carries the detected direction/period for the CSV/report.
    """
    info = {"profile_mode": mode, "stripe_cross_deg": None, "stripe_ridge_deg": None,
            "stripe_period_nm": None, "stripe_strength": None, "line_count": 0}
    if mode in ("cross", "auto"):
        st = stripe_orientation(z, px, py)
        info.update({"stripe_cross_deg": st["cross_deg"], "stripe_ridge_deg": st["ridge_deg"],
                     "stripe_period_nm": st["period_nm"], "stripe_strength": st["strength"]})
        use_cross = True if mode == "cross" else st["strength"] >= 8.0
        if use_cross:
            deg = float(stripe_angle) if stripe_angle is not None else st["cross_deg"]
            period = st["period_nm"]
            info["profile_mode"] = "cross"
            info["line_count"] = 1
            lbl = (f"Ruler across the ripples   θ = {_norm_dir(deg):+.1f}°"
                   + (f"\n (period ≈ {period:.0f} nm)" if period and period == period else ""))
            return [{"kind": "angle", "deg": deg, "label": lbl}], info
        info["profile_mode"] = "hv"
    r = z.shape[0] // 2 if row is None else max(0, min(z.shape[0] - 1, int(row)))
    c = z.shape[1] // 2 if col is None else max(0, min(z.shape[1] - 1, int(col)))
    info["line_count"] = 2
    return [{"kind": "row", "pos": r, "label": f"H-line (along X)\n Y = {r * (py or px) / 1000.0:.2f} µm"},
            {"kind": "col", "pos": c, "label": f"V-line (along Y)\n X = {c * px / 1000.0:.2f} µm"}], info

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


def _profile_cells(r):
    """参考线/条纹那几列 (CSV 用): mode / 线条数 / 跨纹方向 / 条纹走向 / 周期 / 峰强"""
    def fmt(key, nd):
        v = r.get(key)
        return f"{v:.{nd}f}" if isinstance(v, (int, float)) and v == v else ""
    return [r.get("profile_mode") or "",
            r.get("line_count") if r.get("line_count") else "",
            fmt("stripe_cross_deg", 2), fmt("stripe_ridge_deg", 2),
            fmt("stripe_period_nm", 1), fmt("stripe_strength", 2)]


def run(file=None, folder=None, channel=None, px=None, py=None, output_dir="output",
        z_mode="real", backend="python", level=True,
        profiles=True, profile_row=None, profile_col=None,
        profile_mode="hv", stripe_angle=None):
    """统一入口 (CLI/GUI 调用).

    file: 单个高度图文件 (或一组文件的 list); folder: 批量处理文件夹内所有 .ibw
    z_mode: 3D 图 z 轴显示模式 — "real" (默认, z 与 XY 同比例, 不做纵向夸张) /
            "auto" (z 显示为 xy 平均尺度的 ~25%, 起伏扁平时看得清楚) / 数值放大系数
    profiles: 是否额外输出"参考线剖面图" (左 3D 等比例 + 参考线虚线, 右 沿线的深度曲线);
              profile_row/profile_col 指定参考线所在的像素行列 (默认取正中)
    profile_mode: 参考线怎么画 — "hv" (默认, 横+纵两条: 各向同性面/纳米柱网格) /
              "cross" (只一条, 方向由 2D FFT 定, 横跨条纹: LIPSS) / "auto" (周期性明显才用单条)
    stripe_angle: 手动指定跨纹线方向 (度, 相对 +X), 不填则由 FFT 自动判
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
        paths = list(file) if isinstance(file, (list, tuple)) else [file]
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
            pxf = px if px is not None else px_h          # 每份文件各自的像素尺寸
            pyf = py if py is not None else (py_h or pxf)
            m_py = surface_metrics(z, pxf, pyf or pxf) if pxf else None
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
            if pxf:
                fig_p = os.path.join(out, f"{name}_3D.png")
                src_tag = "(Gwyddion level)" if level else "(Gwyddion raw)"
                plot3d(z, pxf, pyf or pxf, fig_p, z_mode=z_mode,
                       title=f"{name}  3D surface  {src_tag}")
                figures.append(fig_p)
                if profiles:
                    fig_pr = os.path.join(out, f"{name}_profile.png")
                    _lines, _pinfo = profile_lines_for(z, pxf, pyf or pxf, profile_mode,
                                                       stripe_angle=stripe_angle,
                                                       row=profile_row, col=profile_col)
                    plot_profiles(z, pxf, pyf or pxf, fig_pr, title=name, z_mode=z_mode,
                                  lines=_lines)
                    figures.append(fig_pr)
                    results[-1].update(_pinfo)
                grid_data.append((name, z, pxf, {
                    "Sa_nm": g.get("Sa_nm"), "Sq_nm": g.get("Sq_nm"),
                    "Sdr_pct": m_py["Sdr_pct"] if m_py else 0.0}))
            print(f"  {name}: Sa={g.get('Sa_nm')} nm, Sq={g.get('Sq_nm')} nm, "
                  f"Sz={g.get('Sz_nm')} nm  [Gwyddion kernel]")
        csv_path = os.path.join(out, "surface_metrics_summary.csv")
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            wtr = csv.writer(f)
            wtr.writerow(["file", "backend", "level", "Sa_nm", "Sq_nm", "Sz_nm",
                          "skew", "kurt", "S3d_um2", "Sproj_um2", "Sdr_pct",
                          "profile_mode", "n_lines", "stripe_cross_deg", "stripe_ridge_deg",
                          "stripe_period_nm", "stripe_strength"])
            for r in results:
                wtr.writerow([r["file"], r["backend"], r["level"],
                              f"{r['Sa_nm']:.4f}" if r["Sa_nm"] is not None else "",
                              f"{r['Sq_nm']:.4f}" if r["Sq_nm"] is not None else "",
                              f"{r['Sz_nm']:.4f}" if r["Sz_nm"] is not None else "",
                              f"{r['skew']:.4f}" if r.get("skew") is not None else "",
                              f"{r['kurt']:.4f}" if r.get("kurt") is not None else "",
                              f"{r['S3d_um2']:.4f}" if r["S3d_um2"] is not None else "",
                              f"{r['Sproj_um2']:.4f}" if r["Sproj_um2"] is not None else "",
                              f"{r['Sdr_pct']:.4f}" if r["Sdr_pct"] is not None else ""]
                             + _profile_cells(r))
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
        pxf = px if px is not None else px_h          # 每份文件各自的像素尺寸
        pyf = py if py is not None else (py_h or pxf)
        if pxf is None:
            raise ValueError(f"像素尺寸未知: {name} — 请用 --px/px 指定 (nm)")
        m = surface_metrics(z, pxf, pyf or pxf)
        results.append({"file": name, "path": p, **m})
        fig_p = os.path.join(out, f"{name}_3D.png")
        plot3d(z, pxf, pyf or pxf, fig_p, title=f"{name}  3D surface", z_mode=z_mode)
        figures.append(fig_p)
        if profiles:
            fig_pr = os.path.join(out, f"{name}_profile.png")
            _lines, _pinfo = profile_lines_for(z, pxf, pyf or pxf, profile_mode,
                                               stripe_angle=stripe_angle,
                                               row=profile_row, col=profile_col)
            plot_profiles(z, pxf, pyf or pxf, fig_pr, title=name, z_mode=z_mode, lines=_lines)
            figures.append(fig_pr)
            results[-1].update(_pinfo)
        grid_data.append((name, z, pxf, m))
        print(f"  {name}: Sa={m['Sa_nm']:.2f} nm, Sq={m['Sq_nm']:.2f} nm, "
              f"Sz={m['Sz_nm']:.1f} nm, Sdr={m['Sdr_pct']:.3f}%")

    csv_path = os.path.join(out, "surface_metrics_summary.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        wtr = csv.writer(f)
        wtr.writerow(["file", "Sa_nm", "Sq_nm", "Sz_nm", "S3d_um2", "Sproj_um2", "Sdr_pct",
                      "profile_mode", "n_lines", "stripe_cross_deg", "stripe_ridge_deg",
                      "stripe_period_nm", "stripe_strength"])
        for r in results:
            wtr.writerow([r["file"], f"{r['Sa_nm']:.4f}", f"{r['Sq_nm']:.4f}",
                          f"{r['Sz_nm']:.4f}", f"{r['S3d_um2']:.4f}",
                          f"{r['Sproj_um2']:.4f}", f"{r['Sdr_pct']:.4f}"]
                         + _profile_cells(r))

    grid_path = None
    if len(grid_data) > 1:
        grid_path = os.path.join(out, "all_3D_grid.png")
        plot_grid(grid_data, grid_path, title="AFM surface analysis (3D)", z_mode=z_mode)
    return {"results": results, "csv": csv_path, "figures": figures, "grid": grid_path}
