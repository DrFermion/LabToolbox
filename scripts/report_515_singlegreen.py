# -*- coding: utf-8 -*-
"""
report_515_singlegreen.py — 515nm 单绿染总菌计数 docx 报告 (ImageJ 引擎)

读取 imagej_counts/ 下的:
  singlegreen_raw.csv / singlegreen_summary_by_region.csv / singlegreen_stats.csv / singlegreen_geometry.csv
生成:
  imagej_counts/singlegreen_report.docx
含: 方法学 / 图像数与排除政策 / 汇总表 / 统计表 / 三张图 / 备注与局限 / 文件清单
"""
import os
import datetime
import numpy as np
import pandas as pd

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_"
        r"Antibacterial Surfaces\Live_Dead Bacteria Test\515-singlegreen")
OUT = os.path.join(BASE, "imagej_counts")

raw = pd.read_csv(os.path.join(OUT, "singlegreen_raw.csv"), encoding="utf-8-sig")
summ = pd.read_csv(os.path.join(OUT, "singlegreen_summary_by_region.csv"), encoding="utf-8-sig")
stats_df = pd.read_csv(os.path.join(OUT, "singlegreen_stats.csv"), encoding="utf-8-sig")
geo_path = os.path.join(OUT, "singlegreen_geometry.csv")
geo = pd.read_csv(geo_path, encoding="utf-8-sig") if os.path.exists(geo_path) else None

excluded = raw[raw["excluded"].fillna(False).astype(bool)]
flagged = raw[(raw["mad_flag"].fillna(False).astype(bool)) & ~raw["excluded"].fillna(False).astype(bool)]
n_dirs = raw.groupby(["species", "time"]).ngroups

from docx import Document
from docx.shared import Pt, Inches

doc = Document()
doc.add_heading("515 nm coupons — total attached bacteria (single green stain, ImageJ re-count)", 0)
p = doc.add_paragraph()
p.add_run("Date: %s · repeat 1 · Data: %d image fields over %d sample groups"
          % (datetime.date.today().isoformat(), len(raw), n_dirs)).italic = True

doc.add_heading("Sample & methods", level=1)
doc.add_paragraph(
    "Sample: 515 nm laser-textured 316L stainless-steel coupons. Each coupon carries three zones: "
    "control (untextured), LIPSS (laser-induced periodic surface structures) and nanopillar texture. "
    "Bacterial adhesion assay with E. coli and S. aureus; imaging at 3, 6, 8 and 24 h adhesion time "
    "(repeat 1; repeats 2-3 folders are empty at the time of this report).")
doc.add_paragraph(
    "Stain: single green stain (SYTO9 only, no PI) — i.e. all attached bacteria are stained and the "
    "counts below are TOTAL attached bacteria (no live/dead split).")
doc.add_paragraph(
    "Counting engine: ImageJ 1.54 (classic, headless -batch). Adaptive threshold = background-histogram "
    "mode + 40, then Analyze Particles (size 3-500 px, 8-connected). Images are RGB TIFFs named "
    "{region}-{n}.tif without a channel suffix; each image was fed to the macro as {region}-{n}-g.tif "
    "so the macro selects the green channel, and results were mapped back to the original names. "
    "Field area (40x objective): 46946.10 um2; density [cells/cm2] = count / 46946.10 x 1e8.")
doc.add_paragraph(
    "Image QC (independent, pixel-geometry diagnostic — diagnose_515_singlegreen.py): for every image "
    "the thresholded connected components were re-computed; the 3-500 px component count matches the "
    "ImageJ count on all %d images (max |diff| = 0-3 px-level rounding), and two per-field diagnostics "
    "were derived: the fraction of thresholded signal sitting in >500 px merged clumps (big_frac) and "
    "the coverage (cover_pct). big_frac quantifies the undercount risk in fields where bacteria touch "
    "each other and merge into objects larger than the 500 px upper size limit." % len(raw))

