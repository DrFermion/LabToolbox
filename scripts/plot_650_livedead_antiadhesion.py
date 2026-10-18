# -*- coding: utf-8 -*-
"""650nm anti-adhesion figure — (N_control - N_surface) / N_control x 100, repeat 1.

口径 (Materials & Design Eq.4):  Nc = 对照平均, Nt = 处理表面平均;
活菌 (live) 和总数 (total = live + dead) 分别计算。
正值 = 抗黏附 (处理面黏附更少); 负值 = 表观促黏附。
每个时间点并行展示 LIPSS 与 Nanopillar 两个表面。

数据源: <DS>/imagej_counts/<species>/livedead_raw_counts.csv (ImageJ 计数, 与 timecourse 图同源)
输出:   <IC>/650nm_livedead_antiadhesion_repeat1.png (+ _summary.csv)
        + 副本到 LabToolbox mirror 和个人夹
误差棒: 均值之比 delta 法传播 SD (同时含对照与处理面的视野间变异)。
显著性: Welch t 检验 (对照 vs 表面, 每时间点, 未校正) — * p<0.05 ** p<0.01 *** p<0.001。
规则:   不用红/绿 (红绿仅表示死/活); LIPSS=蓝, Nanopillar=橙; 不完整配对排除。
"""
import os
import shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy import stats

DS = ('F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - '
      'Ruinong Pan_Antibacterial Surfaces/Live_Dead Bacteria Test/650nm-20261014')
IC = os.environ.get('LIVEDEAD_650_OUT') or os.path.join(DS, 'imagej_counts')
SIZE_LABEL = os.environ.get('LIVEDEAD_650_SIZE_LABEL', '3\u2013500')
MIRROR = 'E:/LabToolbox/output/livedead_650nm_20261014'
PERSONAL = ('F:/OneDrive - University of Dundee/Ruinong_Pan_Personal/'
            '650nm_LIVE-DEAD_repeat1_20261015')

ALL_TIMES = ['3h', '5h', '7h', '24h']
SPECIES = [('E.coli', 'E. coli'), ('S.aureus', 'S. aureus')]
TREATED = [('1', 'LIPSS'), ('2', 'Nanopillar')]
C_LIPSS, C_NANO = '#1565C0', '#EF6C00'
QC_FLAGS = {('S. aureus', '5h', '2'):
            'S. aureus 5 h Nanopillar: green channel near-empty (possible acquisition issue)'}


def aa_with_sd(ctrl, trat):
    """(mean_c - mean_t)/mean_c x 100 + delta-method SD (both groups' field variation)."""
    mc, mt = ctrl.mean(), trat.mean()
    sc, st = ctrl.std(ddof=1), trat.std(ddof=1)
    aa = (mc - mt) / mc * 100.0
    R = mt / mc
    rel = np.sqrt((sc / np.sqrt(len(ctrl)) / mc) ** 2 + (st / np.sqrt(len(trat)) / mt) ** 2)
    return aa, 100.0 * R * rel


def stars(p):
    if p < 0.001:
        return '***'
    if p < 0.01:
        return '**'
    if p < 0.05:
        return '*'
    return ''


rows = []
excl = []
data = {}
for sp_dir, sp_label in SPECIES:
    raw = pd.read_csv(os.path.join(IC, sp_dir, 'livedead_raw_counts.csv'),
                      encoding='utf-8-sig')
    raw['g_image'] = raw['g_image'].fillna('')
    raw['r_image'] = raw['r_image'].fillna('')
    bad = raw[(raw.g_image == '') | (raw.r_image == '')]
    for _, b in bad.iterrows():
        excl.append('%s %s %s/%s #%s' % (sp_label, b['repeat'], b['time'], b['area'], b['num']))
    ok = raw[(raw.g_image != '') & (raw.r_image != '')].dropna(subset=['live', 'dead']).copy()
    data[sp_label] = ok

    for t in ALL_TIMES:
        gc = ok[(ok.time.astype(str) == t) & (ok.area.astype(str) == 'c')]
        if len(gc) == 0:
            continue
        for reg, reg_name in TREATED:
            gt = ok[(ok.time.astype(str) == t) & (ok.area.astype(str) == reg)]
            if len(gt) == 0:
                continue
            cl, tl = gc['live'].values.astype(float), gt['live'].values.astype(float)
            ct, tt = gc['total'].values.astype(float), gt['total'].values.astype(float)
            aa_l, sd_l = aa_with_sd(cl, tl)
            aa_t, sd_t = aa_with_sd(ct, tt)
            p_l = stats.ttest_ind(cl, tl, equal_var=False).pvalue
            p_t = stats.ttest_ind(ct, tt, equal_var=False).pvalue
            rows.append(dict(species=sp_label, time=t, region=reg, surface=reg_name,
                             n_ctrl=len(gc), n_treat=len(gt),
                             aa_live=aa_l, aa_live_sd=sd_l, aa_total=aa_t, aa_total_sd=sd_t,
                             p_live=p_l, p_total=p_t,
                             ctrl_live_mean=cl.mean(), treat_live_mean=tl.mean(),
                             ctrl_total_mean=ct.mean(), treat_total_mean=tt.mean(),
                             qc_flag='?' if (sp_label, t, reg) in QC_FLAGS else ''))
S = pd.DataFrame(rows)
csv_path = os.path.join(IC, '650nm_livedead_antiadhesion_summary.csv')
S.to_csv(csv_path, index=False, encoding='utf-8-sig')
print(S.round(2).to_string(index=False))
print()
print('excluded (incomplete pairs):', '; '.join(excl) if excl else 'none')

