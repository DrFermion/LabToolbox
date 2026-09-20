# -*- coding: utf-8 -*-
"""细菌在织构表面的 3D 示意图 + 接触几何图 (纯 matplotlib, 严格同比例).

风格: 灰阶轴测表面 + 绿杆/橙球细菌 + 红虚线尺寸标注 + 蓝虚线俯视/剖面小图.
几何全部来自 geometry.py 的实测值; 细胞尺寸默认为文献标称值 (可覆盖).
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

try:                                     # 与 surfmetrics 一致的中文字体设置
    from ..surfmetrics.surfmetrics import _setup_cjk_font
    _setup_cjk_font()
except Exception:
    pass

GREY = np.array([0.60, 0.61, 0.63])
GREEN = np.array([0.13, 0.60, 0.26])
ORANGE = np.array([0.95, 0.52, 0.12])
LIGHT = np.array([0.5, 0.35, 0.62]); LIGHT /= np.linalg.norm(LIGHT)
RED, BLUE, DARK = "#d81f1f", "#12296b", "#2b2b2b"
LS = matplotlib.colors.LightSource(azdeg=235, altdeg=32)

# 文献标称尺寸 (µm) —— 不是本组实测, 图注/README 必须写明
ECOLI_L, ECOLI_D, SAUREUS_D = 2.0, 0.5, 0.9


# ------------------------------------------------------------------ 基础
def _shade(fc, nrm, base=0.32, gain=0.75):
    lam = np.clip(nrm @ LIGHT, 0, 1)
    rgba = np.zeros(nrm.shape[:2] + (4,))
    rgba[..., :3] = np.clip(fc[None, None, :] * (base + gain * lam)[..., None], 0, 1)
    rgba[..., 3] = 1.0
    return rgba


def _normals(Z, dx, dy):
    a, b = np.gradient(Z, dx, dy)
    n = np.dstack([-a, -b, np.ones_like(Z)])
    return n / np.linalg.norm(n, axis=2, keepdims=True)


def _lipss_xyz(W, H, period, depth, nx=560, ny=300):
    """LIPSS: 起伏沿 Y 变化 → 条纹(脊)沿 X → 细胞 0°(沿 X) 即平行于条纹."""
    x, y = np.linspace(0, W, nx), np.linspace(0, H, ny)
    X, Y = np.meshgrid(x, y)
    return X, Y, 0.5 * depth * np.cos(2 * np.pi * Y / period) - 0.5 * depth


def _pillar_xyz(W, H, spacing, height, nx=420, ny=230, seed=7):
    rng = np.random.default_rng(seed)
    x, y = np.linspace(0, W, nx), np.linspace(0, H, ny)
    X, Y = np.meshgrid(x, y)
    Z = np.zeros_like(X)
    for i in range(int(W / spacing) + 2):
        for j in range(int(H / spacing) + 2):
            cx = (i - 0.5) * spacing + rng.normal(0, 0.02 * spacing)
            cy = (j - 0.5) * spacing + rng.normal(0, 0.02 * spacing)
            r = 0.36 * spacing * (1 + rng.normal(0, 0.10))
            h = height * (1 + rng.normal(0, 0.12))
            d = np.hypot(X - cx, Y - cy)
            Z += np.maximum(0, h * np.cos(np.clip(d / r, 0, 1) * np.pi / 2) ** 2)
    return X, Y, Z - Z.min()


def _capsule_mesh(length, diam, nu1=16, nu2=34, nv=64):
    r = diam / 2
    xs, rs = [], []
    for u in np.linspace(0, np.pi / 2, nu1):
        xs.append(r * (1 - np.cos(u))); rs.append(r * np.sin(u))
    for t in np.linspace(0, length - 2 * r, nu2):
        xs.append(r + t); rs.append(r)
    for u in np.linspace(np.pi / 2, np.pi, nu1):
        xs.append((length - r) + r * (1 - np.cos(u))); rs.append(r * np.sin(u))
    xs, rs = np.array(xs), np.array(rs)
    TH = np.linspace(0, 2 * np.pi, nv)
    XS, THS = np.meshgrid(xs, TH)
    RS, _ = np.meshgrid(rs, TH)
    return XS, RS * np.cos(THS), RS * np.sin(THS)


def _capsule(ax, center, theta_deg, length=ECOLI_L, diam=ECOLI_D, z=12):
    XS, YC, ZC = _capsule_mesh(length, diam)
    th = np.radians(theta_deg)
    ax.plot_surface(XS * np.cos(th) - YC * np.sin(th) + center[0],
                    XS * np.sin(th) + YC * np.cos(th) + center[1], ZC + center[2],
                    color=tuple(GREEN), linewidth=0, antialiased=False, shade=True, lightsource=LS, zorder=z)


def _sphere(ax, center, diam=SAUREUS_D, n=56, z=12):
    u, v = np.linspace(0, np.pi, n), np.linspace(0, 2 * np.pi, n)
    U, V = np.meshgrid(u, v); r = diam / 2
    ax.plot_surface(r * np.sin(U) * np.cos(V) + center[0], r * np.sin(U) * np.sin(V) + center[1],
                    r * np.cos(U) + center[2], color=tuple(ORANGE), linewidth=0,
                    antialiased=False, shade=True, lightsource=LS, zorder=z)


# ------------------------------------------------------------------ 3D 面板
def _figure(kind, geom, label, out_base, cell=(ECOLI_L, ECOLI_D), coccus=SAUREUS_D, dpi=190):
    W, H = 5.5, 2.8                       # µm 视野 (容纳整个细胞 + 余量)
    if kind == "lipss":
        period = geom["lipss"]["period_nm"]["mean"] / 1000.0
        depth = geom["lipss"]["depth_nm"]["mean"] / 1000.0
        X, Y, Z = _lipss_xyz(W, H, period, depth)
        skw = {}
        title = (f"Bacterial adhesion on {label} LIPSS-textured 316L stainless steel — "
                 f"measured period {period * 1000:.0f} nm, depth {depth * 1000:.0f} nm (to scale)")
        subs = {"period": period, "depth": depth, "spacing": 0.190}
    else:
        spacing = geom["nanopillar"]["spacing_nm"]["mean"] / 1000.0
        height = geom["nanopillar"]["height_nm"]["mean"] / 1000.0
        X, Y, Z = _pillar_xyz(W, H, spacing, height)
        skw = dict(base=0.22, gain=1.05)
        title = (f"Bacterial adhesion on {label} nanopillar-textured 316L stainless steel — "
                 f"measured spacing {spacing * 1000:.0f} nm, height {height * 1000:.0f} nm (to scale)")
        subs = {"spacing": spacing, "height": height, "period": 0.412}
    N = _normals(Z, X[0, 1] - X[0, 0], Y[1, 0] - Y[0, 0])
    ztop, zbot = Z.max(), Z.min()
    ec_l, ec_d = cell
    sa_d = coccus

    fig = plt.figure(figsize=(20, 5.6))
    L, R, T, B = 0.004, 0.996, 0.905, 0.055
    GW, GH = (R - L) / 5, (T - B)

    def panel(col, name, zlim):
        x0 = L + col * GW
        ax = fig.add_axes([x0, T - GH, GW, GH], projection="3d")
        ax.computed_zorder = False                      # 手动 z 序: 细胞必须压在表面之上
        ax.set_proj_type("ortho")
        ax.view_init(elev=16, azim=-64)
        ax.set_box_aspect((W, H, zlim[1] - zlim[0]), zoom=1.30)
        ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_zlim(*zlim)
        ax.set_axis_off()
        ax.set_title(name, fontsize=13, pad=-2)
        return ax, (x0, T - GH, GW, GH)

    def surf(ax):
        ax.plot_surface(X, Y, Z, facecolors=_shade(GREY, N, **skw), linewidth=0,
                        antialiased=False, shade=False, zorder=1)

    # (a) 形貌 + 剖面
    ax, b = panel(0, "(a) Surface morphology", (zbot - 0.30, ztop + 0.75))
    surf(ax)
    _xsection(fig, b, kind, subs, label)

    # (b)(c)(d) 三种取向
    for col, ang, name in ((1, 0, "(b) E. coli — parallel (0°)"),
                           (2, 45, "(c) E. coli — 45°"),
                           (3, 90, "(d) E. coli — perpendicular (90°)")):
        ax, b = panel(col, name, (zbot - 0.30, ztop + ec_d / 2 + 0.45))
        surf(ax)
        _capsule(ax, (W / 2, H / 2, ztop + ec_d / 2), ang, length=ec_l, diam=ec_d)
        _topview(fig, b, kind, theta_deg=ang, period=subs.get("period", 0.412),
                 spacing=subs.get("spacing", 0.190))

    # (e) 球菌
    ax, b = panel(4, "(e) S. aureus — cocci", (zbot - 0.30, ztop + sa_d + 0.55))
    surf(ax)
    for yy in (H / 2 - 0.75, H / 2, H / 2 + 0.75):
        _sphere(ax, (W / 2, yy, ztop + sa_d / 2), diam=sa_d)
    _topview(fig, b, kind, coccus=True, coccus_d=sa_d, period=subs.get("period", 0.412),
             spacing=subs.get("spacing", 0.190))

    from matplotlib.lines import Line2D
    h = [Line2D([0], [0], marker="o", color="w", markerfacecolor=tuple(GREEN), markersize=15,
                label=f"E. coli — rod, {ec_l:.1f} × {ec_d:.1f} µm"),
         Line2D([0], [0], marker="o", color="w", markerfacecolor=tuple(ORANGE), markersize=13,
                label=f"S. aureus — cocci, {sa_d:.1f} µm"),
         Line2D([0], [0], marker="o", color="w", markerfacecolor=RED, markersize=8,
                label="predicted contact points"),
         Line2D([0], [0], color=RED, ls=(0, (4, 3)), lw=2, label="AFM-measured dimensions")]
    fig.legend(handles=h, loc="lower center", ncol=4, frameon=False, fontsize=12, bbox_to_anchor=(0.5, 0.008))
    fig.text(0.5, 0.965, title, ha="center", fontsize=16)
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_base}.{ext}", dpi=dpi)
    plt.close(fig)
    return f"{out_base}.png"


def _topview(fig, bounds, kind, theta_deg=None, coccus=False, coccus_d=SAUREUS_D,
             period=0.412, spacing=0.190):
    x0, y0, gw, gh = bounds
    ax = fig.add_axes([x0 + gw * 0.63 - 0.004, y0 + gh * 0.02, gw * 0.37, gh * 0.43])
    ax.set_xlim(0, 2.6); ax.set_ylim(0, 1.6)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#1a49c8"); s.set_linestyle((0, (3, 2))); s.set_linewidth(1.2)
    ax.set_facecolor("#fbfbfd")
    ax.set_aspect("equal", adjustable="datalim")      # 圆就是圆, 不被拉成椭圆
    if kind == "lipss":
        for e in np.arange(0, 1.9, period):          # 条纹沿 X, 故用水平色带
            ax.axhspan(e, e + period / 2, color="#b9bac0", lw=0)
    else:
        for i in range(14):
            for j in range(9):
                ax.add_patch(Circle((0.09 + i * spacing, 0.09 + j * spacing), 0.40 * spacing,
                                    color="#9fa1a8", lw=0))
    # 平行于条纹的杆放在"脊顶"上 (灰带 = 沟, 无填充 = 脊顶 → 周期内 0.5–1.0 为脊顶)
    cy = 0.75 * period + round((0.80 - 0.75 * period) / period) * period if kind == "lipss" else 0.80
    if coccus:
        ax.add_patch(Circle((1.30, cy), coccus_d / 2, fill=False, ec=tuple(ORANGE), lw=2.4))
        for xx in (0.72, 1.10, 1.48, 1.86):
            ax.plot([xx, xx], [cy - 0.10, cy + 0.10], color=RED, lw=3.6, solid_capstyle="round")
    else:
        th = np.radians(theta_deg or 0)
        dx, dy = np.cos(th) * ECOLI_L / 2, np.sin(th) * ECOLI_L / 2
        x0_, x1_, y0_, y1_ = 1.30 - dx, 1.30 + dx, cy - dy, cy + dy
        ax.plot([x0_, x1_], [y0_, y1_], color=DARK, lw=8, solid_capstyle="round", alpha=0.85)
        for t in np.linspace(0.06, 0.94, 9):
            px, py = x0_ + t * (x1_ - x0_), y0_ + t * (y1_ - y0_)
            if kind == "lipss":
                band = (py % period) / period          # 沿 Y 度量"跨条纹"位置
                if abs(band - 0.75) <= 0.20:           # 落在脊顶 → 接触
                    ax.add_patch(Circle((px, py), 0.09, color=RED, zorder=6))
            else:
                ax.add_patch(Circle((px, py), 0.09, color=RED, zorder=6))
    if theta_deg is not None:
        ax.annotate("", xy=(1.92, 1.20), xytext=(1.92, 0.40),
                    arrowprops=dict(arrowstyle="<->", color="#1a49c8", lw=1.4))
        ax.plot([1.05, 2.20], [0.40, 0.40], color="#1a49c8", lw=1.4, ls="--")
        ax.text(2.02, 1.02, f"{theta_deg:.0f}°", color="#1a49c8", fontsize=15.5, ha="left",
                va="center", weight="bold")
    ax.text(0.06, 1.52, "top view", color="#1a49c8", fontsize=11, ha="left", va="top")
    ax.plot([1.98, 2.48], [0.10, 0.10], color=DARK, lw=2.6)
    ax.text(2.23, 0.17, "1 µm", color=DARK, fontsize=10.5, ha="center")


def _xsection(fig, bounds, kind, subs, label):
    x0, y0, gw, gh = bounds
    ax = fig.add_axes([x0 + gw * 0.03, y0 + gh * 0.02, gw * 0.40, gh * 0.42])
    if kind == "lipss":
        period, depth = subs["period"], subs["depth"]
        x = np.linspace(0, 2.2, 900)
        z = 0.5 * depth * np.cos(2 * np.pi * x / period)
        y = z.max() + 0.10
        ax.annotate("", xy=(0.35, y), xytext=(0.35 + period, y),
                    arrowprops=dict(arrowstyle="<->", color=RED, lw=1.8, linestyle=(0, (5, 3))))
        ax.text(0.35 + period / 2, y + 0.06, f"{period * 1000:.0f} nm period", color=BLUE,
                fontsize=12.5, ha="center", weight="bold")
        xd = 2.0
        ax.annotate("", xy=(xd, z.min()), xytext=(xd, z.max()),
                    arrowprops=dict(arrowstyle="<->", color=RED, lw=1.8, linestyle=(0, (5, 3))))
        ax.text(xd - 0.07, 0, f"{depth * 1000:.0f} nm depth", color=BLUE, fontsize=12.5,
                ha="right", va="center", rotation=90, weight="bold")
        top, bot = z.max() + 0.15, z.min() - 0.05
    else:
        spacing, height = subs["spacing"], subs["height"]
        x = np.linspace(0, 2.2, 2000)
        z = np.zeros_like(x)
        rng = np.random.default_rng(11)
        r = 0.36 * spacing
        for i in range(int(2.2 / spacing) + 2):
            cx = (i - 0.5) * spacing + rng.normal(0, 0.02 * spacing)
            d = np.abs(x - cx)
            z = z + np.where(d < r, height * np.cos(np.clip(d / r, 0, 1) * np.pi / 2) ** 2, 0)
        y = z.max() + 0.045
        ax.annotate("", xy=(0.5, y), xytext=(0.5 + spacing, y),
                    arrowprops=dict(arrowstyle="<->", color=RED, lw=1.8, linestyle=(0, (5, 3))))
        ax.text(0.5 + spacing / 2, y + 0.035, "~%.0f nm spacing" % (spacing * 1000), color=BLUE,
                fontsize=11.5, ha="center", weight="bold")
        xd = 2.05
        ax.annotate("", xy=(xd, 0), xytext=(xd, height),
                    arrowprops=dict(arrowstyle="<->", color=RED, lw=1.8, linestyle=(0, (5, 3))))
        ax.text(xd - 0.075, height / 2, "~%.0f nm height" % (height * 1000), color=BLUE,
                fontsize=12, ha="right", va="center", rotation=90, weight="bold")
        top, bot = z.max() + 0.15, -0.05
    ax.fill_between(x, z, z.min() - 0.03, color="#c3c4ca", lw=1.2, edgecolor="#8a8c94")
    ax.set_xlim(0, 2.2); ax.set_ylim(bot, top)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#1a49c8"); s.set_linestyle((0, (3, 2))); s.set_linewidth(1.2)
    ax.set_facecolor("#fbfbfd")
    ax.text(0.05, 0.97, "cross-section", color="#1a49c8", fontsize=11, ha="left", va="top",
            transform=ax.transAxes)


# ------------------------------------------------------------------ 接触几何
def _min_dist(xc, zc, R, x):
    return float(np.min(np.hypot(x - xc, _ripple(x) - zc)))


def _ripple(x, period=412.0, amp=50.0):
    return amp * np.cos(2 * np.pi * x / period)


def _resting_zc(xc, R, x, period, amp):
    def md(zc):
        return float(np.min(np.hypot(x - xc, _ripple(x, period, amp) - zc)))
    lo, hi = -amp - 100.0, amp + 2 * R + 500.0
    for _ in range(70):
        mid = (lo + hi) / 2
        if md(mid) < R:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _contacts(xc, zc, R, x, period, amp):
    d = np.hypot(x - xc, _ripple(x, period, amp) - zc)
    idx = [i for i in range(1, len(x) - 1)
           if d[i] <= d[i - 1] and d[i] <= d[i + 1] and d[i] < R * 1.002]
    keep = []
    for i in idx:
        if not keep or x[i] - keep[-1] > period * 0.25:
            keep.append(i)
    return [(x[i], float(_ripple(x[i], period, amp))) for i in keep]


def render_contact_geometry(geom, out_base, label="515 nm",
                            coccus_d=SAUREUS_D, rod_d=ECOLI_D, dpi=190):
    """三面板: 球形菌 SEI 几何 / 杆菌平行 (真实相切) / 杆菌跨越 (只碰脊顶)."""
    period = geom["lipss"]["period_nm"]["mean"]
    depth = geom["lipss"]["depth_nm"]["mean"]
    amp = depth / 2.0
    R_C, R_R = coccus_d * 500.0, rod_d * 500.0        # µm→nm 半径
    X = np.linspace(-700, 1200, 20000)

    fig, axs = plt.subplots(1, 3, figsize=(20, 6.6))
    fig.subplots_adjust(left=0.025, right=0.995, top=0.88, bottom=0.10, wspace=0.13)

    def base(ax, x0=-760, x1=1240):
        ax.fill_between(X, _ripple(X, period, amp), -140, color="#c9ccd4", lw=0)
        ax.plot(X, _ripple(X, period, amp), color="#6f7480", lw=1.7, zorder=3)
        ax.set_xlim(x0, x1); ax.set_ylim(-330, 1250)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_aspect("equal")
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_xlabel("distance along the surface (nm)", fontsize=11, labelpad=1)

    def txt(ax, x, y, s, color=DARK, fs=16, ha="center", va="center", weight="normal", bg=False):
        kw = dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85) if bg else None
        ax.text(x, y, s, color=color, fontsize=fs, ha=ha, va=va, style="italic", weight=weight,
                zorder=25, bbox=kw)

    def dline(ax, p0, p1):
        ax.annotate("", xy=p1, xytext=p0,
                    arrowprops=dict(arrowstyle="<->", color=RED, lw=1.5, linestyle=(0, (5, 3))), zorder=20)

    # (a) 球形菌 + SEI 符号
    ax = axs[0]
    xc = 0.0
    zc = _resting_zc(xc, R_C, X, period, amp) + 60.0
    base(ax)
    ax.add_patch(Circle((xc, zc), R_C, fill=False, ec=BLUE, lw=2.8, zorder=12))
    ax.plot([xc, xc], [zc, _ripple(xc, period, amp)], color=RED, lw=1.6, ls=(0, (4, 3)), zorder=20)
    txt(ax, xc + 26, (zc + _ripple(xc, period, amp)) / 2 + 8, "h", fs=16, color=RED, ha="left", bg=True)
    ax.plot([xc, xc - R_C * 0.66], [zc, zc + R_C * 0.75], color=DARK, ls=(0, (4, 3)), lw=1.2, zorder=18)
    txt(ax, xc - R_C * 0.50, zc + R_C * 0.55, "R", fs=18, bg=True)
    xp = xc + 300.0
    ax.plot([xc, xp], [zc, zc], color=DARK, ls=(0, (4, 3)), lw=1.2, zorder=18)
    txt(ax, xc + 150, zc + 34, "r", fs=18)
    ax.plot([xp, xp], [_ripple(xp, period, amp), zc], color=DARK, ls=(0, (2, 2)), lw=1.2, zorder=18)
    txt(ax, xp + 40, (_ripple(xp, period, amp) + zc) / 2, r"$\sqrt{R^2-r^2}$", fs=15, ha="left", bg=True)
    tt = np.linspace(0, np.arctan2(300, R_C), 60)
    ax.plot(xc + 170 * np.sin(tt), zc - 170 * np.cos(tt), color=BLUE, lw=1.5, zorder=18)
    txt(ax, xc + 58, zc - 196, r"$\theta$", fs=17, color=BLUE, bg=True)
    ze = zc - np.sqrt(max(R_C ** 2 - 300 ** 2, 1))
    dline(ax, (xp, _ripple(xp, period, amp)), (xp, ze))
    txt(ax, xp + 26, (_ripple(xp, period, amp) + ze) / 2, "D", fs=16, color=RED, ha="left")
    ax.annotate("", xy=(period, _ripple(period, period, amp) - 8), xytext=(0, _ripple(0, period, amp) - 8),
                arrowprops=dict(arrowstyle="<->", color=RED, lw=1.6, linestyle=(0, (5, 3))), zorder=20)
    txt(ax, period / 2, _ripple(0, period, amp) - 78, f"Λ = {period:.0f} nm", fs=13, color=RED, weight="bold")
    ax.annotate("", xy=(-period * 0.98, _ripple(-period, period, amp) + 4),
                xytext=(-period * 0.98, _ripple(-period / 2, period, amp) + 4),
                arrowprops=dict(arrowstyle="<->", color=RED, lw=1.4, linestyle=(0, (5, 3))), zorder=20)
    txt(ax, -period * 1.32, 0, f"{depth:.0f} nm", fs=12, color=RED, weight="bold")
    txt(ax, xc, _ripple(0, period, amp) + R_C + 190,
        f"spherical cell,  R = {R_C:.0f} nm  (S. aureus Ø {coccus_d:.1f} µm)", fs=12.5, weight="normal")
    txt(ax, xc, _ripple(0, period, amp) + R_C + 120, r"$D(r)=h+R-\sqrt{R^2-r^2}$", fs=13, color=BLUE,
        weight="normal")
    ax.set_title("(a) Sphere above a ridge — SEI geometry", fontsize=13.5, pad=6)

    # (b) 杆菌平行 → 真实相切 (沟两侧斜坡)
    ax = axs[1]
    xc = period / 2 + period
    zc = _resting_zc(xc, R_R, X, period, amp)
    base(ax)
    ax.add_patch(Circle((xc, zc), R_R, fill=False, ec=BLUE, lw=2.8, zorder=12))
    for px, pz in _contacts(xc, zc, R_R, X, period, amp):
        ax.plot(px, pz, marker="o", ms=10, color=RED, zorder=22)
    ax.plot([xc, xc], [zc, -140], color=DARK, ls=(0, (2, 2)), lw=1.1, zorder=8)
    ax.plot([xc, xc + R_R * 0.95], [zc, zc + R_R * 0.30], color=DARK, ls=(0, (4, 3)), lw=1.2, zorder=18)
    txt(ax, xc + R_R * 0.62, zc + R_R * 0.26, "R", fs=18, bg=True)
    txt(ax, xc, amp + 560, "rod axis parallel to the striations", fs=12.5, weight="normal")
    txt(ax, xc, amp + 490, f"R/Λ ≈ {R_R / period:.1f} → line contacts on the groove slopes",
        fs=12, weight="normal")
    ax.set_title("(b) Rod cell (E. coli) — parallel to LIPSS", fontsize=13.5, pad=6)

    # (c) 杆菌跨越 → 只碰脊顶
    ax = axs[2]
    base(ax)
    zr = amp
    ax.fill_between([-700, 1200], zr, zr + 500, color="#a9d5b4", alpha=0.5, zorder=5)
    ax.plot([-700, 1200], [zr, zr], color=BLUE, lw=2.8, zorder=12)
    ax.plot([-700, 1200], [zr + 500, zr + 500], color=BLUE, lw=1.6, linestyle=(0, (7, 5)), zorder=11)
    for m in range(-1, 4):
        cx = m * period
        ax.plot(cx, _ripple(cx, period, amp), marker="o", ms=10, color=RED, zorder=22)
    cx0 = 1.5 * period
    dline(ax, (cx0, _ripple(cx0 + period / 2, period, amp)), (cx0, zr))
    txt(ax, cx0 + 26, (_ripple(cx0 + period / 2, period, amp) + zr) / 2, "h", fs=16, color=RED,
        ha="left", bg=True)
    txt(ax, 0.0, zr + 700, "rod axis perpendicular to the striations", fs=12.5, weight="normal")
    txt(ax, 0.0, zr + 630, "touches ridge crests only → discontinuous contact", fs=12, weight="normal")
    ax.set_title("(c) Rod cell — perpendicular (side view, ≙ cross-section of the ripples)",
                 fontsize=13, pad=6)

    fig.suptitle(f"Contact geometry of bacterial cells on {label} laser-induced periodic surface "
                 f"structures (LIPSS) — measured period Λ = {period:.0f} nm, depth = {depth:.0f} nm",
                 fontsize=14, y=0.965)
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_base}.{ext}", dpi=dpi)
    plt.close(fig)
    return f"{out_base}.png"


# ------------------------------------------------------------------ 一键
def render_all(geom, out_dir, label="515 nm", dpi=190, cell=(ECOLI_L, ECOLI_D),
               coccus=SAUREUS_D):
    """出 fig1(LIPSS) / fig2(纳米柱) / fig3(接触几何), 返回文件列表."""
    os.makedirs(out_dir, exist_ok=True)
    made = []
    if geom["lipss"]["period_nm"]["n"]:
        made.append(_figure("lipss", geom, label, os.path.join(out_dir, "fig1_LIPSS_adhesion"), cell, coccus, dpi))
        made.append(render_contact_geometry(geom, os.path.join(out_dir, "fig3_contact_geometry"), label,
                                            coccus, cell[1], dpi))
    if geom["nanopillar"]["spacing_nm"]["n"]:
        made.append(_figure("pillars", geom, label, os.path.join(out_dir, "fig2_nanopillar_adhesion"), cell, coccus, dpi))
    return made
