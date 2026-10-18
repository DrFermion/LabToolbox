# -*- coding: utf-8 -*-
"""build_650_minpx_report.py — 650 nm LIVE/DEAD：忽略最小像素限制的重统计报告 (docx -> PDF)

输入 (均在 imagej_counts_no_minpx/): compare_3-500_vs_min0.csv, survival_anova_old_vs_new.csv,
      minpx_sensitivity.csv, sub3px_particles_per_field.csv, 三张 PNG
输出: <scratch>/650nm_LIVE-DEAD_repeat1_no-min-pixel_20261018.pdf
      -> 共享夹 650nm-20261014/ 、个人夹 650nm_LIVE-DEAD_no_minpixel_20261018/ 、E: 镜像

用法: C:/Users/PC/miniconda3/python.exe scripts/build_650_minpx_report.py
"""
import os
import shutil

import pandas as pd
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

DS = ('F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - '
      'Ruinong Pan_Antibacterial Surfaces/Live_Dead Bacteria Test/650nm-20261014')
OUT = os.path.join(DS, 'imagej_counts_no_minpx')
PERSONAL = ('F:/OneDrive - University of Dundee/Ruinong_Pan_Personal/'
            '650nm_LIVE-DEAD_no_minpixel_20261018')
MIRROR = 'E:/LabToolbox/output/650_minpx_20261018'
SCRATCH = 'C:/Users/PC/AppData/Local/hermes/cache/scratch/650_minpx'
PDF_NAME = '650nm_LIVE-DEAD_repeat1_no-min-pixel_20261018.pdf'

FIGS = [('650nm_livedead_timecourse_repeat1.png',
         'Figure 1. Time course with the minimum particle size removed (0–500 px): stacked live '
         '(green) + dead (red) density in cells/cm², bar labels = pooled viability.'),
        ('650nm_minpx_viability_compare.png',
         'Figure 2. Paired comparison of pooled viability between the previous (3–500 px, open '
         'circle) and the re-counted (no minimum size, filled circle). Only groups shifting by '
         '≥ 1 percentage point are annotated.'),
        ('650nm_minpx_sensitivity.png',
         'Figure 3. Viability as a function of the minimum particle size (0/2/3/5/10/20 px; the '
         '500 px upper limit is unchanged). Thick lines = the three groups that move most.'),
        ('650nm_livedead_antiadhesion_repeat1.png',
         'Figure 4. Anti-adhesion vs the untreated control at 0–500 px — left column live cells, '
         'right column total cells (live + dead). Positive = fewer cells on the textured area than '
         'on the control; asterisks = Welch t-test per timepoint (uncorrected); hatched = QC-flagged.')]

CMP = pd.read_csv(os.path.join(OUT, 'compare_3-500_vs_min0.csv'), encoding='utf-8-sig')
ANV = pd.read_csv(os.path.join(OUT, 'survival_anova_old_vs_new.csv'), encoding='utf-8-sig')
SENS = pd.read_csv(os.path.join(OUT, 'minpx_sensitivity.csv'), encoding='utf-8-sig')
SUB = pd.read_csv(os.path.join(OUT, 'sub3px_particles_per_field.csv'), encoding='utf-8-sig')
TIMES = ['3h', '5h', '7h', '24h']
SPECIES = [('E. coli', 'E.coli'), ('S. aureus', 'S.aureus')]
REGS = ['Control', 'LIPSS', 'Nanopillar']
QC = {('S. aureus', '5h', 'Nanopillar')}


def fp(p):
    if pd.isna(p):
        return '—'
    if p < 0.001:
        return '< 0.001'
    return '%.3f' % p


def get_cmp(sp, t, reg, col):
    g = CMP[(CMP.species == sp) & (CMP.time == t) & (CMP.region == reg)]
    return float(g[col].iloc[0]) if len(g) else float('nan')


doc = Document()
for sec in doc.sections:
    sec.left_margin = Cm(2.0)
    sec.right_margin = Cm(2.0)
st = doc.styles['Normal']
st.font.name = 'Arial'
st.font.size = Pt(10)

doc.add_heading('650 nm textured stainless steel — LIVE/DEAD recounts without a minimum '
                'particle-size limit (repeat 1)', level=0)
p = doc.add_paragraph('Prepared 18 October 2026  ·  Dataset: Live_Dead Bacteria Test/650nm-20261014  ·  '
                      'E. coli and S. aureus  ·  3 / 5 / 7 / 24 h  ·  n = 5 fields per condition  ·  '
                      're-analysis of the 15 October 2026 summary')
p.alignment = WD_ALIGN_PARAGRAPH.LEFT

