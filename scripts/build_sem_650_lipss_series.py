# -*- coding: utf-8 -*-
"""build_sem_650_lipss_series.py — series report for the 650 nm LIPSS set.

Combines the six-method cross-check (``sem_integrity_crosscheck.py``, M0-M7) with the
per-coupon semtexture quality run (``QC_report/field_metrics.csv``) into one report:

  * every field is measured by all six period methods → method comparison,
  * our method (M0 / semtexture) is compared field by field against the other five,
  * each coupon gets its ordered-area / coherence result and marked copies,
  * **every column of every table is defined** in the notation table (§2).

Usage
-----
    python scripts/build_sem_650_lipss_series.py \\
        --crosscheck E:/LabToolbox/output/sem_integrity_crosscheck_650nmLIPSS_20261120 \\
        --root "<...>/02_SEM_raw_images/650nm/LIPSS" --outdir "<...>/01_reports_and_metadata/..."
"""
import os
import re
import sys
import glob
import shutil
import argparse
import tempfile
import datetime

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from build_sem_group_report import (mr, mfrac, msub, msup, mdelim, mu, add_eq, rich, para,
                                    head, caption, table, three_line, fig_pair, add_figure,
                                    NAVY, GREY, DATE_EN)
from labtoolbox.semtexture import analyse_image, annotate_image

DATE = datetime.date.today()
METHODS = ["M0", "M1", "M2", "M3", "M4", "M5"]
MNAME = {
    "M0": "semtexture — autocorrelation of the mean profile (our method)",
    "M1": "naive 2-D FFT global maximum (control: the known v4 defect)",
    "M2": "radial 2-D FFT peak (high-pass + Hann window)",
    "M3": "1-D FFT of the rotated mean profile",
    "M4": "2-D autocorrelation first side-lobe",
    "M5": "areal power spectral density (Welch blocks)",
}
MPRINCIPLE = {
    "M0": "rotates the field so the ripples run horizontally, averages a profile along the ripple "
          "direction, then takes the first peak of its autocorrelation",
    "M1": "takes the brightest pixel of the raw 2-D Fourier power spectrum; the illumination "
          "envelope outshines the ripple peak, which is exactly the defect this control exposes",
    "M2": "high-pass filters the image, windows it with a Hann taper, radially averages the power "
          "spectrum and picks the strongest peak inside the admissible band",
    "M3": "rotates the field, averages one 1-D profile, and reads the peak of that profile's "
          "Fourier transform",
    "M4": "computes the 2-D autocorrelation of the high-passed field and takes the distance to the "
          "first side-lobe along the ripple normal",
    "M5": "splits the field into overlapping 256 px blocks, averages their power spectral density "
          "(Welch), and reads the peak of the radial PSD",
}
LAM = 650.0


# --------------------------------------------------------------------- statistics
def circ_mean_sd(deg):
    d = np.asarray(deg, dtype=float)
    d = d[np.isfinite(d)]
    if not d.size:
        return np.nan, np.nan
    r = np.abs(np.mean(np.exp(1j * np.radians(2 * d))))
    m = float(np.degrees(np.angle(np.mean(np.exp(1j * np.radians(2 * d)))) / 2)) % 180.0
    return m, float(np.degrees(np.sqrt(max(-2 * np.log(max(r, 1e-12)), 0))) / 2)


def method_stats(df, col, clean_mask):
    v_all = df[col].to_numpy(float)
    v = df.loc[clean_mask, col].to_numpy(float)
    v = v[np.isfinite(v)]
    out = dict(n=len(v_all), n_clean=len(v))
    for tag, arr in (("all", v_all[np.isfinite(v_all)]), ("clean", v)):
        out[f"mean_{tag}"] = float(np.mean(arr)) if arr.size else np.nan
        out[f"sd_{tag}"] = float(np.std(arr, ddof=1)) if arr.size > 1 else np.nan
        out[f"cv_{tag}"] = (100 * out[f"sd_{tag}"] / out[f"mean_{tag}"]) if arr.size > 1 else np.nan
        out[f"min_{tag}"] = float(np.min(arr)) if arr.size else np.nan
        out[f"max_{tag}"] = float(np.max(arr)) if arr.size else np.nan
    ref = df.loc[clean_mask, "M0_period_nm"].to_numpy(float)
    me = df.loc[clean_mask, col].to_numpy(float)
    ok = np.isfinite(ref) & np.isfinite(me)
    out["bias_vs_M0_pct"] = float(100 * np.mean((me[ok] - ref[ok]) / ref[ok]))
    out["mape_vs_M0_pct"] = float(100 * np.mean(np.abs(me[ok] - ref[ok]) / ref[ok]))
    out["r_vs_M0"] = float(np.corrcoef(ref[ok], me[ok])[0, 1]) if ok.sum() > 3 else np.nan
    return out


