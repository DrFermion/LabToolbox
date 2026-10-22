# -*- coding: utf-8 -*-
"""compare_650_minpx_3_vs_7.py — 650 nm LIVE/DEAD: min particle size 3 px vs 7 px.

Reads the two count tables per repeat and reports, per condition:
  live / dead / total mean counts, viability, and the change introduced by
  raising the minimum particle size from 3 px to 7 px.

Outputs (into --out):
  650nm_minpx_3_vs_7.csv     per repeat x species x time x area
  650nm_minpx_3_vs_7.png     2 rows (species) x 2 cols: % change in total count,
                             change in viability (percentage points)
"""
from __future__ import annotations

import argparse
import os
import textwrap

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

DS = ('F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - '
      'Ruinong Pan_Antibacterial Surfaces/Live_Dead Bacteria Test/650nm-20261014')
SPECIES = [('E.coli', 'E. coli'), ('S.aureus', 'S. aureus')]
TIMES = ['3h', '5h', '7h', '24h']
AREAS = ['c', '1', '2']
AREA_SHORT = {'c': 'Ctrl', '1': 'LIPSS', '2': 'Nano'}
SURF_COLOR = {'c': '#9E9E9E', '1': '#1565C0', '2': '#EF6C00'}


def load(path):
    d = pd.read_csv(path, encoding='utf-8-sig')
    d['area'] = d['area'].astype(str)
    d['time'] = d['time'].astype(str)
    d['live'] = pd.to_numeric(d['live'], errors='coerce')
    d['dead'] = pd.to_numeric(d['dead'], errors='coerce')
    d['total'] = d['live'].fillna(0) + d['dead'].fillna(0)
    return d


