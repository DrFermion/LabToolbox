# -*- coding: utf-8 -*-
"""plot_650_repeat2.py — 650 nm LIVE/DEAD: repeat-2 / combined / validation figures.

Figures produced (all written into --out):
  A  650nm_livedead_repeat2.png
     rows = species; col 1 = green/red stacked live+dead density (cells/cm2);
     col 2 = total-cell adhesion (live+dead, cells/cm2), anti-adhesion % over the
     treated bars, control shown as the grey bar.
  B  650nm_livedead_combined_repeat1_repeat2.png
     same layout, bars = mean of the repeat means, per-repeat means as markers.
  C  650nm_livedead_validation_5h_Saureus.png
     S. aureus 5 h: the QC coupon (repeat 1 Nanopillar / repeat 2 sample #3) vs the
     normal Nanopillar coupon (repeat 2 sample #2) and the controls.

Counting rule: ImageJ 1.54, adaptive threshold (bg mode + 40), size 3-500 px,
40x field area 46946.10 um2 -> density = count / 46946.10 um2 * 1e8.

Data model: <ic>/<species>/livedead_raw_counts.csv with columns
    repeat,time,area,num,g_image,r_image,live,dead,total,dead_rate
`area` codes: c = Control, 1 = LIPSS, 2 = Nanopillar, 3 = extra coupon (re-shot of a
previously problematic Nanopillar coupon) - code 3 is kept OUT of all statistics and
only shown in figure C (--exclude-3).

Borrowed control: --borrow "S.aureus|7h" replaces a missing repeat-2 control at that
timepoint with the repeat-1 control (marked with a dagger in the figures).

Usage
  python plot_650_repeat2.py --demo --out <dir> --exclude-3 --borrow "S.aureus|7h"
  python plot_650_repeat2.py --ic <...>/imagej_counts_repeat2 --ic-r1 <...>/imagej_counts \
      --out <dir> --borrow "S.aureus|7h" --exclude-3
"""
from __future__ import annotations

import argparse
import os
import re
import textwrap

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from scipy import stats

AREA_UM2 = 46946.10
K = 1e8 / AREA_UM2
SPECIES = [('E.coli', 'E. coli'), ('S.aureus', 'S. aureus')]
TIMES = ['3h', '5h', '7h', '24h']
AREAS = ['c', '1', '2']
AREA_SHORT = {'c': 'Ctrl', '1': 'LIPSS', '2': 'Nano', '3': 'Nano\nre-shot'}
SURF_COLOR = {'c': '#9E9E9E', '1': '#1565C0', '2': '#EF6C00', '3': '#6A1B9A'}
C_LIVE, C_DEAD = '#2E7D32', '#C62828'
DEMO_TAG = 'TEMPLATE - layout preview; repeat-2 values are placeholders, NOT measurements'
R1_DIR = ('F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - '
          'Ruinong Pan_Antibacterial Surfaces/Live_Dead Bacteria Test/650nm-20261014/imagej_counts')


def load_raw(path, keep_red_only=True):
    """Read the engine-format count table.

    Rows with only one channel are kept when keep_red_only is set: S. aureus
    repeat 2 / 24 h has a contaminated control coupon where the red channel was
    counted as TOTAL cells (no green channel). For those rows live = NaN,
    total = red count, so viability is unavailable but the total is usable.
    """
    raw = pd.read_csv(path, encoding='utf-8-sig')
    raw['g_image'] = raw['g_image'].fillna('')
    raw['r_image'] = raw['r_image'].fillna('')
    if keep_red_only:
        raw = raw[(raw.g_image != '') | (raw.r_image != '')].copy()
    else:
        raw = raw[(raw.g_image != '') & (raw.r_image != '')].copy()
    raw['live'] = pd.to_numeric(raw['live'], errors='coerce')
    raw['dead'] = pd.to_numeric(raw['dead'], errors='coerce')
    raw = raw[~(raw.live.isna() & raw.dead.isna())].copy()
    raw['red_only'] = raw['live'].isna() & raw['dead'].notna()
    raw['total'] = raw['live'].fillna(0) + raw['dead'].fillna(0)
    raw['area'] = raw['area'].astype(str)
    raw['time'] = raw['time'].astype(str)
    raw['repeat'] = raw['repeat'].astype(str)
    return raw


def demo_raw(rng, sp_dir):
    base_live = {'E.coli': {'c': 120, '1': 70, '2': 85}, 'S.aureus': {'c': 190, '1': 150, '2': 175}}
    base_dead = {'E.coli': {'c': 60, '1': 95, '2': 70}, 'S.aureus': {'c': 45, '1': 130, '2': 80}}
    rows = []
    for t in TIMES:
        for a in AREAS:
            for n in range(1, 6):
                lv = max(1, int(base_live[sp_dir][a] * rng.uniform(0.75, 1.3)))
                dd = max(1, int(base_dead[sp_dir][a] * rng.uniform(0.75, 1.3)))
                rows.append(dict(repeat='repeat 2', time=t, area=a, num=n,
                                 g_image='%s-g%d.tif' % (a, n), r_image='%s-r%d.tif' % (a, n),
                                 live=lv, dead=dd))
        if sp_dir == 'S.aureus' and t == '5h':
            for n in range(1, 6):
                rows.append(dict(repeat='repeat 2', time=t, area='3', num=n,
                                 g_image='3-g%d.tif' % n, r_image='3-r%d.tif' % n,
                                 live=int(rng.integers(0, 6)), dead=int(rng.integers(1600, 1900))))
    df = pd.DataFrame(rows)
    df['total'] = df['live'] + df['dead']
    return df


