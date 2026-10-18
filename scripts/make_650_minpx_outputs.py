# -*- coding: utf-8 -*-
"""make_650_minpx_outputs.py — 650 nm LIVE/DEAD：最小像素限制敏感性对比图表

输入:
  <DS>/imagej_counts_no_minpx/<species>/livedead_raw_counts.csv      (min = 0 px, 本次重计)
  <DS>/imagej_counts_no_minpx/minpx_sensitivity.csv                  (min = 0/2/3/5/10/20)
  E:/LabToolbox/output/650_minpx_20261018/backup/<species>_raw_counts_v3-500.csv  (旧口径)
输出 (均写入 <DS>/imagej_counts_no_minpx/):
  compare_3-500_vs_min0.csv       逐条件新旧对照 + 各自 ANOVA p
  survival_anova_old_vs_new.csv   每菌种×时间点的 3 区 ANOVA p (存活率)
  650nm_minpx_viability_compare.png   dumbbell: 旧口径 → 无最小尺寸
  650nm_minpx_sensitivity.png         存活率随 min 尺寸的变化
"""
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy import stats

DS = ('F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - '
      'Ruinong Pan_Antibacterial Surfaces/Live_Dead Bacteria Test/650nm-20261014')
OUT = os.path.join(DS, 'imagej_counts_no_minpx')
BACKUP = 'E:/LabToolbox/output/650_minpx_20261018/backup'
SPECIES = [('E.coli', 'E. coli'), ('S.aureus', 'S. aureus')]
TIMES = ['3h', '5h', '7h', '24h']
REGIONS = ['c', '1', '2']
REG_NAME = {'c': 'Control', '1': 'LIPSS', '2': 'Nanopillar'}
MS_LABEL = {0: 'none (>=1 px)', 2: '2 px', 3: '3 px (previous)', 5: '5 px',
            10: '10 px', 20: '20 px'}
QC = {('S. aureus', '5h', 'Nanopillar'): True}


def p_anova(df, t):
    grps = []
    for reg in REGIONS:
        g = df[(df.time == t) & (df.area.astype(str) == reg)].dropna(subset=['live', 'dead'])
        if len(g) >= 2:
            grps.append(g.live / (g.live + g.dead) * 100)
    if len(grps) < 2:
        return np.nan
    return float(stats.f_oneway(*grps)[1])


