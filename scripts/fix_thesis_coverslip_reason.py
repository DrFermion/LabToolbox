# -*- coding: utf-8 -*-
"""Thesis §3.4.1.1: remove the coverslip rationale (and the rim/transition clause).

The current samples are small coupons whose whole front face is treated and flat, so there is
no height step and no untextured rim — the capillary-accumulation argument no longer applies.
The factual imaging description (no coverslip, long-working-distance air objective, thin saline
layer) is kept; only the justification and the rim wording are removed.  Idempotent.
"""
from __future__ import annotations

import datetime
import os
import shutil

import docx

THESIS = (r"F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - "
          r"Ruinong Pan_Antibacterial Surfaces/Thesis.docx")
BACKUP_DIR = os.path.join(os.path.dirname(THESIS), "Thesis_backups")


def rep(run, old, new, label):
    n = run.text.count(old)
    assert n == 1, f"[{label}] anchor count {n} != 1"
    run.text = run.text.replace(old, new)
    print(f"  ok  {label}")


def main():
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup = os.path.join(BACKUP_DIR, f"Thesis_backup_{stamp}_before_coverslip_reason_fix.docx")
    shutil.copy2(THESIS, backup)
    print("backup:", backup)

    d = docx.Document(THESIS)
    p293 = d.paragraphs[293]

    old_a = ("Because the whole textured face of a coupon lies a few micrometres below the "
             "surrounding un-irradiated rim, a coverslip would draw the adhering cells toward "
             "that recess by capillary action; the surfaces were therefore imaged without a "
             "coverslip using a long-working-distance air objective, kept covered with a thin "
             "layer of saline throughout.")
    new_a = ("The surfaces were imaged without a coverslip using a long-working-distance air "
             "objective, kept covered with a thin layer of saline throughout.")

    old_b = ("taken from the central portion of the face and away from the rim where the "
             "transition between textured and untextured metal lies,")
    new_b = "taken from the central portion of each face, away from the coupon edges,"

    hit_a = hit_b = False
    for r in p293.runs:
        if old_a in r.text:
            rep(r, old_a, new_a, "remove coverslip rationale")
            hit_a = True
        if old_b in r.text:
            rep(r, old_b, new_b, "remove rim/transition clause")
            hit_b = True
    assert hit_a, "coverslip rationale sentence not found"
    assert hit_b, "rim clause not found"

    d.save(THESIS)
    print("saved:", THESIS)

    d2 = docx.Document(THESIS)
    t = d2.paragraphs[293].text
    for bad in ("capillary", "recess", "un-irradiated rim", "untextured metal", "×10"):
        assert bad not in t, f"still contains: {bad}"
    print("  OK  no capillary / recess / rim / ×10 wording left")
    print("\n--- final microscopy paragraph ---\n" + t)


if __name__ == "__main__":
    main()