# ---------------- figure ----------------
fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.4), dpi=200)
METRICS = [('live', 'live cells', 'aa_live', 'aa_live_sd', 'p_live'),
           ('total', 'total cells', 'aa_total', 'aa_total_sd', 'p_total')]
for i, (sp_dir, sp_label) in enumerate(SPECIES):
    sub = S[S.species == sp_label]
    times = [t for t in ALL_TIMES if t in set(sub.time)]
    for j, (mkey, mlab, vcol, scol, pcol) in enumerate(METRICS):
        ax = axes[i, j]
        xmin, xmax = None, None
        vals = []
        for ti, t in enumerate(times):
            center = ti * 3.0
            for k, (reg, reg_name) in enumerate(TREATED):
                g = sub[(sub.time == t) & (sub.region == reg)]
                if g.empty:
                    continue
                v = float(g[vcol].iloc[0])
                e = float(g[scol].iloc[0])
                p = float(g[pcol].iloc[0])
                x = center + (k - 0.5) * 1.15
                color = C_LIPSS if reg_name == 'LIPSS' else C_NANO
                flagged = (sp_label, t, reg) in QC_FLAGS
                bar_kw = dict(width=1.0, color=color, edgecolor='black', linewidth=0.5)
                if flagged:
                    bar_kw.update(hatch='///', alpha=0.55)
                ax.bar(x, v, **bar_kw)
                ax.errorbar(x, v, yerr=e, fmt='none', ecolor='#333333', elinewidth=0.9,
                            capsize=3)
                lab = '%.1f%s' % (v, stars(p))
                if flagged:
                    lab += ' ?'
                if v >= 0:
                    ax.text(x, v + e + 3.0, lab, ha='center', fontsize=7.2, color='#333333')
                else:
                    ax.text(x, v - e - 3.0, lab, ha='center', va='top', fontsize=7.2,
                            color='#333333')
                vals += [v, v - e, v + e]
        ax.axhline(0, color='black', linewidth=0.9)
        if vals:
            lo, hi = min(vals), max(vals)
            pad = max(8.0, 0.18 * max(abs(lo), abs(hi)))
            ax.set_ylim(min(lo - pad, -5), max(hi + pad, 5))
        ax.set_xticks([ti * 3.0 for ti in range(len(times))])
        ax.set_xticklabels(times, fontsize=10, fontweight='bold')
        ax.set_xlim(-1.6, (len(times) - 1) * 3.0 + 1.6)
        if j == 0:
            ax.set_ylabel('Anti-adhesion (%)\n(N$_{control}$ \u2212 N$_{surface}$)/N$_{control}$ \u00d7 100',
                          fontsize=9.5)
        ax.set_title('(%s) %s \u2014 %s' % ('ac'[i] if j == 0 else 'bd'[i], sp_label, mlab),
                     fontsize=10.5)
        ax.grid(axis='y', alpha=0.25)
        if i == 0 and j == 0:
            ax.legend(handles=[Patch(facecolor=C_LIPSS, edgecolor='black', label='LIPSS'),
                               Patch(facecolor=C_NANO, edgecolor='black', label='Nanopillar'),
                               Patch(facecolor='white', edgecolor='black', hatch='///',
                                     label='QC-flagged')],
                      frameon=False, fontsize=8.5, loc='lower left')
        if i == 1 and j == 1:
            ax.text(0.995, 0.02, 'repeat 1 \u00b7 n = 5 fields per bar', transform=ax.transAxes,
                    ha='right', fontsize=7.5, color='#888888', style='italic')

fig.suptitle('650 nm sample \u2014 anti-adhesion vs Control, repeat 1  (preliminary; '
             'positive = fewer cells than control; negative = apparent pro-adhesion)',
             fontsize=11)
note = ('ImageJ 1.54 (bg mode + 40, size ' + SIZE_LABEL + ' px) \u00b7 40\u00d7 field area 46 946 \u00b5m\u00b2 \u00b7 '
        'error bars = propagated SD of the ratio (delta method, both groups) \u00b7 '
        'asterisks: Welch t-test control vs surface per time point (uncorrected): '
        '* p<0.05, ** p<0.01, *** p<0.001')
if QC_FLAGS:
    note += ' \u00b7 ? = QC flag: ' + '; '.join(sorted(set(QC_FLAGS.values())))
if excl:
    note += ' \u00b7 excluded (incomplete pairs): ' + '; '.join(excl)
fig.text(0.99, 0.005, note, ha='right', fontsize=6.3, color='#666666', style='italic',
         wrap=True)
fig.tight_layout(rect=(0, 0.045, 1, 0.945))
figp = os.path.join(IC, '650nm_livedead_antiadhesion_repeat1.png')
fig.savefig(figp)
plt.close(fig)
print('figure:', figp, os.path.getsize(figp), 'bytes')

# ---------------- distribute ----------------
if os.environ.get('LIVEDEAD_650_NO_DISTRIBUTE'):
    print('distribution skipped (LIVEDEAD_650_NO_DISTRIBUTE)')
    raise SystemExit(0)
os.makedirs(PERSONAL, exist_ok=True)
os.makedirs(MIRROR, exist_ok=True)
for src in (figp, csv_path):
    for dst_dir in (MIRROR, PERSONAL):
        dst = os.path.join(dst_dir, os.path.basename(src))
        shutil.copy2(src, dst)
        print('copied ->', dst, os.path.getsize(dst))
