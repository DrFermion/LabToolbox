# -*- coding: utf-8 -*-
"""plot_livedead_antiadhesion.py — LIVE/DEAD 抗黏附统计图（活菌 + 总菌数），通用版

口径 (Materials & Design Eq.4):
    AA = (N_control - N_surface) / N_control × 100
  正值 = 抗黏附；负值 = 表观促黏附。**同时给活菌 (live) 和总菌数 (live+dead) 两套** ——
  主人 2026-10-18 定规: 以后处理 LIVE/DEAD 结果一律连总菌数抗黏附统计图一起出。

误差棒: 均值之比的 delta 法传播 SD（含两组视野间变异）。
显著性: Welch t 检验（对照 vs 表面，每个时间点，未校正）* / ** / ***。
输入: <ic>/<species>/livedead_raw_counts.csv（repeat,time,area,num,live,dead,total 列；
      由 livedead_cellcounter 引擎输出）。不完整配对自动排除。

用法示例:
  python plot_livedead_antiadhesion.py --ic <数据集>/imagej_counts \
      --area-um2 46946.10 --title "650 nm sample — anti-adhesion vs Control, repeat 1" \
      --out-prefix 650nm --qc-flag "S. aureus|5h|2" --size-label "3–500"
默认: 自动发现 species 子目录、时间点与区域 (c/1/2 → Control/LIPSS/Nanopillar)。
"""
from __future__ import annotations

import argparse
import os
import re

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scipy import stats

DEFAULT_REGIONS = {'c': 'Control', '1': 'LIPSS', '2': 'Nanopillar'}
C_LIPSS, C_NANO = '#1565C0', '#EF6C00'


def aa_with_sd(ctrl, trat):
    """(mean_c - mean_t)/mean_c × 100 + delta 法 SD"""
    mc, mt = ctrl.mean(), trat.mean()
    sc, st = ctrl.std(ddof=1), trat.std(ddof=1)
    aa = (mc - mt) / mc * 100.0
    rel = np.sqrt((sc / np.sqrt(len(ctrl)) / mc) ** 2 + (st / np.sqrt(len(trat)) / mt) ** 2)
    return aa, 100.0 * (mt / mc) * rel


def stars(p):
    return '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''


