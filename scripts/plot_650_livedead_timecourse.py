# -*- coding: utf-8 -*-
"""650nm LIVE/DEAD 时间历程图 (repeat 1, 双菌种, 随时间更新)。
数据源: <DS>/imagej_counts/<species>/livedead_raw_counts.csv (ImageJ 计数, 已几何校验)
输出:   <DS>/imagej_counts/650nm_livedead_timecourse_repeat1.png (+ .csv)
纵轴  : 密度 = count / 46946.10 µm² 视野 × 1e8 -> cells/cm²
规则  : 不完整配对 (缺 g 或 r 通道) 全部排除, 不参与任何统计。
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
AREA = 46946.10
K = 1e8 / AREA  # counts per field -> cells/cm2
ALL_TIMES = ['3h', '5h', '7h', '24h']
TIMES = ALL_TIMES
SPECIES = [('E.coli', 'E. coli'), ('S.aureus', 'S. aureus')]
RC = {'c': ('Control', '#616161'), '1': ('LIPSS', '#1565C0'), '2': ('Nanopillar', '#EF6C00')}
REGIONS = ['c', '1', '2']

rows = []
excl = []
for sp_dir, sp_label in SPECIES:
    raw = pd.read_csv(os.path.join(OUT, sp_dir, 'livedead_raw_counts.csv'))
    raw['g_image'] = raw['g_image'].fillna('')
    raw['r_image'] = raw['r_image'].fillna('')
    bad = raw[(raw.g_image == '') | (raw.r_image == '')]
    for _, b in bad.iterrows():
        excl.append('%s %s %s/%s #%s (缺%s通道)' % (sp_label, b['repeat'], b['time'], b['area'], b['num'],
                                                   'g' if b['g_image'] == '' else 'r'))
    ok = raw[(raw.g_image != '') & (raw.r_image != '')].dropna(subset=['live', 'dead']).copy()
    for t in TIMES:
        for reg in REGIONS:
            g = ok[(ok.time.astype(str) == t) & (ok.area.astype(str) == reg)]
            if len(g) == 0:
                continue
            vf = (g['live'] / (g['live'] + g['dead']) * 100).values
            rows.append(dict(species=sp_label, time=t, region=reg, region_name=RC[reg][0], n=len(g),
                             live_mean=g['live'].mean(), live_sd=g['live'].std(),
                             dead_mean=g['dead'].mean(), dead_sd=g['dead'].std(),
                             viability_pooled=g['live'].sum() / g['total'].sum() * 100,
                             viability_mean=vf.mean(), viability_sd=vf.std(ddof=1),
                             live_cm2=g['live'].mean() * K, live_cm2_sd=g['live'].std() * K,
                             dead_cm2=g['dead'].mean() * K, dead_cm2_sd=g['dead'].std() * K))
S = pd.DataFrame(rows)
S.to_csv(os.path.join(OUT, '650nm_livedead_timecourse_summary.csv'), index=False, encoding='utf-8-sig')
print(S.round(1).to_string(index=False))
print()
print('排除的不完整配对:')
for e in excl:
    print(' ', e)
print()

# per species-time ANOVA (viability across regions)
for sp_dir, sp_label in SPECIES:
    raw = pd.read_csv(os.path.join(OUT, sp_dir, 'livedead_raw_counts.csv'))
    raw['g_image'] = raw['g_image'].fillna('')
    raw['r_image'] = raw['r_image'].fillna('')
    ok = raw[(raw.g_image != '') & (raw.r_image != '')].dropna(subset=['live', 'dead'])
    for t in TIMES:
        sub = ok[ok.time.astype(str) == t]
        if sub.empty or sub.area.nunique() < 3:
            continue
        grp = [sub[sub.area.astype(str) == reg]['live'] / (sub[sub.area.astype(str) == reg]['live']
               + sub[sub.area.astype(str) == reg]['dead']) * 100 for reg in REGIONS]
        F, p = stats.f_oneway(*grp)
        print('%s @ %s ANOVA viability: F=%.2f p=%.4f' % (sp_label, t, F, p))

# ---- figure ----
fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.6), dpi=200)
xp = {t: i for i, t in enumerate(TIMES)}
for i, (sp_dir, sp_label) in enumerate(SPECIES):
    sub = S[S.species == sp_label]
    present = sorted(set(sub.time), key=lambda t: TIMES.index(t))
    ax = axes[i, 0]
    for reg in REGIONS:
        g = sub[sub.region == reg].sort_values('time', key=lambda c: c.map(xp))
        if g.empty:
            continue
        name, col = RC[reg]
        ax.errorbar([xp[t] for t in g.time], g['viability_mean'], yerr=g['viability_sd'],
                    marker='o', ms=6, lw=2, capsize=4, color=col, label='%s (pooled: %s)' % (
                        name, ', '.join('%.1f%%' % v for v in g['viability_pooled'])))
    ax.set_xticks(range(len(TIMES)))
    ax.set_xticklabels(TIMES)
    ax.set_ylim(0, 100)
    ax.set_xlim(-0.3, len(TIMES) - 0.7)
    ax.set_ylabel('Viability (%)')
    ax.set_title('(%s) %s — viability vs time' % ('ac'[i], sp_label), fontsize=10.5)
    ax.legend(frameon=False, fontsize=8)
    ax.grid(alpha=0.25)

    ax = axes[i, 1]
    for reg in REGIONS:
        g = sub[sub.region == reg].sort_values('time', key=lambda c: c.map(xp))
        if g.empty:
            continue
        name, col = RC[reg]
        ax.errorbar([xp[t] for t in g.time], g['live_cm2'], yerr=g['live_cm2_sd'],
                    marker='o', ms=6, lw=2, capsize=4, color=col, label=name + ' (live)')
        ax.errorbar([xp[t] for t in g.time], g['dead_cm2'], yerr=g['dead_cm2_sd'],
                    marker='s', ms=4.5, lw=1.2, ls='--', capsize=3, color=col, alpha=0.75,
                    label=name + ' (dead)')
    ax.yaxis.set_major_formatter(lambda v, pos: '{:,.0f}'.format(v))
    ax.set_xticks(range(len(TIMES)))
    ax.set_xticklabels(TIMES)
    ax.set_xlim(-0.3, len(TIMES) - 0.7)
    ax.set_ylabel('Cell density (cells/cm²)')
    ax.set_title('(%s) %s — density vs time (solid = live, dashed = dead)' % ('bd'[i], sp_label), fontsize=10.5)
    ax.legend(frameon=False, fontsize=7.5, ncol=2)
    ax.grid(alpha=0.25)

fig.suptitle('650 nm sample — LIVE/DEAD time course, repeat 1 (preliminary; error bars = SD over fields; '
             'density = cells/cm²)', fontsize=11)
note = 'ImageJ 1.54 (bg mode + 40, size 3-500 px) · 40× field area 46 946 µm²'
if excl:
    note += ' · excluded (incomplete pairs): ' + '; '.join(excl)
fig.text(0.99, 0.01, note, ha='right', fontsize=7, color='#666666', style='italic')
fig.tight_layout(rect=(0, 0.03, 1, 0.95))
figp = os.path.join(OUT, '650nm_livedead_timecourse_repeat1.png')
fig.savefig(figp)
plt.close(fig)
print('figure:', figp, os.path.getsize(figp), 'bytes')
