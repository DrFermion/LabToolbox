# -*- coding: utf-8 -*-
"""Build the consolidated XDLVO-SEI + BSA protein-modelling report (docx + md).

Numbers sourced from delivered artifacts, harvested 2026-09-24:
  - final repro report (docx dump, group folder XDLVO-SEI_analysis_20260921)
  - bsa_sei_selfcheck.txt / bsa_sei_field_stats.csv / bsa_sei_curvature_curve.csv
  - bsa_sample_level_weighted.csv / bsa_per_zone_by_day.csv
  - anchor validation re-run 2026-09-24 (xdlvo_validate.py: 3/3 PASS)
Figures: 6 (2 repro + 4 BSA), embedded resized; originals copied by the packaging step.
"""
import os, sys, shutil
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ONEDRIVE = r"F:\OneDrive - University of Dundee\Ruinong_Pan_Personal"
PKG = os.path.join(ONEDRIVE, "XDLVO-SEI_BSA综合报告_20260924")
TMP = os.path.join(os.environ["LOCALAPPDATA"], "Temp", "report_embed")
os.makedirs(PKG, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

FIG = {
    "fig1_reproduction": os.path.join(ONEDRIVE, r"XDLVO-SEI复现对比_20260921\fig1_reproduction.png"),
    "fig2_sei_vs_flat": os.path.join(ONEDRIVE, r"XDLVO-SEI复现对比_20260921\fig2_sei_vs_flat.png"),
    "fig1_bsa_factor_vs_curvature": r"E:\LabToolbox\output\bsa_sei_515_20260924\fig1_bsa_factor_vs_curvature.png",
    "fig2_bsa_field_factor_hist": r"E:\LabToolbox\output\bsa_sei_515_20260924\fig2_bsa_field_factor_hist.png",
    "fig3_map_LIPSS": r"E:\LabToolbox\output\bsa_sei_515_20260924\fig3_map_LIPSS.png",
    "fig_bsa_sample_level_vs_day": r"E:\LabToolbox\output\bsa_sample_level_20260924\fig_bsa_sample_level_vs_day.png",
}

def prep_img(name, maxw=1800):
    src = FIG[name]
    dst = os.path.join(TMP, name + ".png")
    im = Image.open(src)
    if im.mode not in ("RGB",):
        im = im.convert("RGB")
    if im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    im.save(dst, "PNG", optimize=True)
    return dst

# ---------------------------------------------------------------- content model
# blocks: (kind, payload)
#  h1: text | h2: text | p: text | bullets: [..] | table: dict(caption, headers, rows[, widths])
#  fig: dict(name, width_cm, caption)
B = []
def h1(t): B.append(("h1", t))
def h2(t): B.append(("h2", t))
def p(t): B.append(("p", t))
def bs(items): B.append(("bullets", items))
def table(caption, headers, rows, widths=None): B.append(("table", dict(caption=caption, headers=headers, rows=rows, widths=widths)))
def fig(name, width_cm, caption): B.append(("fig", dict(name=name, width_cm=width_cm, caption=caption)))

TITLE = "XDLVO–SEI Modelling Report: Bacterial and Protein Adhesion on Laser-Textured 316L Stainless Steel"
SUBTITLE = ("Combined analyses — (1) reproduction of the published XDLVO–SEI study (Wang et al., 2026, Materials & Design 263, 115626); "
            "(2) BSA protein-adhesion predictions for the 515 nm surfaces of this thesis, including texture-geometry (SEI) and sample-level (area-weighted) estimates.")
DATELINE = ("Version 1.0 · 24 September 2026 · Analysis report (not part of the thesis text) · "
            "Companion to Thesis.docx (Chapter 4, §4.4) and to the standalone reproduction report XDLVO-SEI_reproduction_report.docx (group folder, 2026-09-21/22)")

h1("Executive summary")
bs([
 "The XDLVO–SEI framework of Wang et al. (2026) was re-implemented independently and validated in four independent ways (§3): SEI versus the closed-form Derjaguin result (+0.1 % on a flat surface), mesh convergence (< 0.2 %), three literature anchors for BSA adsorption reproduced (§5, re-verified 24 Sep 2026), and internal cross-checks of the protein-scale calculations (< 0.01 %–3.4 %).",
 "Against the published S. aureus profile on mirror-polished 316L (R = 500 nm): the primary-minimum position is reproduced exactly (0.158 vs 0.157 nm), its magnitude to within 56 %, and the primary barrier to within 5 % when λ_AB = 0.5 nm is used (barrier position 0.66 vs ≈ 1 nm). The source paper does not state λ_AB, ζ or R; the two free parameters are stated explicitly here. Both the barrier height and the minimum depth are strongly ζ-dependent (×19 and ×48 across ζ_surface = −25 to −40 mV, Table 4).",
 "On the real ripple topography, the SEI energy collapses to ≈ 16 % of the flat-surface value for the ridge-confined geometries (L355-2, L1064-2), quantitatively supporting the geometric-shielding mechanism proposed in the published work (sign inversion for L532-2; Table 3, Figure 2).",
 "For BSA (R = 3.5 nm) on the 515 nm surfaces: the fresh (day-0) LIPSS and nanopillar zones are predicted to repel adsorption (ΔG_ADH = +6.9 and +6.3 mJ m⁻²; barriers 40.7 and 38.4 kT), whereas the as-prepared control surface is already weakly attractive (−6.7 mJ m⁻², no barrier). All three conditions become attractive within about one week of ambient ageing (§6).",
 "At the protein scale the surface texture is geometrically irrelevant: the area-averaged SEI geometric factor is 1.000–1.004 on all three measured AFM fields, with per-pixel deviations of ±3–10 % (§7) — roughly six times weaker than the same texture computed for bacterial cells (≈ 16 % energy reduction). Protein adsorption on these surfaces is therefore predicted to be controlled by surface chemistry (ageing), not by topography.",
 "Area-weighted sample-level estimate (§8): ≈ +2.2 mJ m⁻² (weakly repulsive) on day 0, crossing to attraction within about a week, and reaching ≈ −31 to −36 mJ m⁻² at day 58–73 (day 81: −22, following a positive contact-angle spike in the LIPSS zone).",
 "All values above are model predictions of thermodynamic tendency, not measurements. They are formulated as testable statements (§9) to be checked by the planned protein-adsorption (BCA) experiment — measure the contact angles on the same day as the adsorption assay.",
])

h1("1. Scope and provenance")
p("This report consolidates the modelling work carried out on the XDLVO–SEI framework up to 24 September 2026: (i) the independent reproduction of the published study (companion: the standalone reproduction report in the group folder); (ii) the BSA protein-parameterisation together with its literature-anchor validation; (iii) the BSA adhesion predictions for the 515 nm laser-textured surfaces (first delivered 12 Sep 2026, extended 24 Sep 2026); (iv) the protein-scale SEI study on measured AFM topography; and (v) the area-weighted sample-level estimate.")
p("Data provenance. All values above use measured inputs: substrate surface energies from sessile-drop contact angles (three probe liquids, van Oss–Chaudhury–Good model, measured in this work) and texture topography measured by AFM (LIPSS Λ = 412 ± 69 nm, Δ ≈ 90 nm; nanopillar spacing ≈ 187 nm, height ≈ 60 nm). Bacterial surface energies and the published interaction profiles are taken from Wang et al. (2026) (Table S3; §3.4 and Table S2 respectively; strains E. coli F1693 WT and S. aureus ATCC 12600). BSA parameters are taken from Wang & Newby (2014, Biointerphases 9, 041006). Predictions are labelled as such throughout; measurements and model outputs are never mixed.")

h1("2. Methods and implementation")
p("Theory (van Oss acid–base combination, as in the published work). The interaction energy per unit area at separation h is ΔG(h) = ΔG_LW(h) + ΔG_AB(h) + ΔG_EL(h), with")
bs([
 "LW: ΔG_LW(h) = ΔG_LW(h₀)·(h₀/h)²",
 "AB: ΔG_AB(h) = ΔG_AB(h₀)·exp[(h₀ − h)/λ_AB]",
 "EL: ΔG_EL(h) = (κ ε ε₀/2)·[(ζ₁² + ζ₂²)(1 − coth κh) + 2ζ₁ζ₂ csch κh]",
])
p("Contact values from the surface-energy components (van Oss combination). Parameters: h₀ = 0.158 nm; I = 0.15 M (PBS); T = 298.15 K; λ_AB = 0.5 nm was adopted for the reproduction comparisons (best match to the published barrier position, §4), while the calculations for this thesis' own series use λ_AB = 0.6 nm as previously delivered. Both values are stated explicitly wherever they matter.")
p("Sphere–flat geometry: Derjaguin integral U(h) = 2πR ∫ₕ^∞ ΔG(x) dx (evaluated analytically); sphere radius R = 500 nm for S. aureus (best-matching the published magnitudes; the source paper's “R ≈ 1–2 µm” is internally inconsistent) and R = 3.5 nm for BSA. E. coli is approximated as a sphere-chain of R = 250 nm. For textured/real surfaces the surface-element-integration (SEI) formulation is used: U = Σ ΔG(h_ij)·dA over the discretised height field. The published ripple topography is represented by the sinusoidal groove array, z = (Δ/2)·sin(2πx/Λ).")
p("Numerical implementation. An independent Python implementation in SI units (lengths in m internally; 1400 × 1400 sphere mesh for the reproduction; per-pixel curvature lookup tables for the protein-scale study) written for this work — not a port of the authors' MATLAB code (Text S1 was not available). Code: labtoolbox/xdlvo/ (xdlvo.py, sei.py) in the LabToolbox repository; analysis scripts accompany this report.")

h1("3. Validation of the implementation")
table("Table 1. Validation summary — reproduction of the published framework (§4) and internal cross-checks of the protein-scale calculations (§5–§7).",
 ["Test", "Result"],
 [["SEI vs closed-form Derjaguin, flat surface (R = 500 nm)", "−7.788 × 10⁻¹⁹ J vs −7.780 × 10⁻¹⁹ J, deviation +0.1 %"],
  ["Mesh convergence (700 → 1400 → 2100 elements)", "< 0.2 % change in U"],
  ["BSA literature anchors (Table 5)", "3 / 3 reproduced within tolerance (re-verified 24 Sep 2026)"],
  ["BSA ΔG values vs the 12 Sep 2026 delivery", "agree to < 0.01 mJ m⁻² (LW/AB/ADH)"],
  ["Derjaguin barrier vs delivered values (BSA)", "39.4 vs 40.7 kT (3.2 %); 37.1 vs 38.4 kT (3.4 %)"],
  ["SEI vs analytic Derjaguin at protein scale", "R = 450 nm: −0.09 %; R = 3.5 nm: −17.6 % (SEI value used; the Derjaguin approximation fails at protein scale)"],
  ["Geometric-factor grid convergence (n = 200 → 800)", "< 0.01 %"],
  ["Geometric factor vs surface chemistry (LIPSS vs control)", "±0.06 % (the factor is chemistry-insensitive)"]],
 widths=[7.5, 8.0])

h1("4. Reproduction of the published results (Wang et al., 2026, §3.4)")
table("Table 2. Reproduction of the published interaction profile (mirror-polished 316L SS, S. aureus).",
 ["Quantity", "Reported (Wang et al., 2026)", "This work (λ_AB = 0.5 nm)", "Deviation"],
 [["Primary minimum U_min (J)", "−6.28 × 10⁻¹⁹", "−2.77 × 10⁻¹⁹", "−56 %"],
  ["Position of U_min (nm)", "0.157", "0.158", "0 %"],
  ["Primary barrier U_max (J)", "+6.44 × 10⁻¹⁹", "+6.11 × 10⁻¹⁹", "−5 %"],
  ["Position of U_max (nm)", "≈ 1", "0.66", "−34 %"]],
 widths=[5.3, 4.0, 4.2, 2.5])
p("The primary-minimum position reproduces exactly; the barrier height agrees to 5 % at λ_AB = 0.5 nm (it is 2.6× lower at λ_AB = 0.6 nm). The published work does not state λ_AB, ζ, or a self-consistent R; the barrier position (≈ 1 nm) is best matched at λ_AB ≈ 0.5 nm and the absolute magnitudes at R ≈ 500 nm. These are the only two free parameters of the comparison and both are reported explicitly. The residual 56 % offset in the minimum magnitude is dominated by these unstated parameters, not by an implementation difference (§3).")
fig("fig1_reproduction", 15.5, "Figure 1. (a) Reproduction of the published flat-surface interaction profiles U(h) (S. aureus, R = 500 nm; the four surface conditions of Wang et al., 2026). (b) Adhesion free energy ΔG_ADH of the 515 nm surfaces of this thesis versus ambient ageing, both organisms (red: S. aureus; blue: E. coli; circles: LIPSS, squares: nanopillar, triangles: control 316L).")
table("Table 3. Flat-surface versus SEI energies on the published geometries (S. aureus, R = 500 nm).",
 ["Surface", "ΔG_ADH (mJ m⁻²)", "SEI / flat ratio"],
 [["316L SS (polished)", "−3.19", "1.01"],
  ["L355-2 (Λ = 262 nm)", "−11.02", "0.16"],
  ["L532-2 (Λ = 402 nm)", "+6.58", "sign inversion — ratio not meaningful"],
  ["L1064-2 (Λ = 866 nm)", "−4.28", "0.15"]],
 widths=[5.5, 4.5, 6.0])
p("For the two strongly corrugated samples (L355-2, L1064-2) the SEI energy on the real ripple topography is only ≈ 16 % of the ideal-flat value: ridges and grooves confine contact to discrete ridge crests, quantitatively supporting the geometric-shielding mechanism proposed in the published work. For L532-2 the flat-surface value is itself repulsive (+6.58 mJ m⁻²) and the textured value is positive (sign inversion), so the ratio is not quoted.")
fig("fig2_sei_vs_flat", 13.5, "Figure 2. SEI energy on the measured LIPSS topography versus the ideal flat-surface value for the published geometries (S. aureus, R = 500 nm). Grey: flat-surface (Derjaguin) minimum; red: SEI on the real ripple topography. For L532-2 the flat value is ≈ 0 on this scale (−2.5 × 10⁻²⁰ J) and the SEI value is positive (sign inversion).")
table("Table 4. Sensitivity of the interaction profile to ζ (validated sweep; ζ_cell held 5 mV less negative than ζ_surface).",
 ["ζ_surface / ζ_cell (mV)", "Primary minimum U_min (J)", "Primary barrier U_max (J)"],
 [["0 / 0", "−2.70 × 10⁻¹⁸", "no barrier (−6.25 × 10⁻²¹)"],
  ["−10 / −10", "−2.41 × 10⁻¹⁸", "no barrier (−6.25 × 10⁻²¹)"],
  ["−25 / −20", "−1.27 × 10⁻¹⁸", "+9.25 × 10⁻²⁰"],
  ["−30 / −25", "−5.29 × 10⁻¹⁹", "+4.26 × 10⁻¹⁹"],
  ["−40 / −35", "−2.64 × 10⁻²⁰", "+1.80 × 10⁻¹⁸"]],
 widths=[4.5, 5.5, 6.0])
p("The electrostatic contribution to ΔG(h₀) is < 1 %, yet the barrier height is strongly ζ-sensitive because the barrier is a near-cancellation of the LW attraction and the AB repulsion. ζ-potentials were not measured in this work; literature-typical values were assumed (−30 mV surface, −25 mV cell), and the published profile is reproduced at ζ ≈ −30/−25 mV, which is adopted as the reference case. Barrier heights and minimum depths must therefore always be quoted together with the ζ used.")

h1("5. BSA protein parameterisation and literature anchors")
p("BSA is described by γ_LW = 40.6, γ⁺ = 1.16, γ⁻ = 20.03 mJ m⁻², ζ = −13 mV, effective radius R = 3.5 nm (Wang & Newby, 2014, Table I; derived from three-liquid contact angles 54°/38°/5°). The implementation was locked to the same source with three literature anchors — BSA adsorption barriers on glass, PEG and polystyrene — which must be re-run whenever the core formulae are modified:")
table("Table 5. BSA literature anchors (Wang & Newby, 2014; PMC4286104). Re-verified 24 Sep 2026: 3 / 3 PASS (tolerance ±35 %).",
 ["Surface (γ_LW / γ⁺ / γ⁻, mJ m⁻²)", "Literature barrier", "This implementation"],
 [["Glass (36.7 / 0.24 / 68.27)", "61.2 kT", "62.8 kT (+2.6 %)"],
  ["PEG (45.3 / 0.04 / 39.92)", "11.8 kT", "9.7 kT (−18 %)"],
  ["Polystyrene (41.9 / 0.08 / 0.15)", "no barrier", "no barrier"]],
 widths=[6.5, 4.5, 5.5])
p("The implementation reproduces the qualitative ranking (glass ≫ PEG; no barrier on PS) and the glass barrier to 3 %; the PEG value deviates by 18 %, within the 35 % tolerance of the anchor set — the residual scatter reflects unknown details of the source's parameterisation. The discriminating quantity for protein attachment is the barrier height in kT, not ΔG alone: a barrier above ≈ 10 kT effectively prevents adsorption, while the disappearance of the barrier marks the onset of irreversible attachment.")

h1("6. BSA adhesion predictions for the 515 nm surfaces")
p("Fresh surfaces (day 0).")
table("Table 6. BSA predictions on freshly prepared surfaces (day 0; γ⁻ from this work's contact angles).",
 ["Surface", "γ⁻ (mJ m⁻²)", "ΔG_ADH (mJ m⁻²)", "Barrier (kT)", "Predicted behaviour"],
 [["LIPSS", "57.28", "+6.9", "40.7", "repels adsorption"],
  ["Nanopillar", "55.71", "+6.3", "38.4", "repels adsorption"],
  ["Control 316L", "25.43", "−6.7", "none", "already attractive"]],
 widths=[3.6, 3.0, 3.4, 2.6, 4.0])
p("Full ageing trajectory (per zone; extract of the 2026-09-12/24 dataset). Negative U(contact) means no repulsive barrier — the value is the depth of the contact attraction well.")
table("Table 7. BSA per-zone predictions vs ambient ageing (extract; days 0/3/7/15/22/49/58/81).",
 ["Surface", "Day", "γ⁻ (mJ m⁻²)", "ΔG_ADH (mJ m⁻²)", "U(contact) (kT)"],
 [["LIPSS", "0", "57.28", "+6.89", "+39.4"],
  ["LIPSS", "3", "44.92", "+1.79", "+20.1"],
  ["LIPSS", "7", "20.49", "−11.05", "−28.4"],
  ["LIPSS", "15", "4.42", "−25.36", "−82.5"],
  ["LIPSS", "22", "0.01", "−36.75", "−126.5"],
  ["LIPSS", "49", "6.35", "−22.89", "−73.2"],
  ["LIPSS", "58", "0.22", "−34.99", "−118.9"],
  ["LIPSS", "81", "57.13", "+6.55", "+39.3 (contact-angle spike)"],
  ["Nanopillar", "0", "55.71", "+6.29", "+37.1"],
  ["Nanopillar", "3", "43.03", "+0.95", "+16.9"],
  ["Nanopillar", "7", "17.64", "−12.98", "−35.7"],
  ["Nanopillar", "15", "11.31", "−17.91", "−54.4"],
  ["Nanopillar", "22", "7.37", "−21.74", "−68.8"],
  ["Nanopillar", "49", "7.87", "−21.21", "−66.8"],
  ["Nanopillar", "58", "0.00", "−37.87", "−129.5"],
  ["Nanopillar", "81", "0.01", "−37.19", "−127.2"],
  ["Control 316L", "0", "25.43", "−6.67", "−17.7"],
  ["Control 316L", "3", "21.36", "−9.27", "−27.0"],
  ["Control 316L", "7", "57.13", "+6.55", "+39.3 (flagged outlier)"],
  ["Control 316L", "15", "4.66", "−24.02", "−81.8"],
  ["Control 316L", "22", "14.46", "−13.89", "−45.4"],
  ["Control 316L", "49", "0.00", "−37.69", "−129.2"],
  ["Control 316L", "58", "0.19", "−35.20", "−119.7"],
  ["Control 316L", "81", "0.10", "−35.89", "−122.3"]],
 widths=[3.4, 1.5, 3.0, 3.4, 4.2])
p("Reading the trajectory: fresh laser-treated zones repel BSA with high barriers (≈ 38–41 kT), the as-prepared control is attractive from the start, and within 3–7 days of ambient ageing the surface energies fall (γ⁻ collapse) so that all three zones turn attractive. The control day-7 and LIPSS day-81 points follow positive contact-angle spikes in the measured series and are flagged as outliers (data flag in the delivered dataset); the trend, not these points, should be read.")

h1("7. Texture-geometry effect at the protein scale (SEI on measured AFM fields)")
p("The question: does the laser texture itself change BSA adsorption thermodynamics? Method: the SEI geometric factor — the ratio U(textured)/U(flat) — was computed for BSA (R = 3.5 nm) on the real measured ZSR height fields (512 × 512, 19.5 nm/px), using per-pixel principal curvatures and a validated curvature lookup table (curvature radii resolved: 6 nm – 2 µm).")
table("Table 8. BSA geometric factor on the measured fields (1 px Gaussian smoothing; deviation percentiles quoted as factor − 1).",
 ["Field", "Rc median (nm)", "Factor (mean)", "Factor (median)", "[P1, P99]", "|dev| > 5 %"],
 [["LIPSS (515LIPSS-10x10_area2)", "47.2", "1.0035", "0.991", "[−5.9 %, +10.1 %]", "12.4 %"],
  ["Nanopillar (515 NP-10x10-area1)", "52.5", "1.0020", "1.005", "[−4.9 %, +6.0 %]", "3.8 %"],
  ["Control (VirginSS-6)", "687.6", "1.0000", "1.000", "[−0.7 %, +0.8 %]", "0.0 %"]],
 widths=[4.6, 2.6, 2.2, 2.4, 2.6, 1.7])
p("The curvature extremes are large only on near-atomic features: at Rc = 6 nm the factor reaches +26.5 % (concave) / −16.1 % (convex); by Rc ≈ 100 nm it is ±1.2 %. The measured fields have median Rc ≈ 47–53 nm, where concave and convex contributions cancel: the area-averaged factor is 1.000–1.004 on all three surfaces. Per-pixel deviations are ±3–10 % (smoothing-narrowed ±3.7–6.4 %).")
fig("fig1_bsa_factor_vs_curvature", 13.5, "Figure 3. BSA (R = 3.5 nm) geometric factor U(curved)/U(flat) versus principal radius of curvature (concave and convex branches). Shaded band: range of curvatures resolved in the real LIPSS AFM scan (median Rc ≈ 47 nm).")
fig("fig2_bsa_field_factor_hist", 15.5, "Figure 4. Distribution of the per-pixel BSA geometric factor (deviation from unity, %) over the three measured AFM fields (ZSR): LIPSS, nanopillar, control (log counts, common range).")
fig("fig3_map_LIPSS", 15.5, "Figure 5. The LIPSS field, per pixel: topography, left; BSA geometric factor − 1 (%), right.")
p("Comparison with the bacterial scale: for S. aureus the same texture reduces the interaction energy to ≈ 16 % of the flat value (a ×6 suppression — the geometric shielding mechanism of §4). For BSA the same metric is ≈ 1.00. Conclusion: the laser texture does not modify BSA adsorption thermodynamics through geometry; any measured zone-to-zone differences in protein uptake should track surface chemistry (γ⁻/ageing), not topography. Caveat: at 19.5 nm/px the finest topographic features are smoothed by the scan resolution; sharper nanoscale features (if any) would act through the Rc < 20 nm range of Figure 3.")

h1("8. Sample-level (area-weighted) estimate")
p("The coupon carries three treatment zones; the BSA prediction for the whole sample is the area-weighted average of the zone values. Assuming equal zone areas (true dimensions pending), and with two bracketing scenarios, the weighted ΔG_ADH evolves as follows:")
table("Table 9. Area-weighted BSA ΔG_ADH (mJ m⁻²) versus ageing (equal-thirds assumption, plus two bracketing scenarios).",
 ["Day", "Equal thirds", "Control-heavy", "Treated-heavy"],
 [["0", "+2.2", "−0.0", "+3.9"],
  ["3", "−2.2", "−3.9", "−0.8"],
  ["7", "−5.8", "−2.7", "−8.3"],
  ["15", "−22.4", "−22.8", "−22.1"],
  ["22", "−24.1", "−21.6", "−26.2"],
  ["49", "−27.3", "−29.9", "−25.2"],
  ["58", "−36.0", "−35.8", "−36.2"],
  ["73", "−30.9", "−31.2", "−30.7"],
  ["81", "−22.2", "−25.6", "−19.4"]],
 widths=[2.0, 3.6, 3.6, 3.6])
fig("fig_bsa_sample_level_vs_day", 14.0, "Figure 6. BSA adsorption tendency on the 515 nm coupon: per-zone ΔG_ADH (LIPSS / nanopillar / control) and the area-weighted sample value (equal zone areas; dashed) versus ambient ageing.")
p("The sample-level picture: weakly repulsive on day 0 (+2.2), attraction established within about a week, and a broad strong-attraction plateau (−31 to −36 mJ m⁻²) at day 58–73 before the day-81 contact-angle spike lifts the estimate (−22). The three area scenarios span only ±3–4 mJ m⁻², so the conclusion is robust to the unknown zone fractions. The dominant variable by far is sample ageing; replacing the equal-thirds assumption with real zone dimensions will refine the day-0 value only marginally.")

h1("9. Testable statements for the planned protein experiment")
bs([
 "H1 — fresh treated zones resist, control adsorbs. Day-0 LIPSS and nanopillar are predicted to repel BSA (ΔG_ADH > 0, barriers ≈ 38–41 kT ≫ 10 kT) while the as-prepared control is attractive. Test: BCA protein assay on fresh coupons — BSA uptake should be lower on the laser-treated zones than on the control (opposite of a simple texture-trapping expectation).",
 "H2 — topography contributes negligibly at protein scale. The geometric factor is ≈ 1.00, so any zone-to-zone difference in measured BSA uptake should track surface chemistry (γ⁻), not roughness. If the experiment shows texture-dependent uptake beyond what chemistry explains, the continuum/rigid-sphere assumptions should be revisited.",
 "H3 — ageing dominates. The sign of ΔG_ADH is controlled by the ageing time through γ⁻; the adsorption result will be interpretable only if the surface state at assay time is quantified. Test: record contact angles on the same day as the assay; expect monotonically increasing BSA uptake as coupons age (barrier vanishes after ≈ 3–7 days).",
 "Note for assay design: once the barrier disappears, adsorption is thermodynamically irreversible — the day-0 window is the only one where the “anti-fouling” prediction can be tested positively.",
])

h1("10. Limitations")
bs([
 "All outputs are predictions of thermodynamic tendency from a continuum model (van Oss XDLVO + SEI). They contain no kinetics, no protein conformational change, no orientation effects, and no competitive (Vroman) adsorption.",
 "BSA is modelled as a rigid sphere (R = 3.5 nm). Literature parameter sets for the same protein differ by up to a factor of ≈ 2 (e.g., a second BSA set exists in the parameter library); the sign of the control-zone day-0 verdict can flip between sets. The BSA set used here is the one validated against the three anchors (Table 5).",
 "ζ-potentials were not measured; literature-typical values were assumed. Barrier heights and minimum depths depend on ζ by up to ×19 / ×48 (Table 4) and must always be quoted with the assumed values.",
 "The reproduction carries two free parameters (λ_AB, R) that the source paper does not state; both are reported explicitly. The residual 56 % offset in the minimum magnitude is dominated by that parameter freedom.",
 "The contact-angle ageing series contains positive spikes (measured outliers, e.g., control day-7, LIPSS day-81); the trend should be read, and the flagged points excluded from quantitative fitting.",
 "The sample-level estimate assumes equal zone areas (or the two bracketing scenarios); real zone dimensions will refine it.",
 "The protein-scale SEI inherits the scan resolution (19.5 nm/px): sub-20 nm topography is smoothed and acts only through the curvature lookup range.",
 "No protein-adsorption measurement exists yet on these surfaces — by construction, everything protein-related in this report awaits experimental test.",
])

h1("11. Reproducibility and file inventory")
bs([
 "Implementation and scripts: E:\\LabToolbox\\scripts\\ (recount/analysis scripts; bsa_sei_515_pilot.py, bsa_sample_level_weighting.py build the protein results; xdlvo core in E:\\LabToolbox\\labtoolbox\\xdlvo\\) — LabToolbox repository, commits 7a6527e (counting scripts) and 89b75df (BSA-SEI pilot + sei.py NaN fix). Anchor regression: xdlvo_validate.py in the research-skill folder (re-run 24 Sep 2026, 3/3 PASS).",
 "This report: build_xdlvo_sei_bsa_report.py regenerates the .docx and .md; figures/ holds the six figures in original resolution; data/ holds the underlying CSV/TXT tables (reproduction comparison and sensitivity; BSA self-checks, field statistics, curvature curve; per-zone and sample-level tables).",
 "Companion documents: XDLVO-SEI_reproduction_report.docx/.md (group folder; full reproduction report including the complete day-by-day SEI table); BSA预测_纹理效应与整片_20260924 (personal folder; the 24 Sep delivery); protein_BSA_*.csv (12 Sep BSA delivery data).",
])

h1("References")
bs([
 "Wang, Y., Olugbade, T. O., Zhao, Y.-Y., Dai, H., Zhang, S., Abdolvand, A., Zhao, Q., & Zolotovskaya, S. A. (2026). Geometry-driven control of bacterial adhesion and corrosion performance on LIPSS-textured 316 L stainless steel. Materials & Design, 263, 115626. https://doi.org/10.1016/j.matdes.2026.115626",
 "Wang, H., & Newby, B. Z. M. (2014). Applicability of the extended Derjaguin–Landau–Verwey–Overbeek theory on the adsorption of bovine serum albumin on solid surfaces. Biointerphases, 9(4), 041006. https://doi.org/10.1116/1.4904074 (PMC4286104)",
 "van Oss, C. J. (2006). Interfacial Forces in Aqueous Media (2nd ed.). CRC Press.",
 "Derjaguin, B. V. (1934). Untersuchungen über die Reibung und Adhäsion. Kolloid-Zeitschrift, 69, 155–164.",
 "Bhattacharjee, S., & Elimelech, M. (1997). Surface element integration: A novel technique for evaluation of DLVO interaction between a particle and a flat plate. Journal of Colloid and Interface Science, 193, 273–285.",
 "Pogodin, S., Hasan, J., Baulin, V. A., et al. (2013). Biophysical model of bacterial cell interactions with nanopatterned cicada wing surfaces. Biophysical Journal, 104, 835–840.",
 "Wang, Y., Dong, Y., Quan, Y., Wackerow, S., Abdolvand, A., Zolotovskaya, S. A., & Zhao, Q. (2025). Hybrid antibacterial surfaces: Combining laser-induced periodic surface structures with polydopamine–chitosan–silver nanoparticle nanocomposite coating. Advanced Materials Interfaces, 12(6), 2400660.",
])

# ---------------------------------------------------------------- docx render
doc = Document()
for sec in doc.sections:
    sec.top_margin = Cm(2.2); sec.bottom_margin = Cm(2.2)
    sec.left_margin = Cm(2.2); sec.right_margin = Cm(2.2)

def _borders(table):
    tblPr = table._tbl.tblPr
    b = OxmlElement('w:tblBorders')
    for edge, sz in (('top', 12), ('bottom', 12), ('left', 0), ('right', 0), ('insideH', 0), ('insideV', 0)):
        el = OxmlElement('w:' + edge)
        if sz:
            el.set(qn('w:val'), 'single'); el.set(qn('w:sz'), str(sz)); el.set(qn('w:space'), '0'); el.set(qn('w:color'), '000000')
        else:
            el.set(qn('w:val'), 'none')
        b.append(el)
    tblPr.append(b)

def _hdr_rule(row):
    for c in row.cells:
        tcPr = c._tc.get_or_add_tcPr()
        tb = OxmlElement('w:tcBorders'); el = OxmlElement('w:bottom')
        el.set(qn('w:val'), 'single'); el.set(qn('w:sz'), '6'); el.set(qn('w:space'), '0'); el.set(qn('w:color'), '000000')
        tb.append(el); tcPr.append(tb)

def add_par(text, style=None, size=None, bold=None, italic=None, align=None):
    if style:
        par = doc.add_paragraph(style=style)
    else:
        par = doc.add_paragraph()
    run = par.add_run(text)
    if size: run.font.size = Pt(size)
    if bold is not None: run.font.bold = bold
    if italic is not None: run.font.italic = italic
    if align: par.alignment = align
    return par

def add_table(spec):
    add_par(spec["caption"], size=10.5)
    t = doc.add_table(rows=len(spec["rows"]) + 1, cols=len(spec["headers"]))
    _borders(t)
    hdr = t.rows[0]
    for j, htxt in enumerate(spec["headers"]):
        cell = hdr.cells[j]; cell.text = ""
        r = cell.paragraphs[0].add_run(htxt); r.font.bold = True; r.font.size = Pt(10.5)
    _hdr_rule(hdr)
    for i, row in enumerate(spec["rows"]):
        for j, val in enumerate(row):
            cell = t.rows[i + 1].cells[j]; cell.text = ""
            r = cell.paragraphs[0].add_run(str(val)); r.font.size = Pt(10.5)
    if spec.get("widths"):
        for j, wcm in enumerate(spec["widths"]):
            for row in t.rows:
                row.cells[j].width = Cm(wcm)

# title block
tp = doc.add_paragraph(style="Title"); tp.add_run(TITLE)
add_par(SUBTITLE, size=11)
add_par(DATELINE, size=10, italic=True)
doc.add_paragraph()

for kind, payload in B:
    if kind == "h1":
        doc.add_heading(payload, level=1)
    elif kind == "h2":
        doc.add_heading(payload, level=2)
    elif kind == "p":
        add_par(payload, size=11)
    elif kind == "bullets":
        for it in payload:
            par = doc.add_paragraph(style="List Bullet"); par.add_run(it).font.size = Pt(11)
    elif kind == "table":
        add_table(payload)
        doc.add_paragraph()
    elif kind == "fig":
        path = prep_img(payload["name"])
        par = doc.add_paragraph(); par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.add_run().add_picture(path, width=Cm(payload["width_cm"]))
        add_par(payload["caption"], size=10)

DOCX = os.path.join(PKG, "XDLVO-SEI_BSA_report_20260924.docx")
doc.save(DOCX)
print("docx saved:", DOCX, os.path.getsize(DOCX), "bytes")

# ---------------------------------------------------------------- md render
md = []
md.append(f"# {TITLE}\n")
md.append(f"*{SUBTITLE}*\n")
md.append(f"*{DATELINE}*\n")
for kind, payload in B:
    if kind == "h1": md.append(f"\n## {payload}\n")
    elif kind == "h2": md.append(f"\n### {payload}\n")
    elif kind == "p": md.append(f"{payload}\n")
    elif kind == "bullets":
        for it in payload: md.append(f"- {it}")
        md.append("")
    elif kind == "table":
        md.append(f"{payload['caption']}\n")
        md.append("| " + " | ".join(payload["headers"]) + " |")
        md.append("|" + "---|" * len(payload["headers"]))
        for row in payload["rows"]:
            md.append("| " + " | ".join(str(v) for v in row) + " |")
        md.append("")
    elif kind == "fig":
        md.append(f"![{payload['name']}](figures/{payload['name']}.png)\n")
        md.append(f"{payload['caption']}\n")
MD = os.path.join(PKG, "XDLVO-SEI_BSA_report_20260924.md")
open(MD, "w", encoding="utf-8").write("\n".join(md))
print("md saved:", MD, os.path.getsize(MD), "bytes")
print("blocks:", len(B), "| tables:", sum(1 for k, _ in B if k == "table"), "| figs:", sum(1 for k, _ in B if k == "fig"))