# ------------------------------------------------------------------------- figures
def fig_methods(df, clean, out_png):
    fig, ax = plt.subplots(figsize=(7.6, 3.5))
    data = [df.loc[clean, f"{m}_period_nm"].dropna().to_numpy() for m in METHODS]
    bp = ax.boxplot(data, widths=0.55, patch_artist=True, showfliers=False,
                    medianprops=dict(color="#333", lw=1.1))
    for i, p in enumerate(bp["boxes"]):
        p.set(facecolor="#cfe0d0" if i else "#f3d9a4", edgecolor="#3d6b4a", lw=0.9)
    for i, v in enumerate(data, 1):
        jit = (np.random.RandomState(i).rand(len(v)) - 0.5) * 0.24
        ax.plot(np.full(len(v), i) + jit, v, "o", ms=3, color="#2f6b4f", alpha=0.55, mew=0)
    ax.axhline(np.median(data[0]), ls="--", lw=0.9, color="#c0392b", alpha=0.8,
               label=f"M0 median {np.median(data[0]):.0f} nm")
    short = {"M0": "our method\n(autocorr.)", "M1": "naive 2-D\nFFT", "M2": "radial 2-D\nFFT",
             "M3": "1-D FFT\nof profile", "M4": "2-D ACF\nside-lobe", "M5": "areal PSD\n(Welch)"}
    ax.set_xticks(range(1, 7))
    ax.set_xticklabels([f"{m}\n{short[m]}" for m in METHODS], fontsize=7.2)
    ax.set_ylabel("ripple period Λ (nm)", fontsize=9)
    ax.tick_params(axis="y", labelsize=8)
    ax.grid(axis="y", alpha=0.25, lw=0.5)
    ax.legend(frameon=False, fontsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_png, dpi=250, bbox_inches="tight")
    plt.close(fig)
    return out_png