doc.add_heading("Exclusion policy (this dataset)", level=1)
doc.add_paragraph(
    "Two-tier policy, since the ss-control-style forced MAD trimming proved unsuitable here: "
    "(1) EXCLUDED — only images where the background mode is saturated (mode >= 250) so that the "
    "mode+40 threshold is invalid (count 0 is a false zero). %s; "
    "(2) FLAGGED, NOT EXCLUDED — fields deviating strongly from their group median "
    "(|x - median| > 5 x MAD). In this dataset several groups are so uniform that 5 x MAD falls below "
    "5-15%% of the median (e.g. the 8 h LIPSS group: median 223, 5 x MAD = 30 px-level counts), where "
    "forced trimming would discard physiologically normal fields (all three flagged fields there were "
    "within +-26%% of the median). QC review of the flagged fields found no artefact evidence "
    "(object-size distributions normal; the same type of large clumps occur in non-flagged fields of "
    "the same group), so no counts were removed; the MAD diagnostics remain in the raw CSV. "
    "%d field(s) carry a flag: %s."
    % ("Excluded: " + "; ".join(
        "%s %s %s-%d.tif (mode=%d)" % (r["species"], r["time"], r["region"], r["num"], r["bg"])
        for _, r in excluded.iterrows()) if len(excluded) else "No image was excluded.",
       len(flagged),
       ", ".join("%s %s %s-%d (%d, %.1f x MAD)" % (r["species"], r["time"], r["region"], r["num"],
                                                   r["count"], r["mad_mult"])
                 for _, r in flagged.iterrows()) if len(flagged) else "none"))

if geo is not None:
    gf = geo.groupby(["species", "time", "region"])["big_frac"].mean().round(2)
    hot = gf[gf >= 0.30]
    hot_txt = "; ".join("%s %s %s: %.2f" % (sp, t, rg, v) for (sp, t, rg), v in hot.items())
    doc.add_paragraph(
        "Merged-clump diagnostic (big_frac, mean per group; 0 = all signal in countable objects): "
        "groups >= 0.30: %s. In these groups a large part of the fluorescent material sits in objects "
        "larger than the 500 px size limit (merged bacteria clusters), so the reported counts are "
        "LOWER BOUNDS and comparisons in those groups are conservative." % (hot_txt or "none"))

doc.add_heading("Summary by species / time / texture zone (per-field counts and density)", level=1)
t = doc.add_table(rows=1, cols=8)
t.style = "Light Grid Accent 1"
hdr = ["species", "time", "region", "n", "excluded", "count mean ± SD", "density mean (cells/cm2)", "density SD"]
for j, c in enumerate(hdr):
    t.rows[0].cells[j].text = c
for _, r in summ.iterrows():
    cells = t.add_row().cells
    cells[0].text = str(r["species"])
    cells[1].text = str(r["time"])
    cells[2].text = str(r["region_label"])
    cells[3].text = str(int(r["n"]))
    cells[4].text = str(int(r["n_excluded"]))
    cells[5].text = "%.1f ± %.1f" % (r["count_mean"], r["count_sd"] if np.isfinite(r["count_sd"]) else 0)
    cells[6].text = "%.3g" % r["cm2_mean"]
    cells[7].text = "%.3g" % (r["cm2_sd"] if np.isfinite(r["cm2_sd"]) else 0)

doc.add_heading("Statistics: change vs control (BH-adjusted)", level=1)
t2 = doc.add_table(rows=1, cols=8)
t2.style = "Light Grid Accent 1"
hdr2 = ["species", "time", "LIPSS Δ%", "p (BH)", "sig", "Nanopillar Δ%", "p (BH)", "sig"]
for j, c in enumerate(hdr2):
    t2.rows[0].cells[j].text = c


def sig(p):
    if not np.isfinite(p):
        return ""
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"