def aa_with_sd(ctrl, trat):
    mc, mt = ctrl.mean(), trat.mean()
    sc, st = ctrl.std(ddof=1), trat.std(ddof=1)
    aa = (mc - mt) / mc * 100.0
    rel = np.sqrt((sc / np.sqrt(len(ctrl)) / mc) ** 2 + (st / np.sqrt(len(trat)) / mt) ** 2)
    return aa, 100.0 * (mt / mc) * rel


def group_stats(raw, times, areas=AREAS):
    """Per (time, area) statistics.

    Total-cell columns use every row that carries a count (including red-only
    rows where the red channel stands in for the total); live/dead/viability
    only use rows where both channels were counted and are NaN otherwise.
    """
    out = []
    for t in times:
        for a in areas:
            g = raw[(raw.time == t) & (raw.area == a)]
            if len(g) == 0:
                continue
            full = g.dropna(subset=['live', 'dead'])
            nf = len(full)
            out.append(dict(time=t, area=a, n=nf, n_total=len(g),
                            live=full['live'].mean() if nf else np.nan,
                            live_sd=full['live'].std(ddof=1) if nf > 1 else np.nan,
                            dead=full['dead'].mean() if nf else np.nan,
                            dead_sd=full['dead'].std(ddof=1) if nf > 1 else np.nan,
                            total=g['total'].mean(),
                            total_sd=g['total'].std(ddof=1) if len(g) > 1 else np.nan,
                            viability=(full['live'].sum() / full['total'].sum() * 100)
                            if nf and full['total'].sum() else np.nan,
                            live_cm2=full['live'].mean() * K if nf else np.nan,
                            dead_cm2=full['dead'].mean() * K if nf else np.nan,
                            total_cm2=g['total'].mean() * K,
                            total_cm2_sd=(g['total'].std(ddof=1) * K) if len(g) > 1 else np.nan))
    return pd.DataFrame(out)


def surface_aa(raw, t, area):
    c = raw[(raw.time == t) & (raw.area == 'c')]
    s = raw[(raw.time == t) & (raw.area == area)]
    if len(c) < 2 or len(s) < 2:
        return None
    d = {}
    d['aa_live'], d['aa_live_sd'] = aa_with_sd(c['live'].astype(float), s['live'].astype(float))
    d['aa_total'], d['aa_total_sd'] = aa_with_sd(c['total'].astype(float), s['total'].astype(float))
    d['p_live'] = stats.ttest_ind(c['live'], s['live'], equal_var=False).pvalue
    d['p_total'] = stats.ttest_ind(c['total'], s['total'], equal_var=False).pvalue
    return d


def _xmap(times, areas):
    xs, groups = {}, []
    for ti, t in enumerate(times):
        center = ti * 4.0
        groups.append(center)
        for ai, a in enumerate(areas):
            xs[(t, a)] = center + (ai - (len(areas) - 1) / 2.0) * 1.05
    return xs, groups


def _time_labels(ax, times, xs, groups, areas, borrowed=(), viab_borrowed=()):
    ax.set_xticks([xs[(t, a)] for t in times for a in areas])
    ax.set_xticklabels([AREA_SHORT[a] for t in times for a in areas], fontsize=7.2)
    for t, gc in zip(times, groups):
        mark = ' $\\ddagger$' if t in viab_borrowed else (' $\\dagger$' if t in borrowed else '')
        ax.text(gc, -0.15, t + mark, transform=ax.get_xaxis_transform(),
                ha='center', fontsize=10.5, fontweight='bold')
    ax.set_xlim(-1.7, (len(times) - 1) * 4.0 + 1.7)


def panel_stacked(ax, st, times, areas, title, borrowed=(), viab_borrowed=(), est_times=()):
    xs, groups = _xmap(times, areas)
    ymax = float((st['live_cm2'] + st['dead_cm2']).max())
    if not np.isfinite(ymax) or ymax <= 0:
        ymax = float(st['total_cm2'].max())
    for (t, a), x in xs.items():
        g = st[(st.time == t) & (st.area == a)]
        if g.empty or not np.isfinite(float(g['live_cm2'].iloc[0])):
            continue
        if a == 'c' and t in est_times:
            continue                # control not measured: the dashed estimate line stands alone
        lv, dd = float(g['live_cm2'].iloc[0]), float(g['dead_cm2'].iloc[0])
        ax.bar(x, lv, 0.9, color=C_LIVE, edgecolor='black', linewidth=0.45)
        ax.bar(x, dd, 0.9, bottom=lv, color=C_DEAD, edgecolor='black', linewidth=0.45)
        if np.isfinite(float(g['viability'].iloc[0])):
            ax.text(x, lv + dd + ymax * 0.012, '%.0f%%' % float(g['viability'].iloc[0]),
                    ha='center', va='bottom', fontsize=6.8, color='#444444')
    for t in est_times:
        g = st[(st.time == t) & (st.area == 'c')]
        if g.empty:
            continue
        vc = float(g['total_cm2'].iloc[0])
        _draw_est(ax, xs[(t, 'c')] - 0.5, xs[(t, '2')] + 0.5, vc, label='est. control total')
        ymax = max(ymax, vc)
    ax.set_ylim(0, ymax * 1.13)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: '{:,.0f}'.format(v)))
    _time_labels(ax, times, xs, groups, areas, borrowed, viab_borrowed)
    ax.set_ylabel('Cell density (cells/cm$^2$)', fontsize=9)
    ax.set_title(title, fontsize=10.2)
    ax.grid(axis='y', alpha=0.25)


