# -*- coding: utf-8 -*-
"""analyze_650_batch2.py — 650 nm LIVE/DEAD, batch B (dataset 650nm-20261111).

Treatment of the data
---------------------
* Batch B is analysed on its own two repeats (repeat 1, repeat 2); the previous
  dataset (650nm-20261014, repeats 1-4) is kept as batch A and only used for a
  cross-batch comparability section.
* Area codes: c = control, 1 = LIPSS, 2 = nanopillar.  Area code 3 exists only in
  S. aureus / repeat 2 / 24 h and is **another nanopillar coupon**: it is kept out
  of every batch statistic and compared one-to-one with area 2 of the same block.
* One documented exclusion: S. aureus 3 h LIPSS in both repeats is an acquisition
  artefact (sub-cell speckle; 7 000-8 900 objects per field with a median object
  area of 27-66 px in repeat 1, and 1 750-2 120 red-channel objects at 39-48 px in
  repeat 2, against 380-750 objects at 69-107 px in the control and nanopillar
  areas of the same sessions).  All other conditions are used as measured.

Outputs -> --outdir
  batchB_raw_counts_used.csv      per-field table actually used (with flags)
  batchB_condition_summary.csv    per repeat x species x time x area
  batchB_antiadhesion.csv         per-condition AA with cross-repeat mean/SD
  batchB_coupon3_vs_2.csv         the extra nanopillar coupon comparison
  batchB_vs_batchA.csv            control level + AA comparison between batches
  figures/*.png

Usage:
  env -u PYTHONPATH C:/Users/PC/miniconda3/python.exe scripts/analyze_650_batch2.py
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
from scipy import stats

DS_B = ('F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - '
        'Ruinong Pan_Antibacterial Surfaces/Live_Dead Bacteria Test/650nm-20261111')
DS_A = ('F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - '
        'Ruinong Pan_Antibacterial Surfaces/Live_Dead Bacteria Test/650nm-20261014')
OUT = 'E:/LabToolbox/output/650_batch2_20261112_min15'
FIG = os.path.join(OUT, 'figures')
AREA_UM2 = 46946.10
K_CM2 = 1e8 / AREA_UM2
TIMES = ['3h', '5h', '7h', '24h']
REGION = {'c': 'Control', '1': 'LIPSS', '2': 'Nanopillar', '3': 'Nanopillar (extra coupon)'}
SPECIES = [('E.coli', 'E. coli'), ('S.aureus', 'S. aureus')]

# documented exclusion: (species, repeat, time, area, issue, detail)
EXCLUSIONS = [
    ('S. aureus', 'repeat 1', '3h', '1', 'acquisition anomaly on the LIPSS coupon',
     '8 875 / 7 005 / 7 540 / 7 334 / 7 589 objects per field with median object '
     'area 27-71 px (green 3 623-4 835, red 3 078-4 040) at exposure 0.40-0.50 s, '
     'against 662-885 objects at 69-107 px in the control and nanopillar areas of '
     'the same 3 h session at 0.20 s.  The objects are sub-cell speckle, not cocci.'),
    ('S. aureus', 'repeat 2', '3h', '1', 'acquisition anomaly on the LIPSS coupon',
     'red channel carries 1 751-2 118 objects per field with median area 39-48 px, '
     'against 77-95 objects in the control of the same session, while the green '
     'channel is normal (333-455 objects).  Dead count is therefore an artefact and '
     'the viability of this cell is meaningless.'),
]


def load(path):
    df = pd.read_csv(path, encoding='utf-8-sig')
    df['area'] = df['area'].astype(str)
    df['time'] = df['time'].astype(str)
    return df


def condition_table(df):
    rows = []
    for sp, sp_label in SPECIES:
        d = df[df.species == sp_label]
        for rep in sorted(d['repeat'].unique()):
            for t in TIMES:
                for ar in ['c', '1', '2']:
                    g = d[(d['repeat'] == rep) & (d.time == t) & (d.area == ar)]
                    g = g.dropna(subset=['live', 'dead'])
                    if g.empty:
                        continue
                    rows.append(dict(
                        species=sp_label, repeat=rep, time=t, area=ar,
                        region=REGION[ar], n_fields=len(g),
                        live_mean=g.live.mean(), live_sd=g.live.std(ddof=1),
                        dead_mean=g.dead.mean(), dead_sd=g.dead.std(ddof=1),
                        total_mean=g.total.mean(), total_sd=g.total.std(ddof=1),
                        viability_pooled=g.live.sum() / g.total.sum() * 100,
                        live_cm2=g.live.mean() * K_CM2,
                        total_cm2=g.total.mean() * K_CM2))
    return pd.DataFrame(rows)


def aa_table(cond):
    """AA per repeat (against that repeat's own control) + cross-repeat summary."""
    rows = []
    for sp in ['E. coli', 'S. aureus']:
        for t in TIMES:
            ctrl = cond[(cond.species == sp) & (cond.time == t) & (cond.area == 'c')]
            if ctrl.empty:
                continue
            for ar in ['1', '2']:
                rec = dict(species=sp, time=t, area=ar, region=REGION[ar])
                for _, c in ctrl.iterrows():
                    a = cond[(cond.species == sp) & (cond.time == t) &
                             (cond.area == ar) & (cond.repeat == c['repeat'])]
                    if a.empty:
                        continue
                    a = a.iloc[0]
                    aa = (c.total_mean - a.total_mean) / c.total_mean * 100
                    aa_sd = np.sqrt((a.total_sd / c.total_mean) ** 2 +
                                    (a.total_mean * c.total_sd / c.total_mean ** 2) ** 2) * 100
                    aal = (c.live_mean - a.live_mean) / c.live_mean * 100
                    tag = c['repeat'].replace('repeat ', 'r')
                    rec[f'{tag}_AA'] = aa
                    rec[f'{tag}_AA_sd'] = aa_sd
                    rec[f'{tag}_AAlive'] = aal
                vals = [rec.get(f'{r.replace("repeat ", "r")}_AA')
                        for r in sorted(cond['repeat'].unique())]
                vals = [v for v in vals if v is not None and not pd.isna(v)]
                live_vals = [rec.get(f'{r.replace("repeat ", "r")}_AAlive')
                             for r in sorted(cond['repeat'].unique())]
                live_vals = [v for v in live_vals if v is not None and not pd.isna(v)]
                rec['AA_mean'] = float(np.mean(vals)) if vals else np.nan
                rec['AA_sd_across_repeats'] = float(np.std(vals, ddof=1)) if len(vals) > 1 else np.nan
                rec['AAlive_mean'] = float(np.mean(live_vals)) if live_vals else np.nan
                rec['n_repeats'] = len(vals)
                rec['signs'] = ('same' if len(vals) > 1 and len(set(np.sign(vals))) == 1 else
                                ('mixed' if len(vals) > 1 else 'single'))
                rows.append(rec)
    cols = ['species', 'time', 'area', 'region']
    df = pd.DataFrame(rows)
    other = [c for c in df.columns if c not in cols]
    return df[cols + sorted(other, key=lambda c: (c not in ('AA_mean', 'AA_sd_across_repeats',
                                                            'AAlive_mean', 'n_repeats', 'signs'), c))]


def coupon3(df):
    d = df[(df.species == 'S. aureus') & (df['repeat'] == 'repeat 2') & (df.time == '24h')]
    out = {}
    for ar in ['c', '2', '3']:
        g = d[d.area == ar].dropna(subset=['live', 'dead'])
        out[ar] = g
    rows = []
    for ar, g in out.items():
        rows.append(dict(area=ar, region=REGION[ar], n_fields=len(g),
                         live_mean=g.live.mean(), dead_mean=g.dead.mean(),
                         total_mean=g.total.mean(), total_sd=g.total.std(ddof=1),
                         viability=g.live.sum() / g.total.sum() * 100,
                         total_cm2=g.total.mean() * K_CM2))
    summ = pd.DataFrame(rows)
    ctrl = summ[summ.area == 'c'].total_mean.iloc[0]
    summ['AA_vs_control_pct'] = (ctrl - summ.total_mean) / ctrl * 100
    # extra coupon vs the original nanopillar coupon of the same block
    a2, a3 = out['2'], out['3']
    t_tot = stats.ttest_ind(a2.total, a3.total, equal_var=False)
    t_dead = stats.ttest_ind(a2.dead / a2.total, a3.dead / a3.total, equal_var=False)
    test = pd.DataFrame([
        dict(comparison='extra coupon (3) vs nanopillar (2)',
             variable='total cells per field', value_2=a2.total.mean(),
             value_3=a3.total.mean(), difference_pct=(a3.total.mean() - a2.total.mean()) /
             a2.total.mean() * 100, t=float(t_tot.statistic), p=float(t_tot.pvalue)),
        dict(comparison='extra coupon (3) vs nanopillar (2)',
             variable='dead fraction of cells', value_2=(a2.dead / a2.total).mean(),
             value_3=(a3.dead / a3.total).mean(),
             difference_pct=np.nan, t=float(t_dead.statistic), p=float(t_dead.pvalue)),
    ])
    return summ, test


def batch_compare(aa):
    """Batch A (650nm-20261014, 4 repeats, its own exclusion registry) vs batch B.

    Batch A numbers are taken from the delivered per-repeat AA table and combined
    summary so that this comparison uses exactly the values that were reported
    before, not a re-derivation with different exclusion rules.
    """
    pa = pd.read_csv(os.path.join(DS_A, '650nm_livedead_perrepeat_aa.csv'),
                     encoding='utf-8-sig')
    pa['area'] = pa['area'].astype(str)
    ca = pd.read_csv(os.path.join(DS_A, '650nm_livedead_combined_summary.csv'),
                     encoding='utf-8-sig')
    ca['area'] = ca['area'].astype(str)
    rows = []
    for sp in ['E. coli', 'S. aureus']:
        for t in TIMES:
            for ar in ['c', '1', '2']:
                ca_row = ca[(ca.species == sp) & (ca.time == t) & (ca.area == ar)]
                a_aa = pa[(pa.species == sp) & (pa.time == t) & (pa.area == ar)]
                b_aa = aa[(aa.species == sp) & (aa.time == t) & (aa.area == ar)]
                rows.append(dict(
                    species=sp, time=t, area=ar, region=REGION[ar],
                    batchA_total_cm2=ca_row.total_cm2.iloc[0] if len(ca_row) else np.nan,
                    batchA_sd_cm2=ca_row.total_cm2_sd.iloc[0] if len(ca_row) else np.nan,
                    batchA_n_repeats=int(ca_row.n.iloc[0]) if len(ca_row) else 0,
                    batchA_AA=a_aa.aa.iloc[0] if len(a_aa) else np.nan,
                    batchA_AA_sd=a_aa.aa_sd.iloc[0] if len(a_aa) else np.nan,
                    batchA_AA_n=int(a_aa.n_aa.iloc[0]) if len(a_aa) else 0,
                    batchB_AA=b_aa.AA_mean.iloc[0] if len(b_aa) else np.nan,
                    batchB_AA_sd=b_aa.AA_sd_across_repeats.iloc[0] if len(b_aa) else np.nan,
                    batchB_AA_n=int(b_aa.n_repeats.iloc[0]) if len(b_aa) else 0,
                ))
    df = pd.DataFrame(rows)
    df['same_sign'] = np.where(
        df.batchA_AA.isna() | df.batchB_AA.isna(), '',
        np.where(np.sign(df.batchA_AA) == np.sign(df.batchB_AA), 'same', 'opposite'))
    return df


def fig_stacked(cond):
    """Live and dead densities as *grouped* bars: a stacked bar on a log axis is
    not additive and would misrepresent the live/dead split."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(11, 8.6))
    for ax, sp in zip(axes, ['E. coli', 'S. aureus']):
        labels, live, dead, viab, excl = [], [], [], [], []
        for t in TIMES:
            for ar in ['c', '1', '2']:
                g = cond[(cond.species == sp) & (cond.time == t) & (cond.area == ar)]
                labels.append(t + '\n' + REGION[ar][:5])
                if g.empty:
                    live.append(np.nan); dead.append(np.nan); viab.append(np.nan)
                    excl.append(True)
                    continue
                excl.append(False)
                live.append((g.live_mean * K_CM2).mean())
                dead.append((g.dead_mean * K_CM2).mean())
                viab.append(g.viability_pooled.mean())
        x = np.arange(len(labels))
        w = 0.36
        ax.bar(x - w / 2, live, width=w, color='#2e9e5b', label='Live (SYTO 9)')
        ax.bar(x + w / 2, dead, width=w, color='#c0392b', label='Dead (PI)')
        for xi, (li, de, v, ex) in enumerate(zip(live, dead, viab, excl)):
            if ex:
                ax.text(xi, 1.5e5, 'excluded (artefact)', ha='center', va='bottom',
                        fontsize=6.5, rotation=90, color='0.45')
                continue
            ax.text(xi, max(li, de) * 1.9, '%.0f%%' % v, ha='center', va='bottom',
                    fontsize=7, color='0.25')
        ax.set_yscale('log')
        ax.set_ylim(3e3, 5e8)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7)
        ax.set_ylabel('cells cm$^{-2}$')
        ax.set_title(sp + ' — batch B (650 nm, 20261111); mean of 2 repeats, 5 fields each',
                     fontsize=10)
        ax.legend(frameon=False, fontsize=8, loc='upper left', ncol=2)
        ax.grid(axis='y', ls=':', lw=0.5, alpha=0.6)
    fig.text(0.01, 0.005, 'Grouped bars (not stacked) because the y axis is logarithmic. '
             'Percentage above each pair = pooled viability (live/(live+dead)). '
             'S. aureus 3 h LIPSS excluded: sub-cell speckle, see the QC figure.',
             fontsize=7, color='0.35')
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    p = os.path.join(FIG, 'batchB_livedead_density.png')
    fig.savefig(p, dpi=220)
    plt.close(fig)
    return p


def fig_aa(aa):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    for ax, sp in zip(axes, ['E. coli', 'S. aureus']):
        d = aa[aa.species == sp]
        labels, vals, errs, marks = [], [], [], []
        for t in TIMES:
            for ar in ['1', '2']:
                g = d[(d.time == t) & (d.area == ar)]
                if g.empty:
                    continue
                labels.append(f'{t}\n{REGION[ar][:5]}')
                vals.append(g.AA_mean.iloc[0])
                errs.append(g.AA_sd_across_repeats.iloc[0] if g.n_repeats.iloc[0] > 1 else 0)
                r = g.iloc[0]
                marks.append([r.get('r1_AA'), r.get('r2_AA')])
        x = np.arange(len(labels))
        cols = ['#1f6fb4' if 'LIPSS' in l else '#b5651d' for l in labels]
        ax.bar(x, vals, color=cols, alpha=0.85)
        ax.errorbar(x, vals, yerr=errs, fmt='none', ecolor='0.25', capsize=3, lw=1)
        for xi, m in enumerate(marks):
            for k, v in enumerate([v for v in m if v is not None and not pd.isna(v)]):
                ax.plot(xi + (k - 0.5) * 0.22, v, marker='o' if k == 0 else 's',
                        ms=3.5, mfc='none', mec='k', mew=0.7)
        ax.axhline(0, color='k', lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7)
        ax.set_title(f'{sp} — anti-adhesion, batch B')
        ax.set_ylabel('AA vs own control (%)')
        ax.grid(axis='y', ls=':', lw=0.5, alpha=0.6)
    fig.text(0.01, 0.01, 'Positive = fewer cells than the control. Bars = mean of two repeats '
             '(each computed against its own control); error bars = SD across repeats; '
             'open circles/squares = repeat 1 / repeat 2.', fontsize=7, color='0.35')
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    p = os.path.join(FIG, 'batchB_antiadhesion.png')
    fig.savefig(p, dpi=220)
    plt.close(fig)
    return p


def fig_coupon3(df):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    d = df[(df.species == 'S. aureus') & (df['repeat'] == 'repeat 2') & (df.time == '24h')]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2))
    for ax, (col, ylab) in zip(axes, [('total', 'total cells per field'),
                                      ('dead_rate', 'dead fraction')]):
        data = [d[d.area == ar][col].dropna().values for ar in ['c', '2', '3']]
        bp = ax.boxplot(data, widths=0.5, patch_artist=True)
        for patch, colr in zip(bp['boxes'], ['#7f8c8d', '#b5651d', '#8e44ad']):
            patch.set_facecolor(colr)
            patch.set_alpha(0.55)
        for i, vals in enumerate(data, start=1):
            ax.plot(np.full(len(vals), i) + np.random.default_rng(1).normal(0, 0.045, len(vals)),
                    vals, 'o', ms=4, mfc='none', mec='k', mew=0.7)
        ax.set_xticks([1, 2, 3])
        ax.set_xticklabels(['Control', 'Nanopillar\n(coupon 2)', 'Nanopillar\n(extra coupon 3)'],
                           fontsize=8)
        ax.set_ylabel(ylab)
        ax.grid(axis='y', ls=':', lw=0.5, alpha=0.6)
    fig.suptitle('S. aureus, repeat 2, 24 h — extra nanopillar coupon 3 vs coupon 2', fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    p = os.path.join(FIG, 'batchB_coupon3_vs_2.png')
    fig.savefig(p, dpi=220)
    plt.close(fig)
    return p


def fig_cross_batch(cmp_ba):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    d = cmp_ba[(cmp_ba.area != 'c') & cmp_ba.batchA_AA.notna() & cmp_ba.batchB_AA.notna()]
    fig, ax = plt.subplots(figsize=(5.6, 5.2))
    markers = {'E. coli': 'o', 'S. aureus': 's'}
    colours = {'1': '#1f6fb4', '2': '#b5651d'}
    for _, r in d.iterrows():
        ax.scatter(r.batchA_AA, r.batchB_AA, marker=markers[r.species], s=46,
                   facecolor=colours[str(r.area)] if r.same_sign == 'same' else 'none',
                   edgecolor='k', linewidth=0.8)
        ax.annotate('%s %s %s' % (r.species.split()[0][0] + '. ' + r.species.split()[1],
                                  r.time, REGION[str(r.area)][:4]),
                    (r.batchA_AA, r.batchB_AA), textcoords='offset points', xytext=(4, 3),
                    fontsize=5.5, color='0.3')
    ax.axhline(0, color='k', lw=0.8)
    ax.axvline(0, color='k', lw=0.8)
    lim = [-90, 90]
    ax.plot(lim, lim, ls='--', lw=0.8, color='0.5')
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel('batch A anti-adhesion (%, 4 repeats)')
    ax.set_ylabel('batch B anti-adhesion (%, 2 repeats)')
    ax.set_title('Same condition, two batches', fontsize=10)
    ax.grid(ls=':', lw=0.5, alpha=0.6)
    fig.text(0.02, 0.005, 'Filled = same sign in both batches; open = opposite sign. '
             'Dashed line = equality. Colour: blue LIPSS, brown nanopillar.',
             fontsize=6.5, color='0.35')
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    p = os.path.join(FIG, 'batchB_vs_batchA_antiadhesion.png')
    fig.savefig(p, dpi=220)
    plt.close(fig)
    return p


def fig_qc():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    q = pd.read_csv(os.path.join(OUT, 'acquisition_qc.csv'), encoding='utf-8-sig')
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.0))
    groups = [('repeat 1', 'c', '#7f8c8d'), ('repeat 1', '1', '#c0392b'),
              ('repeat 1', '2', '#b5651d'), ('repeat 2', 'c', '#95a5a6'),
              ('repeat 2', '1', '#e74c3c'), ('repeat 2', '2', '#d68910')]
    for j, (metric, ylab) in enumerate([('n_kept', 'objects per image (15-500 px)'),
                                        ('area_med', 'median object area (px)'),
                                        ('exposure_s', 'exposure time (s)')]):
        ax = axes[j]
        for i, (rep, ar, colr) in enumerate(groups):
            g = q[(q.species == 'S.aureus') & (q['repeat'] == rep) & (q.time == '3h') &
                  (q.area == ar)]
            ax.scatter(np.full(len(g), i) + np.random.default_rng(j).normal(0, 0.05, len(g)),
                       g[metric], s=18, color=colr, alpha=0.85, edgecolor='k', linewidth=0.3)
        ax.set_xticks(range(len(groups)))
        ax.set_xticklabels([f'{r.replace("repeat ", "r")}\n{REGION[a][:5]}'
                            for r, a, _ in groups], fontsize=7)
        ax.set_ylabel(ylab)
        ax.grid(axis='y', ls=':', lw=0.5, alpha=0.6)
    fig.suptitle('S. aureus 3 h — evidence for the LIPSS acquisition artefact', fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    p = os.path.join(FIG, 'batchB_qc_exclusion_evidence.png')
    fig.savefig(p, dpi=220)
    plt.close(fig)
    return p


def main():
    os.makedirs(FIG, exist_ok=True)
    frames = []
    for sp, label in SPECIES:
        f = os.path.join(DS_B, 'imagej_counts_min15', sp, 'livedead_raw_counts.csv')
        d = load(f)
        assert not d.empty, f
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df['excluded'] = False
    df['exclusion_reason'] = ''
    for sp, rep, t, ar, issue, detail in EXCLUSIONS:
        m = (df.species == sp) & (df['repeat'] == rep) & (df.time == t) & (df.area == ar)
        df.loc[m, 'excluded'] = True
        df.loc[m, 'exclusion_reason'] = issue
    used = df[~df.excluded].copy()
    used.to_csv(os.path.join(OUT, 'batchB_raw_counts_used.csv'), index=False,
                encoding='utf-8-sig')
    pd.DataFrame([dict(species=s, repeat=r, time=t, area=a, issue=i, detail=d_)
                  for s, r, t, a, i, d_ in EXCLUSIONS]).to_csv(
        os.path.join(OUT, 'batchB_exclusions.csv'), index=False, encoding='utf-8-sig')

    cond = condition_table(used)
    cond.to_csv(os.path.join(OUT, 'batchB_condition_summary.csv'), index=False,
                encoding='utf-8-sig')
    aa = aa_table(cond)
    aa.to_csv(os.path.join(OUT, 'batchB_antiadhesion.csv'), index=False, encoding='utf-8-sig')
    summ3, test3 = coupon3(df)          # coupon 3 is in the raw table, never in cond
    summ3.to_csv(os.path.join(OUT, 'batchB_coupon3_summary.csv'), index=False,
                 encoding='utf-8-sig')
    test3.to_csv(os.path.join(OUT, 'batchB_coupon3_vs_2.csv'), index=False,
                 encoding='utf-8-sig')
    cmp_ba = batch_compare(aa)
    cmp_ba.to_csv(os.path.join(OUT, 'batchB_vs_batchA.csv'), index=False, encoding='utf-8-sig')

    figs = [fig_stacked(cond), fig_aa(aa), fig_coupon3(df), fig_qc(),
            fig_cross_batch(cmp_ba)]

    # ---- console report with the numbers used in the write-up
    print('=== condition summary (used fields) ===')
    print(cond.round(1).to_string(index=False))
    print('\n=== anti-adhesion ===')
    print(aa[['species', 'time', 'area', 'AA_mean', 'AA_sd_across_repeats',
              'AAlive_mean', 'n_repeats', 'signs']].round(1).to_string(index=False))
    print('\n=== coupon 3 vs 2 ===')
    print(summ3.round(2).to_string(index=False))
    print(test3.round(4).to_string(index=False))
    print('\n=== batch A vs batch B controls (cells per field) ===')
    print(cmp_ba.round(1).to_string(index=False))
    print('\nfigures:', *figs, sep='\n  ')
    print('\nfiles ->', OUT)


if __name__ == '__main__':
    main()
