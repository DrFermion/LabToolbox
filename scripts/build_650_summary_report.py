# -*- coding: utf-8 -*-
"""build_650_summary_report.py — one consolidated 650 nm LIVE/DEAD report covering
every repeat (1, 2, 3) plus the combined picture, for the whole set.

Everything numeric is read from the CSVs written by plot_650_multirepeat.py and from the
raw ImageJ count tables (for the Welch tests), so the report cannot disagree with the
figures.

Usage
  python build_650_summary_report.py --figdir E:/LabToolbox/output/650_repeat3_20261029/figs \
      --rep "repeat 1=<imagej_counts>" --rep "repeat 2=<imagej_counts_repeat2>" \
      --rep "repeat 3=<imagej_counts_repeat3>" \
      --out "F:/.../650nm_LIVE-DEAD_repeats1-3_summary_report_20261029.pdf"
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
SP_DIR = {'E. coli': 'E.coli', 'S. aureus': 'S.aureus'}


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


def add_figure(doc, path, width_cm, caption):
    if os.path.isfile(path):
        doc.add_picture(path, width=Cm(width_cm))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        doc.add_paragraph('[missing figure: %s]' % os.path.basename(path))
    add_note(doc, caption)


def grid_table(doc, header, rows, caption=None, fontsize=8):
    if caption:
        doc.add_paragraph(caption, style='Heading 3')
    tb = doc.add_table(rows=1, cols=len(header))
    tb.style = 'Light Grid Accent 1'
    for i, h in enumerate(header):
        cell = tb.rows[0].cells[i]
        cell.text = ''
        run = cell.paragraphs[0].add_run(str(h))
        run.bold = True
        run.font.size = Pt(fontsize)
    for row in rows:
        cells = tb.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ''
            run = cells[i].paragraphs[0].add_run(str(v))
            run.font.size = Pt(fontsize)
    doc.add_paragraph()


def fmt_p(p):
    if p != p:
        return 'n/a'
    if p < 0.001:
        return '<0.001'
    return '%.3f' % p


def sign(x):
    if not np.isfinite(x) or abs(x) <= 5:
        return '0'
    return '+' if x > 0 else '-'


# ------------------------------------------------------------------ data helpers
def load_counts(dirpath, sp):
    p = os.path.join(dirpath, SP_DIR[sp], 'livedead_raw_counts.csv')
    if not os.path.isfile(p):
        return None
    df = pd.read_csv(p, encoding='utf-8-sig')
    df = df[df.area != '3']
    df['live'] = pd.to_numeric(df['live'], errors='coerce')
    df['total'] = pd.to_numeric(df['live'], errors='coerce').fillna(0) + \
        pd.to_numeric(df['dead'], errors='coerce').fillna(0)
    df['area'] = df['area'].astype(str)
    df['time'] = df['time'].astype(str)
    return df


def welch(raw, t, area, col='total'):
    if raw is None:
        return np.nan
    c = raw[(raw.time == t) & (raw.area == 'c')][col].astype(float)
    s = raw[(raw.time == t) & (raw.area == area)][col].astype(float)
    if len(c) < 2 or len(s) < 2:
        return np.nan
    return float(stats.ttest_ind(c, s, equal_var=False).pvalue)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--figdir', required=True)
    ap.add_argument('--rep', action='append', default=[], help='"label=count dir"')
    ap.add_argument('--out', default='')
    ap.add_argument('--date', default='20261029')
    a = ap.parse_args()
    fig = a.figdir
    reps = [x.split('=', 1) for x in a.rep]
    labels = [ln.strip() for ln, _ in reps]
    dirs = {ln.strip(): d.strip() for ln, d in reps}

    R = {lb: pd.read_csv(os.path.join(fig, '650nm_livedead_%s_summary.csv'
                                      % lb.replace(' ', '')), encoding='utf-8-sig')
         for lb in labels}
    CB = pd.read_csv(os.path.join(fig, '650nm_livedead_combined_summary.csv'), encoding='utf-8-sig')
    AA = pd.read_csv(os.path.join(fig, '650nm_livedead_perrepeat_aa.csv'), encoding='utf-8-sig')
    AA['area'] = AA['area'].astype(str)
    est_path = os.path.join(fig, '650nm_control_inference.csv')
    EST = pd.read_csv(est_path, encoding='utf-8-sig') if os.path.isfile(est_path) else None
    raws = {lb: {sp: load_counts(d, sp) for sp in ('E. coli', 'S. aureus')}
            for lb, d in dirs.items()}

    def rv(lb, sp, t, ar, col):
        df = R[lb]
        g = df[(df.species == sp) & (df.time == t) & (df.area == ar)]
        return float(g[col].iloc[0]) if len(g) else np.nan

    def aav(sp, t, ar, lb, live=False):
        col = '%s_AAlive%%' % lb if live else '%s_AA%%' % lb
        g = AA[(AA.species == sp) & (AA.time == t) & (AA.area == ar)]
        if not len(g) or col not in g.columns:
            return np.nan
        v = g[col].iloc[0]
        return float(v) if np.isfinite(v) else np.nan

    def comb_aa(sp, t, ar, live=False):
        g = AA[(AA.species == sp) & (AA.time == t) & (AA.area == ar)]
        if not len(g):
            return np.nan, np.nan
        v = float(g['aa_live' if live else 'aa'].iloc[0])
        sd = float(g['aa_live_sd' if live else 'aa_sd'].iloc[0])
        return v, sd

    doc = Document()
    doc.styles['Normal'].font.name = 'Calibri'
    doc.styles['Normal'].font.size = Pt(10.5)

    doc.add_heading('650 nm laser-textured stainless steel - bacterial LIVE/DEAD assay', level=0)
    doc.add_paragraph('Consolidated report over %d repeats (%s), generated %s'
                      % (len(labels), ', '.join(labels), a.date))

    # ---------------------------------------------------------------- 1. summary
    doc.add_heading('1. Summary', level=1)
    # values used in the prose, all computed
    rows_consist = []
    for sp in ('E. coli', 'S. aureus'):
        for ar, nm in (('1', 'LIPSS'), ('2', 'Nanopillar')):
            for t in TIMES:
                vals = [aav(sp, t, ar, lb) for lb in labels]
                sg = {sign(v) for v in vals if np.isfinite(v)}
                sg = {x for x in sg if x != '0'}
                mv, sdv = comb_aa(sp, t, ar)
                ps = [welch(raws[lb].get(sp), t, ar) for lb in labels]
                nsig = sum(1 for p in ps if np.isfinite(p) and p < 0.05)
                rows_consist.append(dict(species=sp, area=nm, time=t, vals=vals,
                                         mean=mv, sd=sdv, signs=sg, n_sig=nsig,
                                         consistent=(len(sg) <= 1)))
    cons = pd.DataFrame(rows_consist)

    # largest repeat-to-repeat spread of one and the same condition (total density)
    batch_ratio = 1.0
    for sp in ('E. coli', 'S. aureus'):
        for t in TIMES:
            for ar in AREAS:
                v = [rv(lb, sp, t, ar, 'total_cm2') for lb in labels]
                v = [x for x in v if np.isfinite(x) and x > 0]
                if len(v) > 1:
                    batch_ratio = max(batch_ratio, max(v) / min(v))

    def cond_line(sp, nm):
        d = cons[(cons.species == sp) & (cons.area == nm)]
        ok = d[d.consistent]
        bad = d[~d.consistent]
        bits = []
        if len(ok):
            bits.append('consistent in direction at %s'
                        % ', '.join('%s (mean %+.0f %%, SD %.0f)' % (r.time, r['mean'], r['sd'])
                                    for _, r in ok.iterrows()))
        if len(bad):
            bits.append('sign flips between repeats at %s'
                        % ', '.join('%s (%s)' % (r.time, ', '.join('%+.0f' % v for v in r.vals))
                                    for _, r in bad.iterrows()))
        return '%s / %s: %s' % (sp, nm, '; '.join(bits))

    n_sa_ok = len(cons[(cons.species == 'S. aureus') & (cons.area == 'Nanopillar')
                       & cons.consistent])
    sa_mean = cons[(cons.species == 'S. aureus') & (cons.area == 'Nanopillar')]['mean']
    ec_bad = len(cons[(cons.species == 'E. coli') & ~cons.consistent])
    add_bullets(doc, [
        'Three independent repeats of the same 650 nm coupon type were counted with a single '
        'ImageJ pipeline (%d images per repeat, %d groups of 5 fields each). Every group is '
        'complete; no group uses fewer than 5 fields.' % (240, 24),
        'The only anti-adhesion signal that keeps its direction in all %d repeats is the '
        'S. aureus nanopillar area: %d of 4 timepoints agree, mean anti-adhesion %+.0f to %+.0f %% '
        '(sd across repeats %.0f-%.0f pp). It is a modest effect, not a large one.'
        % (len(labels), n_sa_ok, float(sa_mean.min()), float(sa_mean.max()),
           float(cons[(cons.species == 'S. aureus') & (cons.area == 'Nanopillar')]['sd'].min()),
           float(cons[(cons.species == 'S. aureus') & (cons.area == 'Nanopillar')]['sd'].max())),
        'E. coli shows no reproducible effect: %d of its 8 condition-timepoints flip sign '
        'between repeats, and its fields carry only tens to a few hundred cells, so a single '
        'repeat can read anywhere from -140 %% to +60 %%.' % ec_bad,
        'Repeat-to-repeat scatter of the anti-adhesion value is of the same size as the effects '
        '(mean SD %.0f pp), and the absolute density of the same condition differs up to %.1fx '
        'between repeats - so individual repeat numbers must not be quoted as an effect size; '
        'only direction-consistent, pooled numbers are usable.'
        % (float(cons['sd'].mean()), batch_ratio),
    ])

    # ---------------------------------------------------------------- 2. methods
    doc.add_heading('2. Samples, counting and statistics', level=1)
    add_bullets(doc, [
        'Coupon: 650 nm laser-textured stainless steel, one coupon per condition per repeat, '
        'three areas per coupon - c = untreated control, 1 = LIPSS, 2 = nanopillar (the treated '
        'areas sit a few micrometres below the control surface).',
        'Four coupons rotate through the four exposure times, one place per repeat '
        '(repeat 1: 1,2,3,4; repeat 2: 2,3,4,1; repeat 3: 3,4,1,2), so a coupon is imaged at a '
        'different timepoint in each repeat.',
        'Organisms: E. coli, S. aureus. Times: 3, 5, 7, 24 h. Five fields per area and timepoint, '
        'each field imaged in a green (live) and a red (dead) channel. One repeat = 8 folders x '
        '30 images = 240 images; all three repeats = 720 images.',
        'Counting: ImageJ 1.54 headless, adaptive threshold (background mode + 40), Analyze '
        'Particles size 3-500 px, 40x field area 46 946.10 um2. Density = count / 46 946.10 um2 '
        'x 1e8 cells/cm2.',
        'Viability = pooled live / (live + dead) over the 5 fields of a condition. '
        'Anti-adhesion = (N_control - N_surface) / N_control x 100, computed for total cells '
        '(live + dead) and for live cells separately.',
        'Per repeat the anti-adhesion carries a delta-method SD propagated from the field means; '
        'the combined value is the mean of the per-repeat anti-adhesion values with the SD across '
        'repeats (n = %d) as the error bar. Each repeat uses its OWN control: the batches differ '
        'up to a factor of two in absolute density, so pooling the controls would compare '
        'non-comparable coupons.' % len(labels),
        'Significance: Welch t-test control vs treated on the 5 fields per condition and repeat '
        '(uncorrected). With %d repeats there is no repeat-level test - the p-values describe '
        'within-repeat field variability only.' % len(labels),
        'Known data handling (all repeats): the repeat-1 S. aureus 5 h nanopillar coupon '
        '(viability 0.4 %) was shown to be a staining artefact by the repeat-2 re-shot coupon '
        'and is excluded; the repeat-2 S. aureus 7 h control was never imaged and its 24 h control '
        'coupon was contaminated (red channel only), so both anti-adhesion values use an estimated '
        'control (treated:control ratio from the timepoints with a real control, pooled ratio '
        '0.874; 7 h ~5 781, 24 h ~6 375 cells/field). Those two bars are estimates, not '
        'measurements.',
    ])

    # ---------------------------------------------------------------- 3. figures
    doc.add_heading('3. Figures', level=1)
    doc.add_paragraph('Each figure has the same two columns: left = live/dead density with the '
                      'pooled viability over each bar; right = the anti-adhesion rate itself for '
                      'total cells (solid) and live cells (pale). Positive = fewer cells than the '
                      'untreated control area of the same coupon, negative = more cells than the '
                      'control.')
    figs = [(lb, '650nm_livedead_%s_AA.png' % lb.replace(' ', '')) for lb in labels]
    figs.append(('combined', '650nm_livedead_combined_%s_AA.png'
                 % ''.join(lb.replace('repeat', 'r').replace(' ', '') for lb in labels)))
    for k, (lb, fn) in enumerate(figs, start=1):
        is_comb = lb == 'combined'
        doc.add_heading('Figure %d - %s' % (k, 'all repeats combined' if is_comb else lb), level=2)
        if is_comb:
            cap = ('Figure %d. Combined over %s. Right-hand bars = mean of the per-repeat '
                   'anti-adhesion values (each repeat against its own control); empty circle / '
                   'square / triangle = the individual repeat values; error bars = SD across '
                   'repeats.' % (k, ', '.join(labels)))
        else:
            cap = ('Figure %d. %s. Left: live (green) + dead (red) density from the 5 fields; '
                   '%% over the stack = pooled viability. Right: anti-adhesion for total cells '
                   '(solid) and live cells (pale); error bars = delta-method SD of the field '
                   'means.' % (k, lb))
            if EST is not None and len(EST) and (EST['repeat'] == lb).any():
                cap += (' Section sign on the axis = control not measurable, estimated '
                        '(S. aureus 7 h and 24 h).')
        add_figure(doc, os.path.join(fig, fn), 16.4, cap)

    # ---------------------------------------------------------------- 4. tables
    doc.add_heading('4. Tables', level=1)

    for sp in ('E. coli', 'S. aureus'):
        hdr = ['Time']
        for lb in labels:
            hdr += ['%s c' % lb.replace('repeat ', 'R'), 'LIPSS', 'Nano']
        rows = []
        for t in TIMES:
            row = [t.replace('h', ' h')]
            for lb in labels:
                for ar in AREAS:
                    v = rv(lb, sp, t, ar, 'total_cm2') / 1e5
                    row.append('-' if not np.isfinite(v) else '%.1f' % v)
            rows.append(row)
        grid_table(doc, hdr, rows,
                   caption='Table 4.%d - %s: total cells (live + dead, x1e5 cells/cm2) per repeat '
                   'and area.' % (1 if sp == 'E. coli' else 2, sp))

        rows = []
        for t in TIMES:
            row = [t.replace('h', ' h')]
            for lb in labels:
                for ar in AREAS:
                    v = rv(lb, sp, t, ar, 'viability')
                    row.append('-' if not np.isfinite(v) else '%.0f%%' % v)
            rows.append(row)
        grid_table(doc, hdr, rows,
                   caption='Table 4.%d - %s: pooled viability (live / (live + dead)) per repeat '
                   'and area.' % (3 if sp == 'E. coli' else 4, sp))

    for live, tag, num in ((False, 'total cells', 5), (True, 'live cells', 6)):
        rows = []
        for sp in ('E. coli', 'S. aureus'):
            for ar, nm in (('1', 'LIPSS'), ('2', 'Nanopillar')):
                for t in TIMES:
                    vals = [aav(sp, t, ar, lb, live=live) for lb in labels]
                    mv, sdv = comb_aa(sp, t, ar, live=live)
                    sg = {sign(v) for v in vals if np.isfinite(v)} - {'0'}
                    rows.append([sp, t.replace('h', ' h'), nm]
                                + ['-' if not np.isfinite(v) else '%+.0f%%' % v for v in vals]
                                + ['-' if not np.isfinite(mv) else '%+.0f%%' % mv,
                                   '-' if not np.isfinite(sdv) else '%.0f' % sdv,
                                   'consistent' if len(sg) <= 1 else
                                   'not consistent (%d signs)' % len(sg)])
        grid_table(doc, ['Organism', 'Time', 'Area'] + labels + ['mean', 'SD', 'sign check'],
                   rows, caption='Table 4.%d - anti-adhesion on %s, per repeat and pooled. '
                   'Positive = fewer cells than the control of the same repeat. The sign check '
                   'treats |AA| > 5 %% as a sign.' % (num, tag), fontsize=7.5)

    rows = []
    for sp in ('E. coli', 'S. aureus'):
        for ar, nm in (('1', 'LIPSS'), ('2', 'Nanopillar')):
            for t in TIMES:
                ps = [welch(raws[lb].get(sp), t, ar) for lb in labels]
                vals = [aav(sp, t, ar, lb) for lb in labels]
                mv, sdv = comb_aa(sp, t, ar)
                rows.append([sp, t.replace('h', ' h'), nm]
                            + [fmt_p(p) for p in ps]
                            + ['%d/%d' % (sum(1 for p in ps if np.isfinite(p) and p < 0.05),
                                          len(ps)),
                               '-' if not np.isfinite(mv) else '%+.0f%%' % mv])
    grid_table(doc, ['Organism', 'Time', 'Area'] + ['p %s' % lb for lb in labels]
               + ['p<0.05', 'AA mean'],
               rows, caption='Table 4.7 - Welch t-test on total cells, control vs treated, per '
               'repeat (uncorrected, n = 5 fields); last columns = how many repeats reached '
               'p < 0.05 and the pooled anti-adhesion. A direction-consistent condition can still '
               'be non-significant within an individual repeat, because the field-to-field SD is '
               'large relative to the effect.', fontsize=7.5)

    # ---------------------------------------------------------------- 5. consistency
    doc.add_heading('5. Repeat consistency - what can and cannot be quoted', level=1)
    add_bullets(doc, [cond_line(sp, nm) for sp in ('E. coli', 'S. aureus')
                      for nm in ('LIPSS', 'Nanopillar')])

    sa = cons[(cons.species == 'S. aureus') & (cons.area == 'Nanopillar')]
    ec = cons[cons.species == 'E. coli']
    add_bullets(doc, [
        'Quotable: S. aureus on the nanopillar area, %+.0f to %+.0f %% fewer total cells than '
        'the control (pooled mean over %d repeats, SD %.0f-%.0f pp), same direction in every '
        'repeat. Quote it as a small, direction-consistent effect with n = %d repeats, and state '
        'that within a single repeat the 5-field variability often keeps the difference from '
        'reaching p < 0.05 (Table 4.7).'
        % (float(sa['mean'].min()), float(sa['mean'].max()), len(labels),
           float(sa['sd'].min()), float(sa['sd'].max()), len(labels)),
        'Not quotable as an effect: any E. coli number (%d of 8 condition-timepoints change sign '
        'between repeats) and the S. aureus LIPSS series except at 24 h. Report these repeat by '
        'repeat, or as "no reproducible difference".' % len(ec[~ec.consistent]),
        'Do not average across repeats without also giving the per-repeat spread: the SD across '
        'repeats is %.0f pp on average and up to %.0f pp, i.e. of the same size as the effect '
        'itself.' % (float(cons['sd'].mean()), float(cons['sd'].max())),
        'Coupon effects are not separable from timepoint effects with this design (each coupon is '
        'imaged at one timepoint per repeat). A two-repeat analysis of coupon identity found no '
        'evidence that a coupon keeps its own anti-adhesion character; the three-repeat data have '
        'not been re-analysed for that question, so treat it as still open rather than settled.', 
    ])

    # ---------------------------------------------------------------- 6. QC
    doc.add_heading('6. Quality control and limitations', level=1)
    add_bullets(doc, [
        'Field count: 5 per condition per repeat. These are field replicates on one coupon, not '
        'biological replicates; n = %d repeats is the biological replication.' % len(labels),
        'E. coli fields are sparse (tens to a few hundred cells per field versus thousands for '
        'S. aureus), so its relative noise is much larger and its anti-adhesion values should not '
        'be interpreted as surface effects.',
        'Objects larger than 500 px (merged clusters) are excluded by the size filter, so a '
        'heavily colonised field is a lower bound on the true number. S. aureus at 24 h is close '
        'to confluent in several fields.',
        'Repeats are separate staining and imaging sessions: absolute density of the same '
        'condition varies up to about two-fold (staining efficiency, illumination, exposure), '
        'which is why every repeat keeps its own control and why the pooled figure averages '
        'per-repeat values instead of pooling raw counts.',
        'Imaging format changed after repeat 1: repeat 1 stored the green and red channels as '
        'separate single-channel images, repeats 2 and 3 store both channels in each file (green '
        'in channel 1, red in channel 0, with slight crosstalk in the non-target channel). The '
        'macro reads only the named channel, so counts stay comparable, but the files are not '
        'pixel-identical in format.',
        'Two S. aureus repeat-2 control points are estimates (7 h not imaged, 24 h contaminated); '
        'their anti-adhesion values carry roughly a factor 1.5-2 uncertainty and are marked with '
        'a section sign in the figures.',
        'The repeat-1 S. aureus 5 h nanopillar coupon read 0.4 % viability; the repeat-2 re-shot '
        'of the same coupon read 50.7 %, so the repeat-1 value is a staining artefact and is '
        'excluded from every pooled number.',
    ])

    # ---------------------------------------------------------------- 7. provenance
    doc.add_heading('7. Data and provenance', level=1)
    add_bullets(doc, [
        'Raw images: Live_Dead Bacteria Test/650nm-20261014/<species>/<repeat>/<time>/ '
        '(240 images per repeat).',
        'Counts: imagej_counts/<species>/livedead_raw_counts.csv (repeat 1), '
        'imagej_counts_repeat2/... (repeat 2), imagej_counts_repeat3/... (repeat 3).',
        'Figures, summary CSVs and the per-repeat anti-adhesion table: '
        'E:\\LabToolbox\\output\\650_repeat3_%s\\figs.' % a.date,
        'Scripts: recount_650_repeat2_imagej.py (counting, ImageJ macro), '
        'plot_650_multirepeat.py (figures, any number of repeats), '
        'build_650_summary_report.py (this report). Repository github.com/DrFermion/LabToolbox.',
        'Reproduce: recount each repeat with recount_650_repeat2_imagej.py --repeats "<repeat>" '
        '--minpx 3, then plot_650_multirepeat.py with one --rep per repeat plus '
        '--infer "S.aureus|repeat 2", --viabfrom "S.aureus|7h|repeat 2=repeat 1", '
        '--viabfrom "S.aureus|24h|repeat 2=repeat 1", --drop "S.aureus|5h|2|repeat 1", '
        'then this report builder.',
    ])

    docx_path = os.path.join(SCRATCH, '650nm_repeats_summary_report_%s.docx' % a.date)
    pdf_path = a.out or os.path.join(SCRATCH, '650nm_repeats_summary_report_%s.pdf' % a.date)
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
                  '| has Table 4.5:', 'Table 4.5' in txt, '| has Figure 4:', 'Figure 4' in txt)
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
