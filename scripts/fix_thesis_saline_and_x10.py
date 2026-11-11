# -*- coding: utf-8 -*-
"""Two corrections to Thesis §3.4.1 after the user's review:
  (1) resuspension saline 0.9 % -> 0.85 % (matches the governing protocol and the historical data);
  (2) remove every ×10 mention from the microscopy paragraph (the ×10 exclusion sentence and the
      ×10 field-of-view value).
Idempotent: every replacement asserts its anchor exists exactly once.
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
    backup = os.path.join(BACKUP_DIR, f"Thesis_backup_{stamp}_before_saline_and_x10_fix.docx")
    shutil.copy2(THESIS, backup)
    print("backup:", backup)

    d = docx.Document(THESIS)

    # (1) 0.9 % -> 0.85 % NaCl
    done = False
    for r in d.paragraphs[289].runs:
        if "0.9 % NaCl" in r.text:
            rep(r, "resuspending in 0.9 % NaCl", "resuspending in 0.85 % NaCl", "saline 0.85 %")
            done = True
    assert done, "0.9 % NaCl not found in para 289"

    # (2a) drop the ×10 exclusion sentence I added earlier
    p293 = d.paragraphs[293]
    drop = (" fields recorded at ×10 magnification were used only to locate the coupon and were "
            "not counted, because the diffraction limit at that magnification (≈1.3 µm) is larger "
            "than the width of E. coli (≈0.8 µm);")
    done_a = False
    for r in p293.runs:
        if drop in r.text:
            rep(r, drop, "", "drop ×10 exclusion sentence")
            done_a = True
    assert done_a, "×10 exclusion sentence not found"

    # (2b) drop the ×10 field-of-view value
    done_b = False
    for r in p293.runs:
        if "and 7.39 × 10⁵ µm² at ×10" in r.text:
            rep(r, "at ×40 and 7.39 × 10⁵ µm² at ×10.", "at ×40.", "drop ×10 field area")
            done_b = True
    assert done_b, "×10 field-of-view clause not found"

    d.save(THESIS)
    print("saved:", THESIS)

    # ---- verify
    d2 = docx.Document(THESIS)
    p289 = d2.paragraphs[289].text
    p293 = d2.paragraphs[293].text
    assert "0.85 % NaCl" in p289 and "0.9 % NaCl" not in p289, "saline check failed"
    assert "×10" not in p293, "a ×10 mention survives in the microscopy paragraph"
    print("  OK  saline -> 0.85 %")
    print("  OK  no ×10 in the microscopy paragraph")
    # where else does ×10 appear in the body?
    hits = [(i, p.text[:160]) for i, p in enumerate(d2.paragraphs) if "×10" in p.text or "10×" in p.text]
    print(f"  ×10 mentions elsewhere in the body: {len(hits)}")
    for i, t in hits[:10]:
        print(f"    [{i}] {t}")


if __name__ == "__main__":
    main()
