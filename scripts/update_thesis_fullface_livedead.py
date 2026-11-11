# -*- coding: utf-8 -*-
"""Update Thesis §3.4.1 (bacterial anti-adhesion assay) for the full-face sample design.

Old design: one coupon carried several zones (control / LIPSS / nanopillar) side by side.
New design: small coupons, the WHOLE front face of each coupon carries one condition.

Every replacement asserts its anchor occurs exactly once in the target run, so the edit is
idempotent and refuses to fire twice. A timestamped backup is written to Thesis_backups/.
"""
from __future__ import annotations

import datetime
import os
import shutil

import docx

THESIS = (r"F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - "
          r"Ruinong Pan_Antibacterial Surfaces/Thesis.docx")
BACKUP_DIR = os.path.join(os.path.dirname(THESIS), "Thesis_backups")


def replace_in_run(run, old, new, label):
    s = run.text
    n = s.count(old)
    assert n == 1, f"[{label}] anchor found {n} times, expected 1"
    run.text = s.replace(old, new)
    print(f"  ok  {label}: {len(old)} chars -> {len(new)} chars")


def main():
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup = os.path.join(BACKUP_DIR, f"Thesis_backup_{stamp}_before_fullface_update.docx")
    shutil.copy2(THESIS, backup)
    print("backup:", backup)

    d = docx.Document(THESIS)
    p289 = d.paragraphs[289]
    p290 = d.paragraphs[290]
    p293 = d.paragraphs[293]
    p294 = d.paragraphs[294]

    # ---- 1. state the new sample design in the assay paragraph -------------------
    anchor1 = ("The anti-adhesion performance of the laser-textured surfaces was assessed "
               "with a static bacterial adhesion assay.")
    add1 = (" Each coupon carries a single surface condition: the whole front face is either "
            "the polished control or is laser-textured over its entire area, so that a treated "
            "region never shares a coupon with an untreated one and every coupon is an "
            "independent replicate of exactly one surface condition.")
    done1 = False
    for r in p289.runs:
        if anchor1 in r.text:
            replace_in_run(r, anchor1, anchor1 + add1, "para289 full-face design")
            done1 = True
            break
    assert done1, "para289 anchor not found"

    # ---- 2. replicates vs fields (pseudo-replication) ---------------------------
    anchor2 = "so that only the surface topography differed between the samples."
    add2 = (" The three coupons of a condition are the independent replicates: the fields "
            "recorded on one coupon are averaged into a single value before any comparison, "
            "so that field-to-field scatter within a coupon does not inflate the replicate "
            "number.")
    done2 = False
    for r in p290.runs:
        if anchor2 in r.text:
            replace_in_run(r, anchor2, anchor2 + add2, "para290 replicate structure")
            done2 = True
            break
    assert done2, "para290 anchor not found"

    # ---- 3. coverslip rationale + rim avoidance + x10 exclusion -----------------
    old3 = ("Because the laser-textured coupons carry recessed treated areas, over which a "
            "coverslip would draw the adhering cells together by capillary action, the "
            "surfaces were imaged without a coverslip using a long-working-distance air "
            "objective, kept covered with a thin layer of saline throughout.")
    new3 = ("Because the whole textured face of a coupon lies a few micrometres below the "
            "surrounding un-irradiated rim, a coverslip would draw the adhering cells toward "
            "that recess by capillary action; the surfaces were therefore imaged without a "
            "coverslip using a long-working-distance air objective, kept covered with a thin "
            "layer of saline throughout.")
    old3b = ("Several randomly selected fields were recorded per coupon, with the same number "
             "of fields for every surface condition;")
    new3b = ("Several randomly selected fields were recorded per coupon, taken from the "
             "central portion of the face and away from the rim where the transition between "
             "textured and untextured metal lies, with the same number of fields for every "
             "surface condition; fields recorded at ×10 magnification were used only to locate "
             "the coupon and were not counted, because the diffraction limit at that "
             "magnification (≈1.3 µm) is larger than the width of E. coli (≈0.8 µm);")
    hit3 = hit3b = False
    for r in p293.runs:
        if old3 in r.text:
            replace_in_run(r, old3, new3, "para293 coverslip rationale")
            hit3 = True
        if old3b in r.text:
            replace_in_run(r, old3b, new3b, "para293 rim + x10")
            hit3b = True
    assert hit3 and hit3b, f"para293 anchors: {hit3=} {hit3b=}"

    # ---- 4. analysis paragraph: state the coupon-level unit ---------------------
    anchor4 = "and the results were expressed as cell densities (cells cm⁻²)"
    add4 = (" (per projected area, with the developed-area normalisation of Section 4.2 "
            "reported alongside the projected value)")
    done4 = False
    for r in p294.runs:
        if anchor4 in r.text:
            replace_in_run(r, anchor4, anchor4 + add4, "para294 density basis")
            done4 = True
            break
    assert done4, "para294 anchor not found"

    d.save(THESIS)
    print("saved:", THESIS)

    # ---- verify by reloading --------------------------------------------------
    d2 = docx.Document(THESIS)
    checks = {
        "full face per coupon": "whole front face is either the polished control",
        "replicates": "The three coupons of a condition are the independent replicates",
        "rim": "lies a few micrometres below the surrounding un-irradiated rim",
        "x10 excluded": "were used only to locate the coupon and were not counted",
        "density basis": "per projected area, with the developed-area normalisation",
    }
    body = "\n".join(p.text for p in d2.paragraphs)
    for k, v in checks.items():
        print(f"  {'OK ' if v in body else 'MISSING'} {k}")
        assert v in body, k
    print("paragraphs:", len(d2.paragraphs), "tables:", len(d2.tables))


if __name__ == "__main__":
    main()
