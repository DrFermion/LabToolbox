# -*- coding: utf-8 -*-
"""Schematic figures for the laser-textured antibacterial review (EN + ZH).
Generates into <OUTDIR>/figures/:
  fig1_process_map_{lang}.png/pdf        – process map: fluence vs pulses per spot
  fig2_lipss_mechanism_{lang}.png/pdf    – LIPSS formation physics, 4 panels
  fig3_antibacterial_{lang}.png/pdf      – antibacterial mechanisms, 4 panels
Usage: python make_review_figures.py [output_dir]
Rendered at final print width 6.1 in (15.5 cm), 300 dpi, fonts 8–10.5 pt.
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle, Polygon, Ellipse, Circle, FancyArrowPatch, FancyBboxPatch

OUTDIR = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:\Users\PC\AppData\Local\hermes\cache\scratch\review_20261007\build"
FIGDIR = os.path.join(OUTDIR, "figures")
os.makedirs(FIGDIR, exist_ok=True)

PAL = dict(steel="#9AA6B0", steel_dark="#525C66", steel_edge="#3E474F",
           laser="#E4572E", wave="#2F6FD0", energy="#D94838",
           bac="#4CAF6D", bac_edge="#2A7D47", bac_dead="#B9C6BC",
           mem="#C0466F", oxide="#C79A4B", prot1="#8E6FC0", prot2="#D98C5F", prot3="#5FA8D3",
           ink="#3F4A54", dim="#2F6FD0", grey="#6B7680")
FONTS = {"en": ["Arial", "DejaVu Sans"], "zh": ["Microsoft YaHei", "SimHei", "DejaVu Sans"]}
DEJAVU = FontProperties(family="DejaVu Sans")   # glyph fallback (⊥ etc.) for EN figures


def apply_style(lang):
    plt.rcParams.update({
        "font.sans-serif": FONTS[lang], "font.family": "sans-serif",
        "axes.unicode_minus": False, "font.size": 9.5,
        "savefig.dpi": 300, "figure.dpi": 300,
    })


def _arrow(ax, p1, p2, color, lw=1.6, rad=0.0, style="-|>", ms=9, z=8):
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=ms,
                        color=color, lw=lw, connectionstyle=f"arc3,rad={rad}",
                        shrinkA=0, shrinkB=0, zorder=z)
    ax.add_patch(a)


def _dim(ax, p1, p2, text, color=None, fs=9, dy=0.03):
    color = color or PAL["dim"]
    _arrow(ax, p1, p2, color, lw=1.0, style="<|-|>", ms=7)
    mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    ax.text(mid[0], mid[1] + dy, text, ha="center", va="bottom", color=color, fontsize=fs)


def slab(ax, x0, x1, ytop, depth=0.22, z=2):
    ax.add_patch(Rectangle((x0, ytop - depth), x1 - x0, depth,
                           facecolor=PAL["steel"], edgecolor="none", zorder=z))
    ax.plot([x0, x1], [ytop, ytop], color=PAL["steel_edge"], lw=1.2, zorder=z + 1)


def ripple(ax, x0, x1, y0, amp, period, z=5, fill_depth=0.25):
    x = np.linspace(x0, x1, 600)
    y = y0 + amp * (0.5 - 0.5 * np.cos(2 * np.pi * (x - x0) / period))
    ax.fill_between(x, y, y0 - fill_depth, color=PAL["steel"], lw=0, zorder=z)
    ax.plot(x, y, color=PAL["steel_edge"], lw=1.2, zorder=z + 1)
    return x, y


def pillars(ax, xs, y0, h=0.34, w=0.085, z=5):
    for x in xs:
        ax.add_patch(Polygon([(x - w / 2, y0), (x, y0 + h), (x + w / 2, y0)],
                             facecolor=PAL["steel"], edgecolor=PAL["steel_edge"],
                             lw=1.0, zorder=z))


def bacterium(ax, x, y, L=0.4, W=0.17, angle=0.0, color=None, z=10, dead=False):
    color = color or (PAL["bac_dead"] if dead else PAL["bac"])
    ax.add_patch(Ellipse((x, y), L, W, angle=angle, facecolor=color,
                         edgecolor=PAL["bac_edge"], lw=1.1, zorder=z))
    t = np.linspace(0, 1, 40)
    fx = x - L / 2 - 0.02 - 0.10 * t
    fy = y + 0.035 * np.sin(6 * np.pi * t)
    ax.plot(fx, fy, color=PAL["bac_edge"], lw=0.9, zorder=z)


# ---------------------------------------------------------------- Figure 1
FIG1 = {
 "en": dict(
   xlabel="Accumulated pulses per spot, N", ylabel="Peak fluence (× ablation threshold)",
   threshold="single-pulse ablation threshold", nomod="no significant\nmodification",
   lipss="LIPSS region\n(quasi-periodic ripples)", trans="strong ablation / melt",
   pillars="nanopillars & cones\n(black metals)",
   incub="incubation: effective\nthreshold decreases", note="(schematic; not to scale)"),
 "zh": dict(
   xlabel="累积脉冲数（每点）N", ylabel="峰值注量（× 烧蚀阈值）",
   threshold="单脉冲烧蚀阈值", nomod="无明显改性",
   lipss="LIPSS 区\n（准周期沟脊）", trans="强烧蚀 / 熔体回凝",
   pillars="纳米柱与锥\n（黑金属）",
   incub="孵化效应：有效\n阈值下移", note="（示意图，非等比）"),
}


def fig1(lang):
    L = FIG1[lang]
    fig, ax = plt.subplots(figsize=(6.1, 3.9))
    fig.subplots_adjust(left=0.105, right=0.985, top=0.965, bottom=0.155)
    ax.set_xscale("log")
    ax.set_xlim(1, 2500)
    ax.set_ylim(0.15, 3.4)
    N = np.logspace(0, np.log10(2500), 400)
    lu = np.log10(N)

    def sig(x, x0, w):
        return 1.0 / (1.0 + np.exp(-(x - x0) / w))

    bottom = 0.55 - 0.27 * sig(lu, 2.15, 0.40)
    top = 1.30 - 0.44 * sig(lu, 2.05, 0.45)
    melt_top = 1.95 - 0.55 * sig(lu, 1.90, 0.50)

    ax.fill_between(N, 0.15, bottom, color="#EEF0F2", lw=0, zorder=1)
    ax.fill_between(N, bottom, top, color="#D6EAD8", lw=0, zorder=1)
    ax.fill_between(N, top, melt_top, color="#FBE7D5", lw=0, zorder=1)
    ax.fill_between(N, melt_top, 3.4, color="#F6CDB8", lw=0, zorder=1)

    ax.axhline(1.0, color=PAL["grey"], ls=(0, (6, 4)), lw=1.1, zorder=2)
    ax.text(2450, 1.05, L["threshold"], ha="right", va="bottom", color="#4A5460", fontsize=9,
            bbox=dict(fc="white", ec="none", alpha=0.75, pad=1.2), zorder=3)

    bbox = dict(fc="white", ec="none", alpha=0.78, pad=1.6)
    ax.text(2.0, 0.30, L["nomod"], ha="left", va="center", color=PAL["ink"], fontsize=9, bbox=bbox, zorder=4)
    ax.text(240, 0.70, L["lipss"], ha="center", va="center", color="#2E6B3D", fontsize=9.5, bbox=bbox, zorder=4)
    ax.text(1100, 1.22, L["trans"], ha="center", va="center", color="#A05A28", fontsize=8.5, bbox=bbox, zorder=4)
    ax.text(300, 2.80, L["pillars"], ha="center", va="center", color="#8C4A22", fontsize=9, bbox=bbox, zorder=4)

    _arrow(ax, (15, 0.92), (900, 0.55), PAL["wave"], lw=1.6, rad=-0.18)
    ax.text(8, 0.88, L["incub"], ha="left", va="top", color=PAL["wave"], fontsize=8.5, zorder=6,
            bbox=dict(fc="white", ec="none", alpha=0.55, pad=1.2))

    xi = np.linspace(900, 1200, 60)
    ax.plot(xi, 0.75 + 0.045 * np.sin(np.linspace(0, 6 * np.pi, 60)),
            color=PAL["steel_edge"], lw=1.3, zorder=6)
    pillars(ax, [170, 255, 340, 425], 2.08, h=0.42, w=0.055, z=6)

    ax.set_xticks([1, 10, 100, 1000])
    ax.set_xticklabels(["1", "10", "100", "1000"])
    ax.set_yticks([0.5, 1, 2, 3])
    ax.set_yticklabels(["0.5", "1", "2", "3"])
    ax.tick_params(colors=PAL["ink"], labelsize=8.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#C4CBD2")
    ax.set_xlabel(L["xlabel"], fontsize=9.5, color=PAL["ink"])
    ax.set_ylabel(L["ylabel"], fontsize=9.5, color=PAL["ink"])
    ax.text(0.985, 0.03, L["note"], transform=ax.transAxes, ha="right", va="bottom",
            color=PAL["grey"], fontsize=8)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIGDIR, f"fig1_process_map_{lang}.{ext}"))
    plt.close(fig)


# ---------------------------------------------------------------- Figure 2
FIG2 = {
 "en": dict(
   a_title="Surface-wave excitation", beam="incident\nlight", spp="surface wave (SPP)",
   rough="roughness (seeding)",
   b_title="Interference → periodic energy", intensity="near-field intensity",
   c_title="Material response → ripples", period="Λ ≈ 0.7–0.9 λ",
   topview="top view:  E  ⊥  ripples",
   d_title="Positive feedback: self-organised",
   fb1="periodic\nripples", fb2="stronger\ncoupling",
   fbnote="ripples re-couple energy into the wave"),
 "zh": dict(
   a_title="激光激发表面波", beam="入射光", spp="表面电磁波（SPP）", rough="粗糙度（种子）",
   b_title="干涉 → 周期性能量分布", intensity="近场强度",
   c_title="材料响应 → 沟脊结构", period="Λ ≈ 0.7–0.9 λ",
   topview="俯视：条纹 ⊥ E（偏振方向）",
   d_title="正反馈：自组织生长",
   fb1="周期\n刻纹", fb2="耦合\n增强",
   fbnote="沟脊（光栅）把能量持续耦合回表面波"),
}


def fig2(lang):
    L = FIG2[lang]
    fig, axs = plt.subplots(2, 2, figsize=(6.1, 4.9))
    fig.subplots_adjust(left=0.035, right=0.965, top=0.955, bottom=0.035,
                        wspace=0.18, hspace=0.42)
    for ax in axs.flat:
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    # (a) excitation
    ax = axs[0, 0]
    ax.text(0.01, 1.0, "(a)", fontsize=10, fontweight="bold", color=PAL["ink"], va="top")
    ax.text(0.11, 1.0, L["a_title"], fontsize=9.5, color=PAL["ink"], va="top")
    slab(ax, 0.02, 0.98, 0.30, depth=0.24)
    for xb in (0.52, 0.60, 0.68):
        ax.add_patch(Polygon([(xb - 0.030, 0.30), (xb, 0.345), (xb + 0.030, 0.30)],
                             facecolor=PAL["steel"], edgecolor=PAL["steel_edge"], lw=0.8, zorder=6))
    for i in range(3):
        _arrow(ax, (0.34 + i * 0.09, 0.86), (0.25 + i * 0.09, 0.40), PAL["laser"], lw=2.6, ms=11)
    ax.text(0.05, 0.66, L["beam"], fontsize=9, color=PAL["laser"], ha="left", va="center")
    xs = np.linspace(0.20, 0.93, 300)
    amp = 0.055 * np.exp(-((xs - 0.70) ** 2) / 0.050)
    ax.plot(xs, 0.33 + amp * np.sin(2 * np.pi * xs * 9), color=PAL["wave"], lw=1.7, zorder=7)
    _arrow(ax, (0.90, 0.33), (0.965, 0.345), PAL["wave"], lw=1.7, ms=9)
    ax.text(0.74, 0.55, L["spp"], fontsize=9, color=PAL["wave"], ha="center")
    ax.text(0.70, 0.405, L["rough"], fontsize=8, color="#4A5460", ha="center")

    # (b) interference
    ax = axs[0, 1]
    ax.text(0.01, 1.0, "(b)", fontsize=10, fontweight="bold", color=PAL["ink"], va="top")
    ax.text(0.11, 1.0, L["b_title"], fontsize=9.5, color=PAL["ink"], va="top")
    slab(ax, 0.02, 0.98, 0.22, depth=0.18)
    xi = np.linspace(0.06, 0.94, 500)
    per = 0.176
    inten = 0.24 + 0.44 * (np.sin(np.pi * (xi - 0.06) / per)) ** 2
    ax.fill_between(xi, 0.22, inten, color=PAL["energy"], alpha=0.22, lw=0, zorder=4)
    ax.plot(xi, inten, color=PAL["energy"], lw=1.5, zorder=5)
    peaks = [0.06 + per / 2 + per * k for k in range(6)]
    for px in peaks[1:-1]:
        ax.plot([px, px], [0.22, 0.78], color=PAL["grey"], lw=0.7, ls=(0, (3, 3)), zorder=3)
    _dim(ax, (peaks[1], 0.80), (peaks[2], 0.80), "Λ")
    ax.text(0.975, 0.66, L["intensity"], fontsize=8.5, color=PAL["energy"], ha="right", va="bottom")

    # (c) material response
    ax = axs[1, 0]
    ax.text(0.01, 1.0, "(c)", fontsize=10, fontweight="bold", color=PAL["ink"], va="top")
    ax.text(0.11, 1.0, L["c_title"], fontsize=9.5, color=PAL["ink"], va="top")
    ripple(ax, 0.04, 0.96, 0.50, amp=0.075, period=0.15, fill_depth=0.125)
    _dim(ax, (0.265, 0.70), (0.415, 0.70), "Λ")
    ax.text(0.43, 0.715, L["period"], fontsize=9, color=PAL["dim"], ha="left")
    ax.add_patch(Rectangle((0.06, 0.10), 0.88, 0.20, facecolor="#F2F4F6",
                           edgecolor="#C4CBD2", lw=0.8, zorder=2))
    for sxp in np.linspace(0.10, 0.90, 13):
        ax.plot([sxp, sxp], [0.115, 0.285], color=PAL["steel_edge"], lw=1.3, zorder=3)
    _arrow(ax, (0.12, 0.20), (0.88, 0.20), PAL["laser"], lw=1.6, style="<|-|>", ms=8)
    ax.text(0.80, 0.215, "E", fontsize=9, color=PAL["laser"], ha="right")
    tvkw = dict(ha="center", color=PAL["ink"], fontsize=8.5)
    if lang == "en":
        tvkw["fontproperties"] = DEJAVU
    ax.text(0.50, 0.335, L["topview"], **tvkw)

    # (d) feedback
    ax = axs[1, 1]
    ax.text(0.01, 1.0, "(d)", fontsize=10, fontweight="bold", color=PAL["ink"], va="top")
    ax.text(0.11, 1.0, L["d_title"], fontsize=9.5, color=PAL["ink"], va="top")
    b1 = FancyBboxPatch((0.05, 0.42), 0.34, 0.30, boxstyle="round,pad=0.02",
                        fc="#EDF3FB", ec=PAL["wave"], lw=1.2, zorder=4)
    b2 = FancyBboxPatch((0.61, 0.42), 0.34, 0.30, boxstyle="round,pad=0.02",
                        fc="#EDF3FB", ec=PAL["wave"], lw=1.2, zorder=4)
    ax.add_patch(b1); ax.add_patch(b2)
    ax.text(0.22, 0.575, L["fb1"], ha="center", va="center", fontsize=8.5, color=PAL["ink"], zorder=5)
    ax.text(0.78, 0.575, L["fb2"], ha="center", va="center", fontsize=8.5, color=PAL["ink"], zorder=5)
    _arrow(ax, (0.41, 0.635), (0.59, 0.635), PAL["wave"], lw=1.4, rad=-0.45, ms=9)
    _arrow(ax, (0.59, 0.505), (0.41, 0.505), PAL["wave"], lw=1.4, rad=-0.45, ms=9)
    ax.text(0.50, 0.26, L["fbnote"], ha="center", va="center", fontsize=8.5, color=PAL["grey"])
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIGDIR, f"fig2_lipss_mechanism_{lang}.{ext}"))
    plt.close(fig)


# ---------------------------------------------------------------- Figure 3
FIG3 = {
 "en": dict(
   a_title="Anti-adhesion (geometry)", a_note="much smaller features → few contact points",
   b_title="Mechano-bactericidal action", b_note="membrane stretched between pillars → rupture",
   c_title="Surface chemistry", c_note="laser-induced oxide layer / charge",
   d_title="Conditioning film (Vroman)", d_note="proteins adsorb first — a new interface"),
 "zh": dict(
   a_title="抗粘附（几何）", a_note="特征尺寸远小于细菌：接触点少",
   b_title="机械杀菌作用", b_note="柱间膜拉伸 → 破裂",
   c_title="表面化学", c_note="激光氧化层 / 电荷状态",
   d_title="蛋白条件膜（Vroman）", d_note="蛋白先行吸附 → 细菌面对新界面"),
}


def fig3(lang):
    L = FIG3[lang]
    fig, axs = plt.subplots(2, 2, figsize=(6.1, 4.6))
    fig.subplots_adjust(left=0.035, right=0.965, top=0.955, bottom=0.035,
                        wspace=0.18, hspace=0.42)
    for ax in axs.flat:
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    def head(ax, tag, title, note):
        ax.text(0.01, 1.0, tag, fontsize=10, fontweight="bold", color=PAL["ink"], va="top")
        ax.text(0.11, 1.0, title, fontsize=9.5, color=PAL["ink"], va="top")
        ax.text(0.115, 0.895, note, fontsize=8, color=PAL["grey"], va="top")

    # (a) anti-adhesion
    ax = axs[0, 0]
    head(ax, "(a)", L["a_title"], L["a_note"])
    ripple(ax, 0.04, 0.96, 0.30, amp=0.055, period=0.075, fill_depth=0.22)
    bacterium(ax, 0.38, 0.62, L=0.44, W=0.18, angle=-6)
    for cx in (0.30, 0.50):
        ax.plot([cx, cx], [0.515, 0.375], color=PAL["steel_dark"], lw=1.2, zorder=9)
        ax.add_patch(Circle((cx, 0.375), 0.013, fc=PAL["ink"], ec="none", zorder=11))
        ax.add_patch(Circle((cx, 0.515), 0.013, fc=PAL["ink"], ec="none", zorder=11))

    # (b) mechano-bactericidal
    ax = axs[0, 1]
    head(ax, "(b)", L["b_title"], L["b_note"])
    slab(ax, 0.06, 0.94, 0.16, depth=0.10, z=2)
    pillars(ax, [0.14, 0.30, 0.62, 0.82], 0.16, h=0.40, w=0.085)
    xt = np.linspace(0.27, 0.65, 80)
    sag = 0.58 - 0.23 * np.exp(-((xt - 0.46) ** 2) / 0.012)
    topc = sag + 0.155
    verts = list(zip(xt, topc)) + list(zip(xt[::-1], sag[::-1]))
    ax.add_patch(Polygon(verts, closed=True, facecolor=PAL["bac"], edgecolor=PAL["bac_edge"],
                         lw=1.2, zorder=10))
    ax.add_patch(Polygon([(0.428, 0.39), (0.492, 0.39), (0.46, 0.338)],
                         closed=True, facecolor="white", edgecolor=PAL["mem"], lw=1.2, zorder=11))
    bx, by = 0.46, 0.352
    for dx, dy in ((0.0, -0.085), (-0.055, -0.06), (0.055, -0.06), (-0.09, -0.02), (0.09, -0.02)):
        ax.plot([bx, bx + dx], [by, by + dy], color=PAL["mem"], lw=1.5, zorder=12)
    for dotx, doty in ((0.42, 0.20), (0.46, 0.165), (0.50, 0.20)):
        ax.add_patch(Circle((dotx, doty), 0.012, fc=PAL["mem"], ec="none", zorder=12))

    # (c) surface chemistry
    ax = axs[1, 0]
    head(ax, "(c)", L["c_title"], L["c_note"])
    slab(ax, 0.05, 0.95, 0.38, depth=0.30)
    ax.add_patch(Rectangle((0.05, 0.38), 0.90, 0.075, facecolor=PAL["oxide"],
                           edgecolor="none", alpha=0.95, zorder=6))
    for sx, sym, colr in ((0.22, "+", "#B4443C"), (0.42, "−", "#3F6FB5"),
                          (0.62, "+", "#B4443C"), (0.80, "−", "#3F6FB5")):
        ax.plot([sx, sx], [0.46, 0.52], color="#6B7680", lw=1.2, zorder=7)
        ax.text(sx, 0.545, sym, fontsize=12, color=colr, ha="center", zorder=7)

    # (d) conditioning film
    ax = axs[1, 1]
    head(ax, "(d)", L["d_title"], L["d_note"])
    slab(ax, 0.05, 0.95, 0.30, depth=0.24)
    rng = np.random.default_rng(7)
    prot_colors = [PAL["prot1"], PAL["prot2"], PAL["prot3"]]
    for i, px in enumerate(np.linspace(0.075, 0.925, 13)):
        py = 0.42 + 0.045 * rng.random()
        e = Ellipse((px, py), 0.085 + 0.025 * rng.random(), 0.065 + 0.02 * rng.random(),
                    angle=float(rng.uniform(0, 180)), facecolor=prot_colors[i % 3],
                    edgecolor="none", alpha=0.9, zorder=6)
        ax.add_patch(e)
    bacterium(ax, 0.48, 0.61, L=0.42, W=0.17, angle=-5, z=10)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIGDIR, f"fig3_antibacterial_{lang}.{ext}"))
    plt.close(fig)


def main():
    for lang in ("en", "zh"):
        apply_style(lang)
        fig1(lang)
        fig2(lang)
        fig3(lang)
    print("figures written to:", FIGDIR)
    for f in sorted(os.listdir(FIGDIR)):
        p = os.path.join(FIGDIR, f)
        print(f"  {f}  {os.path.getsize(p)} bytes")


if __name__ == "__main__":
    main()
