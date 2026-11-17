#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Back-face / edge contribution in coupon elution CFU — closed-form correction.

Problem
-------
The elution step sonicates the WHOLE coupon, so the recovery liquid contains
bacteria from the treated front face (a_f), the untreated back face (a_b) and the
side edges (a_e).  Dividing by a_f inflates the density; dividing by the total
area dilutes the treatment effect.  No sealing pads -> do the algebra instead.

Model (CFU per coupon)
----------------------
    N = a_f*rho_f + a_b*rho_b + a_e*rho_e

Control coupon: front and back are the same untreated finish -> rho_f = rho_b = rho_u
    N_c = (a_f + a_b)*rho_u + a_e*rho_e

Treated coupon: only the front is treated, back/edges unchanged (assumption A1)
    N_t = a_f*rho_t + a_b*rho_u + a_e*rho_e

Subtract -> the back and the edges CANCEL exactly:
    rho_t = rho_u + (N_t - N_c)/a_f          (A1 only)

With rho_e = k*rho_u (assumption A2 for the absolute level):
    rho_u = N_c / (a_f + a_b + k*a_e)
    AA    = (N_c - N_t)(a_f + a_b + k*a_e) / (a_f * N_c)
          = (1 - N_t/N_c) * G,      G = 2 + k*a_e/a_f   (a_b = a_f)

So the naive ratio difference must be multiplied by G ~ 2.0-2.8 for a plate-like
coupon.  Only A1 (treated back == control back) is needed for the corrected
anti-adhesion; A2 (k) only shifts the absolute density.

Sub-commands
------------
    demo        synthetic validation: does the correction recover a known truth?
    plan        areas / G factor for a given coupon geometry
    apply       apply the correction to a measurement CSV (control column needed)

CSV for `apply` (one row per coupon, one column per metric):
    condition,round,time_h,N_total