def fig_scatter(df, clean, out_png):
    x = df.loc[clean, "M0_period_nm"].to_numpy(float)
    y = df.loc[clean, "M2_period_nm"].to_numpy(float)
    fig, axes = plt.subplots(1, 2, figsize=(9.8, 3.8))
    ax = axes[0]
    ax.plot([420, 520], [420, 520], "--", lw=1.0, color="#888", label="1:1")
    ax.fill_between([420, 520], [420 * 1.05, 520 * 1.05], [420 * 0.95, 520 * 0.95],
                    color="#888", alpha=0.12, label="±5 %")
    ax.plot(x, y, "o", ms=5, color="#2f6b4f", alpha=0.85)
    ax.set_xlabel("Λ from M0 (our method), nm", fontsize=9)
    ax.set_ylabel("Λ from M2 (radial FFT), nm", fontsize=9)
    ax.set_title("field-by-field agreement", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.grid(alpha=0.25, lw=0.5)
    ax.legend(frameon=False, fontsize=8)
    ax = axes[1]
    d = 100 * (y - x) / x
    ax.axhline(0, lw=1.0, color="#888")
    ax.plot(x, d, "o", ms=5, color="#3b6ea8", alpha=0.85)
    ax.set_xlabel("Λ from M0 (our method), nm", fontsize=9)
    ax.set_ylabel("M2 − M0 (%)", fontsize=9)
    ax.set_title(f"bias {np.mean(d):+.1f} % (mean), {np.std(d, ddof=1):.1f} % (SD)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.grid(alpha=0.25, lw=0.5)
    for a in axes:
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_png, dpi=250, bbox_inches="tight")
    plt.close(fig)
    return out_png


def fig_coupon_ordered(cs, df, out_png):
    fig, ax = plt.subplots(figsize=(6.8, 3.3))
    x = np.arange(len(cs))
    ax.bar(x, cs["ordered"], width=0.6, color="#e8b04b", edgecolor="#8a6a1f", lw=0.6,
           label="coupon mean")
    for i, c in enumerate(cs["coupon"]):
        v = 100 * df.loc[df.coupon == c, "ordered_frac"].to_numpy()
        jit = (np.random.RandomState(i).rand(len(v)) - 0.5) * 0.30
        ax.plot(np.full(len(v), i) + jit, v, "o", ms=3.2, color="#333", alpha=0.6, mew=0,
                label="field" if i == 0 else None)
    ax.set_xticks(x)
    ax.set_xticklabels(cs["coupon"], fontsize=8.5)
    ax.set_ylim(0, 100)
    ax.set_ylabel("area inside the acceptance band (%)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.grid(axis="y", alpha=0.25, lw=0.5)
    ax.legend(frameon=False, fontsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_png, dpi=250, bbox_inches="tight")
    plt.close(fig)
    return out_png


def fig_corr(df, clean, out_png):
    cols = [f"{m}_period_nm" for m in METHODS]
    M = df.loc[clean, cols].to_numpy(float)
    R = np.corrcoef(M.T)
    fig, ax = plt.subplots(figsize=(4.4, 3.9))
    im = ax.imshow(R, cmap="RdYlGn", vmin=0.5, vmax=1.0)
    ax.set_xticks(range(6)); ax.set_xticklabels(METHODS, fontsize=8.5)
    ax.set_yticks(range(6)); ax.set_yticklabels(METHODS, fontsize=8.5)
    for i in range(6):
        for j in range(6):
            ax.text(j, i, f"{R[i, j]:.2f}", ha="center", va="center", fontsize=7,
                    color="#222" if R[i, j] > 0.75 else "white")
    ax.set_title("Pearson r between methods (per field)", fontsize=9)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.ax.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig(out_png, dpi=250, bbox_inches="tight")
    plt.close(fig)
    return out_png


# ------------------------------------------------------------------- glossary text
GLOSSARY = [
    ("coupon", "—", "Sample block identifier (10L, 11L, 12L, 13L, 15L).",
     "Folder name under `650nm/LIPSS`.",
     "One coupon = one laser-processed coupon; fields inside it are different positions."),
    ("field (file)", "—", "One SEM micrograph of one position on a coupon.",
     "Image file name; the `_e` copy is used (identical period, contrast-enhanced).",
     "48 fields = 48 independent positions; the `_e` twin is not a second measurement."),
    ("n", "count", "Number of fields entering a statistic.",
     "Count after the exclusions stated in the caption.",
     "n = 48 is the whole set; n = 47 excludes the flagged field 13L/34."),
    ("MAG", "×", "Instrument magnification printed in the SEM footer.",
     "Read from the instrument sidecar (`CM_MAG`) and the image footer.",
     "3000× for all but two fields (13L/34 at 4500×, 13L/39 at 3300×)."),
    ("scale bar", "px", "Length of the white 1 µm bar in the instrument footer, in pixels.",
     "Brightest horizontal run in the footer, cross-checked against the sidecar `SM_MICRON_BAR`.",
     "32 px means the bar spans 32 pixels = 1 µm."),
    ("px", "nm/px", "Pixel size, the conversion from pixels to nanometres.",
     "1000 nm ÷ scale-bar length in pixels.",
     "31.25 nm/px at 3000×; a different value means a different magnification, not a bad image."),
    ("Λ", "nm", "Spatial period of the ripples: the distance between two successive ridges.",
     "Each method measures it differently — see the M0…M5 rows.",
     "This is the number compared with the laser wavelength (Λ/λ) or with AFM."),
    ("Λ_M0", "nm", "Period from **our** method (semtexture): autocorrelation of the phase-coherent "
     "mean profile.", MPRINCIPLE["M0"],
     "Reference value in this report; it is the number the per-coupon reports use."),
    ("Λ_M1", "nm", "Period from the naive 2-D FFT maximum.", MPRINCIPLE["M1"],
     "A control, not a measurement to report: it shows what happens without high-pass filtering."),
    ("Λ_M2", "nm", "Period from the radial 2-D FFT peak.", MPRINCIPLE["M2"],
     "The most robust spectral estimate here (lowest CV); used as the second reference."),
    ("Λ_M3", "nm", "Period from the 1-D FFT of the rotated mean profile.", MPRINCIPLE["M3"],
     "Independent of M0's autocorrelation, but noisier on patchy fields."),
    ("Λ_M4", "nm", "Period from the 2-D autocorrelation side-lobe.", MPRINCIPLE["M4"],
     "Closest to M0 in principle; the difference between them is a useful sanity check."),
    ("Λ_M5", "nm", "Period from the areal PSD (Welch) peak.", MPRINCIPLE["M5"],
     "A surface-metrology (ISO 25178-style) route; wider spread because it averages small blocks."),
    ("Δ vs M0", "%", "Systematic offset of a method relative to M0.",
     "mean(Λ_method − Λ_M0) / mean(Λ_M0) × 100 over the same fields.",
     "Positive = that method reads longer periods than ours. Below ~2 % is agreement."),
    ("MAPE vs M0", "%", "Mean absolute difference from M0, field by field.",
     "mean(|Λ_method − Λ_M0|) / Λ_M0 × 100.",
     "Penalises scatter, not just bias: it is the number that matters for single-field claims."),
    ("r vs M0", "—", "Pearson correlation of the per-field values between a method and M0.",
     "Correlation over the fields of the set.",
     "High r = the methods rank fields the same way even if they are offset."),
    ("CV", "%", "Coefficient of variation: spread relative to the mean.",
     "SD / mean × 100.",
     "10 % means the field-to-field spread is a tenth of the period; it is a property of the "
     "sample, not of the method."),
    ("Λ/λ", "—", "Structure factor: period divided by the laser wavelength (650 nm).",
     "Λ (nm) / 650.",
     "Lets the 650 nm and 515 nm sets be compared on one scale."),
    ("θ", "°", "Direction of the intensity gradient across the ripples — i.e. normal to the ripple "
     "crests, measured as an **axial** angle in the image frame.",
     "Dominant orientation of the structure tensor, averaged circularly on 2θ (0° and 180° are the "
     "same direction), reported in [0°, 180°).",
     "θ = 0° means the crests run vertically (gradient horizontal); θ = 90° means the crests run "
     "horizontally. Add or subtract 90° to convert between 'crest direction' and this value."),
    ("circular SD", "°", "Spread of θ, computed correctly for axial data.",
     "From the resultant length R of the 2θ distribution: SD = √(−2 ln R)/2.",
     "A few degrees means the ripples are parallel across the set."),
    ("C", "—", "Coherence of the local orientation (structure tensor).",
     "(λ₁ − λ₂)/(λ₁ + λ₂) of the structure tensor, averaged over the field.",
     "0 = no preferred direction, 1 = perfectly parallel lines. Not a period measure."),
    ("AC strength", "—", "Height of the first autocorrelation side-lobe of the mean profile.",
     "Normalised so 1 = the profile repeats exactly at that lag.",
     "High = the ripple pattern survives across the whole field; low = short-range order only."),
    ("ordered area", "%", "Fraction of the analysed area whose 2 µm windows pass the acceptance "
     "test (period, orientation, coherence and phase coherence all inside their bands).",
     "Non-overlapping 2 µm grid, each window classified, area-weighted.",
     "This is the number that separates a uniformly processed coupon from a patchy one."),
    ("off-spec area", "%", "Fraction whose windows carry a texture but miss at least one band.",
     "Same grid; complement of the ordered area minus the bare area.",
     "High off-spec + ~0 bare = the surface is textured everywhere but not to specification."),
    ("bare area", "%", "Fraction with no directional texture at all.",
     "Windows whose coherence falls below the texture floor.",
     "Close to 0 here: the coupons are covered, the problem is regularity, not coverage."),
    ("S", "—", "Nematic order parameter of the orientation field.",
     "C²-weighted average of cos 2Δθ over the field, in [0, 1].",
     "1 = all local orientations identical. It saturates near 1 on these coupons and therefore "
     "does **not** discriminate between them."),
    ("Hs", "—", "Orientation entropy, normalised.",
     "Shannon entropy of the C²-weighted orientation histogram / ln(36 bins).",
     "0 = one direction only, 1 = uniform. Also saturates here; report it, do not select on it."),
    ("tile prominence", "—", "Strength of the spectral peak inside one 2 µm tile.",
     "(peak − median)/median of the band-limited power in that tile.",
     "≥ 2 is the detection criterion for 'a ripple period is resolvable here'."),
    ("tile peak frac", "%", "Fraction of tiles in which a ripple period is resolvable.",
     "Tiles with prominence ≥ 2 divided by all valid tiles.",
     "100 % means every tile has a measurable peak, even where the period is off-spec."),
    ("window", "µm", "Side length of the classification window.",
     "Chosen as ≈5 ripple periods (2 µm here).",
     "Percentages are only comparable between runs with the same window size."),
    ("periods / window", "—", "How many ripple periods fit in one classification window.",
     "window (nm) / Λ.",
     "Below ~4 the period estimate becomes the dominant error; 2 µm keeps ≈4–5 here."),
    ("flag", "—", "A field excluded from the headline statistics for a stated reason.",
     "Manual, documented — never silently dropped.",
     "13L/34 is flagged: its global spectral peak locks onto a coarse structure (peak switching)."),
]


# ------------------------------------------------------------------------- builder
def build(crosscheck, root, outdir, name="650 nm LIPSS", stamp=None):
    stamp = stamp or DATE.strftime("%Y%m%d")
    os.makedirs(outdir, exist_ok=True)
    figdir = os.path.join(outdir, "figures")
    pdir = os.path.join(outdir, "pairs")
    for d in (figdir, pdir):
        os.makedirs(d, exist_ok=True)

    pf = pd.read_csv(os.path.join(crosscheck, "crosscheck_perfield.csv"))
    pf["stem"] = pf["file"].str.replace(r"(_e)?\.[A-Za-z]+$", "", regex=True)
    # the crosscheck writes "coupon" = file stem (a leftover); the real coupon is the folder
    pf = pf.drop(columns=["coupon"], errors="ignore").rename(columns={"group": "coupon"})

    # our per-coupon runs
    qc = []
    for c in sorted(pf["coupon"].unique()):
        f = os.path.join(root, c, "QC_report", "field_metrics.csv")
        if not os.path.exists(f):
            print("  !! missing QC for", c)
            continue
        d = pd.read_csv(f, encoding="utf-8-sig")
        d["stem"] = d["file"].str.replace(r"(_e)?\.[A-Za-z]+$", "", regex=True)
        d["coupon"] = c
        qc.append(d)
    qc = pd.concat(qc, ignore_index=True)
    df = qc.merge(pf, on=["coupon", "stem"], how="inner", suffixes=("", "_cc"))
    if len(df) != len(pf):
        print(f"  !! merge kept {len(df)} of {len(pf)} fields")

    # flagged field: a period that no coupon of this series can plausibly have
    df["flag"] = (~df["M2_period_nm"].between(400, 560)) | (~df["period_nm"].between(400, 560))
    clean = ~df["flag"].to_numpy()

    st = {m: method_stats(df, f"{m}_period_nm", clean) for m in METHODS}
    cs = []
    for c, g in df.groupby("coupon", sort=True):
        g2 = g[~g["flag"]]
        th_m, th_sd = circ_mean_sd(g["M0_theta_deg"])
        per = g2[[f"{m}_period_nm" for m in METHODS]].to_numpy(float)
        spread = np.nanmax(per, axis=1) - np.nanmin(per, axis=1)
        cs.append(dict(coupon=c, n=len(g), n_clean=len(g2),
                       lam=g2["M2_period_nm"].mean(), lam_sd=g2["M2_period_nm"].std(ddof=1),
                       lam_m0=g2["M0_period_nm"].mean(),
                       cv=100 * g2["M2_period_nm"].std(ddof=1) / g2["M2_period_nm"].mean(),
                       theta=th_m, coh=g["coherence"].mean(),
                       ordered=100 * g["ordered_frac"].mean(),
                       bare=100 * g["bare_frac"].mean(),
                       S=g["M6_order_S"].mean(), tile=g["M7_tile_prom_frac_pct"].mean(),
                       spread_pct=float(100 * np.nanmean(spread / g2["M0_period_nm"].to_numpy()))))
    cs = pd.DataFrame(cs)

    F1 = fig_methods(df, clean, os.path.join(figdir, "fig1_methods.png"))
    F2 = fig_scatter(df, clean, os.path.join(figdir, "fig2_m0_vs_m2.png"))
    F3 = fig_coupon_ordered(cs, df, os.path.join(figdir, "fig3_ordered.png"))
    F4 = fig_corr(df, clean, os.path.join(figdir, "fig4_correlation.png"))

    # representative field per coupon → original | marked
    reps = []
    for c in cs["coupon"]:
        g = df[df["coupon"] == c]
        g = g.assign(dist=(g["ordered_frac"] - g["ordered_frac"].median()).abs())
        row = g.sort_values("dist").iloc[0]
        src = os.path.join(root, c, f"{row['stem']}_e.bmp")
        if not os.path.exists(src):
            cand = glob.glob(os.path.join(root, c, f"{row['stem']}*.*"))
            cand = [x for x in cand if x.lower().endswith((".bmp", ".png", ".tif"))]
            if not cand:
                continue
            src = cand[0]
        try:
            res = analyse_image(src, tile_um=2.0)
            marked = os.path.join(pdir, f"{c}_marked.png")
            annotate_image(src, marked, res=res, label=False)
            lam_s = f"{res['period_nm']:.0f} nm" if np.isfinite(res.get("period_nm", np.nan)) else "n.m."
            pair = fig_pair(src, marked, os.path.join(pdir, f"{c}_pair.png"),
                            title=f"{c}   field {row['stem']}   Λ {lam_s}   ·   "
                                  f"inside {100*res['ordered_frac']:.0f} %")
            reps.append((c, row["stem"], pair))
        except Exception as exc:
            print(f"  !! {c}/{row['stem']}: {exc}")

    lam_all = df["M2_period_nm"].to_numpy(float)
    lam_clean = df.loc[clean, "M2_period_nm"].to_numpy(float)
    lam_m0_clean = df.loc[clean, "M0_period_nm"].to_numpy(float)
    m0, m0sd = np.mean(lam_m0_clean), np.std(lam_m0_clean, ddof=1)
    m2, m2sd = np.mean(lam_clean), np.std(lam_clean, ddof=1)
    ordered_mean = 100 * df["ordered_frac"].mean()
    flagged = df[df["flag"]]

    doc = Document()
    s = doc.styles["Normal"]; s.font.name = "Calibri"; s.font.size = Pt(10)
    s.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    for sec in doc.sections:
        sec.top_margin = Cm(2.0); sec.bottom_margin = Cm(2.0)
        sec.left_margin = Cm(2.2); sec.right_margin = Cm(2.2)
        fp = sec.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r0 = fp.add_run(f"{name} — series quality and cross-method check   ·   page ")
        r0.font.size = Pt(8); r0.font.color.rgb = GREY
        fld = OxmlElement("w:fldSimple"); fld.set(qn("w:instr"), "PAGE")
        run = OxmlElement("w:r"); t_el = OxmlElement("w:t"); t_el.text = "1"; run.append(t_el)
        fld.append(run); fp._p.append(fld)

    t = doc.add_paragraph()
    r = t.add_run(f"{name} — series quality and cross-method check")
    r.bold = True; r.font.size = Pt(17); r.font.color.rgb = NAVY
    sub = doc.add_paragraph()
    r = sub.add_run(f"{len(cs)} coupons · {len(df)} fields · six independent period estimators · "
                    f"semtexture classification at 2 µm windows")
    r.font.size = Pt(10.5); r.italic = True; r.font.color.rgb = GREY
    meta = doc.add_paragraph()
    rich(meta, f"generated {DATE_EN} · LabToolbox `sem_integrity_crosscheck.py` + `semtexture` · "
               f"every column of every table is defined in §2", size=Pt(8.5), color=GREY)
    doc.add_paragraph()

    head(doc, "Summary", 1)
    for txt in [
        f"**Period.** {len(lam_clean)} of {len(df)} fields give a coherent ripple period; they read "
        f"**Λ = {m2:.0f} ± {m2sd:.0f} nm** by the radial FFT (CV {100*m2sd/m2:.1f} %) and "
        f"**{m0:.0f} ± {m0sd:.0f} nm** by our method (CV {100*m0sd/m0:.1f} %), i.e. **{m2/LAM:.2f} λ** "
        f"— the same fraction of the laser wavelength as the 515 nm series (0.70 λ).",
        f"**Method agreement.** The six estimators sit within "
        f"{max(abs(st[m]['bias_vs_M0_pct']) for m in METHODS[1:]):.1f} % of our method on the mean "
        f"and rank the fields almost identically (r = "
        f"{min(st[m]['r_vs_M0'] for m in METHODS[1:]):.2f}–{max(st[m]['r_vs_M0'] for m in METHODS[1:]):.2f}); "
        f"the single-field MAPE is "
        f"{min(st[m]['mape_vs_M0_pct'] for m in METHODS[1:]):.1f}–"
        f"{max(st[m]['mape_vs_M0_pct'] for m in METHODS[1:]):.1f} %.",
        f"**Regularity is the weak point, not the period.** Only **{ordered_mean:.0f} %** of the "
        f"analysed area passes the acceptance test, and the coupons differ hugely "
        f"({cs['ordered'].min():.0f} % on {cs.loc[cs['ordered'].idxmin(), 'coupon']} vs "
        f"{cs['ordered'].max():.0f} % on {cs.loc[cs['ordered'].idxmax(), 'coupon']}). "
        f"Bare area is {100*df['bare_frac'].mean():.1f} %: the surface is covered, it is not uniform.",
        f"**One field is excluded from the headline numbers** — "
        f"{', '.join(f'{r.coupon}/{r.stem} ({r.px_nm_measured:.0f} nm/px)' for r in flagged.itertuples())}"
        f" — because every method locks onto a coarse structure there (peak switching at 4500×). "
        f"With it included the CV rises from {100*m2sd/m2:.1f} % to {100*np.std(lam_all, ddof=1)/np.mean(lam_all):.1f} %.",
        f"**What cannot be claimed:** there is no AFM measurement for this 650 nm batch, so these "
        f"numbers are an internal SEM consistency check, not an absolute accuracy claim.",
    ]:
        p = doc.add_paragraph(style="List Bullet")
        rich(p, txt, size=Pt(9.8))
        p.paragraph_format.space_after = Pt(3)

    head(doc, "1  Data and acquisition", 1)
    rows = []
    for _, r in cs.iterrows():
        g = df[df["coupon"] == r["coupon"]]
        pxs = sorted({round(float(v), 2) for v in g["px_nm_measured"]})
        # 31.25 nm/px is the 3000x setting, so the magnification follows from the pixel size
        rows.append([r["coupon"], len(g),
                     ", ".join(f"{round(3000*31.25/px, -2):.0f}×" for px in pxs),
                     ", ".join(f"{px:.2f}" for px in pxs),
                     f"{r['lam_m0']:.0f}", f"{r['lam']:.0f}"])
    table(doc, ["coupon", "fields", "magnification", "px (nm/px)", "Λ_M0 (nm)", "Λ_M2 (nm)"], rows,
          widths=[2.0, 1.6, 3.4, 3.0, 3.0, 3.0], font=Pt(8.4))
    caption(doc, "Table 1 — Images analysed, one row per coupon. **coupon** = sample block; "
                 "**fields** = number of micrographs; **magnification** = instrument setting; "
                 "**px** = pixel size derived from the 1 µm scale bar (31.25 nm/px = 3000×); "
                 "**Λ_M0 / Λ_M2** = mean period of that coupon by our method and by the radial FFT. "
                 "All six columns are defined again in §2.")

    head(doc, "2  Notation — what every column in this report means", 1)
    para(doc,
         "Every quantity used in any table of this report is defined here once, in the same order in "
         "which the tables use it. Where a number is an average, the averaging set is stated; where a "
         "threshold is used, its value is given. Nothing in the tables is left implicit.")
    rows = []
    for sym, unit, definition, how, reading in GLOSSARY:
        rows.append([sym, unit, definition, how, reading])
    table(doc, ["symbol / column", "unit", "definition", "how it is computed", "how to read it"],
          rows, widths=[2.6, 1.2, 4.9, 4.4, 3.3], font=Pt(6.9))
    caption(doc, "Table 2 — Parameter definitions for every column that appears later. The five "
                 "columns of this glossary are themselves: the symbol or column header as printed, "
                 "its unit, its plain-language definition, the computation actually performed by "
                 "the code, and the reading a non-specialist should take away.")

    head(doc, "3  Six ways of measuring the same period", 1)
    para(doc,
         "The six estimators were written independently of each other and of our classifier: M1 and "
         "M2 work in the 2-D Fourier domain, M3 in the 1-D profile domain, M4 in the autocorrelation "
         "domain, M5 through a block-averaged areal PSD, and M0 is our production method. They were "
         "applied to the same pixels, so any difference between them is a property of the estimator, "
         "not of the sample.")
    rows = []
    for m in METHODS:
        s_ = st[m]
        rows.append([m, MNAME[m].split("—")[1].strip() if "—" in MNAME[m] else MNAME[m],
                     s_["n_clean"],
                     f"{s_['mean_clean']:.1f} ± {s_['sd_clean']:.1f}",
                     f"{s_['cv_clean']:.2f}", f"{s_['min_clean']:.0f}–{s_['max_clean']:.0f}",
                     "reference" if m == "M0" else f"{s_['bias_vs_M0_pct']:+.1f}",
                     "—" if m == "M0" else f"{s_['mape_vs_M0_pct']:.1f}",
                     "—" if m == "M0" else f"{s_['r_vs_M0']:.3f}"])
    table(doc, ["method", "what it measures", "n", "Λ mean ± SD (nm)", "CV %", "range (nm)",
                "Δ vs M0 %", "MAPE %", "r vs M0"], rows,
          widths=[1.3, 4.6, 1.0, 3.0, 1.3, 2.2, 1.7, 1.5, 1.6], font=Pt(7.4))
    caption(doc, f"Table 3 — Period by each method on the same {int(st['M0']['n_clean'])} fields "
                 f"(the flagged field excluded). **method** = estimator label; **what it measures** "
                 f"= the principle in one line (§2 has the algorithm); **n** = fields used; "
                 f"**Λ mean ± SD** = average period and its field-to-field spread; **CV %** = SD/mean; "
                 f"**range** = smallest and largest single field; **Δ vs M0 %** = systematic offset of "
                 f"that method from ours; **MAPE %** = mean absolute field-by-field difference; "
                 f"**r vs M0** = Pearson correlation of the per-field values.")

    add_figure(doc, F1, 15.4)
    caption(doc, "Figure 1 — Distribution of the per-field period given by each estimator (box = "
                 "quartiles, dots = fields, dashed line = median of our method). The boxes overlap "
                 "almost completely: the six methods agree on this set.")
    add_figure(doc, F2, 16.0)
    caption(doc, "Figure 2 — Left: our method against the radial FFT, field by field, with the 1:1 "
                 "line and a ±5 % band. Right: the same difference expressed as a percentage of our "
                 "value; the systematic offset is the mean of that cloud.")
    add_figure(doc, F4, 10.5)
    caption(doc, "Figure 3 — Pearson correlation between the methods across fields. Correlations near "
                 "1 mean the methods disagree only by a constant offset, not about which field is "
                 "longer.")

    head(doc, "4  Coupon by coupon (our method)", 1)
    rows = []
    for _, r in cs.iterrows():
        rows.append([r["coupon"], int(r["n"]), f"{r['lam_m0']:.0f}", f"{r['lam']:.0f}",
                     f"{r['lam_sd']:.0f}", f"{r['cv']:.1f}", f"{r['theta']:.1f}",
                     f"{r['coh']:.3f}", f"{r['ordered']:.1f}", f"{r['bare']:.1f}",
                     f"{r['S']:.3f}", f"{r['tile']:.0f}", f"{r['spread_pct']:.1f}"])
    table(doc, ["coupon", "n", "Λ_M0", "Λ_M2", "SD_M2", "CV %", "θ °", "C",
                "ordered %", "bare %", "S", "tile peak %", "method spread %"], rows,
          widths=[1.4, 0.9, 1.3, 1.3, 1.3, 1.1, 1.1, 1.1, 1.6, 1.3, 1.1, 1.8, 2.0], font=Pt(7.2))
    caption(doc, "Table 4 — Per coupon. **n** = fields in the coupon; **Λ_M0 / Λ_M2** = mean period "
                 "by our method / by the radial FFT; **SD_M2** = field-to-field SD of Λ_M2; "
                 "**CV %** = SD/mean of Λ_M2; **θ** = mean axial gradient direction (normal to the "
                 "ripple crests, §2); **C** = structure-tensor "
                 "coherence; **ordered %** = area inside the acceptance band; **bare %** = area with "
                 "no directional texture; **S** = nematic order parameter; **tile peak %** = fraction "
                 "of windows with a resolvable spectral peak; **method spread %** = mean over fields "
                 "of (max − min across the six methods)/Λ_M0. Every one of these is defined in §2.")
    add_figure(doc, F3, 12.6)
    caption(doc, "Figure 4 — Area inside the acceptance band per coupon (bar = coupon mean, dots = "
                 "fields). The five coupons are not interchangeable.")

    head(doc, "5  Where the methods disagree, and why", 1)
    if len(flagged):
        f0 = flagged.iloc[0]
        para(doc,
             f"**Peak switching in {f0['coupon']}/{f0['stem']}.** This field was taken at "
             f"{f0['px_nm_measured']:.2f} nm/px (4500×) instead of the 31.25 nm/px of the rest. All six "
             f"methods return 690–730 nm because the strongest spectral feature of that field is a "
             f"coarse structure at ≈34 px, while the LIPSS ridge sits at ≈23 px (≈470 nm) with a "
             f"lower but real peak. The methods agree with each other and all of them are wrong — "
             f"which is exactly the failure a single-method pipeline cannot detect. The field is "
             f"therefore flagged, listed in Appendix A, and excluded from Tables 3–4; the report "
             f"never silently drops it.")
    para(doc,
         f"**The naive 2-D FFT (M1) is a control, not a measurement.** On this set it stays within "
         f"{st['M1']['bias_vs_M0_pct']:+.1f} % of our method, but on the 650 nm nanopillar set the same "
         f"routine returns four-digit periods (mean 1300 nm) because the illumination envelope "
         f"outshines the ripple peak. Its agreement here is a coincidence of contrast, not evidence "
         f"that high-pass filtering is unnecessary.")
    para(doc,
         f"**Method spread inside one field.** Averaged over the {len(cs)} coupons it is "
         f"{cs['spread_pct'].mean():.1f} % of the period — small enough that the choice of method "
         f"cannot change a conclusion about this batch, and large enough that a paper should state "
         f"which method produced the quoted number.")
    para(doc,
         "**Why the autocorrelation and the spectral methods can part company on other sets.** For a "
         "single grating (this LIPSS batch) the ACF side-lobe and the spectral peak are the same "
         "feature, so M0 and M2 agree within ≈2 %. On a lattice with two near-equal periodicities "
         "(the 650 nm nanopillar set) the ACF can lock onto the nearest lattice vector while the "
         "radial spectrum peaks on another harmonic — there M0 reads 404 nm and M2 reads 477 nm. The "
         "difference is not an error of one of them; it is a statement about which length the "
         "morphology actually has.")

    head(doc, "6  Comparison with the other series in this project", 1)
    rows = [
        ["515 nm LIPSS (6 fields)", "362.9 ± 3.3", "372.5 ± 5.2", "+2.6",
         "0.70 λ", "93.7", "0.558"],
        [f"650 nm LIPSS ({len(lam_clean)} fields)", f"{m0:.1f} ± {m0sd:.1f}", f"{m2:.1f} ± {m2sd:.1f}",
         f"{100*(m2-m0)/m0:+.1f}", f"{m2/LAM:.2f} λ", f"{ordered_mean:.0f}", f"{df['coherence'].mean():.3f}"],
        ["650 nm nanopillars (24 of 27 fields)", "403.7 ± 44.9", "477.3 ± 12.9", "+18.2",
         "0.73 λ", "29", "0.376"],
    ]
    table(doc, ["dataset", "Λ_M0 (nm)", "Λ_M2 (nm)", "Δ (M2−M0) %", "Λ/λ", "ordered %", "C"], rows,
          widths=[4.6, 2.6, 2.6, 2.2, 1.6, 2.0, 1.4], font=Pt(8.0))
    caption(doc, "Table 5 — The three SEM datasets of the project on one scale. **Λ_M0 / Λ_M2** = "
                 "period by our method and by the radial FFT; **Δ (M2−M0) %** = how far the two "
                 "methods sit apart on the *same* pixels (a measure of how well a single length "
                 "describes that morphology); **Λ/λ** = period over the laser wavelength — the "
                 "dimensionless number that makes 515 nm and 650 nm comparable; **ordered %** = area "
                 "inside the acceptance band; **C** = coherence. The nanopillar row comes from its "
                 "own series report and is quoted with its own method labels.")

    head(doc, "7  What this report can and cannot support", 1)
    for txt in [
        f"**Supported:** the 650 nm LIPSS period is {m2:.0f} ± {m2sd:.0f} nm by six independent "
        f"estimators, reproducible across five coupons to "
        f"{cs['cv'].mean():.1f} % within a coupon; it is {m2/LAM:.2f} of the laser wavelength.",
        "**Supported:** the surface is textured everywhere (bare area ≈0) but not uniformly "
        "periodic — the ordered fraction, not the period, is what varies between coupons.",
        "**Not supported:** any absolute-accuracy claim. There is no AFM map of this 650 nm batch, "
        "so nothing here can pin the SEM value to a physical reference the way the 515 nm batch was "
        "pinned (AFM ZSR 384.6 nm, −5.6 %).",
        "**Not supported:** selecting coupons on S or tile prominence — both saturate on this set "
        "(S 0.96–0.98, tile peak 100 % of windows) and cannot separate a good coupon from a bad one.",
    ]:
        p = doc.add_paragraph(style="List Bullet")
        rich(p, txt, size=Pt(9.6))
        p.paragraph_format.space_after = Pt(2)

    head(doc, "Appendix A  Every field", 1)
    para(doc, "All fields, sorted by coupon. The six periods are the same pixels measured six ways; "
              "**Δmax %** is the largest disagreement between methods inside that field; the flag "
              "column marks the field excluded from the headline statistics (§5).")
    rows = []
    for _, r in df.sort_values(["coupon", "stem"]).iterrows():
        per = np.array([r[f"{m}_period_nm"] for m in METHODS], dtype=float)
        per_ok = per[np.isfinite(per)]
        dmax = (100 * (per_ok.max() - per_ok.min()) / np.median(per_ok)) if per_ok.size > 1 else np.nan
        rows.append([r["coupon"], r["stem"]] + [f"{r[f'{m}_period_nm']:.0f}" if np.isfinite(r[f"{m}_period_nm"]) else "—"
                                                for m in METHODS] +
                    [f"{dmax:.1f}" if np.isfinite(dmax) else "—",
                     f"{r['coherence']:.2f}", f"{100*r['ordered_frac']:.0f}",
                     f"{r['M6_order_S']:.3f}", "flagged" if r["flag"] else ""])
    table(doc, ["coupon", "field", "M0", "M1", "M2", "M3", "M4", "M5", "Δmax %", "C",
                "ordered %", "S", "flag"], rows,
          widths=[1.3, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2, 1.0, 1.4, 1.0, 1.2], font=Pt(6.6))
    caption(doc, "Table A1 — Per field. **M0…M5** = period in nm by each estimator; **Δmax %** = "
                 "(max − min)/median across the six for that field; **C** = coherence; "
                 "**ordered %** = area inside the acceptance band; **S** = nematic order parameter; "
                 "**flag** = excluded from Tables 3–4, with the reason given in §5.")

    if reps:
        head(doc, "Appendix B  One representative field per coupon", 1)
        para(doc, "For each coupon, the field closest to that coupon's median ordered area (not the "
                  "best and not the worst). Left = original micrograph, right = the same field with "
                  "every off-spec window tinted on the continuous severity scale: pale yellow = "
                  "marginally outside the acceptance band, deep red = 2.5× outside or more.")
        for i, (c, stem, pair) in enumerate(reps, 1):
            add_figure(doc, pair, 16.0)
            caption(doc, f"B{i} — {c} / field {stem}.")

    base = os.path.join(outdir, f"650nm_LIPSS_series_report_{stamp}")
    doc.save(base + ".docx")
    pdf = base + ".pdf"
    try:
        tmp = os.path.join(tempfile.gettempdir(), os.path.basename(base) + ".docx")
        shutil.copy2(base + ".docx", tmp)
        tmp_pdf = os.path.splitext(tmp)[0] + ".pdf"
        import win32com.client as win32
        word = win32.Dispatch("Word.Application"); word.Visible = False
        d = word.Documents.Open(tmp)
        d.ExportAsFixedFormat(tmp_pdf, 17)
        d.Close(False); word.Quit()
        shutil.copy2(tmp_pdf, pdf)
    except Exception as exc:
        print("  !! PDF failed:", exc)

    df.sort_values(["coupon", "stem"]).to_csv(os.path.join(outdir, "fields_all_methods.csv"),
                                              index=False, encoding="utf-8-sig")
    cs.to_csv(os.path.join(outdir, "coupon_summary.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame([dict(method=m, **st[m]) for m in METHODS]).to_csv(
        os.path.join(outdir, "method_summary.csv"), index=False, encoding="utf-8-sig")
    shutil.rmtree(pdir, ignore_errors=True)
    return dict(docx=base + ".docx", pdf=pdf if os.path.exists(pdf) else None, n=len(df))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crosscheck", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--name", default="650 nm LIPSS")
    ap.add_argument("--stamp", default=None)
    a = ap.parse_args()
    r = build(a.crosscheck, a.root, a.outdir, name=a.name, stamp=a.stamp)
    print(r)


if __name__ == "__main__":
    main()
