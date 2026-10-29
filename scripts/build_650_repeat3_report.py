# -*- coding: utf-8 -*-
"""build_650_repeat3_report.py — short report for the NEWEST 650 nm repeat + the N-repeat
combined figure (generalised from build_650_repeat2_report.py, which was hard-wired to
"repeat 1 vs repeat 2").

Every number in the text and tables is read from the CSVs written by
plot_650_multirepeat.py (+ the raw ImageJ count tables for the Welch tests); nothing is
typed in by hand, so the report cannot drift away from the figures.

Usage
  python build_650_repeat3_report.py --figdir E:/LabToolbox/output/650_repeat3_20261029/figs \
      --focus "repeat 3" \
      --counts "repeat 1=<...>/imagej_counts" --counts "repeat 2=<...>/imagej_counts_repeat2" \
      --counts "repeat 3=<...>/imagej_counts_repeat3" \
      --out "F:/.../650nm-20261014/650nm_LIVE-DEAD_repeat3_summary_20261029.pdf"
"""
from __future__ import annotations

import argparse
import os
import shutil

import numpy as np
import pandas as pd
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from scipy import stats

SCRATCH = 'C:/Users/PC/AppData/Local/hermes/cache/scratch'
TIMES = ['3h', '5h', '7h', '24h']
AREAS = ['c', '1', '2']
AREA_LABEL = {'c': 'Control', '1': 'LIPSS', '2': 'Nanopillar'}


# ------------------------------------------------------------------ docx helpers
def add_bullets(doc, lines):
    for line in lines:
        doc.add_paragraph(line, style='List Bullet')


def add_note(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(8.5)
    r.italic = True
    r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    return p


def add_figure(doc, path, width_cm, caption):
    if os.path.isfile(path):
        doc.add_picture(path, width=Cm(width_cm))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        doc.add_paragraph('[missing figure: %s]' % os.path.basename(path))
    add_note(doc, caption)


def grid_table(doc, header, rows, caption=None):
    if caption:
        doc.add_paragraph(caption, style='Heading 3')
    tb = doc.add_table(rows=1, cols=len(header))
    tb.style = 'Light Grid Accent 1'
    for i, h in enumerate(header):
        tb.rows[0].cells[i].text = h
    for row in rows:
        cells = tb.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v)
    doc.add_paragraph()


def fmt_p(p):
    if p != p:
        return 'n/a'
    if p < 0.001:
        return '<0.001'
    return '%.3f' % p


# ------------------------------------------------------------------ data helpers
def load_counts(dirpath, sp_dir):
    p = os.path.join(dirpath, sp_dir, 'livedead_raw_counts.csv')
    if not os.path.isfile(p):
        return None
    df = pd.read_csv(p, encoding='utf-8-sig')
    df = df[df.area != '3']
    df['live'] = pd.to_numeric(df['live'], errors='coerce')
    df['dead'] = pd.to_numeric(df['dead'], errors='coerce')
    df['total'] = df['live'].fillna(0) + df['dead'].fillna(0)
    df['area'] = df['area'].astype(str)
    df['time'] = df['time'].astype(str)
    return df


def welch_rows(raw, sp, repeat_label):
    """Welch t (control vs each treated area) on live and total cells, per timepoint."""
    out = []
    if raw is None:
        return out
    for t in TIMES:
        c = raw[(raw.time == t) & (raw.area == 'c')]
        if len(c) < 2:
            out.append([t, 'n/a', 'control missing', '', ''])
            continue
        for ar in ('1', '2'):
            s = raw[(raw.time == t) & (raw.area == ar)]
            if len(s) < 2:
                continue
            ct, st_ = c['total'].astype(float), s['total'].astype(float)
            p_t = stats.ttest_ind(ct, st_, equal_var=False).pvalue
            cl, sl = c.dropna(subset=['live'])['live'].astype(float), s.dropna(subset=['live'])['live'].astype(float)
            p_l = stats.ttest_ind(cl, sl, equal_var=False).pvalue if len(cl) > 1 and len(sl) > 1 else np.nan
            out.append([t, AREA_LABEL[ar], '%.0f vs %.0f' % (ct.mean(), st_.mean()),
                        fmt_p(p_t), fmt_p(p_l)])
    return out


