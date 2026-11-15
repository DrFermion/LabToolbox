# -*- coding: utf-8 -*-
"""Process-flow figure for the viable-clone-count (CFU) protocol (layout v2)."""
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

C_A = "#DCE9F7"
C_B = "#FBE6D2"
C_S = "#E4F1E1"
C_Q = "#F3E1F0"
EDGE = "#3A3A3A"


def box(ax, x, y, w, h, text, color, size=8.4, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.010,rounding_size=0.018",
                                linewidth=1.0, edgecolor=EDGE, facecolor=color))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
            fontweight="bold" if bold else "normal", linespacing=1.35)


def arrow(ax, p0, p1, ls="-", lw=1.15, color=EDGE):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=10,
                                 linewidth=lw, color=color, linestyle=ls,
                                 shrinkA=1, shrinkB=1))


def elbow(ax, pts, ls="-", color=EDGE):
    for a, b in zip(pts[:-1], pts[1:]):
        arrow(ax, a, b, ls=ls, color=color)


def main():
    os.makedirs(OUT, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13.6, 9.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.985, "Viable clone count (CFU) on laser-textured 316L coupons — process flow",
            ha="center", va="top", fontsize=13.5, fontweight="bold")
    ax.text(0.5, 0.952, "下位替代 / cross-check for LIVE/DEAD: culture-based, zone-resolvable, "
                        "immune to staining artefacts", ha="center", va="top",
            fontsize=9.4, color="#444")

    # ---------------- preparation row ----------------
    box(ax, 0.030, 0.845, 0.290, 0.085,
        "1 · Culture & standardise\nsingle colony → TSB, 37 °C overnight\nsub-culture → OD600 target\n"
        "E. coli 0.78 · S. aureus 0.90 · P. aeruginosa 0.63", C_S)
    box(ax, 0.345, 0.845, 0.190, 0.085,
        "2 · Wash & dilute\n2500 × g 15 min\n0.85 % NaCl wash → PBS", C_S)
    box(ax, 0.560, 0.845, 0.410, 0.085,
        "3 · Working suspension 1 × 10⁷ CFU/mL\nE. coli 0.87 mL · S. aureus 3.58 mL · "
        "P. aeruginosa 0.79 mL into a 30 mL bath\nthen plate 100 µL to verify 30–300 colonies", C_S)
    arrow(ax, (0.320, 0.888), (0.345, 0.888))
    arrow(ax, (0.535, 0.888), (0.560, 0.888))

    box(ax, 0.030, 0.735, 0.290, 0.080,
        "4 · Coupon clean & sterilise\n70 % ethanol 15 min → sterile water 15 min\n"
        "air-dry in the cabinet · n = 3 coupons/condition", C_S)
    box(ax, 0.345, 0.735, 0.190, 0.080,
        "5 · Mark zones\nc / 1 / 2 = 7 × 7 mm each\n0.49 cm² of 4.00 cm²", C_S)
    arrow(ax, (0.320, 0.775), (0.345, 0.775))

    # ---------------- branch headers ----------------
    ax.text(0.245, 0.688, "A · zone-resolved  (preferred: keeps c / 1 / 2 separate)",
            ha="center", fontsize=10.0, fontweight="bold", color="#1F4E79")
    ax.text(0.760, 0.688, "B · whole coupon  (directly comparable to the LIVE/DEAD runs)",
            ha="center", fontsize=10.0, fontweight="bold", color="#8A4B12")

    # ---------------- method A ----------------
    a_x, a_w = 0.030, 0.430
    box(ax, a_x, 0.560, a_w, 0.105,
        "6A · Isolate the zone\npress-to-seal silicone well (8 mm ID) or\n"
        "50 µL drop + 10 × 10 mm sterile film\n(no evaporation, no cross-talk between zones)", C_A)
    box(ax, a_x, 0.470, a_w, 0.072,
        "7A · Inoculate & incubate\n100 µL per well, 37 °C, 3 / 5 / 7 / 24 h, static", C_A)
    box(ax, a_x, 0.385, a_w, 0.070,
        "8A · Wash 3 × warm 0.85 % NaCl\naspirate from the well edge, never a jet on the surface", C_A)
    box(ax, a_x, 0.300, a_w, 0.070,
        "9A · Detach inside the well\n1 mL PBS + pipette 10 × up/down, then 40 kHz 5 min (iced bath)", C_A)
    arrow(ax, (a_x + a_w / 2, 0.560), (a_x + a_w / 2, 0.542))
    arrow(ax, (a_x + a_w / 2, 0.470), (a_x + a_w / 2, 0.455))
    arrow(ax, (a_x + a_w / 2, 0.385), (a_x + a_w / 2, 0.370))

    # ---------------- method B ----------------
    b_x, b_w = 0.540, 0.430
    box(ax, b_x, 0.560, b_w, 0.105,
        "6B · Immerse the whole coupon\n30 mL suspension, 37 °C, 30 rpm\n"
        "identical to the LIVE/DEAD incubation\nso the two methods share the exposure step", C_B)
    box(ax, b_x, 0.470, b_w, 0.072,
        "7B · Wash 3 × warm 0.85 % NaCl (no jet)", C_B)
    box(ax, b_x, 0.385, b_w, 0.070,
        "8B · Transfer to 2 mL PBS in a tube\nvortex 30 s + 40 kHz 5 min (iced bath)", C_B)
    box(ax, b_x, 0.300, b_w, 0.070,
        "9B · Prove complete detachment\nrepeat the sonication once more and plate both liquids", C_B)
    arrow(ax, (b_x + b_w / 2, 0.560), (b_x + b_w / 2, 0.542))
    arrow(ax, (b_x + b_w / 2, 0.470), (b_x + b_w / 2, 0.455))
    arrow(ax, (b_x + b_w / 2, 0.385), (b_x + b_w / 2, 0.370))

    # ---------------- feeds into the branches ----------------
    arrow(ax, (0.245, 0.560), (0.245, 0.542))            # from the A header line
    ax.add_patch(FancyArrowPatch((0.440, 0.735), (0.455, 0.665), arrowstyle="-|>",
                                 mutation_scale=10, lw=1.15, color=EDGE,
                                 connectionstyle="arc3,rad=-0.15", shrinkA=1, shrinkB=1))
    elbow(ax, [(0.700, 0.845), (0.700, 0.665)], ls="--")  # suspension -> 6B
    ax.add_patch(FancyArrowPatch((0.245, 0.725), (0.245, 0.665), arrowstyle="-|>",
                                 mutation_scale=10, lw=1.15, color=EDGE,
                                 connectionstyle="arc3,rad=0.0", shrinkA=1, shrinkB=1))

    # ---------------- run controls ----------------
    ax.text(0.5, 0.252,
            "Controls every run:  blank bath without a coupon (no growth in PBS)  ·  "
            "spiked-coupon recovery control (known CFU in → % recovered)  ·  "
            "sterility plate of the diluent  ·  dead-cell control (70 % ethanol-killed suspension)",
            ha="center", va="center", fontsize=8.6, color="#333",
            bbox=dict(boxstyle="round,pad=0.34", facecolor="#FFF8E1", edgecolor="#C9A227", lw=0.9))

    # ---------------- shared downstream ----------------
    box(ax, 0.030, 0.115, 0.290, 0.095,
        "10 · Dilute & plate\n10^-1 … 10^-5, spread 100 µL\n2 plates per dilution, TSA", C_S)
    box(ax, 0.345, 0.115, 0.290, 0.095,
        "11 · Incubate & count\n37 °C 18–24 h\ncount 30–300, use that dilution", C_S)
    box(ax, 0.660, 0.115, 0.310, 0.095,
        "12 · Report\nCFU/cm² and log CFU/cm² · log reduction R\nanti-adhesion %\n"
        "LOD 5 CFU/cm² (coupon) · 20 CFU/cm² (zone)", C_Q)
    arrow(ax, (0.320, 0.162), (0.345, 0.162))
    arrow(ax, (0.635, 0.162), (0.660, 0.162))
    # both branches converge on step 10
    ax.add_patch(FancyArrowPatch((0.245, 0.300), (0.175, 0.212), arrowstyle="-|>",
                                 mutation_scale=10, lw=1.2, color="#1F4E79",
                                 connectionstyle="arc3,rad=0.12", shrinkA=1, shrinkB=1))
    ax.add_patch(FancyArrowPatch((0.755, 0.300), (0.255, 0.212), arrowstyle="-|>",
                                 mutation_scale=10, lw=1.2, color="#8A4B12",
                                 connectionstyle="arc3,rad=0.10", shrinkA=1, shrinkB=1))

    ax.text(0.5, 0.055,
            "Zone-resolved (A) is preferred for the multi-zone coupons; whole-coupon (B) is the "
            "fallback that can be compared with the existing LIVE/DEAD totals on the same design.",
            ha="center", va="center", fontsize=8.4, color="#555", style="italic")

    fig.savefig(os.path.join(OUT, "cfu_process_flow.png"), dpi=190, bbox_inches="tight")
    print(os.path.join(OUT, "cfu_process_flow.png"))


if __name__ == "__main__":
    main()