def _draw_est(ax, x0, x1, v, label='est. control', label_x=None):
    """Horizontal dashed line marking an inferred (not measured) control level."""
    ax.plot([x0, x1], [v, v], color='#222222', linestyle=(0, (6, 3)),
            linewidth=1.6, zorder=6)
    if label:
        lx = x0 + 0.55 if label_x is None else label_x
        ax.text(lx, v, label, fontsize=6.4, color='#111111', va='bottom',
                ha='center', zorder=7,
                bbox=dict(boxstyle='round,pad=0.16', fc='white', ec='none', alpha=0.95))


def panel_total(ax, raw, st, times, areas, title, borrowed=(), viab_borrowed=(), est_times=()):
    xs, groups = _xmap(times, areas)
    ymax = 0.0
    for (t, a), x in xs.items():
        g = st[(st.time == t) & (st.area == a)]
        if g.empty:
            continue
        v = float(g['total_cm2'].iloc[0])
        e = float(g['total_cm2_sd'].iloc[0])
        if a == 'c' and t in est_times:
            continue                    # no control bar: the dashed line below is the estimate
        ax.bar(x, v, 0.9, color=SURF_COLOR[a], edgecolor='black', linewidth=0.45)
        ax.errorbar(x, v, yerr=e, fmt='none', ecolor='#333333', elinewidth=0.9, capsize=3)
        if a != 'c':
            cg = st[(st.time == t) & (st.area == 'c')]
            lab = ''
            if not cg.empty:
                cc = float(cg['total_cm2'].iloc[0])
                if cc:
                    aa_v = (cc - v) / cc * 100.0
                    lab = '0%' if abs(aa_v) < 0.5 else '%.0f%%' % aa_v
            ax.text(x, v + e + ymax * 0.02, lab, ha='center', va='bottom',
                    fontsize=7.0, color='#222222')
        ymax = max(ymax, v + e)
    for t in est_times:
        g = st[(st.time == t) & (st.area == 'c')]
        if g.empty:
            continue
        vc = float(g['total_cm2'].iloc[0])
        _draw_est(ax, xs[(t, 'c')] - 0.5, xs[(t, '2')] + 0.5, vc)
        ymax = max(ymax, vc)
    ax.set_ylim(0, ymax * 1.15)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: '{:,.0f}'.format(v)))
    _time_labels(ax, times, xs, groups, areas, borrowed, viab_borrowed)
    ax.set_ylabel('Total cells (live + dead), cells/cm$^2$', fontsize=9)
    ax.set_title(title, fontsize=10.2)
    ax.grid(axis='y', alpha=0.25)


def figure_legend(fig, with_repeats=False, y=0.062):
    h = [Patch(facecolor=C_LIVE, edgecolor='black', label='Live (green channel)'),
         Patch(facecolor=C_DEAD, edgecolor='black', label='Dead (red channel)'),
         Patch(facecolor=SURF_COLOR['c'], edgecolor='black', label='Control area'),
         Patch(facecolor=SURF_COLOR['1'], edgecolor='black', label='LIPSS area'),
         Patch(facecolor=SURF_COLOR['2'], edgecolor='black', label='Nanopillar area')]
    if with_repeats:
        h += [plt.Line2D([], [], marker='o', linestyle='none', markerfacecolor='white',
                         markeredgecolor='black', label='repeat 1 mean'),
              plt.Line2D([], [], marker='s', linestyle='none', markerfacecolor='white',
                         markeredgecolor='black', label='repeat 2 mean')]
    fig.legend(handles=h, loc='lower center', bbox_to_anchor=(0.5, y),
               ncol=len(h), frameon=False, fontsize=8.8, handlelength=1.6, columnspacing=1.6)


def footer(fig, text, demo, y=0.006, fontsize=7.1, width=168):
    if demo:
        fig.patches.append(plt.Rectangle((0.0, 0.962), 1.0, 0.038, transform=fig.transFigure,
                                         facecolor='#FFCDD2', edgecolor='#C62828', linewidth=1.0,
                                         zorder=5, figure=fig))
        fig.text(0.5, 0.981, DEMO_TAG, ha='center', va='center', fontsize=10,
                 color='#B71C1C', fontweight='bold', zorder=6)
    fig.text(0.005, y, textwrap.fill(text, width), ha='left', va='bottom',
             fontsize=fontsize, color='#666666', style='italic')


