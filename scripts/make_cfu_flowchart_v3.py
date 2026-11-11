# -*- coding: utf-8 -*-
"""Process-flow figure for the viable-clone-count (CFU) protocol — layout v3."""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["axes.unicode_minus"] = False

OUT = "E:/LabToolbox/output/viable_count_plan_20261111"

C_A, C_B, C_S, C_Q = "#DCE9F7", "#FBE6D2", "#E4F1E1", "#F3E1F0"
BLUE, ORANGE, EDGE = "#1F4E79", "#8A4B12", "#3A3A3A"


def box(ax, x, y, w, h, text, color, size=8.4):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.010,rounding_size=0.018",
                                linewidth=1.0, edgecolor=EDGE, facecolor=color))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
            linespacing=1.35)


def arrow(ax, p0, p1, color=EDGE, ls="-", lw=1.15, rad=0.0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=10, linewidth=lw,
                                 color=color, linestyle=ls, shrinkA=0.5, shrinkB=0.5,
                                 connectionstyle=f"arc3,rad={rad}"))


def main():
    os.makedirs(OUT, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13.6, 9.6))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.04, 1)
    ax.axis("off")

    ax.text(0.5, 0.998, "Viable clone count (CFU) on laser-textured 316L coupons — process flow",
            ha="center", va="top", fontsize=13.5, fontweight="bold")
    ax.text(0.5, 0.972, "下位替代 / cross-check for LIVE/DEAD — culture-based, zone-resolvable, "
                        "immune to staining artefacts", ha="center", va="top",
            fontsize=9.2, color="#333")

    # ---------------- row 1: inoculum ----------------
    box(ax, 0.030, 0.845, 0.160, 0.085,
        "1 · Culture & standardise\nsingle colony → TSB 37 °C o/n\nsub-culture to OD600 target\n"
        "E. coli 0.78 · S. aureus 0.90\nP. aeruginosa 0.63", C_S)
    box(ax, 0.205, 0.845, 0.125, 0.085,
        "2 · Wash\n2500 × g 15 min\n0.85 % NaCl → PBS", C_S)
    box(ax, 0.345, 0.845, 0.155, 0.085,
        "3 · Working suspension\n1 × 10⁷ CFU/mL in PBS\n30 mL bath", C_S)
    # ---------------- row 1 right: coupon prep ----------------
    box(ax, 0.545, 0.845, 0.155, 0.085,
        "4 · Coupon clean & sterilise\n70 % ethanol 15 min\nsterile water 15 min, air-dry\n"
        "n = 3 coupons/condition", C_S)
    box(ax, 0.715, 0.845, 0.165, 0.085,
        "5 · Mark zones\nc / 1 / 2 = 7 × 7 mm each\n0.49 cm² of the 4.00 cm² coupon", C_S)
    arrow(ax, (0.190, 0.888), (0.205, 0.888))
    arrow(ax, (0.330, 0.888), (0.345, 0.888))
    arrow(ax, (0.700, 0.888), (0.715, 0.888))

    # ---------------- feed bus: both streams feed both branches ----------------
    ax.plot([0.070, 0.930], [0.783, 0.783], color=EDGE, lw=1.15, solid_capstyle="round")
    ax.plot([0.422, 0.422], [0.845, 0.783], color=EDGE, lw=1.15)     # from the suspension
    ax.plot([0.797, 0.797], [0.845, 0.783], color=EDGE, lw=1.15)     # from the marked coupons
    arrow(ax, (0.070, 0.783), (0.070, 0.668), color=BLUE)
    arrow(ax, (0.930, 0.783), (0.930, 0.668), color=ORANGE)
    ax.text(0.5, 0.748, "both preparation streams feed both branches", ha="center",
            va="center", fontsize=8.0, color="#555", style="italic")

    # ---------------- branch labels ----------------
    ax.text(0.265, 0.700, "A · zone-resolved   (preferred)",
            ha="center", fontsize=10.0, fontweight="bold", color=BLUE)
    ax.text(0.755, 0.700, "B · whole coupon",
            ha="center", fontsize=10.0, fontweight="bold", color=ORANGE)

    # ---------------- method A ----------------
    a_x, a_w = 0.030, 0.430
    box(ax, a_x, 0.560, a_w, 0.100,
        "6A · Isolate the zone\npress-to-seal silicone well (8 mm ID) or\n"
        "50 µL drop + 10 × 10 mm sterile film\n(no evaporation, no cross-talk)", C_A)
    box(ax, a_x, 0.470, a_w, 0.072,
        "7A · Inoculate & incubate\n100 µL per well, 37 °C, 3 / 5 / 7 / 24 h, static", C_A)
    box(ax, a_x, 0.385, a_w, 0.070,
        "8A · Wash 3 × warm 0.85 % NaCl\naspirate at the well edge, never a jet on the surface", C_A)
    box(ax, a_x, 0.300, a_w, 0.070,
        "9A · Detach inside the well\n1 mL PBS + pipette 10 × up/down, then 40 kHz 5 min (iced)", C_A)
    arrow(ax, (a_x + a_w / 2, 0.560), (a_x + a_w / 2, 0.544))
    arrow(ax, (a_x + a_w / 2, 0.470), (a_x + a_w / 2, 0.457))
    arrow(ax, (a_x + a_w / 2, 0.385), (a_x + a_w / 2, 0.372))

    # ---------------- method B ----------------
    b_x, b_w = 0.540, 0.430
    box(ax, b_x, 0.560, b_w, 0.100,
        "6B · Immerse the whole coupon\n30 mL suspension, 37 °C, 30 rpm — identical to\nthe LIVE/DEAD incubation, so the exposure step is shared", C_B)
    box(ax, b_x, 0.470, b_w, 0.072,
        "7B · Wash 3 × warm 0.85 % NaCl (no jet)", C_B)
    box(ax, b_x, 0.385, b_w, 0.070,
        "8B · Transfer to 2 mL PBS in a tube\nvortex 30 s + 40 kHz 5 min (iced)", C_B)
    box(ax, b_x, 0.300, b_w, 0.070,
        "9B · Prove complete detachment\nsonicate a second time and plate both liquids", C_B)
    arrow(ax, (b_x + b_w / 2, 0.560), (b_x + b_w / 2, 0.544))
    arrow(ax, (b_x + b_w / 2, 0.470), (b_x + b_w / 2, 0.457))
    arrow(ax, (b_x + b_w / 2, 0.385), (b_x + b_w / 2, 0.372))

    # ---------------- converge into the shared downstream ----------------
    arrow(ax, (0.245, 0.300), (0.185, 0.212), color=BLUE, rad=0.10)
    arrow(ax, (0.755, 0.300), (0.265, 0.212), color=ORANGE, rad=0.10)

    # ---------------- shared downstream ----------------
    box(ax, 0.030, 0.115, 0.290, 0.095,
        "10 · Dilute & plate\n10^-1 ... 10^-5, spread 100 µL\n2 plates per dilution, TSA", C_S)
    box(ax, 0.345, 0.115, 0.290, 0.095,
        "11 · Incubate & count\n37 °C 18–24 h\ncount 30–300, use that dilution", C_S)
    box(ax, 0.660, 0.115, 0.310, 0.095,
        "12 · Report\nCFU/cm² and log CFU/cm² · log reduction R\nanti-adhesion %\n"
        "LOD 5 CFU/cm² (coupon) · 20 CFU/cm² (zone)", C_Q)
    arrow(ax, (0.320, 0.162), (0.345, 0.162))
    arrow(ax, (0.635, 0.162), (0.660, 0.162))

    # ---------------- controls + footnote ----------------
    ax.text(0.5, 0.055,
            "Controls every run:  blank bath without a coupon (no growth in PBS)  ·  "
            "spiked-coupon recovery control (known CFU in → % recovered)  ·  "
            "sterility plate of the diluent  ·  dead-cell control (70 % ethanol-killed)",
            ha="center", va="center", fontsize=8.6, color="#333",
            bbox=dict(boxstyle="round,pad=0.34", facecolor="#FFF8E1", edgecolor="#C9A227", lw=0.9))
    ax.text(0.5, -0.012,
            "A is preferred for the multi-zone coupons; B is the fallback whose totals can be "
            "compared directly with the existing LIVE/DEAD data.",
            ha="center", va="center", fontsize=8.3, color="#555", style="italic")

    path = os.path.join(OUT, "cfu_process_flow.png")
    fig.savefig(path, dpi=190, bbox_inches="tight")
    print(path)


if __name__ == "__main__":
    main()