def time_key(t):
    m = re.match(r'^(\d+)', str(t))
    return int(m.group(1)) if m else 10 ** 6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ic', required=True, help='imagej_counts 目录（内含 <species>/livedead_raw_counts.csv）')
    ap.add_argument('--area-um2', type=float, default=None, help='单视野面积（仅用于标题脚注，可省）')
    ap.add_argument('--regions', default='c:Control,1:LIPSS,2:Nanopillar')
    ap.add_argument('--treated', default='1,2', help='处理区代码（默认 1,2），Control 固定为 c')
    ap.add_argument('--species', default='', help='逗号分隔的 "目录:显示名"，缺省自动发现')
    ap.add_argument('--times', default='', help='逗号分隔的时间点顺序，缺省按数据排序')
    ap.add_argument('--qc-flag', action='append', default=[], help='"species|time|region" 可重复')
    ap.add_argument('--title', default='LIVE/DEAD — anti-adhesion vs Control')
    ap.add_argument('--out-prefix', default='livedead_antiadhesion')
    ap.add_argument('--size-label', default='')
    a = ap.parse_args()

    reg_map = {}
    for item in a.regions.split(','):
        k, v = item.split(':', 1)
        reg_map[k.strip()] = v.strip()
    treated = [x.strip() for x in a.treated.split(',') if x.strip()]
    qc = set()
    for item in a.qc_flag:
        s, t, r = item.split('|')
        qc.add((s.strip(), t.strip(), r.strip()))

    if a.species:
        species = [tuple(x.split(':', 1)) for x in a.species.split(',')]
    else:
        species = [(d, d) for d in sorted(os.listdir(a.ic))
                   if os.path.exists(os.path.join(a.ic, d, 'livedead_raw_counts.csv'))]

    rows, excl, data = [], [], {}
    for sp_dir, sp_label in species:
        raw = pd.read_csv(os.path.join(a.ic, sp_dir, 'livedead_raw_counts.csv'),
                          encoding='utf-8-sig')
        raw['g_image'] = raw['g_image'].fillna('')
        raw['r_image'] = raw['r_image'].fillna('')
        bad = raw[(raw.g_image == '') | (raw.r_image == '')]
        for _, b in bad.iterrows():
            excl.append('%s %s %s/%s #%s' % (sp_label, b['repeat'], b['time'], b['area'], b['num']))
        ok = raw[(raw.g_image != '') & (raw.r_image != '')].dropna(subset=['live', 'dead']).copy()
        ok['total'] = ok.get('total', ok['live'] + ok['dead'])
        data[sp_label] = ok

        times = [t for t in (a.times.split(',') if a.times else sorted(ok.time.astype(str).unique(),
                                                                      key=time_key))]
        for t in times:
            gc = ok[(ok.time.astype(str) == t) & (ok.area.astype(str) == 'c')]
            if len(gc) == 0:
                continue
            for reg in treated:
                gt = ok[(ok.time.astype(str) == t) & (ok.area.astype(str) == reg)]
                if len(gt) == 0:
                    continue
                cl, tl = gc['live'].values.astype(float), gt['live'].values.astype(float)
                ct, tt = gc['total'].values.astype(float), gt['total'].values.astype(float)
                aa_l, sd_l = aa_with_sd(cl, tl)
                aa_t, sd_t = aa_with_sd(ct, tt)
                rows.append(dict(
                    species=sp_label, time=t, region=reg,
                    surface=reg_map.get(reg, reg), n_ctrl=len(gc), n_treat=len(gt),
                    aa_live=aa_l, aa_live_sd=sd_l, aa_total=aa_t, aa_total_sd=sd_t,
                    p_live=stats.ttest_ind(cl, tl, equal_var=False).pvalue,
                    p_total=stats.ttest_ind(ct, tt, equal_var=False).pvalue,
                    ctrl_live_mean=cl.mean(), treat_live_mean=tl.mean(),
                    ctrl_total_mean=ct.mean(), treat_total_mean=tt.mean(),
                    qc_flag='?' if (sp_label, t, reg) in qc else ''))
        S_sp = pd.DataFrame(rows)
    S = pd.DataFrame(rows)
    if S.empty:
        raise SystemExit('没有可统计的对照/处理配对')
    csv_path = os.path.join(a.ic, f'{a.out_prefix}_summary.csv')
    S.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(S.round(2).to_string(index=False))
    print('excluded (incomplete pairs):', '; '.join(excl) if excl else 'none')

    # ---------------- figure: species × (live | total) ----------------
    ncol = 2
    fig, axes = plt.subplots(len(data), ncol, figsize=(6.2 * ncol, 3.1 * len(data) + 1.4),
                             dpi=200, squeeze=False)
    metrics = [('live cells', 'aa_live', 'aa_live_sd', 'p_live'),
               ('total cells (live + dead)', 'aa_total', 'aa_total_sd', 'p_total')]
    letters = ['a', 'b', 'c', 'd', 'e', 'f']
    for i, sp_label in enumerate(data):
        sub = S[S.species == sp_label]
        times = [t for t in dict.fromkeys(sub.time)]
        for j, (mlab, vcol, scol, pcol) in enumerate(metrics):
            ax = axes[i, j]
            vals = []
            for ti, t in enumerate(times):
                center = ti * 3.0
                for k, reg in enumerate(treated):
                    g = sub[(sub.time == t) & (sub.region == reg)]
                    if g.empty:
                        continue
                    v, e, p = float(g[vcol].iloc[0]), float(g[scol].iloc[0]), float(g[pcol].iloc[0])
                    x = center + (k - 0.5) * 1.15
                    color = C_LIPSS if k == 0 else C_NANO
                    flagged = (sp_label, t, reg) in qc
                    kw = dict(width=1.0, color=color, edgecolor='black', linewidth=0.5)
                    if flagged:
                        kw.update(hatch='///', alpha=0.55)
                    ax.bar(x, v, **kw)
                    ax.errorbar(x, v, yerr=e, fmt='none', ecolor='#333333', elinewidth=0.9, capsize=3)
                    lab = '%.1f%s' % (v, stars(p)) + (' ?' if flagged else '')
                    ax.text(x, v + e + 3 if v >= 0 else v - e - 3, lab, ha='center',
                            va='bottom' if v >= 0 else 'top', fontsize=7.2, color='#333333')
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
                ax.set_ylabel('Anti-adhesion (%)\n(N$_{control}$ − N$_{surface}$)/N$_{control}$ × 100',
                              fontsize=9)
            ax.set_title('(%s) %s — %s' % (letters[(i * ncol + j) % len(letters)], sp_label, mlab),
                         fontsize=10.5)
            ax.grid(axis='y', alpha=0.25)
            if i == 0 and j == 0:
                ax.legend(handles=[Patch(facecolor=C_LIPSS, edgecolor='black', label=reg_map.get(treated[0], 'LIPSS')),
                                   Patch(facecolor=C_NANO, edgecolor='black',
                                         label=reg_map.get(treated[-1], 'Nanopillar')),
                                   Patch(facecolor='white', edgecolor='black', hatch='///',
                                         label='QC-flagged')],
                          frameon=False, fontsize=8.5, loc='lower left')
    fig.suptitle(a.title + '  (positive = fewer cells than control; negative = apparent pro-adhesion)',
                 fontsize=11)
    note = 'Welch t-test control vs surface per time point (uncorrected): * p<0.05, ** p<0.01, *** p<0.001'
    if a.area_um2:
        note += ' · field area %.2f µm²' % a.area_um2
    if a.size_label:
        note += ' · ImageJ bg mode + 40, size ' + a.size_label + ' px'
    if qc:
        note += ' · ? = QC-flagged (do not quote)'
    if excl:
        note += ' · excluded (incomplete pairs): ' + '; '.join(excl)
    fig.text(0.99, 0.005, note, ha='right', fontsize=6.3, color='#666666', style='italic')
    fig.tight_layout(rect=(0, 0.045, 1, 0.945))
    figp = os.path.join(a.ic, f'{a.out_prefix}.png')
    fig.savefig(figp)
    plt.close(fig)
    print('figure:', figp)
    print('summary:', csv_path)


if __name__ == '__main__':
    main()