def combined_table(r1, r2, times, areas=AREAS, r2_tot=None):
    """r2 carries the viability view (borrowed control where flagged), r2_tot the
    total-cell view (red-as-total rows kept). A condition present in only one
    repeat (the other one dropped as superseded) yields that single repeat value
    and a NaN SD, so it is not drawn as if it were a two-repeat mean."""
    st1 = group_stats(r1, times, areas)
    st2 = group_stats(r2, times, areas)
    st2t = group_stats(r2_tot if r2_tot is not None else r2, times, areas)

    def pick(a, b):
        vals = [v for v in (a, b) if v == v]
        if not vals:
            return np.nan, np.nan
        return float(np.mean(vals)), (float(np.std(vals, ddof=1)) if len(vals) > 1 else np.nan)

    rows = []
    for t in times:
        for ar in areas:
            g1 = st1[(st1.time == t) & (st1.area == ar)]
            g2 = st2[(st2.time == t) & (st2.area == ar)]
            g2t = st2t[(st2t.time == t) & (st2t.area == ar)]
            if g1.empty and g2t.empty:
                continue
            v1 = lambda col: (float(g1[col].iloc[0]) if not g1.empty else np.nan)
            v2 = lambda col: (float(g2[col].iloc[0]) if not g2.empty else np.nan)
            v2t = lambda col: (float(g2t[col].iloc[0]) if not g2t.empty else np.nan)
            live, _ = pick(v1('live_cm2'), v2('live_cm2'))
            dead, _ = pick(v1('dead_cm2'), v2('dead_cm2'))
            total, total_sd = pick(v1('total_cm2'), v2t('total_cm2'))
            viab, _ = pick(v1('viability'), v2('viability'))
            rows.append(dict(time=t, area=ar, n=int((not g1.empty) + (not g2t.empty)),
                             live_cm2=live, dead_cm2=dead,
                             total_cm2=total, total_cm2_sd=total_sd, viability=viab,
                             r1_live=v1('live_cm2'), r2_live=v2('live_cm2'),
                             r1_dead=v1('dead_cm2'), r2_dead=v2('dead_cm2'),
                             r1_total=v1('total_cm2'), r2_total=v2t('total_cm2')))
    return pd.DataFrame(rows)


def display_table(rawT, rawV, times, areas=AREAS):
    """Total-cell view (rawT, keeps red-as-total rows) merged with the viability
    view (rawV, borrowed control where flagged). Where viability is unavailable
    the live/dead/viability columns are NaN, the total columns are not."""
    stT = group_stats(rawT, times, areas)
    stV = group_stats(rawV, times, areas)
    add = stV[['time', 'area', 'n', 'live', 'live_sd', 'dead', 'dead_sd', 'viability',
               'live_cm2', 'dead_cm2']]
    return stT.merge(add, on=['time', 'area'], how='left', suffixes=('_t', ''))


def panel_stacked_combined(ax, cd, times, title, marks=True, est_times=()):
    xs, groups = _xmap(times, AREAS)
    ymax = 0.0
    for col in ('live_cm2', 'dead_cm2', 'total_cm2', 'r1_live', 'r2_live'):
        v = cd[col].max()
        if np.isfinite(v):
            ymax = max(ymax, float(v))
    ymax = max(ymax, float(cd['r1_total'].max(skipna=True)), float(cd['r2_total'].max(skipna=True)))
    for (t, a), x in xs.items():
        g = cd[(cd.time == t) & (cd.area == a)]
        if g.empty or not np.isfinite(float(g['live_cm2'].iloc[0])):
            continue
        if a == 'c' and t in est_times:
            continue                # control not measured: the dashed estimate line stands alone
        lv, dd = float(g['live_cm2'].iloc[0]), float(g['dead_cm2'].iloc[0])
        ax.bar(x, lv, 0.9, color=C_LIVE, edgecolor='black', linewidth=0.45)
        ax.bar(x, dd, 0.9, bottom=lv, color=C_DEAD, edgecolor='black', linewidth=0.45)
        for rv, mk, dx in ((float(g.r1_live.iloc[0]), 'o', -0.21),
                           (float(g.r2_live.iloc[0]), 's', 0.21)):
            if not marks or not np.isfinite(rv):
                continue
            ax.plot(x + dx, rv, marker=mk, markersize=4.4, markerfacecolor='white',
                    markeredgecolor='black', markeredgewidth=0.9, zorder=5)
        if np.isfinite(float(g['viability'].iloc[0])):
            ax.text(x, lv + dd + ymax * 0.012, '%.0f%%' % float(g['viability'].iloc[0]),
                    ha='center', va='bottom', fontsize=6.8, color='#444444')
    for t in est_times:
        g = cd[(cd.time == t) & (cd.area == 'c')]
        if g.empty:
            continue
        vc = float(g['total_cm2'].iloc[0])
        _draw_est(ax, xs[(t, 'c')] - 0.5, xs[(t, '2')] + 0.5, vc, label='est. control total')
        ymax = max(ymax, vc)
    ax.set_ylim(0, ymax * 1.13)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: '{:,.0f}'.format(v)))
    _time_labels(ax, times, xs, groups, AREAS)
    ax.set_ylabel('Cell density (cells/cm$^2$)', fontsize=9)
    ax.set_title(title, fontsize=10.2)
    ax.grid(axis='y', alpha=0.25)


def panel_total_combined(ax, cd, times, title, borrowed=(), marks=True, est_times=()):
    xs, groups = _xmap(times, AREAS)
    ymax = float(cd[['r1_total', 'r2_total']].max().max())
    for (t, a), x in xs.items():
        g = cd[(cd.time == t) & (cd.area == a)]
        if g.empty:
            continue
        v = float(g['total_cm2'].iloc[0])
        e = float(g['total_cm2_sd'].iloc[0])
        if a == 'c' and t in est_times:
            continue                    # no control bar: the dashed line below is the estimate
        ax.bar(x, v, 0.9, color=SURF_COLOR[a], edgecolor='black', linewidth=0.45)
        ax.errorbar(x, v, yerr=e, fmt='none', ecolor='#333333', elinewidth=0.9, capsize=3)
        for rv, mk, dx in ((float(g.r1_total.iloc[0]), 'o', -0.21),
                           (float(g.r2_total.iloc[0]), 's', 0.21)):
            if not marks or not np.isfinite(rv):
                continue
            ax.plot(x + dx, rv, marker=mk, markersize=4.4, markerfacecolor='white',
                    markeredgecolor='black', markeredgewidth=0.9, zorder=5)
        if a != 'c':
            c = cd[(cd.time == t) & (cd.area == 'c')]
            if not c.empty:
                cc = float(c['total_cm2'].iloc[0])
                ax.text(x, v + e + ymax * 0.02, '%.0f%%' % ((cc - v) / cc * 100),
                        ha='center', va='bottom', fontsize=7.0, color='#222222')
        ymax = max(ymax, v + e)
    for t in est_times:
        g = cd[(cd.time == t) & (cd.area == 'c')]
        if g.empty:
            continue
        vc = float(g['total_cm2'].iloc[0])
        _draw_est(ax, xs[(t, 'c')] - 0.5, xs[(t, '2')] + 0.5, vc)
        ymax = max(ymax, vc)
    ax.set_ylim(0, ymax * 1.15)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: '{:,.0f}'.format(v)))
    _time_labels(ax, times, xs, groups, AREAS, borrowed)
    ax.set_ylabel('Total cells (live + dead), cells/cm$^2$', fontsize=9)
    ax.set_title(title, fontsize=10.2)
    ax.grid(axis='y', alpha=0.25)