doc.add_heading('1. What was asked and what was changed', level=1)
for line in [
    'Request: repeat the 650 nm LIVE/DEAD statistics while ignoring the minimum pixel-size limit '
    'applied during particle analysis.',
    'Previous counting rule: ImageJ 1.54 "Analyze Particles", adaptive threshold (histogram mode of '
    'the background + 40), particle size 3–500 px, 8-connected; green and red images paired per field.',
    'This re-count: identical pipeline and identical threshold rule, but the lower size bound is set '
    'to 0 px, i.e. every thresholded object of 1 px or more is counted. The upper bound stays at '
    '500 px, so large merged clumps are still excluded exactly as before.',
    'Nothing else changed: same ImageJ build, same macro logic (including the channel-trap rule), '
    'same field area (46,946.10 µm², 1392 × 1040 px, 0.180 µm per pixel), same pairing and same '
    'statistics.',
]:
    doc.add_paragraph(line)

doc.add_heading('2. Verification that the pipeline is unchanged', level=1)
for line in [
    'The macro was re-run at 3–500 px and compared field by field with the counts delivered on '
    '15 October: 60/60 field pairs for E. coli and 60/60 for S. aureus reproduced exactly '
    '(0 mismatches in live and dead counts). The only difference between the two runs is therefore '
    'the size filter itself.',
    'A minimum of 0 px and 1 px give identical results (a particle cannot have less than 1 px), so '
    'the re-count is labelled "no minimum size".',
]:
    doc.add_paragraph(line)

doc.add_heading('3. Results', level=1)
doc.add_paragraph('Table 1. Pooled viability (%) per condition: previous 3–500 px rule versus the '
                  're-count with no minimum size. Δ = new − previous (percentage points). '
                  'Conditions shifting by ≥ 1 pp are marked ●.')

tb = doc.add_table(rows=1, cols=8)
tb.style = 'Light Grid Accent 1'
for i, h in enumerate(['Organism', 'Time', 'Surface', 'Live/field (new)', 'Dead/field (new)',
                       'Viability 3–500 px', 'Viability no min', 'Δ (pp)']):
    tb.rows[0].cells[i].text = h
for sp, _ in SPECIES:
    for t in TIMES:
        for reg in REGS:
            c = tb.add_row().cells
            c[0].text = sp if (t == TIMES[0] and reg == REGS[0]) else ''
            c[1].text = t.replace('h', ' h') if reg == REGS[0] else ''
            c[2].text = reg + (' ?' if (sp, t, reg) in QC else '')
            lv = get_cmp(sp, t, reg, 'live_no_min')
            dv = get_cmp(sp, t, reg, 'dead_no_min')
            c[3].text = '%.1f' % lv
            c[4].text = '%.1f' % dv
            c[5].text = '%.1f' % get_cmp(sp, t, reg, 'viab_3_500')
            c[6].text = '%.1f' % get_cmp(sp, t, reg, 'viab_no_min')
            d = get_cmp(sp, t, reg, 'd_viab_pp')
            c[7].text = ('%+.1f' % d) + (' ●' if abs(d) >= 1 else '')
doc.add_paragraph()

for fname, cap in FIGS:
    doc.add_paragraph(cap)
    doc.add_picture(os.path.join(OUT, fname), width=Cm(16.4))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

doc.add_heading('4. Statistics', level=1)
doc.add_paragraph('Table 2. One-way ANOVA of viability across the three areas, per organism and '
                  'timepoint, before and after removing the minimum size. Significance changes are '
                  'marked ●.')
tb = doc.add_table(rows=1, cols=5)
tb.style = 'Light Grid Accent 1'
for i, h in enumerate(['Organism', 'Time', 'p (3–500 px)', 'p (no minimum)', 'Change']):
    tb.rows[0].cells[i].text = h
for sp, _ in SPECIES:
    for t in TIMES:
        r = ANV[(ANV.species == sp) & (ANV.time == t)].iloc[0]
        c = tb.add_row().cells
        c[0].text = sp
        c[1].text = t.replace('h', ' h')
        c[2].text = fp(r.p_3_500)
        c[3].text = fp(r.p_no_min)
        changed = bool(r.sig_3_500) != bool(r.sig_no_min)
        c[4].text = ('● %s → %s' % ('sig.' if r.sig_3_500 else 'ns', 'sig.' if r.sig_no_min else 'ns')) \
            if changed else 'unchanged'
doc.add_paragraph()

doc.add_heading('5. Sensitivity to the minimum size, and what the extra objects are', level=1)
doc.add_paragraph('Table 3. All particles pooled across the data set for each minimum size '
                  '(upper limit 500 px throughout).')
