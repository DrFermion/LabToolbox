# -*- coding: utf-8 -*-
"""Numbers behind the viable-clone-count (CFU) protocol — full-face coupon design (v2).

Samples are small stainless coupons whose WHOLE front face carries one surface condition
(control / LIPSS / nanopillar are separate coupons), so the recovery is a whole-coupon
recovery and the area is the face area of one coupon.

  env -u PYTHONPATH C:/Users/PC/miniconda3/python.exe scripts/viable_count_plan_v2.py \
      --area-cm2 1.0 --recovery-ml 2.0 --outdir E:/LabToolbox/output/viable_count_plan_v2_20261111
"""
from __future__ import annotations

import argparse
import csv
import os

CAL = {
    "E. coli F1693": dict(a=0.894112, b=7.840927, od=0.78, window=(0.45, 1.48)),
    "S. aureus ATCC 12600": dict(a=0.529595, b=7.446047, od=0.90, window=(0.20, 1.06)),
    "P. aeruginosa ATCC 10145": dict(a=1.269960, b=7.776717, od=0.63, window=(0.14, 1.00)),
}
BATH_ML = 30.0
BATH_TARGET = 1e7
AREAS = [0.25, 0.5, 1.0, 2.0, 4.0]      # cm²; 4.0 = the old 20 x 20 mm coupon
RECOVERY_ML = 2.0
PLATE_ML = 0.1
COUNTABLE = (25, 250)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--area-cm2", type=float, default=1.0, help="front-face area of ONE coupon")
    ap.add_argument("--recovery-ml", type=float, default=RECOVERY_ML)
    ap.add_argument("--bath-ml", type=float, default=BATH_ML)
    ap.add_argument("--outdir", default="E:/LabToolbox/output/viable_count_plan_v2_20261111")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    L = ["# Viable clone count (CFU) — worked numbers, full-face coupon design (v2)\n",
         f"One coupon = one surface condition; face area **{a.area_cm2:g} cm²**, "
         f"recovery volume **{a.recovery_ml:g} mL**, plate 100 µL, countable window "
         f"{COUNTABLE[0]}–{COUNTABLE[1]}.\n"]

    # 1. inoculum
    L += ["\n## 1. Inoculum for a 1 × 10⁷ CFU/mL bath\n",
          f"| strain | OD600 | log CFU/mL | stock (CFU/mL) | volume into {a.bath_ml:g} mL |",
          "|---|---|---|---|---|"]
    rows = []
    for s, c in CAL.items():
        lg = c["a"] * c["od"] + c["b"]
        conc = 10 ** lg
        vol = BATH_TARGET * a.bath_ml / conc
        L.append(f"| {s} | {c['od']:.2f} | {lg:.2f} | {conc:.2e} | **{vol:.2f} mL** |")
        rows.append(dict(item="inoculum", strain=s, od=c["od"], log_cfu=round(lg, 3),
                         conc=float(f"{conc:.4e}"), volume_ml=round(vol, 3)))

    # 2. area-resolved LOD and dilution need
    L += ["\n## 2. Limit of detection and dilution need vs coupon face area\n",
          f"LOD = (1 colony ÷ {PLATE_ML*1000:.0f} µL) × {a.recovery_ml:g} mL ÷ area\n",
          "| face area (cm²) | LOD (CFU/cm²) | 10⁴ CFU/cm² → CFU/mL in recoverate | first dilution "
          "in window | 10⁵ CFU/cm² → CFU/mL | first dilution in window |",
          "|---|---|---|---|---|---|"]
    for A in sorted(set(AREAS + [a.area_cm2])):
        lod = (1.0 / PLATE_ML) * a.recovery_ml / A
        cells_lo = 1e4 * A
        cells_hi = 1e5 * A
        c_lo = cells_lo / a.recovery_ml
        c_hi = cells_hi / a.recovery_ml

        def first(c):
            d = 0
            while c / (10 ** d) * PLATE_ML > COUNTABLE[1] and d < 8:
                d += 1
            return f"10^-{d}" if d else "neat"

        mark = " **← if your coupon**" if abs(A - a.area_cm2) < 1e-9 else ""
        L.append(f"| {A:g}{mark} | {lod:.1f} | {c_lo:.2e} | {first(c_lo)} | {c_hi:.2e} | "
                 f"{first(c_hi)} |")
        rows.append(dict(item="lod", strain="", od="", log_cfu="", conc="", volume_ml="",
                         area_cm2=A, lod_cfu_cm2=round(lod, 2)))

    # 3. where the window sits for the chosen area
    lo_total, hi_total = 1e4 * a.area_cm2, 1e6 * a.area_cm2
    L += ["\n## 3. Practical recipe for your coupon\n",
          f"- Expected adhered population at 10⁴–10⁶ CFU/cm²: **{lo_total:.1e} – {hi_total:.1e} CFU "
          f"per coupon**",
          f"- After {a.recovery_ml:g} mL recovery: **{lo_total/a.recovery_ml:.1e} – "
          f"{hi_total/a.recovery_ml:.1e} CFU/mL**",
          f"- Plate the series **10⁻¹ … 10⁻⁴** (two 100 µL plates each); that spans the whole "
          f"range without re-planning",
          f"- LOD for this coupon: **{(1/PLATE_ML)*a.recovery_ml/a.area_cm2:.1f} CFU/cm²** "
          f"(one colony on the plate)",
          "- If a whole run lands below the window, switch to membrane filtration (0.45 µm) and "
          "report the filtration LOD instead"]

    # 4. expressions
    L += ["\n## 4. Expressions\n", "```",
          "CFU/cm²        = (mean colonies × dilution) / plated_volume_mL / face_area_cm²",
          "log reduction  = log10(N_control) − log10(N_treated)        [ISO 22196 style, R]",
          "anti-adhesion% = (N_control − N_treated) / N_control × 100  [thesis Eq. 4]",
          "recovery%      = CFU_detached / (CFU_detached + residual cells on the same coupon) × 100",
          "```",
          "The second term of the recovery expression is now measurable on the SAME coupon: after "
          "detachment the coupon is stained (SYTO 9) or imaged by SEM and the cells still on the "
          "surface are counted — the full-face design makes that possible without sibling coupons.\n"]

    md = os.path.join(a.outdir, "viable_count_numbers_v2.md")
    open(md, "w", encoding="utf-8").write("\n".join(L))
    csvp = os.path.join(a.outdir, "viable_count_numbers_v2.csv")
    keys = sorted({k for r in rows for k in r})
    with open(csvp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})
    print(md)
    print(csvp)
    print("\n".join(L))


if __name__ == "__main__":
    main()
