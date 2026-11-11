# -*- coding: utf-8 -*-
"""Numbers behind the viable-clone-count (CFU) protocol.

Computes, from the group's own geometry and growth-curve calibration:
  * the volume of culture needed to build a 1e7 CFU/mL immersion bath,
  * the expected CFU on a coupon / on one 7x7 mm zone for a range of surface densities,
  * the dilution series and plate counts that land in the countable window (30-300),
  * the limit of detection for each recovery format,
  * the worked example of the log-reduction and anti-adhesion expressions.

Usage:
  env -u PYTHONPATH C:/Users/PC/miniconda3/python.exe scripts/viable_count_plan.py \
      --outdir E:/LabToolbox/output/viable_count_plan_20261111
"""
from __future__ import annotations

import argparse
import csv
import os

# ---------------------------------------------------------------- calibrations
# log10(CFU/mL) = a * OD600 + b   (LabToolbox growth curves; see the od-logcfu skill)
CAL = {
    "E. coli F1693":          dict(a=0.894112, b=7.840927, od_target=0.78, window=(0.45, 1.48)),
    "S. aureus ATCC 12600":   dict(a=0.529595, b=7.446047, od_target=0.90, window=(0.20, 1.06)),
    "P. aeruginosa ATCC 10145": dict(a=1.269960, b=7.776717, od_target=0.63, window=(0.14, 1.00)),
}

# ---------------------------------------------------------------- geometry
COUPON_MM = 20.0          # coupon 20 x 20 mm (LIVE/DEAD protocol staining area)
ZONE_MM = 7.0             # one laser-textured / control zone
COUPON_CM2 = (COUPON_MM / 10.0) ** 2
ZONE_CM2 = (ZONE_MM / 10.0) ** 2

BATH_ML = 30.0            # immersion volume in a 30 mL staining dish
BATH_TARGET = 1e7         # CFU/mL in the bath (same as the LIVE/DEAD working suspension)

RECOVERY_ML = {"whole coupon": 2.0, "one zone": 1.0}
PLATE_ML = {"spread (100 uL)": 0.1, "spread (200 uL)": 0.2, "drop plate (5 x 20 uL)": 0.02}
AREAS = {"whole coupon": COUPON_CM2, "one zone": ZONE_CM2}
SURFACE_DENSITIES = [1e3, 1e4, 1e5, 1e6]     # CFU/cm2, covers the LIVE/DEAD range seen so far
COUNTABLE = (30, 300)