tb = doc.add_table(rows=1, cols=5)
tb.style = 'Light Grid Accent 1'
for i, h in enumerate(['Minimum size', 'E. coli live', 'E. coli dead', 'S. aureus live',
                       'S. aureus dead']):
    tb.rows[0].cells[i].text = h
for m in sorted(SENS.min_px.unique()):
    c = tb.add_row().cells
    d = SENS[SENS.min_px == m]
    c[0].text = {0: 'none (≥1 px)', 2: '2 px', 3: '3 px (previous)', 5: '5 px',
                 10: '10 px', 20: '20 px'}[m]
    for j, sp in enumerate(['E. coli', 'S. aureus']):
        g = d[d.species == sp]
        c[1 + j * 2].text = '%d' % round((g.live_mean * g.n_fields).sum())
        c[2 + j * 2].text = '%d' % round((g.dead_mean * g.n_fields).sum())
doc.add_paragraph()

n_extra = int((SUB.live_sub3 + SUB.dead_sub3).sum())
_d0 = SENS[SENS.min_px == 0]
n_total = float(((_d0.live_mean + _d0.dead_mean) * _d0.n_fields).sum())
share = n_extra / n_total * 100
for line in [
    'Removing the floor adds %d objects in 240 images (1,400 of exactly 1 px and 1,142 of 2 px), '
    'i.e. %.1f %% of all counted objects; 185 of the 240 images contain at least one.' % (n_extra, share),
    'At 0.180 µm per pixel, a 1 px object is smaller than 0.2 µm and a 2 px object is at most about '
    '0.3 µm across — below the optical resolution of the 40× objective and well below the size of a '
    'single cell (E. coli ≈ 0.5 × 2 µm ⇒ ~3 × 11 px; S. aureus ≈ 0.8–1 µm ⇒ 4–6 px diameter, '
    '12–30 px²). A 3 px floor therefore cannot be discarding whole bacteria; it removes '
    'sub-resolution specks (shot noise, debris, threshold fragments).',
    'The extra objects are strongly clustered in a few fields rather than spread evenly. The largest '
    'single-field additions are: S. aureus 24 h LIPSS 1-r1 +128, 1-r2 +107; E. coli 3 h Nanopillar '
    '2-r4 +105; E. coli 24 h LIPSS 1-g4 +93; S. aureus 24 h Control c-r4 +87; E. coli 7 h Control '
    'c-g2 +75. Because E. coli fields contain only 30–350 objects, a burst of specks in one field '
    'moves the group mean appreciably; in S. aureus (800–3,300 objects per field) the same effect is '
    'diluted to a fraction of a percent.',
    'Where the added objects sit (QC): in the E. coli fields they are not randomly scattered. Of the '
    '120 E. coli images, 70 contain at least one 1–2 px object, and within those images a median of '
    '50 % of them (median 74–78 % at 3, 5 and 7 h) lie within ±2 px of one single image row — they '
    'form a one-pixel horizontal line across the field. The QC sheets (qc_sheets/) show this directly '
    'as a chain of magenta boxes. In S. aureus the same objects are distributed over the field '
    '(median 11 % on the modal row). The E. coli viability shifts described below are therefore '
    'driven by a line/scan artefact, not by unresolved bacteria — a further reason to keep the 3 px '
    'floor, and a reason to check the camera/scan for a defective row before the next session.',
]:
    doc.add_paragraph(line)

doc.add_heading('6. What changes, and what does not', level=1)
for line in [
    'Overall: E. coli +4.2 % live and +5.7 % dead objects; S. aureus +0.6 % live and +3.3 % dead. '
    'Pooled viability moves from 60.7 % to 60.4 % (E. coli) and from 68.2 % to 67.6 % (S. aureus), '
    'i.e. the data-set-level viability is unchanged within 0.6 pp.',
    'Most conditions move by less than 1 pp. Three shift materially: E. coli 3 h Nanopillar '
    '58.8 → 47.2 % (−11.6 pp, dead +60 %), E. coli 7 h Control 43.1 → 49.4 % (+6.3 pp, live +31 %), '
    'and E. coli 24 h Control 83.9 → 81.3 % (−2.6 pp, dead +21 %).',
    'Consequently E. coli statistics change: 3 h p = 0.054 → 0.318 (now clearly ns), 7 h ns → 0.042, '
    '24 h p = 0.008 → 0.130 (the between-area difference is lost). S. aureus is unaffected — all four '
    'timepoints remain significant (p ≤ 0.002) because its counts are an order of magnitude larger.',
    'The biological ordering survives the change: at 24 h LIPSS has the lowest viability in both '
    'organisms, and Nanopillar the highest in both (and also at 7 h in S. aureus; at 7 h in E. coli '
    'Nanopillar is the lowest). What does not survive is the E. coli between-area significance at '
    '3 h and 24 h.',
    'S. aureus 5 h Nanopillar remains unusable (viability 0.4 → 0.8 %): removing the size floor adds '
    'a handful of 1 px green specks to a field that is essentially empty. The QC flag stays.',
]:
    doc.add_paragraph(line, style='List Bullet')