def stats(d):
    out = {}
    for t in TIMES:
        for a in AREAS:
            g = d[(d.time == t) & (d.area == a)].dropna(subset=['live', 'dead'])
            if g.empty:
                continue
            out[(t, a)] = dict(n=len(g), live=g.live.mean(), dead=g.dead.mean(),
                               total=g.total.mean(),
                               viability=g.live.sum() / g.total.sum() * 100)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--r1-min3', default=os.path.join(DS, 'imagej_counts'))
    ap.add_argument('--r1-min7', default=os.path.join(DS, 'imagej_counts_min7_r1'))
    ap.add_argument('--r2-min3', default=os.path.join(DS, 'imagej_counts_repeat2'))
    ap.add_argument('--r2-min7', default=os.path.join(DS, 'imagej_counts_min7_r2'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    rows = []
    for sp_dir, sp_label in SPECIES:
        for rep, d3, d7 in (('repeat 1', a.r1_min3, a.r1_min7),
                            ('repeat 2', a.r2_min3, a.r2_min7)):
            s3 = stats(load(os.path.join(d3, sp_dir, 'livedead_raw_counts.csv')))
            s7 = stats(load(os.path.join(d7, sp_dir, 'livedead_raw_counts.csv')))
            for key in sorted(set(s3) & set(s7), key=lambda k: (TIMES.index(k[0]), AREAS.index(k[1]))):
                t, ar = key
                x3, x7 = s3[key], s7[key]
                rows.append(dict(species=sp_label, repeat=rep, time=t, area=ar, n_fields=x3['n'],
                                 live_3px=x3['live'], live_7px=x7['live'],
                                 dead_3px=x3['dead'], dead_7px=x7['dead'],
                                 total_3px=x3['total'], total_7px=x7['total'],
                                 d_total_pct=(x7['total'] - x3['total']) / x3['total'] * 100
                                 if x3['total'] else np.nan,
                                 d_live_pct=(x7['live'] - x3['live']) / x3['live'] * 100
                                 if x3['live'] else np.nan,
                                 d_dead_pct=(x7['dead'] - x3['dead']) / x3['dead'] * 100
                                 if x3['dead'] else np.nan,
                                 viability_3px=x3['viability'], viability_7px=x7['viability'],
                                 d_viability_pp=x7['viability'] - x3['viability']))
    df = pd.DataFrame(rows)
    csv = os.path.join(a.out, '650nm_minpx_3_vs_7.csv')
    df.to_csv(csv, index=False, encoding='utf-8-sig')
    print('csv:', csv)

    fig, axes = plt.subplots(2, 2, figsize=(13.6, 8.6), dpi=200)
    for i, (sp_dir, sp_label) in enumerate(SPECIES):
        sub = df[(df.species == sp_label)]
        for j, (col, ylab, ttl) in enumerate((
                ('d_total_pct', 'Change in total cells (%)\n7 px vs 3 px',
                 '% change in total-cell count'),
                ('d_viability_pp', 'Change in viability (percentage points)\n7 px vs 3 px',
                 'change in viability'))):
            ax = axes[i, j]
            xs, groups = {}, []
            for ti, t in enumerate(TIMES):
                center = ti * 4.0
                groups.append(center)
                for ai, ar in enumerate(AREAS):
                    xs[(t, ar)] = center + (ai - 1) * 1.05
            for (t, ar), x in xs.items():
                for rep, hatch, alpha in (('repeat 1', None, 1.0), ('repeat 2', '///', 0.45)):
                    g = sub[(sub.time == t) & (sub.area == ar) & (sub.repeat == rep)]
                    if g.empty:
                        continue
                    v = float(g[col].iloc[0])
                    if not np.isfinite(v):
                        continue
                    dx = -0.22 if rep == 'repeat 1' else 0.22
                    ax.bar(x + dx, v, 0.42, color=SURF_COLOR[ar], edgecolor='black',
                           linewidth=0.45, hatch=hatch, alpha=alpha)
            ax.axhline(0, color='#333333', linewidth=0.9)
            vals = [float(v) for v in sub[col].tolist() if np.isfinite(v)]
            if vals:
                lo, hi = min(vals), max(vals)
                ax.set_ylim(min(lo, 0) * 1.14 if lo < 0 else -0.5,
                            max(hi, 0) * 1.14 if hi > 0 else 0.5)
            ax.set_xticks([xs[(t, ar)] for t in TIMES for ar in AREAS])
            ax.set_xticklabels([AREA_SHORT[ar] for t in TIMES for ar in AREAS], fontsize=7.2)
            for t, gc in zip(TIMES, groups):
                ax.text(gc, -0.13, t, transform=ax.get_xaxis_transform(),
                        ha='center', fontsize=10.5, fontweight='bold')
            ax.set_xlim(-1.7, (len(TIMES) - 1) * 4.0 + 1.7)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: '{:,.0f}'.format(v)))
            ax.set_ylabel(ylab, fontsize=8.5)
            ax.set_title('(%s) %s - %s' % ('abcd'[i * 2 + j], sp_label, ttl), fontsize=10.5)
            ax.grid(axis='y', alpha=0.25)
    fig.suptitle('650 nm LIVE/DEAD - effect of raising the minimum particle size from 3 px to 7 px '
                 '(grey = Ctrl, blue = LIPSS, orange = Nano)', fontsize=12, y=0.975)
    note = ('Solid bars = repeat 1, hatched pale bars = repeat 2. Counting rule otherwise unchanged: '
            'ImageJ 1.54, adaptive threshold (background mode + 40), size X-500 px, 40x field area '
            '46 946.10 um2. Negative = fewer cells counted with the 7 px minimum; viability change '
            'is in percentage points. S. aureus 24 h control (repeat 2) is red-channel-as-total and '
            'has no viability.')
    fig.text(0.005, 0.006, textwrap.fill(note, 178), ha='left', va='bottom',
             fontsize=6.9, color='#666666', style='italic')
    fig.tight_layout(rect=(0, 0.075, 1, 0.955))
    png = os.path.join(a.out, '650nm_minpx_3_vs_7.png')
    fig.savefig(png)
    plt.close(fig)
    print('figure:', png)

    print('\n== total-cell count change (7 px vs 3 px), repeat 2 ==')
    q = df[(df.repeat == 'repeat 2')]
    for sp in ('E. coli', 'S. aureus'):
        for t in TIMES:
            bits = []
            for ar in AREAS:
                g = q[(q.species == sp) & (q.time == t) & (q.area == ar)]
                if g.empty:
                    continue
                bits.append('%s %+.0f%% (%.0f->%.0f)' % (AREA_SHORT[ar], g.d_total_pct.iloc[0],
                                                         g.total_3px.iloc[0], g.total_7px.iloc[0]))
            if bits:
                print('%-9s %-4s %s' % (sp, t, '   '.join(bits)))


if __name__ == '__main__':
    main()
