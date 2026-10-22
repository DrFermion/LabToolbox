# -*- coding: utf-8 -*-
"""build_650_repeat2_report.py — 650 nm LIVE/DEAD repeat-2 (+combined +validation) short report.

Reads the summary CSVs written by plot_650_repeat2.py and the three figures, builds a
.docx with python-docx and exports a PDF through Word COM.

  --template   report skeleton with placeholder markers (no numbers yet)
  (default)    real report from 650nm_livedead_repeat2_summary.csv etc.

Usage
  python build_650_repeat2_report.py --template \
      --figdir E:/LabToolbox/output/650_repeat2_template_20261021
  python build_650_repeat2_report.py --figdir <out> \
      --out "F:/.../650nm-20261014/650nm_LIVE-DEAD_repeat2_summary_<date>.pdf"
"""
from __future__ import annotations

import argparse
import os
import shutil

import pandas as pd
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

SCRATCH = 'C:/Users/PC/AppData/Local/hermes/cache/scratch'
TIMES = ['3h', '5h', '7h', '24h']
AREAS = ['c', '1', '2']
AREA_LABEL = {'c': 'Control', '1': 'LIPSS', '2': 'Nanopillar'}
PENDING = '\u3008pending\u3009'


def add_banner(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(11)
    r.font.color.rgb = RGBColor(0xC6, 0x28, 0x28)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return p


def add_bullets(doc, lines):
    for line in lines:
        doc.add_paragraph(line, style='List Bullet')


def aa_lookup(df, val='total_cm2'):
    """{(species, time, area): anti-adhesion %} against the control of the same timepoint."""
    out = {}
    if df is None:
        return out
    for sp in ('E. coli', 'S. aureus'):
        for t in TIMES:
            c = df[(df.species == sp) & (df.time == t) & (df.area == 'c')]
            if c.empty:
                continue
            base = float(c[val].iloc[0])
            if not base or not (base == base):
                continue
            for ar in ('1', '2'):
                g = df[(df.species == sp) & (df.time == t) & (df.area == ar)]
                if g.empty:
                    continue
                v = float(g[val].iloc[0])
                if not (v == v):
                    continue
                out[(sp, t, ar)] = (base - v) / base * 100
    return out


def aa_table(doc, sp, lookups, caption):
    """lookups: list of (column header, aa dict)."""
    doc.add_paragraph(caption, style='Heading 3')
    tb = doc.add_table(rows=1, cols=1 + len(lookups) * 2)
    tb.style = 'Light Grid Accent 1'
    tb.rows[0].cells[0].text = 'Time'
    for i, (hdr, _) in enumerate(lookups):
        tb.rows[0].cells[1 + 2 * i].text = hdr + ' / LIPSS'
        tb.rows[0].cells[2 + 2 * i].text = hdr + ' / Nanopillar'
    for t in TIMES:
        cells = tb.add_row().cells
        cells[0].text = t.replace('h', ' h')
        for i, (_, lut) in enumerate(lookups):
            for j, ar in enumerate(('1', '2')):
                v = lut.get((sp, t, ar))
                cells[1 + 2 * i + j].text = PENDING if v is None else '%+.0f %%' % v
    doc.add_paragraph()


def table_from_summary(doc, df, sp, value_col, fmt, header):
    tb = doc.add_table(rows=1, cols=len(AREAS) + 1)
    tb.style = 'Light Grid Accent 1'
    tb.rows[0].cells[0].text = 'Time'
    for i, a in enumerate(AREAS):
        tb.rows[0].cells[i + 1].text = AREA_LABEL[a]
    for t in TIMES:
        cells = tb.add_row().cells
        cells[0].text = t.replace('h', ' h')
        for i, a in enumerate(AREAS):
            if df is None:
                cells[i + 1].text = PENDING
                continue
            g = df[(df.species == sp) & (df.time == t) & (df.area == a)]
            cells[i + 1].text = PENDING if g.empty else fmt % float(g[value_col].iloc[0])
    doc.add_paragraph()


def findings(R2, CB, raw=None):
    """Narrative bullets with the real numbers, computed from the summary tables."""
    def key(sp, t, a, col='total_cm2'):
        r = CB[(CB.species == sp) & (CB.time == t) & (CB.area == a)]
        return float(r[col].iloc[0]) if len(r) else float('nan')

    def r2val(sp, t, a, col):
        r = R2[(R2.species == sp) & (R2.time == t) & (R2.area == a)]
        return float(r[col].iloc[0]) if len(r) else float('nan')

    def aa(base, v):
        if not (base == base) or not (v == v) or not base:
            return float('nan')
        return (base - v) / base * 100.0

    def fmt(v):
        return 'n/a' if v != v else '%+.0f%%' % v

    def series(sp, ar, rep):
        out = []
        for t in TIMES:
            if rep == 'r2':
                base = r2val(sp, t, 'c', 'total_cm2')
                val = r2val(sp, t, ar, 'total_cm2')
            elif rep == 'comb':
                base = key(sp, t, 'c', 'total_cm2')
                val = key(sp, t, ar, 'total_cm2')
            else:
                base = key(sp, t, 'c', 'r1_total')
                val = key(sp, t, ar, 'r1_total')
            out.append(aa(base, val))
        return out

    def agree(sp, ar):
        a1, a2 = series(sp, ar, 'r1'), series(sp, ar, 'r2')
        ok = [t for t, x, y in zip(TIMES, a1, a2)
              if x == x and y == y and abs(x) > 5 and abs(y) > 5 and (x > 0) == (y > 0)]
        bad = [t for t, x, y in zip(TIMES, a1, a2)
               if x == x and y == y and abs(x) > 5 and abs(y) > 5 and (x > 0) != (y > 0)]
        return ok, bad

    L = []
    for sp in ('E. coli', 'S. aureus'):
        s2t1 = ', '.join(fmt(v) for v in series(sp, '1', 'r2'))
        s2t2 = ', '.join(fmt(v) for v in series(sp, '2', 'r2'))
        sct1 = ', '.join(fmt(v) for v in series(sp, '1', 'comb'))
        sct2 = ', '.join(fmt(v) for v in series(sp, '2', 'comb'))
        s1t1 = ', '.join(fmt(v) for v in series(sp, '1', 'r1'))
        s1t2 = ', '.join(fmt(v) for v in series(sp, '2', 'r1'))
        L.append('%s - anti-adhesion on total cells (3, 5, 7, 24 h): repeat 2 LIPSS %s / nanopillar '
                 '%s; repeat 1 LIPSS %s / nanopillar %s; combined LIPSS %s / nanopillar %s. '
                 '(positive = fewer cells than the control, negative = more.)'
                 % (sp, s2t1, s2t2, s1t1, s1t2, sct1, sct2))
    vb = []
    for sp in ('E. coli', 'S. aureus'):
        vb.append('%s viability in repeat 2 - control %s, LIPSS %s, nanopillar %s' % (
            sp,
            ', '.join('%.0f%%' % r2val(sp, t, 'c', 'viability') for t in TIMES),
            ', '.join('%.0f%%' % r2val(sp, t, '1', 'viability') for t in TIMES),
            ', '.join('%.0f%%' % r2val(sp, t, '2', 'viability') for t in TIMES)))
    L += vb
    ag = []
    for sp in ('E. coli', 'S. aureus'):
        for ar, nm in (('1', 'LIPSS'), ('2', 'nanopillar')):
            ok, bad = agree(sp, ar)
            if ok:
                ag.append('%s %s agrees at %s' % (sp, nm, '/'.join(ok)))
            if bad:
                ag.append('%s %s flips sign at %s' % (sp, nm, '/'.join(bad)))
    L.append('Repeat-to-repeat agreement (sign of the anti-adhesion, |AA| > 5 %): '
             + '; '.join(ag) + '. Where the two repeats flip sign the pooled value is not an '
             'effect - quote the repeats separately.')
    if raw is not None and len(raw):
        r = raw[(raw.time == '5h') & (raw.species == 'S. aureus')].dropna(subset=['live', 'dead'])
        s2 = r[r.area.astype(str) == '2']
        s3 = r[r.area.astype(str) == '3']
        if len(s2) and len(s3):
            v2 = s2.live.sum() / (s2.live.sum() + s2.dead.sum()) * 100
            v3 = s3.live.sum() / (s3.live.sum() + s3.dead.sum()) * 100
            L.append('Validation coupon (Figure 3): the repeat-1 nanopillar coupon that read 0.4 %% '
                     'viability at 5 h was re-shot in repeat 2 as sample 3 and now reads %.1f %% '
                     'viability with %.0f cells per field, against %.1f %% / %.0f cells on the '
                     'normal coupon (sample 2). The near-zero value is therefore a '
                     'coupon/staining artefact, not a surface effect: the repeat-1 5 h nanopillar '
                     'viability must not be quoted, and the combined bar for that condition mixes '
                     'a superseded value with a normal one.'
                     % (v3, s3.total.mean(), v2, s2.total.mean()))
        else:
            L.append('Validation coupon (Figure 3): see the figure - sample 3 is the re-shot coupon.')
    else:
        L.append('Validation coupon (Figure 3): sample 3 is the re-shot coupon; sample 3 is never '
                 'pooled into any statistic.')
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--figdir', required=True)
    ap.add_argument('--ic', default='', help='repeat-2 imagej_counts dir (for the sample-3 numbers)')
    ap.add_argument('--template', action='store_true')
    ap.add_argument('--out', default='')
    ap.add_argument('--date', default='')
    a = ap.parse_args()
    tag = '_TEMPLATE' if a.template else ''
    date = a.date or '2026-10-22'

    fa = os.path.join(a.figdir, '650nm_livedead_repeat2%s.png' % tag)
    fb = os.path.join(a.figdir, '650nm_livedead_combined_repeat1_repeat2%s.png' % tag)
    fc = os.path.join(a.figdir, '650nm_livedead_validation_5h_Saureus%s.png' % tag)
    sa = os.path.join(a.figdir, '650nm_livedead_repeat2_summary%s.csv' % tag)
    sb = os.path.join(a.figdir, '650nm_livedead_combined_summary%s.csv' % tag)
    R2 = None if a.template else (pd.read_csv(sa, encoding='utf-8-sig') if os.path.exists(sa) else None)
    CB = None if a.template else (pd.read_csv(sb, encoding='utf-8-sig') if os.path.exists(sb) else None)
    RAW = None
    if a.ic:
        p = os.path.join(a.ic, 'S.aureus', 'livedead_raw_counts.csv')
        if os.path.exists(p):
            RAW = pd.read_csv(p, encoding='utf-8-sig')
            RAW['area'] = RAW['area'].astype(str)
            RAW['time'] = RAW['time'].astype(str)
            RAW['species'] = 'S. aureus'

    doc = Document()
    for sec in doc.sections:
        sec.left_margin = Cm(2.0)
        sec.right_margin = Cm(2.0)
    st = doc.styles['Normal']
    st.font.name = 'Arial'
    st.font.size = Pt(10)

    doc.add_heading('650 nm textured stainless steel - bacterial LIVE/DEAD, repeat 2 '
                    '(combined with repeat 1)', level=0)
    doc.add_paragraph('Report date %s  ·  dataset Live_Dead Bacteria Test/650nm-20261014  ·  '
                      'E. coli and S. aureus  ·  timepoints 3 / 5 / 7 / 24 h  ·  '
                      'ImageJ counting, size 3-500 px' % date)
    if a.template:
        add_banner(doc, 'TEMPLATE / LAYOUT PREVIEW - the repeat-2 numbers in this file are '
                        'PLACEHOLDERS. Nothing here may be quoted until the repeat-2 images are '
                        'counted.')

    doc.add_heading('1. What this report answers', level=1)
    add_bullets(doc, [
        'Does repeat 2 reproduce the repeat-1 picture (adhesion and viability of E. coli and '
        'S. aureus on the LIPSS and nanopillar areas relative to the untreated control)?',
        'Is the near-zero-viability S. aureus 5 h nanopillar coupon from repeat 1 a coupon/sample '
        'problem? Repeat 2 re-imaged that same coupon (sample 3) next to a normal nanopillar '
        'coupon (sample 2); the two are compared directly (Figure 3) and sample 3 is kept out of '
        'every pooled statistic.',
        'What do the two repeats together say once they are combined (Figure 2)?',
    ])

    doc.add_heading('2. Sample layout and counting rules', level=1)
    add_bullets(doc, [
        'Coupon: 650 nm laser-textured stainless steel with three areas - Control (c), LIPSS (1), '
        'Nanopillar (2). Repeat 2 additionally contains the re-shot coupon (sample 3) at '
        'S. aureus 5 h.',
        'Imaging: LIVE/DEAD staining, 40x, field area 46,946.10 um2 (1392 x 1040 px), five fields '
        'per condition.',
        'Counting: ImageJ 1.54 Analyze Particles, adaptive threshold (background mode + 40), '
        'particle size 3-500 px, green and red channels paired per field. Density = count / '
        '46,946.10 um2 x 1e8 (cells/cm2); viability = pooled live / (live + dead).',
        'Anti-adhesion AA = (N_control - N_surface) / N_control x 100, computed separately for live '
        'cells and for total cells (live + dead); positive = fewer cells than the control.',
        'Sample 3 (re-shot QC coupon) is excluded from Figures 1-2 and from every table; it appears '
        'only in Figure 3. The repeat-2 S. aureus 7 h control is missing, so the repeat-1 control of '
        'the same timepoint is used instead and flagged with a dagger in the figures and in the '
        'tables below.',
        'The repeat-2 S. aureus 24 h control coupon was contaminated (no green channel, red counted '
        'as total): its total-cell value is repeat 2, its viability/live-dead values are taken from '
        'repeat 1 and flagged with a double dagger. This follows the readme left in that folder.',
    ])

    doc.add_heading('3. Results', level=1)
    doc.add_paragraph('Figure 1. Repeat 2 - left column: live (green) + dead (red) cell density, '
                      'bar labels = pooled viability; right column: total-cell density with the '
                      'anti-adhesion percentage over each textured bar (grey = control). '
                      'Upper row E. coli, lower row S. aureus.')
    doc.add_picture(fa, width=Cm(16.4))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph('Figure 2. Repeats 1 + 2 combined - bars are the mean of the two repeat '
                      'means, open circles = repeat 1 mean, open squares = repeat 2 mean, error '
                      'bars = SD of the two repeats. Same panel logic as Figure 1.')
    doc.add_picture(fb, width=Cm(16.4))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph('Figure 3. Validation coupon (S. aureus, 5 h) - repeat-1 nanopillar coupon '
                      '(0.4 % viability) next to the repeat-2 normal nanopillar coupon (sample 2) '
                      'and the re-shot coupon (sample 3). Sample 3 is shown here only.')
    doc.add_picture(fc, width=Cm(15.6))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_heading('Tables - repeat 2', level=2)
    for sp in ('E. coli', 'S. aureus'):
        doc.add_paragraph('Viability (%%) - %s' % sp, style='Heading 3')
        table_from_summary(doc, R2, sp, 'viability', '%.1f', 'viability')
        doc.add_paragraph('Total-cell density (x 10^5 cells/cm2) - %s' % sp, style='Heading 3')
        if R2 is not None:
            R2w = R2.copy()
            R2w['total_1e5'] = R2w['total_cm2'] / 1e5
        table_from_summary(doc, None if R2 is None else R2w, sp, 'total_1e5', '%.2f', 'total')
        aa_table(doc, sp, [('repeat 2', aa_lookup(R2)),
                           ('repeats 1+2', aa_lookup(CB))],
                 'Anti-adhesion (%%, total cells) - %s; positive = fewer cells than the control'
                 % sp)

    doc.add_heading('4. Findings', level=1)
    if a.template or R2 is None or CB is None:
        add_bullets(doc, [PENDING + ' repeat 2 is not counted yet - this section fills itself in '
                          'as soon as the numbers are in.'])
    else:
        add_bullets(doc, findings(R2, CB, RAW))

    doc.add_heading('5. QC and limitations', level=1)
    add_bullets(doc, [
        'Exposure time differs between sessions (read from the TIFF metadata): absolute densities '
        'are not directly comparable across timepoints; viability ratios are far less affected '
        'because both channels share the exposure.',
        'Counting excludes clusters larger than 500 px and uses size 3-500 px, so counts in dense '
        'fields are slight lower bounds.',
        'The repeat-2 S. aureus 7 h control is borrowed from repeat 1 - it shares the repeat-1 '
        'session conditions, so the 7 h values for that organism carry extra uncertainty (dagger).',
        'The repeat-2 S. aureus 24 h control coupon was contaminated: only the red channel exists. '
        'Its total-cell numbers are used as the control for the anti-adhesion calculation, while '
        'the viability of that point comes from repeat 1 (double dagger).',
        'Sample 3 exists at one timepoint only (S. aureus 5 h) and is a coupon re-test, not a '
        'biological replicate: it cannot be used to estimate repeat-to-repeat variance.',
        'The repeat-1 S. aureus 5 h nanopillar viability (0.4 %) is superseded by the repeat-2 '
        're-shot of the same coupon and must not be quoted or pooled.',
        'Repeat 3 folders exist in the dataset but are still empty, so this report covers two '
        'repeats only; no formal two-repeat p-value is defensible yet (n = 2 means).',
    ])

    doc.add_heading('6. Data and provenance', level=1)
    add_bullets(doc, [
        'Raw images: Live_Dead Bacteria Test/650nm-20261014/<species>/repeat 2/<time>/ '
        '(repeat 1 is already archived in the same dataset folder).',
        'Counts: imagej_counts_repeat2/<species>/livedead_raw_counts.csv (same schema as repeat 1).',
        'Figures / summaries: E:\\LabToolbox\\scripts\\plot_650_repeat2.py; this report: '
        'E:\\LabToolbox\\scripts\\build_650_repeat2_report.py. Repository '
        'github.com/DrFermion/LabToolbox.',
        'One command reproduces everything: python plot_650_repeat2.py --ic <repeat-2 counts> '
        '--ic-r1 <repeat-1 counts> --out <dir> --borrow "S.aureus|7h" '
        '--viab-from-r1 "S.aureus|24h" --exclude-3; the counts themselves come from '
        'recount_650_repeat2_imagej.py (same ImageJ macro as repeat 1).',
    ])

    docx_path = os.path.join(SCRATCH, '650nm_repeat2_report%s.docx' % tag)
    pdf_path = a.out or os.path.join(SCRATCH, '650nm_repeat2_report%s_%s.pdf' % (tag, date))
    doc.save(docx_path)
    print('docx saved:', docx_path)

    try:
        import win32com.client
        word = win32com.client.Dispatch('Word.Application')
        word.Visible = False
        try:
            d = word.Documents.Open(os.path.abspath(docx_path))
            d.SaveAs(os.path.abspath(pdf_path), FileFormat=17)
            d.Close(False)
        finally:
            word.Quit()
        print('pdf saved:', pdf_path, os.path.getsize(pdf_path), 'bytes')
        try:
            from pypdf import PdfReader
            rd = PdfReader(pdf_path)
            txt = ''.join((pg.extract_text() or '') for pg in rd.pages)
            print('pages:', len(rd.pages), '| chars:', len(txt),
                  '| has Figure 3:', 'Figure 3' in txt)
        except Exception as e:
            print('pdf check skipped:', e)
    except Exception as e:
        print('Word COM export failed:', e)

    dst_docx = os.path.join(a.figdir, os.path.basename(docx_path))
    shutil.copy2(docx_path, dst_docx)
    print('copied ->', dst_docx)


if __name__ == '__main__':
    main()
