# -*- coding: utf-8 -*-
"""CFU protocol flow figure — full-face coupon design (v2, single path)."""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["axes.unicode_minus"] = False

OUT = "E:/LabToolbox/output/viable_count_plan_v2_20261111"
C_S, C_Q, EDGE = "#E4F1E1", "#F3E1F0", "#3A3A3A"
C_MAIN, C_OPT = "#DCE9F7", "#FBE6D2"


def box(ax, x, y, w, h, text, color, size=8.8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                                linewidth=1.0, edgecolor=EDGE, facecolor=color))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, linespacing=1.4)


def arrow(ax, p0, p1, lw=1.3, color=EDGE, ls="-"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=11, linewidth=lw,
                                 color=color, linestyle=ls, shrinkA=1, shrinkB=1))


def main():
    os.makedirs(OUT, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12.4, 11.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.03, 1)
    ax.axis("off")

    ax.text(0.5, 0.995, "Viable clone count (CFU) on full-face laser-treated 316L coupons",
            ha="center", va="top", fontsize=14, fontweight="bold")
    ax.text(0.5, 0.962, "LIVE/DEAD 的下位替代 / 交叉验证 — 每块样品整面一种处理，整片浸没 → 整片剥离 → 涂板计数",
            ha="center", va="top", fontsize=9.6, color="#333")

    # -------- preparation (two parallel streams) --------
    box(ax, 0.055, 0.845, 0.395, 0.085,
        "1 · Culture & standardise\nsingle colony → TSB 37 °C overnight → OD600 target\n"
        "E. coli 0.78 · S. aureus 0.90 · P. aeruginosa 0.63", C_S)
    box(ax, 0.550, 0.845, 0.395, 0.085,
        "2 · Coupon clean & sterilise\n70 % ethanol 15 min → sterile water 15 min, air-dry\n"
        "one coupon = one condition · n = 3 coupons/condition", C_S)
    box(ax, 0.055, 0.735, 0.395, 0.080,
        "3 · Wash → working suspension 1 × 10⁷ CFU/mL\n2500 × g 15 min, 0.85 % NaCl ×1 → PBS\n"
        "E. coli 0.87 mL · S. aureus 3.58 mL · P. aeruginosa 0.79 mL / 30 mL", C_S)
    box(ax, 0.550, 0.735, 0.395, 0.080,
        "4 · Mark the back of each coupon\ncondition, batch, coupon number\n(never mark the front face)", C_S)
    arrow(ax, (0.252, 0.845), (0.252, 0.815))
    arrow(ax, (0.747, 0.845), (0.747, 0.815))

    # -------- merged main path --------
    box(ax, 0.150, 0.615, 0.700, 0.090,
        "5 · Immerse the WHOLE coupon — 30 mL suspension, 37 °C, 30 rpm, 3 / 5 / 7 / 24 h\n"
        "identical exposure to the LIVE/DEAD runs (same bath, same time, same temperature)", C_MAIN)
    arrow(ax, (0.252, 0.735), (0.320, 0.705))
    arrow(ax, (0.747, 0.735), (0.680, 0.705))

    box(ax, 0.150, 0.505, 0.700, 0.080,
        "6 · Wash 3 × warm 0.85 % NaCl — change the liquid, never jet the surface", C_MAIN)
    arrow(ax, (0.500, 0.615), (0.500, 0.585))

    box(ax, 0.150, 0.375, 0.700, 0.100,
        "7 · Detach the whole face: 2 mL PBS in a GLASS tube → vortex 30 s → 40 kHz 5 min at 22 °C\n"
        "(ice bath) → vortex 30 s;  add 0.001 % saponin for S. aureus", C_MAIN)
    arrow(ax, (0.500, 0.505), (0.500, 0.475))

    box(ax, 0.150, 0.255, 0.340, 0.085,
        "8a · (QC) prove complete detachment\nsonicate 2.5 min more, plate separately:\n"
        "second liquid ≤ 10 % of the first", C_OPT)
    box(ax, 0.510, 0.255, 0.340, 0.085,
        "8b · (QC) same-coupon recovery check\nstain (SYTO 9) or SEM the coupon after\ndetachment and count the residual cells", C_OPT)
    arrow(ax, (0.400, 0.375), (0.320, 0.340))
    arrow(ax, (0.600, 0.375), (0.680, 0.340))

    # -------- shared downstream --------
    box(ax, 0.055, 0.135, 0.290, 0.080,
        "9 · Dilute & plate\n10^-1 ... 10^-4, spread 100 µL\n2 plates per dilution, TSA", C_S)
    box(ax, 0.355, 0.135, 0.290, 0.080,
        "10 · Incubate & count\n37 °C 18–24 h\ncount 25–250 (or 30–300 per ISO 22196)", C_S)
    box(ax, 0.660, 0.135, 0.285, 0.080,
        "11 · Report\nCFU/cm², log CFU/cm², R, anti-adhesion %\nLOD 20 CFU/cm² at 1 cm² face", C_Q)
    arrow(ax, (0.300, 0.375), (0.200, 0.215))          # main path: 7 -> dilute & plate
    arrow(ax, (0.320, 0.255), (0.720, 0.215), ls="--", color="#8A4B12")   # QC -> report
    arrow(ax, (0.680, 0.255), (0.800, 0.215), ls="--", color="#8A4B12")   # QC -> report
    arrow(ax, (0.345, 0.175), (0.355, 0.175))
    arrow(ax, (0.645, 0.175), (0.660, 0.175))

    # -------- controls --------
    ax.text(0.5, 0.062,
            "每次必做对照：无样品的空白浴（PBS 不长菌）· 加标回收（已知 CFU 进 → % 回收）· "
            "稀释液无菌平板 · 70 % 乙醇杀死的死菌对照",
            ha="center", va="center", fontsize=8.8, color="#333",
            bbox=dict(boxstyle="round,pad=0.36", facecolor="#FFF8E1", edgecolor="#C9A227", lw=0.9))
    ax.text(0.5, 0.008,
            "n = 每条件 3 块样品；同一块样品的多块平板先平均，样品才是统计单位（避免伪重复）。",
            ha="center", va="center", fontsize=8.4, color="#555", style="italic")

    path = os.path.join(OUT, "cfu_process_flow_fullface.png")
    fig.savefig(path, dpi=190, bbox_inches="tight")
    print(path)


if __name__ == "__main__":
    main()