def main():
    old = {sp: pd.read_csv(os.path.join(BACKUP, f'{sp}_raw_counts_v3-500.csv'),
                           encoding='utf-8-sig') for sp, _ in SPECIES}
    new = {sp: pd.read_csv(os.path.join(OUT, sp, 'livedead_raw_counts.csv'),
                           encoding='utf-8-sig') for sp, _ in SPECIES}
    sens = pd.read_csv(os.path.join(OUT, 'minpx_sensitivity.csv'), encoding='utf-8-sig')

    rows, p_rows = [], []
    for sp, label in SPECIES:
        for t in TIMES:
            p_old, p_new = p_anova(old[sp], t), p_anova(new[sp], t)
            p_rows.append(dict(species=label, time=t, p_3_500=p_old, p_no_min=p_new,
                               sig_3_500=p_old < 0.05, sig_no_min=p_new < 0.05))
            for reg in REGIONS:
                a = old[sp][(old[sp].time == t) & (old[sp].area.astype(str) == reg)].dropna(subset=['live', 'dead'])
                b = new[sp][(new[sp].time == t) & (new[sp].area.astype(str) == reg)].dropna(subset=['live', 'dead'])
                va = a.live.sum() / a.total.sum() * 100
                vb = b.live.sum() / b.total.sum() * 100
                rows.append(dict(
                    species=label, time=t, region=REG_NAME[reg],
                    live_3_500=a.live.mean(), dead_3_500=a.dead.mean(), viab_3_500=va,
                    live_no_min=b.live.mean(), dead_no_min=b.dead.mean(), viab_no_min=vb,
                    d_live_pct=(b.live.mean() - a.live.mean()) / a.live.mean() * 100,
                    d_dead_pct=(b.dead.mean() - a.dead.mean()) / a.dead.mean() * 100,
                    d_viab_pp=vb - va, p_3_500=p_old, p_no_min=p_new))
    cmp_df = pd.DataFrame(rows)
    cmp_df.to_csv(os.path.join(OUT, 'compare_3-500_vs_min0.csv'), index=False, encoding='utf-8-sig')
    pd.DataFrame(p_rows).to_csv(os.path.join(OUT, 'survival_anova_old_vs_new.csv'),
                                index=False, encoding='utf-8-sig')
    print(cmp_df.round(2).to_string(index=False))

    # ---------------- dumbbell: old -> new viability ----------------
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 5.4), dpi=200, sharey=False)
    for ax, (sp, label) in zip(axes, SPECIES):
        d = cmp_df[cmp_df.species == label].copy()
        d['grp'] = d.time + ' · ' + d.region
        d = d.iloc[::-1].reset_index(drop=True)
        y = np.arange(len(d))
        for i, r in d.iterrows():
            col = '#2E7D32' if r.d_viab_pp >= 0 else '#C62828'
            ax.plot([r.viab_3_500, r.viab_no_min], [i, i], color=col, lw=1.6, alpha=0.8, zorder=1)
            ax.scatter(r.viab_3_500, i, s=42, facecolor='white', edgecolor='#37474F', lw=1.3, zorder=3)
            ax.scatter(r.viab_no_min, i, s=42, color=col, zorder=4)
            if abs(r.d_viab_pp) >= 1:
                ax.text(max(r.viab_3_500, r.viab_no_min) + 1.6, i,
                        '%+.1f pp' % r.d_viab_pp, va='center', fontsize=7.5, color=col)
            if QC.get((label, r.time, r.region)):
                ax.text(-6, i, '?', va='center', ha='right', fontsize=9, color='#E65100')
        ax.set_yticks(y)
        ax.set_yticklabels(d.grp, fontsize=8)
        ax.set_xlabel('Pooled viability (%)', fontsize=9.5)
        ax.set_title(label, fontsize=11, fontweight='bold')
        ax.set_xlim(-10, 105)
        ax.grid(axis='x', alpha=0.25)
        ax.tick_params(axis='x', labelsize=8)
    axes[0].legend(handles=[
        Line2D([], [], marker='o', ls='', markerfacecolor='white', markeredgecolor='#37474F',
               markersize=7, label='size 3–500 px (previous)'),
        Line2D([], [], marker='o', ls='', color='#2E7D32', markersize=7,
               label='no minimum size (this re-count)'),
    ], frameon=False, fontsize=8, loc='lower right')
    fig.suptitle('650 nm LIVE/DEAD — effect of removing the 3 px minimum particle size',
                 fontsize=12, fontweight='bold')
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    p1 = os.path.join(OUT, '650nm_minpx_viability_compare.png')
    fig.savefig(p1)
    plt.close(fig)
    print('figure:', p1)

    # ---------------- sensitivity curves ----------------
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 5.2), dpi=200)
    mins = sorted(sens.min_px.unique())
    for ax, (sp, label) in zip(axes, SPECIES):
        d = sens[sens.species == label]
        shifts = (cmp_df[cmp_df.species == label]
                  .assign(k=lambda x: x.d_viab_pp.abs())
                  .nlargest(3, 'k')[['time', 'region']].values.tolist())
        for (t, reg), g in d.groupby(['time', 'region']):
            g = g.sort_values('min_px')
            hot = [t, REG_NAME[reg]] in [[a, b] for a, b in shifts]
            ax.plot(g.min_px, g.viability_pooled,
                    color=('#1565C0' if hot else '#B0BEC5'),
                    lw=2.2 if hot else 1.0, marker='o', ms=4 if hot else 3,
                    zorder=3 if hot else 1,
                    label=('%s · %s' % (t, REG_NAME[reg])) if hot else None)
        ax.set_xscale('symlog', linthresh=2)
        ax.set_xticks(mins)
        ax.set_xticklabels([MS_LABEL.get(m, str(m)) for m in mins], fontsize=7.5, rotation=20)
        ax.set_xlabel('Minimum particle size (px)', fontsize=9.5)
        ax.set_ylabel('Pooled viability (%)', fontsize=9.5)
        ax.set_title(label, fontsize=11, fontweight='bold')
        ax.grid(alpha=0.25)
        ax.legend(frameon=False, fontsize=7.5, title='largest shifts', title_fontsize=7.5)
    fig.suptitle('Sensitivity of viability to the minimum particle size (max 500 px throughout)',
                 fontsize=12, fontweight='bold')
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    p2 = os.path.join(OUT, '650nm_minpx_sensitivity.png')
    fig.savefig(p2)
    plt.close(fig)
    print('figure:', p2)


if __name__ == '__main__':
    main()
