# -*- coding: utf-8 -*-
"""Protocol-protein simulation: BSA (two literature sets) + human fibrinogen on the three 515 nm surface
conditions, fresh vs final stable period. Uses the same model core as proteins_environments.py.
Outputs: CSV + figures + console table."""
import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, r"E:\LabToolbox")
from labtoolbox.xdlvo.xdlvo import SurfaceEnergy, delta_g, interaction_energy  # noqa: E402

OUT = r"E:\LabToolbox\output\proteins_protocol_bsa_fg_20261001"
os.makedirs(OUT, exist_ok=True)
NM = 1e-9; I_M = 0.15; T = 310.15
Z_M = -25.0
DG_CSV = r"E:\LabToolbox\output\xdlvo_515nm_20260912\xdlvo_515nm_dG.csv"
STABLE_DAYS = [49, 58, 65, 73]
DROP_DAYS = {7, 8, 9, 10, 81}

PROT = {
    "BSA set A": dict(g=(40.60, 1.16, 20.03), R=3.5, z=-13.0, src="Wang & Newby 2014, Biointerphases 9, 041006"),
    "BSA set B": dict(g=(43.22, 1.065, 47.68), R=3.5, z=-13.0, src="Membranes 2025, 15, 277, Table 3"),
    "Human fibrinogen": dict(g=(37.6, 0.1, 38.0), R=5.0, z=-20.0, src="van Oss 1990, J. Protein Chem. 9, 487"),
}
se = lambda g: SurfaceEnergy(g[0], g[1], g[2], 2 * np.sqrt(g[1] * g[2]), g[0] + 2 * np.sqrt(g[1] * g[2]))

raw = pd.read_csv(DG_CSV, encoding="utf-8-sig")
surf = (raw.drop_duplicates(["surface", "day"])[["surface", "day", "gamma_LW", "gamma_plus", "gamma_minus"]]
        .sort_values(["surface", "day"]).reset_index(drop=True))
SURFACES = sorted(surf["surface"].unique())
print("surfaces:", SURFACES)

def state_energies(name):
    sub = surf[(surf["surface"] == name) & (~surf["day"].isin(DROP_DAYS))]
    rows = {int(r["day"]): r for _, r in sub.iterrows()}
    out = {}
    if 0 in rows:
        r = rows[0]; out["fresh (day 0)"] = se((r["gamma_LW"], r["gamma_plus"], r["gamma_minus"]))
    st = [r for d, r in rows.items() if d in STABLE_DAYS]
    if st:
        g = tuple(np.mean([r[c] for r in st]) for c in ("gamma_LW", "gamma_plus", "gamma_minus"))
        out["stable period (day 49-73)"] = se(g)
    return out

rows_out, profs = [], {}
for sname in SURFACES:
    for state, s_e in state_energies(sname).items():
        for pname, p in PROT.items():
            p_e = se(p["g"])
            dgc = delta_g(s_e, p_e, I_M, T, zeta_m=Z_M, zeta_f=p["z"])
            prof = interaction_energy(s_e, p_e, dgc, p["R"], I_M, T, zeta_m=Z_M, zeta_f=p["z"])
            h = np.asarray(prof["h"], dtype=float); tot = np.asarray(prof["TOT"], dtype=float)
            row = dict(surface=sname, state=state, protein=pname,
                       dG_ADH_mJm2=round(float(dgc["TOT"]), 2),
                       dG_LW=round(float(dgc["LW"]), 2), dG_AB=round(float(dgc["AB"]), 2), dG_EL=round(float(dgc.get("EL", 0.0)), 3),
                       barrier_kT=round(float(tot.max()), 1), well_kT=round(float(tot.min()), 1),
                       h_well_nm=round(float(h[int(tot.argmin())]), 3),
                       R_nm=p["R"], zeta_mV=p["z"], source=p["src"])
            rows_out.append(row)
            profs[(sname, state, pname)] = (h, tot)
            print(f"  {sname:18s} {state:24s} {pname:17s} ΔG={row['dG_ADH_mJm2']:7.2f} mJ/m²  barrier={row['barrier_kT']:9.1f} kT  well={row['well_kT']:9.1f} kT @ {row['h_well_nm']:.3f} nm")

res = pd.DataFrame(rows_out)
res.to_csv(os.path.join(OUT, "bsa_fg_protocol_predictions.csv"), index=False)

# --- fig A: ΔG and barrier for the three proteins, fresh vs stable, per surface ---
fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.2), dpi=200, sharex=True)
prots = list(PROT.keys()); states = ["fresh (day 0)", "stable period (day 49-73)"]
for j, sname in enumerate(SURFACES):
    for i, metric, ylab in ((0, "dG_ADH_mJm2", "ΔG_ADH (mJ/m²)"), (1, "barrier_kT", "barrier (kT)")):
        ax = axes[i][j]
        vals = [[res[(res.surface == sname) & (res.state == st) & (res.protein == p)][metric].iloc[0]
                 for p in prots] for st in states]
        x = np.arange(len(prots)); w = 0.38
        ax.bar(x - w / 2, vals[0], w, label="fresh", color="#3b6ea5")
        ax.bar(x + w / 2, vals[1], w, label="stable", color="#c0504d")
        ax.axhline(0, color="k", lw=0.7)
        ax.set_xticks(x); ax.set_xticklabels([p.replace(" ", "\n") for p in prots], fontsize=7)
        if i == 0: ax.set_title(sname.replace("_", " "), fontsize=9)
        if j == 0: ax.set_ylabel(ylab, fontsize=9)
        for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
        if i == 0 and j == 0: ax.legend(fontsize=7, frameon=False)
fig.suptitle("Protocol proteins (BSA sets A/B, human fibrinogen) on 515 nm surfaces — 37 °C, I = 0.15 M", fontsize=11, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.95)); fig.savefig(os.path.join(OUT, "fig_protocol_dG_barrier.png")); plt.close(fig)

# --- fig B: U(h) profiles, LIPSS and control, fresh vs stable ---
lip = [s for s in SURFACES if "LIPSS" in s.upper()]
ctl = [s for s in SURFACES if "CONTROL" in s.upper() or "316" in s.upper()]
pick = (lip or SURFACES)[:1] + (ctl or [])[:1]
fig, axes = plt.subplots(2, len(pick), figsize=(11.5, 7.0), dpi=200, sharey=True)
for j, sname in enumerate(pick):
    for i, state in enumerate(states):
        ax = axes[i][j]
        for pname in prots:
            h, tot = profs[(sname, state, pname)]
            ax.plot(h, tot, lw=1.5, label=pname)
        ax.axhline(0, color="k", lw=0.7); ax.set_xscale("log"); ax.set_xlim(0.1, 30)
        if i == 1: ax.set_xlabel("separation h (nm)")
        if j == 0: ax.set_ylabel(f"U(h) (kT)\n{state.split(' (')[0]}", fontsize=9)
        if i == 0: ax.set_title(sname.replace("_", " "), fontsize=9)
        for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
        if i == 0 and j == 0: ax.legend(fontsize=7, frameon=False)
fig.suptitle("Interaction energy profiles of the protocol proteins (37 °C, I = 0.15 M)", fontsize=11, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.95)); fig.savefig(os.path.join(OUT, "fig_protocol_uh_profiles.png")); plt.close(fig)
print("\nsaved to", OUT)
print(res[["surface", "state", "protein", "dG_ADH_mJm2", "barrier_kT", "well_kT"]].to_string(index=False))
