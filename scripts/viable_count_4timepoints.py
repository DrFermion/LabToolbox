#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Viable count (CFU) — 4 time point (3/5/7/24 h) planning + analysis.

Two sub-commands:

  template   write a recording template (CSV) for the bench
  analyse    read the filled template -> per-coupon CFU/cm^2, per-condition-per-time
             mean/SD, log reduction vs control, anti-adhesion %, two-way ANOVA

Examples
--------
    python viable_count_4timepoints.py template --out cfu_records_20261116.csv
    python viable_count_4timepoints.py analyse  --csv cfu_records_20261116.csv \
        --control CTRL --times 3,5,7,24

Conventions
-----------
* One row per (coupon, dilution) plated.
* Plate counts must be colonies per plate (integers). Use -1 for TNTC, blank/empty for not plated.
* The valid dilution per coupon is the one whose mean count falls in [25, 250]
  (use --window 30,300 for the ISO 22196 convention; it is recorded in the output).
* Face area comes from the CSV column face_area_cm2 (per coupon, measured).
* Statistics unit = coupon. Plates per coupon are averaged first.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import sys
from collections import defaultdict
from statistics import mean, stdev

FIELDS = [
    "coupon_id", "condition", "batch", "strain", "time_h", "date", "operator",
    "face_area_cm2", "wash_medium", "wash_n", "elute_vol_ml", "saponin",
    "sonication_min", "sonication_T_C", "dilution", "plate1", "plate2",
    "plate_mean", "cfu_per_ml", "cfu_per_coupon", "log_cfu_cm2",
    "second_elution_cfu", "recovery_pct", "notes",
]

TEMPLATE_ROWS = [
    # clearly-marked example rows: delete before use
    dict(coupon_id="EXAMPLE-CTRL-01", condition="CTRL", batch="B01", strain="E. coli",
         time_h=3, date="2026-11-20", operator="RP", face_area_cm2=1.0,
         wash_medium="0.85% NaCl", wash_n=3, elute_vol_ml=2.0, saponin="no",
         sonication_min=5, sonication_T_C=21, dilution="10^-1", plate1=48, plate2=55,
         notes="EXAMPLE ROW - delete"),
    dict(coupon_id="EXAMPLE-CTRL-01", condition="CTRL", batch="B01", strain="E. coli",
         time_h=3, date="2026-11-20", operator="RP", face_area_cm2=1.0,
         wash_medium="0.85% NaCl", wash_n=3, elute_vol_ml=2.0, saponin="no",
         sonication_min=5, sonication_T_C=21, dilution="10^-2", plate1=6, plate2=4,
         notes="EXAMPLE ROW - delete"),
]


def parse_dilution(s: str) -> float:
    """'10^-2' -> 0.01 ; '1e-2' -> 0.01 ; 'neat' / '' / '0' -> 1.0"""
    s = (s or "").strip().lower().replace("−", "-")
    if s in ("", "neat", "0", "undiluted", "原液"):
        return 1.0
    if s.startswith("10^"):
        return 10.0 ** float(s[3:])
    return float(s)