def est_note(EST):
    """Compact footnote for the inferred controls (kept short: the footer is one text block)."""
    if not EST:
        return ''
    bits = []
    for (sp, t), e in sorted(EST.items()):
        bits.append('%s %s control not measurable in repeat 2 -> estimated %.2e cells/cm2 '
                    '(plausible %.2e-%.2e) from the treated:control ratio at the timepoints with a '
                    'real control (pooled %.2f, spread %.2f-%.2f, %d pairs); dashed line = estimate, '
                    'not a measurement'
                    % (sp, t, e['c'] * K, e['c_lo'] * K, e['c_hi'] * K,
                       e['ratio'], e['lo'], e['hi'], e['n_pairs']))
    return '  ' + '; '.join(bits) + '.'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ic', default='')
    ap.add_argument('--ic-r1', default='')
    ap.add_argument('--out', required=True)
    ap.add_argument('--demo', action='store_true')
    ap.add_argument('--borrow', action='append', default=[],
                    help='species|time whose repeat-2 control is MISSING - taken from repeat 1')
    ap.add_argument('--viab-from-r1', action='append', default=[],
                    help='species|time where the repeat-2 control has no green channel '
                         '(red counted as total): viability borrowed from repeat 1, total '
                         'values stay repeat 2')
    ap.add_argument('--exclude-3', action='store_true')
    ap.add_argument('--infer-ctrl', action='append', default=[],
                    help='species whose repeat-2 control is MISSING or red-only at some timepoint: '
                         'estimate it from the other timepoints (treated:control ratio observed '
                         'where the control is real) and mark the estimate with a dashed line')
    ap.add_argument('--drop-r1', action='append', default=[],
                    help='species|time|area whose repeat-1 measurement is superseded and must be '
                         'left out of the combined figure (e.g. S.aureus|5h|2)')
    ap.add_argument('--plain', action='store_true',
                    help='clean figure: no dagger/double-dagger marks on the time axis and a short '
                         'footnote (data unchanged)')
    ap.add_argument('--no-marks', action='store_true',
                    help='do not draw the per-repeat mean markers (circles/squares)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    borrow = {tuple(x.split('|')) for x in a.borrow}
    viab_r1 = {tuple(x.split('|')) for x in a.viab_from_r1}

    R2, R2V, R2RAW, R1 = {}, {}, {}, {}
    for sp_dir, sp_label in SPECIES:
        if a.demo:
            d = demo_raw(np.random.default_rng(abs(hash(sp_label)) % 2 ** 32), sp_dir)
            R2[sp_label], R2V[sp_label] = d, d.copy()
            R2RAW[sp_label] = d.copy()
        else:
            d = load_raw(os.path.join(a.ic, sp_dir, 'livedead_raw_counts.csv'))
            R2[sp_label] = d                 # total-cell view (red-as-total rows kept)
            R2V[sp_label] = d[d.live.notna()].copy()   # viability view
            R2RAW[sp_label] = d.copy()       # pristine copy for the control inference
        r1_dir = a.ic_r1 or (R1_DIR if a.demo else '')
        if r1_dir:
            R1[sp_label] = load_raw(os.path.join(r1_dir, sp_dir, 'livedead_raw_counts.csv'))

    def _norm(x):
        return x.replace('.', '').replace(' ', '').lower()

    for sp_label in R2:
        for sp_b, t_b, ar_b in {tuple(x.split('|')) for x in a.drop_r1}:
            if _norm(sp_b) != _norm(sp_label) or sp_label not in R1:
                continue
            d0 = R1[sp_label]
            keep = ~((d0.time == t_b) & (d0.area == ar_b))
            if (~keep).sum():
                R1[sp_label] = d0[keep]
                print('dropped repeat-1 measurement: %s %s area %s (%d rows) - superseded coupon'
                      % (sp_label, t_b, ar_b, int((~keep).sum())))
        if a.exclude_3:
            R2[sp_label] = R2[sp_label][R2[sp_label].area != '3']
            R2V[sp_label] = R2V[sp_label][R2V[sp_label].area != '3']
        for sp_b, t_b in borrow:
            if _norm(sp_b) != _norm(sp_label) or sp_label not in R1:
                continue
            miss = R2[sp_label][(R2[sp_label].time == t_b) & (R2[sp_label].area == 'c')]
            if len(miss):
                continue
            donor = R1[sp_label][(R1[sp_label].time == t_b) & (R1[sp_label].area == 'c')].copy()
            if not len(donor):
                continue
            donor['repeat'] = 'repeat 1 (borrowed)'
            for store in (R2, R2V):
                store[sp_label] = pd.concat([store[sp_label], donor], ignore_index=True)
            print('borrowed control: %s %s <- repeat 1 (%d fields)' % (sp_label, t_b, len(donor)))
        for sp_b, t_b in viab_r1:
            if _norm(sp_b) != _norm(sp_label) or sp_label not in R1:
                continue
            have = R2V[sp_label][(R2V[sp_label].time == t_b) & (R2V[sp_label].area == 'c')]
            if len(have):
                continue
            donor = R1[sp_label][(R1[sp_label].time == t_b) & (R1[sp_label].area == 'c')].copy()
            if not len(donor):
                continue
            donor['repeat'] = 'repeat 1 (borrowed viability)'
            R2V[sp_label] = pd.concat([R2V[sp_label], donor], ignore_index=True)
            print('borrowed viability-only control: %s %s <- repeat 1 (%d fields)'
                  % (sp_label, t_b, len(donor)))

    # ---------------- control inference (dashed estimates) ----------------
    EST = {}
    infer_sp = {_norm(x) for x in a.infer_ctrl}
    for sp_label in R2:
        if _norm(sp_label) not in infer_sp:
            continue
        base = R2RAW[sp_label]
        ratios = []
        for t in TIMES:
            c = base[(base.time == t) & (base.area == 'c')]
            if len(c) == 0:
                continue
            if 'red_only' in c.columns and bool(c['red_only'].any()):
                continue                      # contaminated coupon: not a real control
            cm = float(c['total'].mean())
            if not cm:
                continue
            for ar in ('1', '2'):
                g = base[(base.time == t) & (base.area == ar)]
                if len(g):
                    ratios.append((t, ar, float(g['total'].mean()) / cm))
        if not ratios:
            continue
        R = float(np.mean([r[2] for r in ratios]))
        lo = float(np.min([r[2] for r in ratios]))
        hi = float(np.max([r[2] for r in ratios]))
        for t in TIMES:
            c = base[(base.time == t) & (base.area == 'c')]
            real = len(c) and not ('red_only' in c.columns and bool(c['red_only'].any()))
            if real:
                continue
            vals = [float(base[(base.time == t) & (base.area == ar)]['total'].mean())
                    for ar in ('1', '2')
                    if len(base[(base.time == t) & (base.area == ar)])]
            if not vals:
                continue
            mt = float(np.mean(vals))
            EST[(sp_label, t)] = dict(
                ratio=R, lo=lo, hi=hi, treated=mt, c=mt / R, c_lo=mt / hi, c_hi=mt / lo,
                n_pairs=len(ratios),
                basis='; '.join('%s@%s %.3f' % ('LIPSS' if r[1] == '1' else 'Nano', r[0], r[2])
                                for r in ratios))
            x = R2[sp_label]
            x = x[~((x.time == t) & (x.area == 'c'))]
            e = EST[(sp_label, t)]
            row = dict(repeat='repeat 2 (control inferred)', time=t, area='c', num=0,
                       g_image='', r_image='', live=np.nan, dead=e['c'], total=e['c'],
                       dead_rate=np.nan, red_only=False)
            R2[sp_label] = pd.concat([x, pd.DataFrame([row])], ignore_index=True)
            print('inferred control: %s %s -> %.0f cells/field (range %.0f-%.0f); treated mean %.0f,'
                  ' pooled treated:control ratio %.3f from %d pairs'
                  % (sp_label, t, e['c'], e['c_lo'], e['c_hi'], mt, R, len(ratios)))
    if EST:
        pd.DataFrame([dict(species=k[0], time=k[1], treated_mean=v['treated'],
                           ratio_mean=v['ratio'], ratio_min=v['lo'], ratio_max=v['hi'],
                           n_pairs=v['n_pairs'], control_est=v['c'], control_lo=v['c_lo'],
                           control_hi=v['c_hi'], basis=v['basis'])
                      for k, v in sorted(EST.items())]).to_csv(
            os.path.join(a.out, '650nm_control_inference.csv'), index=False, encoding='utf-8-sig')

    suffix = '_TEMPLATE' if a.demo else ''
    # ---------------- A. repeat-2 figure ----------------
    fig, axes = plt.subplots(2, 2, figsize=(14.2, 9.6), dpi=200)
    rows = []
    for i, (sp_dir, sp_label) in enumerate(SPECIES):
        rawT, rawV = R2[sp_label], R2V[sp_label]
        times = [t for t in TIMES if t in set(rawT.time)]
        st = display_table(rawT, rawV, times)
        st.insert(0, 'species', sp_label)
        rows.append(st)
        b_set = {t for sp, t in borrow if _norm(sp) == _norm(sp_label)}
        v_set = {t for sp, t in viab_r1 if _norm(sp) == _norm(sp_label)}
        e_set = {t for sp, t in EST if _norm(sp) == _norm(sp_label)}
        panel_stacked(axes[i, 0], st, times, AREAS,
                      '(%s) %s - live + dead density (stacked)' % ('ac'[i], sp_label),
                      borrowed=b_set, viab_borrowed=v_set, est_times=e_set)
        panel_total(axes[i, 1], rawT, st, times, AREAS,
                    '(%s) %s - total-cell adhesion (labels = anti-adhesion %%)'
                    % ('bd'[i], sp_label), borrowed=b_set, viab_borrowed=v_set, est_times=e_set)
    fig.suptitle('650 nm textured stainless steel - LIVE/DEAD, repeat 2', fontsize=12.5, y=0.975)
    figure_legend(fig, y=0.062)
    note = ('ImageJ 1.54 adaptive threshold (bg mode + 40), size 3-500 px; 40x field area 46 946 um2; '
            'bars = mean of 5 fields; %% over stacked bars = pooled viability; error bars = SD.')
    if borrow:
        note += ('  dagger = the repeat-2 control for that timepoint is missing and taken from '
                 'repeat 1 (' + '; '.join('%s %s' % (s, t) for s, t in sorted(borrow)) + ').')
    if viab_r1:
        note += ('  double dagger = the repeat-2 control coupon at that timepoint was contaminated '
                 '(no green channel, red counted as total): the total-cell bar is repeat 2, the '
                 'viability/live-dead bars are taken from repeat 1 ('
                 + '; '.join('%s %s' % (s, t) for s, t in sorted(viab_r1)) + ').')
    note += est_note(EST)
    note += '  Extra coupon (sample 3) is excluded from every statistic on this figure.'
    footer(fig, note, a.demo)
    fig.tight_layout(rect=(0, 0.085, 1, 0.95))
    pA = os.path.join(a.out, '650nm_livedead_repeat2%s.png' % suffix)
    fig.savefig(pA)
    plt.close(fig)
    pd.concat(rows).to_csv(os.path.join(a.out, '650nm_livedead_repeat2_summary%s.csv' % suffix),
                           index=False, encoding='utf-8-sig')
    print('figure:', pA)

    # ---------------- B. combined repeat1 + repeat2 ----------------
    if R1:
        fig, axes = plt.subplots(2, 2, figsize=(14.2, 9.6), dpi=200)
        rows = []
        for i, (sp_dir, sp_label) in enumerate(SPECIES):
            r1, r2 = R1[sp_label].copy(), R2V[sp_label].copy()
            if a.exclude_3:
                r1 = r1[r1.area != '3']
            times = [t for t in TIMES if t in set(r1.time) | set(r2.time)]
            cd = combined_table(r1, r2, times, r2_tot=R2[sp_label])
            cd.insert(0, 'species', sp_label)
            rows.append(cd)
            b_set = {t for sp, t in borrow if _norm(sp) == _norm(sp_label)}
            v_set = {t for sp, t in viab_r1 if _norm(sp) == _norm(sp_label)}
            e_set = {t for sp, t in EST if _norm(sp) == _norm(sp_label)}
            marks = not a.no_marks
            if a.plain:
                b_set, v_set = set(), set()
            panel_stacked_combined(axes[i, 0], cd, times,
                                   '(%s) %s - live + dead density, repeats 1 + 2'
                                   % ('ac'[i], sp_label), marks=marks, est_times=e_set)
            panel_total_combined(axes[i, 1], cd, times,
                                 '(%s) %s - total-cell adhesion, repeats 1 + 2'
                                 % ('bd'[i], sp_label), borrowed=b_set | v_set, marks=marks,
                                 est_times=e_set)
        fig.suptitle('650 nm textured stainless steel - LIVE/DEAD, repeats 1 + 2 combined',
                     fontsize=12.5, y=0.975)
        figure_legend(fig, with_repeats=marks, y=0.088 if EST else 0.062)
        if a.plain:
            note = ('Bars = mean of the two repeat means; error bars on the adhesion panels = SD of '
                    'the two repeats (stacked panels show the mean viability only); '
                    '% over stacked bars = mean viability; % over adhesion bars = anti-adhesion vs '
                    'the control of the same timepoint. ImageJ 1.54, adaptive threshold, size '
                    '3-500 px, 40x field area 46 946 um2, n = 5 fields per condition. '
                    'S. aureus 7 h control and 24 h control viability are from repeat 1 '
                    '(repeat-2 control missing / contaminated), so those two bars are qualitative.')
            note += est_note(EST)
            if a.drop_r1:
                bits = []
                for tok in a.drop_r1:
                    try:
                        s_b, t_b, ar_b = tok.split('|')
                    except ValueError:
                        continue
                    bits.append('%s %s %s bar = repeat 2 only: the repeat-1 measurement on that '
                                'coupon was a staining artefact and is excluded'
                                % (s_b.replace('.', ' ').strip(), t_b,
                                   AREA_SHORT.get(ar_b, ar_b).replace('\n', ' ')))
                if bits:
                    note += '  ' + '; '.join(bits) + '.'
        else:
            note = ('Bars = mean of the two repeat means; markers = the individual repeat means '
                    '(circles = repeat 1, squares = repeat 2); error bars = SD of the two repeats. '
                    '%% over stacked bars = mean viability; %% over adhesion bars = anti-adhesion vs '
                    'the control of the same repeat and timepoint.')
            if borrow:
                note += '  dagger = repeat-2 control borrowed from repeat 1.'
            if viab_r1:
                note += ('  double dagger = repeat-2 control coupon contaminated (red counted as '
                         'total): total uses repeat 2, viability uses repeat 1.')
            note += ('  The repeat-1 S. aureus 5 h nanopillar marker at ~0 viability is the coupon '
                     'that was re-shot as sample 3 in repeat 2 (Figure 3): the combined viability of '
                     'that single bar mixes a superseded value with a normal one - quote the two '
                     'repeats separately there.')
            note += est_note(EST)
            note += '  Extra coupon (sample 3) excluded.'
        footer(fig, note, a.demo, y=0.004, fontsize=6.8 if EST else 7.1,
               width=190 if EST else 168)
        fig.tight_layout(rect=(0, 0.125 if EST else 0.085, 1, 0.95))
        pB = os.path.join(a.out, '650nm_livedead_combined_repeat1_repeat2%s%s.png'
                          % (suffix, '_clean' if a.plain else ''))
        fig.savefig(pB)
        plt.close(fig)
        pd.concat(rows).to_csv(os.path.join(a.out,
                                            '650nm_livedead_combined_summary%s.csv' % suffix),
                               index=False, encoding='utf-8-sig')
        print('figure:', pB)

    # ---------------- C. validation coupon (S. aureus 5 h) ----------------
    sp_label = 'S. aureus'
    r1 = R1.get(sp_label)
    if a.demo:
        r2_all = demo_raw(np.random.default_rng(12345), 'S.aureus')
    else:
        r2_all = load_raw(os.path.join(a.ic, 'S.aureus', 'livedead_raw_counts.csv'))
    groups = []
    if r1 is not None:
        for ar, tag in (('c', 'R1\nCtrl'), ('2', 'R1\nNano (QC)')):
            g = r1[(r1.time == '5h') & (r1.area == ar)]
            if len(g):
                groups.append((tag, g, SURF_COLOR['c'] if ar == 'c' else '#8D6E63'))
    for ar, tag in (('c', 'R2\nCtrl'), ('2', 'R2\nNano #2'), ('3', 'R2\nNano #3')):
        g = r2_all[(r2_all.time == '5h') & (r2_all.area == ar)]
        if len(g):
            groups.append((tag, g, SURF_COLOR['c'] if ar == 'c' else
                           (SURF_COLOR['2'] if ar == '2' else SURF_COLOR['3'])))
    if groups:
        fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.4), dpi=200)
        xs = np.arange(len(groups))
        ticklab = ['%s\n%d cells' % (tag, round(g['total'].mean())) for tag, g, _ in groups]
        ax = axes[0]
        ymax = max((g['live'].mean() + g['dead'].mean()) * K for _, g, _ in groups)
        for x, (tag, g, col) in zip(xs, groups):
            lv, dd = g['live'].mean() * K, g['dead'].mean() * K
            ax.bar(x, lv, 0.66, color=C_LIVE, edgecolor='black', linewidth=0.5)
            ax.bar(x, dd, 0.66, bottom=lv, color=C_DEAD, edgecolor='black', linewidth=0.5)
            ax.text(x, lv + dd + ymax * 0.018,
                    '%.1f%%' % (g['live'].sum() / g['total'].sum() * 100),
                    ha='center', fontsize=8.4, color='#444444')
        ax.set_xticks(xs)
        ax.set_xticklabels(ticklab, fontsize=8.0)
        ax.set_ylim(0, ymax * 1.16)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: '{:,.0f}'.format(v)))
        ax.set_ylabel('Cell density (cells/cm$^2$)', fontsize=9)
        ax.set_title('(a) S. aureus 5 h - live + dead density by coupon', fontsize=10.5)
        ax.grid(axis='y', alpha=0.25)
        ax.axvline(1.5, color='#999999', linestyle=':', linewidth=1.0)
        ax.legend(handles=[Patch(facecolor=C_LIVE, edgecolor='black', label='Live'),
                           Patch(facecolor=C_DEAD, edgecolor='black', label='Dead')],
                  frameon=False, fontsize=8.4, loc='upper right')

        ax = axes[1]
        for x, (tag, g, col) in zip(xs, groups):
            v = g['live'].sum() / g['total'].sum() * 100
            ax.bar(x, v, 0.66, color=col, edgecolor='black', linewidth=0.5)
            ax.text(x, v + 3.0, '%.1f%%' % v, ha='center', fontsize=8.4, color='#333333')
        ax.set_xticks(xs)
        ax.set_xticklabels(ticklab, fontsize=8.0)
        ax.set_ylim(0, 120)
        ax.set_ylabel('Viability (%)', fontsize=9)
        ax.set_title('(b) S. aureus 5 h - viability (lower label = mean total cells per field)',
                     fontsize=10.5)
        ax.grid(axis='y', alpha=0.25)
        ax.axvline(1.5, color='#999999', linestyle=':', linewidth=1.0)
        ax.legend(handles=[Patch(facecolor=SURF_COLOR['c'], edgecolor='black', label='Control'),
                           Patch(facecolor=SURF_COLOR['2'], edgecolor='black',
                                 label='Nanopillar (normal)'),
                           Patch(facecolor=SURF_COLOR['3'], edgecolor='black',
                                 label='Nanopillar (QC coupon, re-shot)')],
                  frameon=False, fontsize=7.6, loc='upper left', ncol=3,
                  bbox_to_anchor=(0.0, 1.02))
        fig.suptitle('Validation coupon - near-zero-viability Nanopillar coupon vs a normal coupon '
                     '(S. aureus, 5 h)', fontsize=11.5, y=0.90 if a.demo else 0.965)
        footer(fig, 'Left of the dotted line = repeat 1; right = repeat 2. Sample 3 in repeat 2 is a '
                    're-shot of the problematic coupon: shown here only, never pooled into the '
                    'repeat-2 or combined statistics.', a.demo, y=0.012)
        fig.tight_layout(rect=(0, 0.075, 1, 0.855 if a.demo else 0.925))
        pC = os.path.join(a.out, '650nm_livedead_validation_5h_Saureus%s.png' % suffix)
        fig.savefig(pC)
        plt.close(fig)
        print('figure:', pC)


if __name__ == '__main__':
    main()