doc.add_heading('7. Recommendation', level=1)
for line in [
    'Keep 3–500 px for headline numbers. A 3 px floor sits below the projected area of a single '
    'bacterium, so it can only remove objects that cannot be cells, while removing it lets '
    'single-pixel noise into a data set whose E. coli counts are only tens of objects per field.',
    'Report the no-minimum re-count as a sensitivity analysis (this document), not as a replacement: '
    'it shows that the main conclusions are robust to the size filter, and identifies the three '
    'E. coli conditions whose viability is sensitive to sub-resolution specks.',
    'If a size floor is to be revisited experimentally, the productive route is higher-resolution or '
    'higher-SNR imaging (fixed exposure per timepoint, as already recommended), not a lower particle '
    'threshold.',
]:
    doc.add_paragraph(line, style='List Bullet')

doc.add_heading('8. Files and provenance', level=1)
for line in [
    'Counts (no minimum size): imagej_counts_no_minpx/<species>/livedead_raw_counts.csv; '
    'per-condition summary and two-way ANOVA in the same folders.',
    'Comparison tables: compare_3-500_vs_min0.csv, survival_anova_old_vs_new.csv, '
    'minpx_sensitivity.csv, minpx_vs_3-500_deltas.csv, sub3px_particles_per_field.csv.',
    'Figures: 650nm_livedead_timecourse_repeat1.png (panel set regenerated at 0–500 px), '
    '650nm_minpx_viability_compare.png, 650nm_minpx_sensitivity.png; anti-adhesion figure '
    'regenerated as 650nm_livedead_antiadhesion_repeat1.png.',
    'QC images: imagej_counts_no_minpx/<species>/qc/<time>/ — 240 ImageJ overlays at 0–500 px (one '
    'per image, blue circles + numbering); qc_sheets/ — two diagnostic sheets in which blue circles '
    'mark objects already counted at 3 px and magenta boxes the newly added 1–2 px objects, with a '
    '×3 zoom of the densest region (yellow box).',
    'Scripts: E:\\LabToolbox\\scripts\\recount_650_minpx_imagej.py (counting), '
    'make_650_minpx_outputs.py (tables and figures), build_650_minpx_report.py (this report); '
    'macro scripts/imagej/count_livedead.ijm (now takes optional size limits, defaults 3/500). '
    'Repository: github.com/DrFermion/LabToolbox.',
    'Previous 3–500 px delivery (unchanged): 650nm_LIVE-DEAD_repeat1_summary_20261015.pdf and '
    'imagej_counts/.',
]:
    doc.add_paragraph(line, style='List Bullet')

os.makedirs(SCRATCH, exist_ok=True)
docx_path = os.path.join(SCRATCH, '650nm_no_min_pixel_report.docx')
pdf_path = os.path.join(SCRATCH, PDF_NAME)
doc.save(docx_path)
print('docx saved:', docx_path)

import win32com.client
word = win32com.client.Dispatch('Word.Application')
word.Visible = False
try:
    d = word.Documents.Open(docx_path)
    d.SaveAs(pdf_path, FileFormat=17)
    d.Close(False)
finally:
    word.Quit()
print('pdf saved:', pdf_path, os.path.getsize(pdf_path), 'bytes')

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
if PdfReader:
    rd = PdfReader(pdf_path)
    txt = ''.join((pg.extract_text() or '') for pg in rd.pages)
    print('pages:', len(rd.pages), 'chars:', len(txt),
          '| has Table 3:', 'Table 3.' in txt, '| has no minimum:', 'no minimum' in txt)

# ---------------- distribute ----------------
for d0 in (PERSONAL, MIRROR, DS):
    os.makedirs(d0, exist_ok=True)
for src in [pdf_path, docx_path]:
    for dst_dir in (DS, PERSONAL, MIRROR):
        dst = os.path.join(dst_dir, os.path.basename(src))
        if os.path.abspath(dst) != os.path.abspath(src):
            shutil.copy2(src, dst)
            print('copied ->', dst)
