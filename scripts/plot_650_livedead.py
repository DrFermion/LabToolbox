# -*- coding: utf-8 -*-
"""650nm LIVE/DEAD (E. coli, repeat 1, 3h) — 汇总图 + 统计。
数据: imagej_counts/livedead_raw_counts.csv (ImageJ 计数, 已几何校验 30/30 一致)
出图: imagej_counts/650nm_livedead_repeat1_3h_summary.png
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

DS = ('F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - '
      'Ruinong Pan_Antibacterial Surfaces/Live_Dead Bacteria Test/650nm-20261014')
OUT = os.path.join(DS, 'imagej_counts')
df = pd.read_csv(os.path.join(OUT, 'livedead_raw_counts.csv'))

LAB = {'c': 'Control (c)', '1': 'LIPSS (1)', '2': 'Nanopillar (2)'}
order = ['Control (c)', 'LIPSS (1)', 'Nanopillar (2)']
df['region'] = df['area'].astype(str).map(LAB)
AREA = 46946.10  # um^2 per 40x field

rows = []
for r in order:
    g = df[df.region == r]
    viab_field = (g['live'] / (g['live'] + g['dead']) * 100).values
    rows.append(dict(region=r, n=len(g),
                     live=g['live'].mean(), live_sd=g['live'].std(),
                     dead=g['dead'].mean(), dead_sd=g['dead'].std(),
                     viab_mean=viab_field.mean(), viab_sd=viab_field.std(ddof=1),
                     viab_pooled=g['live'].sum() / g['total'].sum() * 100,
                     live_cm2=g['live'].mean() / AREA * 1e8,
                     live_cm2_sd=g['live'].std() / AREA * 1e8,
                     dead_cm2=g['dead'].mean() / AREA * 1e8,
                     dead_cm2_sd=g['dead'].std() / AREA * 1e8))
S = pd.DataFrame(rows)
S.to_csv(os.path.join(OUT, '650nm_livedead_repeat1_3h_summary.csv'), index=False, encoding='utf-8-sig')
print(S.round(2).to_string(index=False))

# stats: one-way ANOVA across regions (viability per field, and log10 live)
grp_v = [df[df.region == r]['live'] / (df[df.region == r]['live'] + df[df.region == r]['dead']) * 100
         for r in order]
F, p = stats.f_oneway(*grp_v)
print('ANOVA viability: F=%.2f p=%.4f' % (F, p))
grp_l = [np.log10(df[df.region == r]['live'] + 1) for r in order]
F2, p2 = stats.f_oneway(*grp_l)
print('ANOVA log10(live+1): F=%.2f p=%.4f' % (F2, p2))
grp_d = [np.log10(df[df.region == r]['dead'] + 1) for r in order]
F3, p3 = stats.f_oneway(*grp_d)
print('ANOVA log10(dead+1): F=%.2f p=%.4f' % (F3, p3))

# ---- figure ----
C_LIVE, C_DEAD = '#2E7D32', '#C62828'   # green = live, red = dead (reserved semantics)
C_VIAB = '#00796B'
x = np.arange(len(order))
w = 0.34
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), dpi=200)

ax = axes[0]
K = 1e8 / AREA  # counts per field -> cells/cm2
lv_cm2, lv_sd_cm2 = S['live'] * K, S['live_sd'] * K
dd_cm2, dd_sd_cm2 = S['dead'] * K, S['dead_sd'] * K
ax.bar(x - w/2, lv_cm2, w, yerr=lv_sd_cm2, capsize=4, color=C_LIVE,
       edgecolor='black', linewidth=0.6, label='Live (green channel)')
ax.bar(x + w/2, dd_cm2, w, yerr=dd_sd_cm2, capsize=4, color=C_DEAD,
       edgecolor='black', linewidth=0.6, label='Dead (red channel)')
for xi in range(len(order)):
    ax.text(xi - w/2, lv_cm2.iloc[xi] + lv_sd_cm2.iloc[xi] + 5000,
            '{:,.0f}'.format(lv_cm2.iloc[xi]), ha='center', fontsize=8.5, color=C_LIVE)
    ax.text(xi + w/2, dd_cm2.iloc[xi] + dd_sd_cm2.iloc[xi] + 5000,
            '{:,.0f}'.format(dd_cm2.iloc[xi]), ha='center', fontsize=8.5, color=C_DEAD)
from matplotlib.ticker import StrMethodFormatter
ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
ax.set_xticks(x)
ax.set_xticklabels(order, fontsize=9.5)
ax.set_ylabel('Bacteria density (cells/cm²)')
ax.set_title('(a) Attached bacteria — live vs dead', fontsize=10.5)
ax.legend(frameon=False, fontsize=9)
ax.grid(axis='y', alpha=0.25)
ax.set_ylim(0, max((lv_cm2 + lv_sd_cm2).max(), (dd_cm2 + dd_sd_cm2).max()) * 1.22)

ax = axes[1]
ax.bar(x, S['viab_mean'], 0.55, yerr=S['viab_sd'], capsize=4, color=C_VIAB,
       edgecolor='black', linewidth=0.6)
for xi, (vm, vp) in enumerate(zip(S['viab_mean'], S['viab_pooled'])):
    ax.text(xi, vm + S['viab_sd'].iloc[xi] + 2, '%.1f%%' % vp, ha='center', fontsize=9.5, color=C_VIAB)
ax.set_xticks(x)
ax.set_xticklabels(order, fontsize=9.5)
ax.set_ylabel('Viability (%)')
ax.set_ylim(0, 100)
ax.set_title('(b) Viability = live / (live + dead)', fontsize=10.5)
ax.grid(axis='y', alpha=0.25)

fig.suptitle('650 nm sample — E. coli LIVE/DEAD, repeat 1 at 3 h  (preliminary, n = 5 fields; '
             'bar labels = pooled %)', fontsize=11)
fig.text(0.99, 0.01, 'ImageJ 1.54 (bg mode + 40, size 3-500 px) · density = count per 46 946 µm² field area (40×)',
         ha='right', fontsize=7.5, color='#666666', style='italic')
fig.tight_layout(rect=(0, 0.03, 1, 0.94))
figp = os.path.join(OUT, '650nm_livedead_repeat1_3h_summary.png')
fig.savefig(figp)
plt.close(fig)
print('figure:', figp, os.path.getsize(figp), 'bytes')