def logcfu(strain):
    c = CAL[strain]
    return c["a"] * c["od_target"] + c["b"], 10 ** (c["a"] * c["od_target"] + c["b"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="E:/LabToolbox/output/viable_count_plan_20261111")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    lines = []
    lines.append("# Viable clone count (CFU) — worked numbers\n")
    lines.append(f"Coupon {COUPON_MM:g}×{COUPON_MM:g} mm = **{COUPON_CM2:.2f} cm²**; "
                 f"one zone {ZONE_MM:g}×{ZONE_MM:g} mm = **{ZONE_CM2:.2f} cm²**.\n")

    # ---- 1. inoculum
    lines.append("\n## 1. Inoculum: getting to 1e7 CFU/mL\n")
    lines.append("| strain | target OD600 | log CFU/mL | stock (CFU/mL) | volume into "
                 f"{BATH_ML:g} mL bath | check |")
    lines.append("|---|---|---|---|---|---|")
    rows = []
    for strain, c in CAL.items():
        lg, conc = logcfu(strain)
        vol_ml = BATH_TARGET * BATH_ML / conc
        ok = c["window"][0] <= c["od_target"] <= c["window"][1]
        lines.append(f"| {strain} | {c['od_target']:.2f} | {lg:.2f} | {conc:.2e} | **{vol_ml:.2f} mL** | "
                     f"{'inside log-phase window' if ok else 'OUTSIDE window — do not extrapolate'} |")
        rows.append(dict(item="inoculum", strain=strain, od=c["od_target"], log_cfu=round(lg, 3),
                         stock_cfu_per_ml=float(f"{conc:.4e}"), volume_ml=round(vol_ml, 3)))
    lines.append("\nAfter adding the culture, top up to the final volume with PBS: "
                 "the dilution of the TSB carry-over is then ≥ 30×, which is enough to stop growth "
                 "during a 24 h contact test (state this explicitly in the thesis).\n")

    # ---- 2. expected counts and dilution
    lines.append("\n## 2. Expected counts and the dilution series\n")
    lines.append("Survival on the coupon follows from the surface density; the volume in which the "
                 "cells are recovered sets the dilution needed to land in the 30–300 window.\n")
    lines.append("| density (CFU/cm²) | CFU per coupon (4 cm²) | CFU per zone (0.49 cm²) | "
                 "coupon: CFU/mL after 2 mL recovery | first dilution that lands ≤300 | "
                 "zone: CFU/mL after 1 mL recovery | first dilution that lands ≤300 |")
    lines.append("|---|---|---|---|---|---|---|")
    for dens in SURFACE_DENSITIES:
        per_coupon = dens * COUPON_CM2
        per_zone = dens * ZONE_CM2
        c_ml = per_coupon / RECOVERY_ML["whole coupon"]
        z_ml = per_zone / RECOVERY_ML["one zone"]
        def first_dil(x):
            d = 0
            while x / (10 ** d) * PLATE_ML["spread (100 uL)"] > COUNTABLE[1] and d < 8:
                d += 1
            return f"10^-{d}" if d else "neat"
        lines.append(f"| {dens:.0e} | {per_coupon:.2e} | {per_zone:.2e} | {c_ml:.2e} | "
                     f"**{first_dil(c_ml)}** | {z_ml:.2e} | **{first_dil(z_ml)}** |")
    lines.append("\nPractical series: plate **10⁻¹ … 10⁻⁵** (spread 100 µL, two plates per dilution), "
                 "i.e. five dilutions cover everything from 10³ to 10⁶ CFU/cm² without re-planning.\n")

    # ---- 3. LOD
    lines.append("\n## 3. Limit of detection (one colony on the plate)\n")
    lines.append("LOD = (1 colony ÷ plated volume) × recovery volume ÷ coupon area\n")
    lines.append("| format | recovery volume | plated volume | LOD (CFU/cm²) |")
    lines.append("|---|---|---|---|")
    for area_name, area in AREAS.items():
        for pname, pv in PLATE_ML.items():
            lod = (1.0 / pv) * RECOVERY_ML[area_name] / area
            lines.append(f"| {area_name}, {pname} | {RECOVERY_ML[area_name]:.0f} mL | "
                         f"{pv*1000:.0f} µL | **{lod:.1f}** |")
            rows.append(dict(item="lod", strain="", od="", log_cfu="", stock_cfu_per_ml="",
                             volume_ml="", format=f"{area_name} | {pname}", lod_ml=round(lod, 2)))
    lines.append("\n→ For the whole coupon, one colony ≈ 5 CFU/cm². For a single 7×7 mm zone the "
                 "same colony is ≈ 20 CFU/cm², so **zone-resolved work needs the plate to be read "
                 "down to single colonies** and the report to state the LOD explicitly.\n")

    # ---- 4. expressions
    lines.append("\n## 4. Expressions to report\n")
    lines.append("```\n"
                 "CFU/cm²        = (mean colonies × dilution) / plated_volume_mL / area_cm²\n"
                 "log CFU/cm²    = log10(CFU/cm²)\n"
                 "log reduction  = log10(N_control) − log10(N_treated)          [ISO 22196 style, R]\n"
                 "anti-adhesion% = (N_control − N_treated) / N_control × 100    [thesis Eq. 4]\n"
                 "recovery%      = CFU_detached / (CFU_detached + cells_remaining_from_imaging) × 100\n"
                 "```\n")
    lines.append("Worked example (illustrative only, replace with measured values): control "
                 "1.2×10⁵ CFU/cm², LIPSS 6.0×10⁴ CFU/cm² → log reduction = log10(1.2e5) − "
                 "log10(6.0e4) = 5.079 − 4.778 = **0.30**; anti-adhesion = **50 %**.\n")

    md = os.path.join(args.outdir, "viable_count_numbers.md")
    with open(md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    csvp = os.path.join(args.outdir, "viable_count_numbers.csv")
    keys = sorted({k for r in rows for k in r})
    with open(csvp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})
    print(md)
    print(csvp)
    print("\n".join(lines[:40]))


if __name__ == "__main__":
    main()