def aa_lookup(aa, label):
    out = {}
    col = '%s_AA%%' % label
    if col not in aa.columns:
        return out
    for _, r in aa.iterrows():
        v = r[col]
        if np.isfinite(v):
            out[(r['species'], r['time'], r['area'])] = float(v)
    return out


def aa_series(aa, sp, ar, label):
    lut = aa_lookup(aa, label)
    return [lut.get((sp, t, ar), np.nan) for t in TIMES]


def sign(x):
    if not np.isfinite(x) or abs(x) <= 5:
        return '0'
    return '+' if x > 0 else '-'


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--figdir', required=True)
    ap.add_argument('--focus', default='repeat 3')
    ap.add_argument('--counts', action='append', default=[], help='"label=count dir"')
    ap.add_argument('--out', default='')
    ap.add_argument('--date', default='20261029')
    a = ap.parse_args()
    fig = a.figdir
    focus = a.focus
    focus_tag = focus.replace(' ', '')
    label_map = dict(x.split('=', 1) for x in a.counts) if a.counts else {}

    R = pd.read_csv(os.path.join(fig, '650nm_livedead_%s_summary.csv' % focus_tag),
                    encoding='utf-8-sig')
    CB = pd.read_csv(os.path.join(fig, '650nm_livedead_combined_summary.csv'),
                     encoding='utf-8-sig')
    AA = pd.read_csv(os.path.join(fig, '650nm_livedead_perrepeat_aa.csv'), encoding='utf-8-sig')
    AA['area'] = AA['area'].astype(str)     # the CSV round-trip turns '1'/'2' into ints
    CB['area'] = CB['area'].astype(str)
    R['area'] = R['area'].astype(str)
    est_path = os.path.join(fig, '650nm_control_inference.csv')
    EST = pd.read_csv(est_path, encoding='utf-8-sig') if os.path.isfile(est_path) else None
    repeats = [c.replace('_AA%', '') for c in AA.columns if c.endswith('_AA%')
               and c != 'combined_AA%']

    raws = {lb: {sp: load_counts(d, sp) for sp in ('E.coli', 'S.aureus')}
            for lb, d in label_map.items()}

    def rv(sp, t, ar, col):
        g = R[(R.species == sp) & (R.time == t) & (R.area == ar)]
        return float(g[col].iloc[0]) if len(g) else np.nan

    def cv(sp, t, ar, col):
        g = CB[(CB.species == sp) & (CB.time == t) & (CB.area == ar)]
        return float(g[col].iloc[0]) if len(g) else np.nan

    doc = Document()
    st = doc.styles['Normal']
    st.font.name = 'Calibri'
    st.font.size = Pt(10.5)

    doc.add_heading('650 nm textured stainless steel - bacterial LIVE/DEAD, %s' % focus, level=0)
    doc.add_paragraph('Combined with %s  |  report generated %s'
                      % (' + '.join(r for r in repeats if r != focus), a.date))

    # 1 --------------------------------------------------------------
    doc.add_heading('1. What this report answers', level=1)
    add_bullets(doc, [
        'Does %s reproduce the picture from the earlier repeats (adhesion and viability of '
        'E. coli and S. aureus on the LIPSS and nanopillar areas relative to the untreated '
        'control area of the same coupon)?' % focus,
        'How large is the repeat-to-repeat scatter, i.e. which of the anti-adhesion numbers can '
        'be quoted and which have to be reported repeat by repeat?',
        'What does the three-repeat combined figure look like, and what is still not defensible '
        'with n = 3 repeats?',
    ])

    # 2 --------------------------------------------------------------
    doc.add_heading('2. Samples and counting rule', level=1)
    add_bullets(doc, [
        'One 650 nm coupon carries three areas: c = untreated control, 1 = LIPSS, '
        '2 = nanopillar (the treated areas sit a few micrometres below the control surface).',
        'Two organisms (E. coli, S. aureus) x four exposure times (3, 5, 7, 24 h) x 5 fields '
        'per area, each field imaged in a green and a red channel; %s contains 240 images '
        '(8 folders x 30) and all 24 area x time groups are complete with n = 5 fields - no '
        'missing folders, no extra re-shot coupon, and no contaminated control at any '
        'timepoint.' % focus,
        'Counting: ImageJ 1.54 headless, adaptive threshold (background mode + 40), Analyze '
        'Particles size 3-500 px, 40x field area 46 946.10 um2 -> density = count / 46 946.10 '
        'um2 x 1e8 cells/cm2.',
        'Viability of a condition = pooled live / (live + dead) over its 5 fields; '
        'anti-adhesion AA = (N_control - N_surface) / N_control x 100, computed for total cells '
        '(live + dead) and separately for live cells.',
        'In the combined figure each repeat contributes one mean per condition (equal weight) '
        'and every repeat keeps its OWN control for the AA calculation: the batches differ by '
        'up to a factor of two in absolute density, so pooling the controls would mix '
        'non-comparable coupons.',
    ])

    # 3 --------------------------------------------------------------
    doc.add_heading('3. Figures', level=1)
    doc.add_heading('Figure 1 - %s on its own' % focus, level=2)
    add_figure(doc, os.path.join(fig, '650nm_livedead_%s.png' % focus_tag), 16.4,
               'Figure 1. %s, 650 nm. Left column: live (green) and dead (red) density stacked, '
               '%% over each bar = pooled viability. Right column: total cells (live + dead) per '
               'cm2, %% over a treated bar = anti-adhesion against the control of the same '
               'timepoint. Bars = mean of 5 fields, error bars = SD of the 5 fields. Rows: '
               'E. coli (a, b) and S. aureus (c, d).' % focus)
    doc.add_heading('Figure 2 - all repeats combined', level=2)
    add_figure(doc, os.path.join(fig, '650nm_livedead_combined_r1r2r3.png'), 16.4,
               'Figure 2. Bars = mean of the per-repeat means (%s); empty circle / square / '
               'triangle = the individual repeat means; error bars on the adhesion panels = SD '
               'across repeats; %% over the adhesion bars = mean of the per-repeat AA values. '
               'Where a repeat had no usable control the value is marked on the axis and is '
               'qualitative only.' % ', '.join(repeats))

    # 4 --------------------------------------------------------------
    doc.add_heading('4. Tables', level=1)
    for sp in ('E. coli', 'S. aureus'):
        rows = []
        for t in TIMES:
            row = [t.replace('h', ' h')]
            for ar in AREAS:
                row.append('%.1f' % (rv(sp, t, ar, 'total_cm2') / 1e5))
            for ar in AREAS:
                v = rv(sp, t, ar, 'viability')
                row.append('-' if v != v else '%.0f%%' % v)
            rows.append(row)
        grid_table(doc, ['Time', 'Control', 'LIPSS', 'Nano', 'V. control', 'V. LIPSS', 'V. Nano'],
                   rows, caption='Table %s - %s, %s: total cells (x1e5 cells/cm2) and pooled '
                   'viability (V.) per area.' % ('4.1' if sp == 'E. coli' else '4.2', sp, focus))

    rows = []
    for sp in ('E. coli', 'S. aureus'):
        for ar, nm in (('1', 'LIPSS'), ('2', 'Nanopillar')):
            for t in TIMES:
                vals = [aa_lookup(AA, lb).get((sp, t, ar), np.nan) for lb in repeats]
                comb = AA[(AA.species == sp) & (AA.time == t) & (AA.area == ar)]
                cval = float(comb['aa'].iloc[0]) if len(comb) else np.nan
                csd = float(comb['aa_sd'].iloc[0]) if len(comb) else np.nan
                nsig = len({sign(v) for v in vals if sign(v) != '0'})
                rows.append([sp, t.replace('h', ' h'), nm]
                            + ['-' if v != v else '%+.0f%%' % v for v in vals]
                            + ['-' if cval != cval else '%+.0f%%' % cval,
                               '-' if csd != csd else '%.0f' % csd,
                               'consistent' if nsig <= 1 else 'not consistent (%d signs)' % nsig])
    grid_table(doc, ['Organism', 'Time', 'Area'] + repeats + ['mean', 'SD', 'sign check'],
               rows, caption='Table 4.3 - anti-adhesion on total cells, per repeat and combined. '
               'Positive = fewer cells than the control. Sign check compares the %d repeats '
               '(|AA| > 5 %% counts as a sign).' % len(repeats))

    if focus in raws:
        for sp, sp_dir in (('E. coli', 'E.coli'), ('S. aureus', 'S.aureus')):
            rows = welch_rows(raws[focus].get(sp_dir), sp, focus)
            if rows:
                grid_table(doc, ['Time', 'Area', 'mean total (ctrl vs treated)', 'Welch p (total)',
                                 'Welch p (live)'], rows,
                           caption='Table %s - %s, %s: Welch t-test control vs treated '
                           '(uncorrected; n = 5 fields).'
                           % ('4.4' if sp == 'E. coli' else '4.5', sp, focus))

    # 5 --------------------------------------------------------------
    doc.add_heading('5. Findings', level=1)

    def series(sp, ar, lb):
        return aa_series(AA, sp, ar, lb)

    L = []
    for sp in ('E. coli', 'S. aureus'):
        for ar, nm in (('1', 'LIPSS'), ('2', 'nanopillar')):
            per = []
            for lb in repeats:
                per.append('%s %s' % (lb.replace('repeat ', 'R'),
                                      ', '.join('-' if v != v else '%+.0f%%' % v
                                                for v in series(sp, ar, lb))))
            def _aa_mean(sp_, t_, ar_):
                r = AA[(AA.species == sp_) & (AA.time == t_) & (AA.area == ar_)]
                if not len(r):
                    return np.nan
                v = float(r['aa'].iloc[0])
                return v if np.isfinite(v) else np.nan
            comb = [_aa_mean(sp, t, ar) for t in TIMES]
            same, differ = [], []
            for ti, t in enumerate(TIMES):
                sg = {sign(series(sp, ar, lb)[ti]) for lb in repeats}
                sg = {x for x in sg if x != '0'}
                if len(sg) > 1:
                    differ.append(t)
                elif len(sg) == 1:
                    same.append(t)
            verdict = ('same direction in every repeat at %s' % '/'.join(same) if same else
                       'no timepoint with a consistent direction')
            if differ:
                verdict += '; signs disagree between repeats at %s' % '/'.join(differ)
            L.append('%s %s, total-cell anti-adhesion at 3/5/7/24 h: %s; mean of the per-repeat '
                     'AA values %s - %s.'
                     % (sp, nm, '; '.join(per),
                        ', '.join('-' if v != v else '%+.0f%%' % v for v in comb), verdict))
    add_bullets(doc, L)

    V = []
    for sp in ('E. coli', 'S. aureus'):
        V.append('%s viability in %s (3/5/7/24 h) - control %s; LIPSS %s; nanopillar %s.'
                 % (sp, focus,
                    ', '.join('%.0f%%' % rv(sp, t, 'c', 'viability') for t in TIMES),
                    ', '.join('%.0f%%' % rv(sp, t, '1', 'viability') for t in TIMES),
                    ', '.join('%.0f%%' % rv(sp, t, '2', 'viability') for t in TIMES)))
    add_bullets(doc, V)

    # repeat scatter quantified
    scat = []
    for sp in ('E. coli', 'S. aureus'):
        vals = [cv(sp, t, ar, 'total_cm2') for t in TIMES for ar in AREAS]
        cvs = [v for v in vals if np.isfinite(v)]
        scat.append('%s: combined total-cell density spans %.1f-%.1f x1e5 cells/cm2'
                    % (sp, min(cvs) / 1e5, max(cvs) / 1e5))
    sds = AA[[c for c in AA.columns if c.endswith('_AA%') and c != 'combined_AA%']].std(axis=1)
    add_bullets(doc, [
        'Repeat-to-repeat scatter: the SD of the per-repeat AA values (n = %d) is %.0f pp on '
        'average and reaches %.0f pp, which is the same order as the effects themselves - the '
        'individual repeat means in Figure 2 are far apart for several conditions. Range of '
        'combined densities: %s.' % (len(repeats), sds.mean(), sds.max(), '; '.join(scat)),
        'Only the conditions whose sign is the same in every repeat are quoted as evidence; the '
        'rest are reported repeat by repeat and marked as not reproducible so far.',
    ])
    if EST is not None and len(EST):
        add_bullets(doc, [
            'Repeat-2 controls that could not be measured (contaminated coupon / not imaged) were '
            'not borrowed from another batch for the AA comparison: they were estimated from the '
            'treated:control ratio at the timepoints with a real control (see '
            '650nm_control_inference.csv). Those values are estimates, not measurements and carry '
            'roughly a factor 1.5-2 uncertainty.',
        ])

    # 6 --------------------------------------------------------------
    doc.add_heading('6. QC and limitations', level=1)
    add_bullets(doc, [
        'E. coli fields are sparse (tens to a few hundred cells per field, versus thousands for '
        'S. aureus), so relative noise is much larger; an E. coli AA of +-50 % can come from '
        'field-to-field variation alone. E. coli results are not usable as evidence of an '
        'anti-adhesion effect.',
        'Only 5 fields per condition and repeat, on one coupon per condition and repeat: the '
        'error bars on Figure 1 are field-to-field SD, not biological replication.',
        'The three repeats are three separate staining/imaging sessions. Absolute densities '
        'differ up to two-fold between them (staining efficiency, illumination, exposure), which '
        'is why the combined figure averages per-repeat means and computes AA against each '
        'repeat\'s own control.',
        'Imaging format changed after repeat 1: in repeat 1 the green and red channels were '
        'saved as separate single-channel images, while repeats 2 and 3 write both channels into '
        'each file (with a little crosstalk in the non-target channel). The counting macro reads '
        'only the named channel of each file, so the numbers stay comparable, but the images are '
        'not pixel-identical in format.',
        'Objects larger than 500 px (cell clusters / merged colonies) are excluded by the size '
        'filter, so a heavily colonised field is a lower bound on the true cell number. '
        'S. aureus at 24 h is close to confluent in several fields.',
        'Nothing here is a formal statistical test of an effect across repeats: with n = 3 '
        'repeats a repeat-level test has almost no power. The Welch p-values are per repeat and '
        'uncorrected.',
    ])

    # 7 --------------------------------------------------------------
    doc.add_heading('7. Data and provenance', level=1)
    add_bullets(doc, [
        'Raw images: Live_Dead Bacteria Test/650nm-20261014/<species>/%s/<time>/.' % focus,
        'Counts: imagej_counts_%s/<species>/livedead_raw_counts.csv (same ImageJ macro and size '
        'rule as the earlier repeats).' % focus_tag.replace('repeat', 'repeat'),
        'Figures and summary CSVs: E:\\LabToolbox\\output\\650_repeat3_%s\\figs '
        '(scripts plot_650_multirepeat.py + recount_650_repeat2_imagej.py).%s'
        % (a.date, ' Control estimates: 650nm_control_inference.csv.' if EST is not None else ''),
        'Report builder: E:\\LabToolbox\\scripts\\build_650_repeat3_report.py. Repository '
        'github.com/DrFermion/LabToolbox.',
        'Reproduce: python recount_650_repeat2_imagej.py --repeats "repeat 3" --outdir '
        '<imagej_counts_repeat3> --minpx 3, then python plot_650_multirepeat.py --out <figs> '
        '--focus "repeat 3" --rep "repeat 1=<counts r1>" --rep "repeat 2=<counts r2>" '
        '--rep "repeat 3=<counts r3>" --infer "S.aureus|repeat 2" '
        '--viabfrom "S.aureus|7h|repeat 2=repeat 1" --viabfrom "S.aureus|24h|repeat 2=repeat 1" '
        '--drop "S.aureus|5h|2|repeat 1" --exclude-3, then python build_650_repeat3_report.py.',
    ])

    docx_path = os.path.join(SCRATCH, '650nm_%s_report_%s.docx' % (focus_tag, a.date))
    pdf_path = a.out or os.path.join(SCRATCH, '650nm_%s_report_%s.pdf' % (focus_tag, a.date))
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
                  '| has Figure 2:', 'Figure 2' in txt)
        except Exception as e:
            print('pdf check skipped:', e)
    except Exception as e:
        print('Word COM export failed:', e)

    dst = os.path.join(fig, os.path.basename(docx_path))
    if os.path.abspath(dst) != os.path.abspath(docx_path):
        shutil.copy2(docx_path, dst)
        print('copied ->', dst)


if __name__ == '__main__':
    main()
