# -*- coding: utf-8 -*-
"""Process-flow figure for the viable-clone-count (CFU) protocol."""
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

C_A = "#DCE9F7"      # method A
C_B = "#FBE6D2"      # method B
C_S = "#E4F1E1"      # shared
C_Q = "#F3E1F0"      # QC / analysis
EDGE = "#3A3A3A"


def box(ax, x, y, w, h, text, color, size=8.6, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                                linewidth=1.0, edgecolor=EDGE, facecolor=color))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
            fontweight="bold" if bold else "normal", wrap=True, linespacing=1.35)


def arrow(ax, p0, p1, style="-|>", lw=1.2, color=EDGE, ls="-"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=11,
                                 linewidth=lw, color=color, linestyle=ls,
                                 shrinkA=1, shrinkB=1))


def main():
    os.makedirs(OUT, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13.2, 8.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.975, "Viable clone count (CFU) on laser-textured 316L coupons — process flow",
            ha="center", va="top", fontsize=13.5, fontweight="bold")
    ax.text(0.5, 0.938, "下位替代 / cross-check for LIVE/DEAD: culture-based, zone-resolvable, "
                        "no staining artefact", ha="center", va="top", fontsize=9.4, color="#444")

    # ---- shared front end
    box(ax, 0.06, 0.80, 0.30, 0.095,
        "1 · Culture & standardise\nsingle colony → TSB 37 °C overnight\nsub-culture → OD600 target\n"
        "E. coli 0.78 / S. aureus 0.90 / P. aeruginosa 0.63", C_S)
    box(ax, 0.40, 0.80, 0.24, 0.095,
        "2 · Wash & dilute\n2 500 × g 15 min, 0.85 % NaCl wash\nresuspend in PBS",
        C_S)
    box(ax, 0.68, 0.80, 0.26, 0.095,
        "3 · Working suspension\n1 × 10⁷ CFU/mL\nE. coli 0.87 mL into 30 mL bath\n"
        "plate 100 µL to verify (30–300)", C_S)
    arrow(ax, (0.36, 0.847), (0.40, 0.847))
    arrow(ax, (0.64, 0.847), (0.68, 0.847))

    # ---- sample prep
    box(ax, 0.06, 0.665, 0.30, 0.085,
        "4 · Coupon clean & sterilise\n70 % ethanol 15 min → sterile water 15 min\n"
        "air-dry in the cabinet; n = 3 coupons per condition", C_S)
    arrow(ax, (0.21, 0.80), (0.21, 0.75))
    box(ax, 0.40, 0.665, 0.24, 0.085,
        "5 · Mark the zones\nc / 1 / 2 = 7 × 7 mm each\n(0.49 cm², coupon 4.0 cm²)", C_S)
    arrow(ax, (0.36, 0.707), (0.40, 0.707))

    # ---- branch
    ax.text(0.30, 0.605, "A · zone-resolved (preferred)", ha="center", fontsize=10.2,
            fontweight="bold", color="#1F4E79")
    ax.text(0.75, 0.605, "B · whole coupon (directly comparable to LIVE/DEAD)", ha="center",
            fontsize=10.2, fontweight="bold", color="#8A4B12")

    # Method A column
    ax1, w1 = 0.045, 0.42
    box(ax, ax1, 0.455, w1, 0.125,
        "6A · Isolate the zone\npress-to-seal silicone well (8 mm ID) or\n"
        "50 µL drop + 10 × 10 mm sterile film\n(prevents evaporation & cross-talk)", C_A)
    arrow(ax, (0.21, 0.665), (0.21, 0.58), ls="--")
    box(ax, ax1, 0.345, w1, 0.085,
        "7A · Inoculate & incubate\n100 µL per well, 37 °C, 3 / 5 / 7 / 24 h\n"
        "static (thin film, no shaking)", C_A)
    arrow(ax, (ax1 + w1 / 2, 0.455), (ax1 + w1 / 2, 0.43))
    box(ax, ax1, 0.235, w1, 0.085,
        "8A · Wash 3 × with warm 0.85 % NaCl\naspirate the well, no direct jet on the surface",
        C_A)
    arrow(ax, (ax1 + w1 / 2, 0.345), (ax1 + w1 / 2, 0.32))
    box(ax, ax1, 0.125, w1, 0.085,
        "9A · Detach inside the well\n1 mL PBS + pipette 10 × up/down,\n"
        "then sonicate 40 kHz 5 min (bath, ice)", C_A)
    arrow(ax, (ax1 + w1 / 2, 0.235), (ax1 + w1 / 2, 0.21))

    # Method B column
    ax2, w2 = 0.535, 0.42
    box(ax, ax2, 0.455, w2, 0.125,
        "6B · Immerse the whole coupon\n30 mL suspension, 37 °C, 30 rpm\n"
        "same bath as the LIVE/DEAD protocol", C_B)
    arrow(ax, (0.52, 0.707), (0.745, 0.58), ls="--")
    box(ax, ax2, 0.345, w2, 0.085,
        "7B · Wash 3 × warm 0.85 % NaCl (no jet)", C_B)
    arrow(ax, (ax2 + w2 / 2, 0.455), (ax2 + w2 / 2, 0.43))
    box(ax, ax2, 0.235, w2, 0.085,
        "8B · Transfer to 2 mL PBS in a tube\n+ vortex 30 s + sonicate 40 kHz 5 min", C_B)
    arrow(ax, (ax2 + w2 / 2, 0.345), (ax2 + w2 / 2, 0.32))
    box(ax, ax2, 0.125, w2, 0.085,
        "9B · (optional) plate the sonication liquid\nin two 2.5 min steps to prove the\n"
        "detachment is complete", C_B)
    arrow(ax, (ax2 + w2 / 2, 0.235), (ax2 + w2 / 2, 0.21))

    # ---- shared downstream
    box(ax, 0.045, 0.015, 0.28, 0.095,
        "10 · Dilute & plate\n10^-1 ... 10^-5, spread 100 µL\n2 plates per dilution, TSA", C_S)
    box(ax, 0.355, 0.015, 0.28, 0.095,
        "11 · Incubate & count\n37 °C 18–24 h; count 30–300\n"
        "take the dilution in window", C_S)
    box(ax, 0.665, 0.015, 0.29, 0.095,
        "12 · Report\nCFU/cm² and log CFU/cm²\nlog reduction R, anti-adhesion %\n"
        "LOD 5 (coupon) / 20 (zone) CFU/cm2", C_Q)
    arrow(ax, (0.255, 0.125), (0.185, 0.11))
    arrow(ax, (0.745, 0.125), (0.815, 0.11))
    arrow(ax, (0.325, 0.062), (0.355, 0.062))
    arrow(ax, (0.635, 0.062), (0.665, 0.062))

    # ---- QC sidebar
    box(ax, 0.045, 0.905, 0.91, 0.001, "", "white")   # spacer (invisible)
    ax.text(0.5, 0.478,
            "Controls every run:  blank bath without coupon (no growth in PBS)  ·  "
            "spiked-coupon recovery control (known CFU in → % recovered)  ·  "
            "sterility plate of the diluent",
            ha="center", va="center", fontsize=8.8, color="#333",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#FFF8E1", edgecolor="#C9A227", lw=0.9))

    fig.savefig(os.path.join(OUT, "cfu_process_flow.png"), dpi=190, bbox_inches="tight")
    print(os.path.join(OUT, "cfu_process_flow.png"))


if __name__ == "__main__":
    main()