"""
from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict


# ---------------------------------------------------------------- geometry ----
def areas(length_mm: float, width_mm: float, thick_mm: float):
    a_f = length_mm * width_mm                    # mm^2, treated face
    a_b = a_f                                     # plate-like coupon
    a_e = 2 * (length_mm + width_mm) * thick_mm   # side edges
    return a_f, a_b, a_e


def gain(length_mm, width_mm, thick_mm, k):
    a_f, a_b, a_e = areas(length_mm, width_mm, thick_mm)
    return (a_f + a_b + k * a_e) / a_f


def rho_u_from_total(N_c, length_mm, width_mm, thick_mm, k):
    a_f, a_b, a_e = areas(length_mm, width_mm, thick_mm)
    # N_c is CFU per coupon; areas in mm^2 -> convert to cm^2 (/100)
    total_cm2 = (a_f + a_b + k * a_e) / 100.0
    return N_c / total_cm2


def corrected_rho_t(N_c, N_t, length_mm, width_mm, thick_mm, k):
    a_f, a_b, a_e = areas(length_mm, width_mm, thick_mm)
    rho_u = rho_u_from_total(N_c, length_mm, width_mm, thick_mm, k)
    rho_t = rho_u + (N_t - N_c) / (a_f / 100.0)
    return rho_u, rho_t


# ------------------------------------------------------------------- demo -----
def cmd_demo(args) -> int:
    L, W, T = args.length, args.width, args.thick
    a_f, a_b, a_e = areas(L, W, T)
    print("=" * 78)
    print(f"coupon {L:g} x {W:g} x {T:g} mm   front {a_f:.0f} mm2 | back {a_b:.0f} mm2 | "
          f"edges {a_e:.0f} mm2 | total/front = {(a_f+a_b+a_e)/a_f:.2f}")
    print("=" * 78)

    rho_u = args.rho_untreated            # CFU/cm^2 on untreated 316L
    print(f"\nassumed untreated density rho_u = {rho_u:.3g} CFU/cm2, k = {args.k}\n")
    print(f"{'true AA':>9}{'rho_t true':>14}{'N_c':>12}{'N_t':>12}"
          f"{'naive AA':>11}{'corrected AA':>14}{'error':>9}")
    for aa in (0.0, 0.1, 0.2, 0.3, 0.5, 0.7):
        rho_t = rho_u * (1 - aa)
        tot_c = (a_f + a_b + args.k * a_e) / 100.0 * rho_u
        tot_t = (a_f + a_b + args.k * a_e) / 100.0 * rho_t + \
                (a_f / 100.0) * 0                      # explicit: same k on both
        # careful: back/edges stay at rho_u for the treated coupon
        tot_t = (a_f / 100.0) * rho_t + ((a_b + args.k * a_e) / 100.0) * rho_u
        naive = 1 - tot_t / tot_c
        ru_hat, rt_hat = corrected_rho_t(tot_c, tot_t, L, W, T, args.k)
        corr = 1 - rt_hat / ru_hat
        print(f"{aa:>9.0%}{rho_t:>14.3g}{tot_c:>12.3g}{tot_t:>12.3g}"
              f"{naive:>11.1%}{corr:>14.1%}{corr-aa:>9.1e}")

    print("\n--- sensitivity to k (edge density relative to faces) ---")
    print(f"{'k':>5}{'G = 2 + k*a_e/a_f':>20}{'AA from a naive 20.8%':>24}")
    for k in (0.0, 0.5, 1.0, 2.0, 3.0):
        g = gain(L, W, T, k)
        print(f"{k:>5.1f}{g:>20.2f}{0.208 * g:>23.1%}")

    print("\n--- sensitivity to assumption A1 (treated back differs by eps) ---")
    print("eps = (rho_back,treated / rho_back,control) - 1")
    print(f"{'eps':>6}{'true AA':>10}{'estimated AA':>15}{'bias':>9}")
    for eps in (0.0, 0.05, 0.10, 0.20, -0.10):
        for aa in (0.3, 0.5):
            rho_t = rho_u * (1 - aa)
            tot_c = (a_f + a_b + args.k * a_e) / 100.0 * rho_u
            tot_t = (a_f / 100.0) * rho_t + (a_b / 100.0) * rho_u * (1 + eps) + \
                    (args.k * a_e / 100.0) * rho_u
            ru_hat, rt_hat = corrected_rho_t(tot_c, tot_t, L, W, T, args.k)
            est = 1 - rt_hat / ru_hat
            print(f"{eps:>6.0%}{aa:>10.0%}{est:>15.1%}{(est-aa)*100:>8.1f}pp")
    return 0


# ------------------------------------------------------------------- plan -----
def cmd_plan(args) -> int:
    print(f"{'coupon (mm)':>16}{'a_f mm2':>9}{'a_b mm2':>9}{'a_e mm2':>9}"
          f"{'total/front':>13}{'G(k=0)':>9}{'G(k=0.5)':>10}{'G(k=1)':>9}")
    for L, W, T in [(5, 5, 0.5), (10, 10, 0.5), (10, 10, 1.0), (15, 15, 1.0),
                    (20, 20, 1.0), (20, 20, 2.0), (25, 25, 1.0)]:
        a_f, a_b, a_e = areas(L, W, T)
        print(f"{f'{L}x{W}x{T}':>16}{a_f:>9.0f}{a_b:>9.0f}{a_e:>9.0f}"
              f"{(a_f+a_b+a_e)/a_f:>13.2f}"
              f"{gain(L,W,T,0.0):>9.2f}{gain(L,W,T,0.5):>10.2f}{gain(L,W,T,1.0):>9.2f}")
    print("\nG = (a_f + a_b + k*a_e)/a_f is what you multiply the naive "
          "(1 - N_t/N_c) by to recover the front-face anti-adhesion.")
    return 0


# ------------------------------------------------------------------ apply -----
def cmd_apply(args) -> int:
    L, W, T, k = args.length, args.width, args.thick, args.k
    rows = list(csv.DictReader(open(args.csv, newline="", encoding="utf-8-sig")))
    if not rows:
        print("empty csv")
        return 2

    # group: (condition, time_h) -> list of (round, N)
    grp = defaultdict(list)
    for r in rows:
        cond = (r.get("condition") or "").strip()
        if not cond:
            continue
        grp[(cond, float(r.get("time_h") or 0))].append(
            ((r.get("round") or "").strip(), float(r.get("N_total"))))

    # match each treated row to the control mean of the same time point (same round)
    ctrl = args.control
    per_time = defaultdict(list)
    for (cond, t), vals in grp.items():
        if cond == ctrl:
            ctrl_by_round = {rd: v for rd, v in vals}
            ctrl_mean = sum(v for _, v in vals) / len(vals)
            for c2, vals2 in grp.items():
                if c2[1] != t or c2[0] == ctrl:
                    continue
                for rd, v in vals2:
                    nc = ctrl_by_round.get(rd, ctrl_mean)
                    ru, rt = corrected_rho_t(nc, v, L, W, T, k)
                    per_time[(c2[0], t, rd)] = (nc, v, ru, rt, 1 - rt / ru)

    print("=" * 96)
    print(f"back/edge correction | coupon {L:g}x{W:g}x{T:g} mm | k = {k} | "
          f"G = {gain(L, W, T, k):.2f}")
    print("=" * 96)
    print(f"{'condition':<14}{'t(h)':>6}{'round':>7}{'N_control':>12}{'N_treated':>11}"
          f"{'rho_u':>12}{'rho_t':>12}{'naive AA':>10}{'corrected AA':>14}")
    for (cond, t, rd), (nc, v, ru, rt, aa) in sorted(per_time.items(),
                                                    key=lambda kv: (kv[0][1], kv[0][0], kv[0][2])):
        naive = 1 - v / nc
        print(f"{cond:<14}{t:>6g}{rd:>7}{nc:>12.4g}{v:>11.4g}{ru:>12.4g}{rt:>12.4g}"
              f"{naive:>10.1%}{aa:>14.1%}")
    print("\nReport the CORRECTED anti-adhesion; state assumptions A1 (back/edges equal "
          "between control and treated coupons) and A2 (k) explicitly.")
    return 0


# --------------------------------------------------------------- simulate -----
def cmd_simulate(args) -> int:
    """Monte-Carlo: bias, noise amplification and CI coverage of the correction."""
    import numpy as np
    rng = np.random.default_rng(args.seed)
    L, W, T, k = args.length, args.width, args.thick, args.k
    a_f, a_b, a_e = areas(L, W, T)
    B = a_b + k * a_e
    rho_u = args.rho_untreated
    g = (a_f + B) / a_f
    print("=" * 92)
    print(f"Monte-Carlo | {L:g}x{W:g}x{T:g} mm | k={k} | G={g:.2f} | "
          f"{args.rounds} rounds/cell | log-SD per coupon = {args.log_sd}")
    print("=" * 92)
    print(f"{'true AA':>8}{'per-coupon AA mean':>20}{'SD':>9}{'CI95 coverage':>15}"
          f"{'ratio-of-means mean':>21}{'SD':>9}")
    for aa in (0.0, 0.2, 0.5):
        rho_t = rho_u * (1 - aa)
        Nc_true = (a_f + B) / 100.0 * rho_u
        Nt_true = (a_f / 100.0) * rho_t + (B / 100.0) * rho_u
        per, rom, cover = [], [], 0
        for _ in range(args.trials):
            vc, vt, cell = [], [], []
            for _rd in range(args.rounds):
                nc = Nc_true * 10 ** rng.normal(0, args.log_sd)
                nt = Nt_true * 10 ** rng.normal(0, args.log_sd)
                vc.append(nc); vt.append(nt)
                ru = nc / ((a_f + B) / 100.0)
                rt = ru + (nt - nc) / (a_f / 100.0)
                cell.append(1 - rt / ru)
            per.extend(cell)
            mc, mt = float(np.mean(vc)), float(np.mean(vt))
            ru_m = mc / ((a_f + B) / 100.0)
            rt_m = ru_m + (mt - mc) / (a_f / 100.0)
            rom.append(1 - rt_m / ru_m)
            m, s = float(np.mean(cell)), float(np.std(cell, ddof=1))
            if s > 0 and abs(m - aa) < 1.96 * s / np.sqrt(len(cell)):
                cover += 1
        print(f"{aa:>8.0%}{np.mean(per):>20.1%}{np.std(per):>9.1%}"
              f"{cover/args.trials:>15.0%}{np.mean(rom):>21.1%}{np.std(rom):>9.1%}")
    print("")
    print("Noise amplification check (theory says exactly G):")
    Nc_true = (a_f + B) / 100.0 * rho_u
    Nt_true = (a_f / 100.0) * rho_u * 0.5 + (B / 100.0) * rho_u
    naive, corr = [], []
    for _ in range(4000):
        nc = Nc_true * 10 ** rng.normal(0, args.log_sd)
        nt = Nt_true * 10 ** rng.normal(0, args.log_sd)
        naive.append(1 - nt / nc)
        ru = nc / ((a_f + B) / 100.0)
        rt = ru + (nt - nc) / (a_f / 100.0)
        corr.append(1 - rt / ru)
    print(f"  SD(naive) = {np.std(naive):.3f}   SD(corrected) = {np.std(corr):.3f}   "
          f"observed amplification = {np.std(corr)/np.std(naive):.2f}  (G = {g:.2f})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="coupon elution: back-face/edge correction")
    sub = ap.add_subparsers(dest="cmd", required=True)

    common = dict(length=10.0, width=10.0, thick=1.0, k=1.0)

    d = sub.add_parser("demo", help="synthetic validation of the correction")
    d.add_argument("--length", type=float, default=common["length"])
    d.add_argument("--width", type=float, default=common["width"])
    d.add_argument("--thick", type=float, default=common["thick"])
    d.add_argument("--k", type=float, default=common["k"])
    d.add_argument("--rho-untreated", type=float, default=1.0e5, dest="rho_untreated")
    d.set_defaults(func=cmd_demo)

    p = sub.add_parser("plan", help="area table and G factors")
    p.set_defaults(func=cmd_plan)

    a = sub.add_parser("apply", help="apply the correction to measurements")
    a.add_argument("--csv", required=True)
    a.add_argument("--control", default="CTRL")
    a.add_argument("--length", type=float, default=common["length"])
    a.add_argument("--width", type=float, default=common["width"])
    a.add_argument("--thick", type=float, default=common["thick"])
    a.add_argument("--k", type=float, default=common["k"])
    a.set_defaults(func=cmd_apply)

    s = sub.add_parser("simulate", help="Monte-Carlo on bias / noise / CI coverage")
    s.add_argument("--length", type=float, default=common["length"])
    s.add_argument("--width", type=float, default=common["width"])
    s.add_argument("--thick", type=float, default=common["thick"])
    s.add_argument("--k", type=float, default=common["k"])
    s.add_argument("--rounds", type=int, default=3)
    s.add_argument("--log-sd", type=float, default=0.10, dest="log_sd")
    s.add_argument("--trials", type=int, default=2000)
    s.add_argument("--rho-untreated", type=float, default=1.0e5, dest="rho_untreated")
    s.add_argument("--seed", type=int, default=11)
    s.set_defaults(func=cmd_simulate)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
