# -*- coding: utf-8 -*-
"""650nm LIVE/DEAD 汇总图 — 堆叠柱状图 (绿=live + 红=dead), repeat 1, 双菌种。
数据源: <DS>/imagej_counts/<species>/livedead_raw_counts.csv (ImageJ 计数, 已几何校验)
输出:   <DS>/imagej_counts/650nm_livedead_timecourse_repeat1.png (+ summary csv)
布局:   行 = 菌种; 列 = (a) 密度堆叠柱 cells/cm² + (b) 存活率柱 (%)
规则:   不完整配对 (缺 g 或 r 通道) 排除; 无任何折线。
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from scipy import stats
from PIL import Image

DS = ('F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - '
      'Ruinong Pan_Antibacterial Surfaces/Live_Dead Bacteria Test/650nm-20261014')
OUT = os.path.join(DS, 'imagej_counts')
AREA = 46946.10
K = 1e8 / AREA  # counts per field -> cells/cm2
ALL_TIMES = ['3h', '5h', '7h', '24h']
SPECIES = [('E.coli', 'E. coli'), ('S.aureus', 'S. aureus')]
RC = {'c': ('Control', 'Ctrl'), '1': ('LIPSS', 'LIPSS'), '2': ('Nanopillar', 'Nano')}
REGIONS = ['c', '1', '2']
C_LIVE, C_DEAD, C_VIAB = '#2E7D32', '#C62828', '#00796B'

rows = []
excl = []
data = {}
for sp_dir, sp_label in SPECIES:
    raw = pd.read_csv(os.path.join(OUT, sp_dir, 'livedead_raw_counts.csv'))
    raw['g_image'] = raw['g_image'].fillna('')
    raw['r_image'] = raw['r_image'].fillna('')
    bad = raw[(raw.g_image == '') | (raw.r_image == '')]
    for _, b in bad.iterrows():
        excl.append('%s %s %s/%s #%s' % (sp_label, b['repeat'], b['time'], b['area'], b['num']))
    ok = raw[(raw.g_image != '') & (raw.r_image != '')].dropna(subset=['live', 'dead']).copy()
    data[sp_label] = ok
    for t in ALL_TIMES:
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
if excl:
    print('排除的不完整配对:', '; '.join(excl))
else:
    print('无不完整配对')

pvals = {}
for sp_label, ok in data.items():
    for t in ALL_TIMES:
        sub = ok[ok.time.astype(str) == t]
        if sub.empty or sub.area.nunique() < 3:
            continue
        grp = [sub[sub.area.astype(str) == reg]['live'] / (sub[sub.area.astype(str) == reg]['live']
               + sub[sub.area.astype(str) == reg]['dead']) * 100 for reg in REGIONS]
        F, p = stats.f_oneway(*grp)
        pvals[(sp_label, t)] = p
        print('%s @ %s ANOVA viability: F=%.2f p=%.4f' % (sp_label, t, F, p))

# ---- figure: stacked bars only, no lines ----
fig, axes = plt.subplots(2, 2, figsize=(11.8, 8.8), dpi=200)
for i, (sp_dir, sp_label) in enumerate(SPECIES):
    sub = S[S.species == sp_label]
    times = [t for t in ALL_TIMES if t in set(sub.time)]
    xs = {}
    for ti, t in enumerate(times):
        for ri, reg in enumerate(REGIONS):
            xs[(t, reg)] = ti * 4 + ri
    groups = [np.mean([xs[(t, reg)] for reg in REGIONS]) for t in times]

    ax = axes[i, 0]
    ymax = (sub['live_cm2'] + sub['dead_cm2']).max()
    for (t, reg), x in xs.items():
        g = sub[(sub.time == t) & (sub.region == reg)]
        if g.empty:
            continue
        lv = g['live_cm2'].iloc[0]
        dd = g['dead_cm2'].iloc[0]
        ax.bar(x, lv, 0.8, color=C_LIVE, edgecolor='black', linewidth=0.5)
        ax.bar(x, dd, 0.8, bottom=lv, color=C_DEAD, edgecolor='black', linewidth=0.5)
        ax.text(x, lv + dd + ymax * 0.012, '%.0f%%' % g['viability_pooled'].iloc[0],
                ha='center', fontsize=7.5, color='#555555')
    ax.set_ylim(0, ymax * 1.18)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: '{:,.0f}'.format(v)))
    ax.set_xticks(list(xs.values()))
    ax.set_xticklabels([RC[reg][1] for (t, reg) in xs], fontsize=8)
    for t, gc in zip(times, groups):
        ax.text(gc, -0.14, t, transform=ax.get_xaxis_transform(),
                ha='center', fontsize=10, fontweight='bold')
    ax.set_xlim(min(xs.values()) - 1, max(xs.values()) + 1)
    ax.set_ylabel('Cell density (cells/cm²)', fontsize=9.5)
    ax.set_title('(%s) %s — live + dead density (stacked)' % ('ac'[i], sp_label), fontsize=10.5)
    ax.legend(handles=[Patch(facecolor=C_LIVE, edgecolor='black', label='Live (green channel)'),
                       Patch(facecolor=C_DEAD, edgecolor='black', label='Dead (red channel)')],
              frameon=False, fontsize=9, loc='upper right')
    ax.grid(axis='y', alpha=0.25)
    miss = [t for t in ALL_TIMES if t not in times]
    if miss:
        ax.text(0.995, 0.02, 'repeat 1 · awaiting ' + ' / '.join(miss), transform=ax.transAxes,
                ha='right', fontsize=7.5, color='#888888', style='italic')

    ax = axes[i, 1]
    for (t, reg), x in xs.items():
        g = sub[(sub.time == t) & (sub.region == reg)]
        if g.empty:
            continue
        vm = g['viability_mean'].iloc[0]
        vs = g['viability_sd'].iloc[0]
        ax.bar(x, vm, 0.8, yerr=vs, capsize=3, color=C_VIAB, edgecolor='black', linewidth=0.5)
        ax.text(x, vm + vs + 2.5, '%.1f%%' % g['viability_pooled'].iloc[0],
                ha='center', fontsize=7.5, color=C_VIAB)
    ax.set_ylim(0, 100)
    ax.set_xticks(list(xs.values()))
    ax.set_xticklabels([RC[reg][1] for (t, reg) in xs], fontsize=8)
    for t, gc in zip(times, groups):
        ax.text(gc, -0.14, t, transform=ax.get_xaxis_transform(),
                ha='center', fontsize=10, fontweight='bold')
        if (sp_label, t) in pvals:
            p = pvals[(sp_label, t)]
            lab = 'p < 0.001' if p < 0.001 else ('ns' if p >= 0.05 else 'p = %.3f' % p)
            ax.text(gc, 94, lab, ha='center', fontsize=8, color='#333333')
    ax.set_xlim(min(xs.values()) - 1, max(xs.values()) + 1)
    ax.set_ylabel('Viability (%)', fontsize=9.5)
    ax.set_title('(%s) %s — viability (labels = pooled %%)' % ('bd'[i], sp_label), fontsize=10.5)
    ax.grid(axis='y', alpha=0.25)

fig.suptitle('650 nm sample — LIVE/DEAD, repeat 1  (preliminary; n = 5 fields per bar; '
             'density = cells/cm²; green = live, red = dead)', fontsize=11)
# ---- exposure scan (from tif metadata) ----
exp_rows = []
for sp_dir, sp_label in SPECIES:
    for t in ALL_TIMES:
        d = os.path.join(DS, sp_dir, 'repeat 1', t)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith('.tif'):
                continue
            desc = str(Image.open(os.path.join(d, f)).tag_v2.get(270, '')).splitlines()
            e = desc[0].strip().replace('Exposure: 000 : 00 : 00 . ', '').split(' :')[0] if desc else '?'
            exp_rows.append(dict(species=sp_label, time=t,
                                 area=RC.get(f.split('-')[0], (f.split('-')[0],))[0],
                                 file=f, exposure_ms=e))
EXP = pd.DataFrame(exp_rows)
EXP.to_csv(os.path.join(OUT, 'exposure_log.csv'), index=False, encoding='utf-8-sig')
exp_notes = []
for (sp_label, t), g in EXP.groupby(['species', 'time']):
    vals = g['exposure_ms'].astype(int)
    mode = int(vals.mode().iloc[0])
    for area, ga in g.groupby('area'):
        vv = ga['exposure_ms'].astype(int)
        dev = sorted(set(vv[vv != mode]))
        if not dev:
            continue
        frac = float(vv.isin(dev).mean())
        exp_notes.append('%s %s %s %s ms%s' % (sp_label, t, area, '/'.join(str(x) for x in dev),
                                               '' if frac == 1 else ' (part)'))
print('exposure exceptions:', '; '.join(exp_notes) if exp_notes else 'none')

note = 'ImageJ 1.54 (bg mode + 40, size 3-500 px) · 40× field area 46 946 µm²'
if exp_notes:
    note += ' · exposure: default 250-300 ms; ' + '; '.join(exp_notes)
if excl:
    note += ' · excluded (incomplete pairs): ' + '; '.join(excl)
fig.text(0.99, 0.01, note, ha='right', fontsize=6.5, color='#666666', style='italic')
fig.tight_layout(rect=(0, 0.03, 1, 0.94))
figp = os.path.join(OUT, '650nm_livedead_timecourse_repeat1.png')
fig.savefig(figp)
plt.close(fig)
print('figure:', figp, os.path.getsize(figp), 'bytes')