for _, r in stats_df.iterrows():
    cells = t2.add_row().cells
    cells[0].text = str(r["species"])
    cells[1].text = str(r["time"])
    cells[2].text = "%+.0f%%" % r["reduction_LIPSS_pct"]
    cells[3].text = "%.3g" % r["p_control_vs_LIPSS_BH"]
    cells[4].text = sig(r["p_control_vs_LIPSS_BH"])
    cells[5].text = "%+.0f%%" % r["reduction_Nanopillar_pct"]
    cells[6].text = "%.3g" % r["p_control_vs_Nanopillar_BH"]
    cells[7].text = sig(r["p_control_vs_Nanopillar_BH"])
doc.add_paragraph(
    "Δ% = (mean density of textured zone - mean density of control) / mean density of control x 100; "
    "negative = fewer attached bacteria than control. Pairwise Mann-Whitney U tests, BH-adjusted "
    "across all 48 comparisons (three pairwise tests x 16 species-time groups); full table incl. "
    "LIPSS vs Nanopillar in singlegreen_stats.csv.")

doc.add_heading("Figures", level=1)
for fn, cap in (
        ("singlegreen_by_region.png",
         "Figure 1. Total attached bacteria per texture zone over time (mean ± SD, individual fields "
         "as dots). Bars: control (grey), LIPSS (blue), nanopillar (violet)."),
        ("singlegreen_reduction_vs_control.png",
         "Figure 2. Change vs control region (%). Stars: BH-adjusted Mann-Whitney (* p<0.05, ** p<0.01)."),
        ("singlegreen_merge_diagnostic.png",
         "Figure 3. Merged-clump diagnostic (fraction of thresholded signal in >500 px clumps; higher = "
         "counts are stronger lower bounds). Same colour code.")):
    fp = os.path.join(OUT, fn)
    if os.path.exists(fp):
        doc.add_picture(fp, width=Inches(5.9))
        doc.add_paragraph(cap)

doc.add_heading("Notes & limitations", level=1)
exp = raw.groupby("species")["exposure_s"].agg(["min", "max"])
doc.add_paragraph(
    "· Exposure times vary within and between groups (E. coli: %.2f-%.2f s; S. aureus: %.2f-%.2f s); "
    "control fields were often imaged with shorter exposure. The adaptive threshold normalises the "
    "background but not the brightness scale, so counts across groups with different exposure carry an "
    "extra uncertainty."
    % (exp.loc["E.coli", "min"], exp.loc["E.coli", "max"], exp.loc["S.aureus", "min"], exp.loc["S.aureus", "max"]))
doc.add_paragraph(
    "· Dense fields: where big_frac is high (see diagnostic section and Figure 3) touching cells merge "
    "into objects above the 500 px cut-off; reported counts there are lower bounds. This affects E. coli "
    "control fields most strongly and the S. aureus 24 h group (control coverage reaches confluence).")
doc.add_paragraph(
    "· At 24 h several S. aureus fields are close to (or at) confluence; single-cell counting becomes "
    "unreliable in such fields and the absolute numbers should be treated as approximate. For repeats "
    "2-3 consider keeping exposure constant and/or using sparser fields (or a lower magnification "
    "overview) for the 24 h point.")
doc.add_paragraph(
    "· Repeat 1 only (repeats 2-3 empty). This is a single-repeat preliminary analysis; treat "
    "differences between zones as indicative until repeats 2-3 are analysed.")
doc.add_paragraph(
    "· QC images (blue circle + number on every counted object) for every counted field are in "
    "qc/<species>/<repeat>/<time>/.")

doc.add_heading("Output files", level=1)
for fn in ("singlegreen_raw.csv", "singlegreen_summary_by_region.csv", "singlegreen_stats.csv",
           "singlegreen_geometry.csv", "singlegreen_by_region.png",
           "singlegreen_reduction_vs_control.png", "singlegreen_merge_diagnostic.png"):
    doc.add_paragraph(os.path.join(OUT, fn))
doc.add_paragraph("QC images: " + os.path.join(OUT, "qc", "<species>", "<time>"))

report = os.path.join(OUT, "singlegreen_report.docx")
doc.save(report)
print("报告:", report)
print("排除:", len(excluded), "张; MAD 标注:", len(flagged), "张")