def as_int(x):
    if x is None:
        return None
    s = str(x).strip()
    if s == "":
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def cmd_template(args) -> int:
    with open(args.out, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in TEMPLATE_ROWS:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    print(f"template written: {args.out}")
    print("columns: " + ", ".join(FIELDS))
    print("Two EXAMPLE rows are included; delete them before use.")
    return 0


def read_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def cmd_analyse(args) -> int:
    lo, hi = args.window
    rows = read_rows(args.csv)
    if not rows:
        print("empty csv", file=sys.stderr)
        return 2

    # ---- per (coupon, dilution) plate mean, then pick the valid dilution ----------
    per_coupon = defaultdict(list)   # coupon_id -> list of dict
    meta = {}
    for r in rows:
        cid = (r.get("coupon_id") or "").strip()
        if not cid or cid.upper().startswith("EXAMPLE"):
            continue
        p1, p2 = as_int(r.get("plate1")), as_int(r.get("plate2"))
        tntc = any(v == -1 for v in (p1, p2))
        vals = [v for v in (p1, p2) if v is not None and v >= 0]
        if not vals and not tntc:
            continue            # nothing plated in this row
        dil = parse_dilution(r.get("dilution"))
        try:
            vol = float(r.get("elute_vol_ml") or 2.0)
            area = float(r.get("face_area_cm2") or args.area_cm2 or 1.0)
            t_h = float(r.get("time_h") or 0)
        except ValueError:
            continue
        pm = mean(vals) if vals else None
        per_coupon[cid].append(dict(dil=dil, plate_mean=pm, tntc=tntc, vol=vol, area=area, t_h=t_h,
                                    plate_vol=args.plate_ml,
                                    condition=(r.get("condition") or "?").strip(),
                                    strain=(r.get("strain") or "?").strip()))
        meta[cid] = dict(condition=(r.get("condition") or "?").strip(),
                         strain=(r.get("strain") or "?").strip(), t_h=t_h)

    coupon_values = []      # (condition, strain, time, log10 CFU/cm2)
    out_rows = []
    tntc_only = []
    for cid, entries in per_coupon.items():
        usable = [e for e in entries if e["plate_mean"] is not None]
        m = meta[cid]
        if not usable:
            tntc_only.append(cid)
            out_rows.append(dict(coupon_id=cid, condition=m["condition"], strain=m["strain"],
                                 time_h=m["t_h"], dilution="", plate_mean="", cfu_per_ml="",
                                 cfu_per_coupon="", cfu_cm2="", log_cfu_cm2="",
                                 note="all plates TNTC — re-plate a higher dilution"))
            continue
        valid = [e for e in usable if lo <= e["plate_mean"] <= hi]
        chosen = None
        note = ""
        if valid:
            chosen = max(valid, key=lambda e: e["dil"])      # most concentrated valid
        else:
            below = [e for e in usable if e["plate_mean"] < lo]
            if below:
                chosen = min(below, key=lambda e: e["dil"])
                note = "below window (censored at LOD side) — treat as an upper bound"
            else:
                chosen = max(usable, key=lambda e: e["dil"])
                note = "above window (TNTC at every usable dilution) — treat as a lower bound"
        cfu_ml = chosen["plate_mean"] / (chosen["plate_vol"] * chosen["dil"])
        cfu_coupon = cfu_ml * chosen["vol"]
        cfu_cm2 = cfu_coupon / chosen["area"]
        logv = math.log10(cfu_cm2) if cfu_cm2 > 0 else None
        m = meta[cid]
        out_rows.append(dict(coupon_id=cid, condition=m["condition"], strain=m["strain"],
                             time_h=m["t_h"], dilution=chosen["dil"], plate_mean=chosen["plate_mean"],
                             cfu_per_ml=cfu_ml, cfu_per_coupon=cfu_coupon, cfu_cm2=cfu_cm2,
                             log_cfu_cm2=logv, note=note))
        if logv is not None:
            coupon_values.append((m["condition"], m["strain"], m["t_h"], logv))

    # ---- per condition x time summary -------------------------------------------
    groups = defaultdict(list)
    for cond, strain, t_h, logv in coupon_values:
        groups[(strain, cond, t_h)].append(logv)

    print("=" * 78)
    print(f"PLATE WINDOW {lo}-{hi} colonies | plated {args.plate_ml*1000:.0f} uL | "
          f"face area default {args.area_cm2:g} cm2")
    print("=" * 78)
    print(f"{'strain':<12}{'condition':<14}{'t(h) ':>7}{'n':>4}{'log CFU/cm2':>16}{'SD':>8}")
    summary = {}
    for (strain, cond, t_h), vals in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        mu = mean(vals)
        sd = stdev(vals) if len(vals) > 1 else float("nan")
        summary[(strain, cond, t_h)] = (len(vals), mu, sd)
        print(f"{strain:<12}{cond:<14}{t_h:>6g}{len(vals):>4}{mu:>16.3f}{sd:>8.2f}")

    if tntc_only:
        print("\n[WARNING] all plates TNTC — excluded from statistics, re-plate a higher dilution:")
        for cid in tntc_only:
            print("   " + cid)

    # ---- log reduction / anti-adhesion vs control -------------------------------
    ctrl = args.control
    print("\n--- vs control (" + ctrl + ") ---")
    print(f"{'strain':<12}{'t(h) ':>7}{'condition':<14}{'log R':>8}{'anti-adhesion %':>17}")
    for (strain, cond, t_h), (n, mu, sd) in sorted(summary.items(), key=lambda kv: (kv[0][0], kv[0][2], kv[0][1])):
        if cond == ctrl:
            continue
        key = (strain, ctrl, t_h)
        if key not in summary:
            continue
        n0, mu0, _ = summary[key]
        R = mu0 - mu
        aa = (10 ** mu0 - 10 ** mu) / 10 ** mu0 * 100
        print(f"{strain:<12}{t_h:>7g}{cond:<14}{R:>8.2f}{aa:>17.1f}")

    # ---- two-way ANOVA (optional, needs statsmodels) ----------------------------
    if args.anova:
        try:
            import pandas as pd
            import statsmodels.api as sm
            from statsmodels.formula.api import ols
            df = pd.DataFrame(coupon_values, columns=["condition", "strain", "time_h", "y"])
            for strain, sub in df.groupby("strain"):
                model = ols("y ~ C(condition) * C(time_h)", data=sub).fit()
                tbl = sm.stats.anova_lm(model, typ=2)
                print(f"\n--- two-way ANOVA, strain = {strain} (response: log10 CFU/cm2) ---")
                print(tbl.round(4).to_string())
        except Exception as exc:                      # pragma: no cover
            print(f"\n[anova skipped] {exc}", file=sys.stderr)

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=["coupon_id", "condition", "strain", "time_h", "dilution",
                                               "plate_mean", "cfu_per_ml", "cfu_per_coupon",
                                               "cfu_cm2", "log_cfu_cm2", "note"])
            w.writeheader()
            for r in out_rows:
                w.writerow({k: ("" if r[k] is None else r[k]) for k in w.fieldnames})
        print(f"\nper-coupon results written: {args.out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Viable count 4-time-point planner/analyser")
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("template", help="write a bench recording template")
    t.add_argument("--out", default="cfu_records.csv")
    t.set_defaults(func=cmd_template)

    a = sub.add_parser("analyse", help="analyse a filled recording csv")
    a.add_argument("--csv", required=True)
    a.add_argument("--control", default="CTRL", help="control condition name (default CTRL)")
    a.add_argument("--window", default="25,250", help="countable window, e.g. 25,250 or 30,300")
    a.add_argument("--plate-ml", type=float, default=0.1, dest="plate_ml")
    a.add_argument("--area-cm2", type=float, default=1.0, dest="area_cm2",
                   help="fallback face area if the csv column is empty")
    a.add_argument("--anova", action="store_true", help="also run two-way ANOVA (statsmodels)")
    a.add_argument("--out", default="", help="write per-coupon results csv here")
    a.set_defaults(func=cmd_analyse)

    args = ap.parse_args()
    if getattr(args, "window", None):
        lo, hi = (int(float(x)) for x in str(args.window).split(","))
        args.window = (lo, hi)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
