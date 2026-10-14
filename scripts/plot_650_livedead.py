# -*- coding: utf-8 -*-
"""650nm LIVE/DEAD 汇总图 (repeat 1 @ 3h, 两个菌种)。
数据源: <DS>/imagej_counts/<species>/livedead_raw_counts.csv (ImageJ 计数, 已几何校验)
输出:   <DS>/imagej_counts/650nm_livedead_3h_repeat1_summary.png (+ .csv)
纵轴  : 密度 = count / 46946.10 µm² 视野 × 1e8 -> cells/cm²
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter
from scipy import stats

DS = ('F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - '
      'Ruinong Pan_Antibacterial Surfaces/Live_Dead Bacteria Test/650nm-20261014')
OUT = os.path.join(DS, 'imagej_counts')
AREA = 46946.10
K = 1e8 / AREA  # counts per field -> cells/cm2
LAB = {'c': 'Control (c)', '1': 'LIPSS (1)', '2': 'Nanopillar (2)'}
order = ['Control (c)', 'LIPSS (1)', 'Nanopillar (2)']
SPECIES = [('E.coli', 'E. coli'), ('S.aureus', 'S. aureus')]
C_LIVE, C_DEAD, C_VIAB = '#2E7D32', '#C62828', '#00796B'

rows = []
for sp_dir, sp_label in SPECIES:
    df = pd.read_csv(os.path.join(OUT, sp_dir, 'livedead_raw_counts.csv'))
    df['region'] = df['area'].astype(str).map(LAB)
    for r in order:
        g = df[df.region == r]
        viab_field = (g['live'] / (g['live'] + g['dead']) * 100).values
        rows.append(dict(species=sp_label, region=r, n=len(g),
                         live=g['live'].mean(), live_sd=g['live'].std(),
                         dead=g['dead'].mean(), dead_sd=g['dead'].std(),
                         viab_mean=viab_field.mean(), viab_sd=viab_field.std(ddof=1),
                         viab_pooled=g['live'].sum() / g['total'].sum() * 100,
                         live_cm2=g['live'].mean() * K, live_cm2_sd=g['live'].std() * K,
                         dead_cm2=g['dead'].mean() * K, dead_cm2_sd=g['dead'].std() * K))
S = pd.DataFrame(rows)
S.to_csv(os.path.join(OUT, '650nm_livedead_3h_repeat1_summary.csv'), index=False, encoding='utf-8-sig')
print(S.round(1).to_string(index=False))

pv = {}
for sp_dir, sp_label in SPECIES:
    df = pd.read_csv(os.path.join(OUT, sp_dir, 'livedead_raw_counts.csv'))
    df['region'] = df['area'].astype(str).map(LAB)
    groups = [df[df.region == r] for r in order]
    F, p = stats.f_oneway(*[g['live'] / (g['live'] + g['dead']) * 100 for g in groups])
    pv[sp_label] = p
    print('%s ANOVA viability: F=%.2f p=%.4f' % (sp_label, F, p))
    F2, p2 = stats.f_oneway(*[np.log10(g['live'] + 1) for g in groups])
    print('%s ANOVA log10(live): F=%.2f p=%.4f' % (sp_label, F2, p2))
    F3, p3 = stats.f_oneway(*[np.log10(g['dead'] + 1) for g in groups])
    print('%s ANOVA log10(dead): F=%.2f p=%.4f' % (sp_label, F3, p3))

fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.6), dpi=200)
x = np.arange(len(order))
w = 0.34
for i, (sp_dir, sp_label) in enumerate(SPECIES):
    sub = S[S.species == sp_label].reset_index(drop=True)
    ax = axes[i, 0]
    ax.bar(x - w/2, sub['live_cm2'], w, yerr=sub['live_cm2_sd'], capsize=4,
           color=C_LIVE, edgecolor='black', linewidth=0.6, label='Live (green channel)')
    ax.bar(x + w/2, sub['dead_cm2'], w, yerr=sub['dead_cm2_sd'], capsize=4,
           color=C_DEAD, edgecolor='black', linewidth=0.6, label='Dead (red channel)')
    top = max((sub['live_cm2'] + sub['live_cm2_sd']).max(), (sub['dead_cm2'] + sub['dead_cm2_sd']).max())
    for xi in range(len(order)):
        ax.text(xi - w/2, sub['live_cm2'][xi] + sub['live_cm2_sd'][xi] + top*0.02,
                '{:,.0f}'.format(sub['live_cm2'][xi]), ha='center', fontsize=8, color=C_LIVE)
        ax.text(xi + w/2, sub['dead_cm2'][xi] + sub['dead_cm2_sd'][xi] + top*0.02,
                '{:,.0f}'.format(sub['dead_cm2'][xi]), ha='center', fontsize=8, color=C_DEAD)
    ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
    ax.set_ylim(0, top*1.25)
    ax.set_xticks(x)
    ax.set_xticklabels(order, fontsize=9)
    ax.set_ylabel('Bacteria density (cells/cm²)', fontsize=9.5)
    ax.set_title('(%s) %s — live vs dead' % ('ac'[i], sp_label), fontsize=10.5)
    ax.legend(frameon=False, fontsize=8.5)
    ax.grid(axis='y', alpha=0.25)

    ax = axes[i, 1]
    ax.bar(x, sub['viab_mean'], 0.55, yerr=sub['viab_sd'], capsize=4,
           color=C_VIAB, edgecolor='black', linewidth=0.6)
    for xi in range(len(order)):
        ax.text(xi, sub['viab_mean'][xi] + sub['viab_sd'][xi] + 2,
                '%.1f%%' % sub['viab_pooled'][xi], ha='center', fontsize=9, color=C_VIAB)
    ax.set_xticks(x)
    ax.set_xticklabels(order, fontsize=9)
    ax.set_ylabel('Viability (%)', fontsize=9.5)
    ax.set_ylim(0, 100)
    ax.set_title('(%s) %s — viability (ANOVA p = %.3f)' % ('bd'[i], sp_label, pv[sp_label]), fontsize=10.5)
    ax.grid(axis='y', alpha=0.25)

fig.suptitle('650 nm sample — LIVE/DEAD, repeat 1 at 3 h  (preliminary, n = 5 fields; bar labels = pooled % per region)', fontsize=11)
fig.text(0.99, 0.01, 'ImageJ 1.54 (bg mode + 40, size 3-500 px) · density = count per 46 946 µm² field area (40×)',
         ha='right', fontsize=7.5, color='#666666', style='italic')
fig.tight_layout(rect=(0, 0.03, 1, 0.95))
figp = os.path.join(OUT, '650nm_livedead_3h_repeat1_summary.png')
fig.savefig(figp)
plt.close(fig)
print('figure:', figp, os.path.getsize(figp), 'bytes')
