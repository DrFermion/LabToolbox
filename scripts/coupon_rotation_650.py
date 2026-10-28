# -*- coding: utf-8 -*-
"""coupon_rotation_650.py — 650 nm LIVE/DEAD: does the same coupon keep its
anti-adhesion character across the rotating timepoint assignment?

Design (Ruinong, 2026-10-28): four coupons (1-4) and four timepoints
(3 / 5 / 7 / 24 h). Each repeat rotates the coupon order by one place:

    repeat 1 : 3h<-1  5h<-2  7h<-3  24h<-4
    repeat 2 : 3h<-2  5h<-3  7h<-4  24h<-1
    repeat 3 : 3h<-3  5h<-4  7h<-1  24h<-2        (folders still empty)
    repeat 4 : 3h<-4  5h<-1  7h<-2  24h<-3        (folders still empty)

So every coupon is imaged at a different timepoint in each repeat, and the
coupon identity of a (repeat, timepoint) folder is fixed by that table. This
script pairs a coupon's two available appearances (repeat 1 and repeat 2) and
asks whether its anti-adhesion (AA) is reproducible.

Statistics reported free of storytelling:
  * per-coupon pairing table (AA at appearance 1 vs appearance 2)
  * Pearson / Spearman across the four coupons + exact permutation p (4! = 24)
  * within-coupon |dAA| compared with the field-to-field noise floor
  * a random-intercept model AA_field ~ C(time) + (1|coupon) for the variance
    split, with the design caveat spelled out (coupon x time x repeat is an
    incomplete Latin square: 8 cells, 8 parameters -> the cell-level coupon
    effect is NOT separately estimable; only the field-level variance split)

Two control bases are computed because repeat 2 is missing/contaminated at
S. aureus 7 h and 24 h:
    base A ("infer")  : control for r2 7/24 h estimated from the treated:control
                        ratio of the timepoints with a real control
    base B ("borrow") : control for r2 7/24 h borrowed from repeat 1
Coupons 4 (r2@7h) and 1 (r2@24h) for S. aureus depend on that choice; for
E. coli no control is missing, so the two bases are identical.

Usage
  python coupon_rotation_650.py --out <dir> [--counts-3px] [--minpx 7]
"""
from __future__ import annotations

import argparse
import itertools
import json
import textwrap
import os

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

DS = ('F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - '
      'Ruinong Pan_Antibacterial Surfaces/Live_Dead Bacteria Test/650nm-20261014')
SPECIES = [('E.coli', 'E. coli'), ('S.aureus', 'S. aureus')]
TIMES = ['3h', '5h', '7h', '24h']
AREAS = [('1', 'LIPSS'), ('2', 'Nano')]
ROTATION = {
    'repeat 1': {'3h': 1, '5h': 2, '7h': 3, '24h': 4},
    'repeat 2': {'3h': 2, '5h': 3, '7h': 4, '24h': 1},
}
C_AREA = {'1': '#1565C0', '2': '#EF6C00'}


def load(path):
    d = pd.read_csv(path, encoding='utf-8-sig')
    d['area'] = d['area'].astype(str)
    d['time'] = d['time'].astype(str)
    d['live'] = pd.to_numeric(d['live'], errors='coerce')
    d['dead'] = pd.to_numeric(d['dead'], errors='coerce')
    d['total'] = d['live'].fillna(0) + d['dead'].fillna(0)
    if 'red_only' not in d.columns:
        d['red_only'] = d['live'].isna() & d['dead'].notna()
    return d


def infer_controls(d):
    """Pooled treated:control ratio over timepoints with a real control, used to
    estimate the absolute cell level of a control that was not measured."""
    ratios = []
    for t in TIMES:
        c = d[(d.time == t) & (d.area == 'c')]
        if len(c) == 0 or bool(c['red_only'].any()):
            continue
        cm = float(c['total'].mean())
        if not cm:
            continue
        for ar in ('1', '2'):
            g = d[(d.time == t) & (d.area == ar)]
            if len(g):
                ratios.append(float(g['total'].mean()) / cm)
    if not ratios:
        return None, []
    return float(np.mean(ratios)), ratios


def build_cells(d, base='infer', r1=None):
    """-> {(time, area): dict(ctrl_mean, ctrl_fields, aa, field_aa, treated_mean)}"""
    ratio, ratios = infer_controls(d)
    out = {}
    for t in TIMES:
        c = d[(d.time == t) & (d.area == 'c')]
        ctrl_fields = None
        if len(c) and not bool(c['red_only'].any()):
            ctrl_fields = [float(v) for v in c['total'].tolist()]
            ctrl_mean = float(np.mean(ctrl_fields))
        else:
            treated = [float(d[(d.time == t) & (d.area == ar)]['total'].mean())
                       for ar in ('1', '2') if len(d[(d.time == t) & (d.area == ar)])]
            if not treated:
                continue
            if base == 'borrow' and r1 is not None:
                c1 = r1[(r1.time == t) & (r1.area == 'c')]
                if len(c1):
                    ctrl_fields = [float(v) for v in c1['total'].tolist()]
                    ctrl_mean = float(np.mean(ctrl_fields))
                else:
                    continue
            else:
                if ratio is None:
                    continue
                ctrl_mean = float(np.mean(treated)) / ratio
                ctrl_fields = None
        for ar in ('1', '2'):
            g = d[(d.time == t) & (d.area == ar)]
            if g.empty:
                continue
            tot = [float(v) for v in g['total'].tolist()]
            out[(t, ar)] = dict(ctrl_mean=ctrl_mean, ctrl_fields=ctrl_fields,
                                treated_mean=float(np.mean(tot)),
                                aa=(ctrl_mean - float(np.mean(tot))) / ctrl_mean * 100.0,
                                field_aa=[(ctrl_mean - v) / ctrl_mean * 100.0 for v in tot])
    return out, ratio, ratios


def perm_p(x, y):
    """Exact permutation p for a correlation, n = 4 (24 pairings)."""
    r_obs = float(np.corrcoef(x, y)[0, 1])
    rs_obs = float(stats.spearmanr(x, y).statistic)
    n = len(x)
    pr = ps = 0
    tot = 0
    for perm in itertools.permutations(range(n)):
        yy = np.array([y[i] for i in perm])
        pr += abs(float(np.corrcoef(x, yy)[0, 1])) >= abs(r_obs) - 1e-12
        ps += abs(float(stats.spearmanr(x, yy).statistic)) >= abs(rs_obs) - 1e-12
        tot += 1
    return r_obs, rs_obs, pr / tot, ps / tot, tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--r1', default=os.path.join(DS, 'imagej_counts'))
    ap.add_argument('--r2', default=os.path.join(DS, 'imagej_counts_repeat2'))
    ap.add_argument('--tag', default='3px')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    rows, pairs, report = [], [], []
    long_rows = []
    for sp_dir, sp_label in SPECIES:
        d1 = load(os.path.join(a.r1, sp_dir, 'livedead_raw_counts.csv'))
        d2 = load(os.path.join(a.r2, sp_dir, 'livedead_raw_counts.csv'))
        for base in ('infer', 'borrow'):
            cells = {}
            for rep, dd, other in (('repeat 1', d1, None), ('repeat 2', d2, d1)):
                c, ratio, ratios = build_cells(dd, base=base, r1=other)
                cells[rep] = c
            for ar, ar_name in AREAS:
                xs, ys, labels, tpair = [], [], [], []
                for coup in (1, 2, 3, 4):
                    t1 = [t for t in TIMES if ROTATION['repeat 1'][t] == coup][0]
                    t2 = [t for t in TIMES if ROTATION['repeat 2'][t] == coup][0]
                    k1, k2 = (t1, ar), (t2, ar)
                    if k1 not in cells['repeat 1'] or k2 not in cells['repeat 2']:
                        continue
                    c1, c2 = cells['repeat 1'][k1], cells['repeat 2'][k2]
                    rows.append(dict(base=base, species=sp_label, area=ar_name, area_code=ar,
                                     coupon=coup, repeat='repeat 1', time=t1,
                                     control=c1['ctrl_mean'], treated=c1['treated_mean'],
                                     aa=c1['aa'], n_fields=len(c1['field_aa'])))
                    rows.append(dict(base=base, species=sp_label, area=ar_name, area_code=ar,
                                     coupon=coup, repeat='repeat 2', time=t2,
                                     control=c2['ctrl_mean'], treated=c2['treated_mean'],
                                     aa=c2['aa'], n_fields=len(c2['field_aa'])))
                    pairs.append(dict(base=base, species=sp_label, area=ar_name, coupon=coup,
                                      time_r1=t1, aa_r1=c1['aa'], time_r2=t2, aa_r2=c2['aa'],
                                      d_aa=c2['aa'] - c1['aa'], abs_d=abs(c2['aa'] - c1['aa'])))
                    xs.append(c1['aa'])
                    ys.append(c2['aa'])
                    labels.append('c%d\n%s>%s' % (coup, t1, t2))
                    tpair.append((coup, t1, t2))
                    for v in c1['field_aa']:
                        long_rows.append(dict(base=base, species=sp_label, area=ar_name,
                                              repeat='repeat 1', time=t1, coupon=coup, aa=v))
                    for v in c2['field_aa']:
                        long_rows.append(dict(base=base, species=sp_label, area=ar_name,
                                              repeat='repeat 2', time=t2, coupon=coup, aa=v))
                if len(xs) >= 3:
                    r, rs, p_r, p_s, nperm = perm_p(np.array(xs), np.array(ys))
                    noise = np.std([v for c in cells.values() for k, c2 in c.items()
                                    if k[1] == ar for v in c2['field_aa']])
                    report.append(dict(base=base, species=sp_label, area=ar_name, n_coupons=len(xs),
                                       pearson_r=r, spearman_rho=rs, perm_p_pearson=p_r,
                                       perm_p_spearman=p_s, n_perm=nperm,
                                       mean_abs_dAA=float(np.mean([abs(y - x) for x, y in zip(xs, ys)])),
                                       within_coupon_sd=float(np.std([y - x for x, y in zip(xs, ys)])),
                                       field_noise_sd=float(noise)))
    df_rows = pd.DataFrame(rows)
    df_pairs = pd.DataFrame(pairs)
    df_rep = pd.DataFrame(report)
    df_long = pd.DataFrame(long_rows)
    df_rows.to_csv(os.path.join(a.out, 'coupon_aa_cells_%s.csv' % a.tag), index=False,
                   encoding='utf-8-sig')
    df_pairs.to_csv(os.path.join(a.out, 'coupon_pairing_%s.csv' % a.tag), index=False,
                    encoding='utf-8-sig')
    df_rep.to_csv(os.path.join(a.out, 'coupon_reproducibility_stats_%s.csv' % a.tag), index=False,
                  encoding='utf-8-sig')
    df_long.to_csv(os.path.join(a.out, 'coupon_field_level_%s.csv' % a.tag), index=False,
                   encoding='utf-8-sig')

    # ---------------- figures ----------------
    fig, axes = plt.subplots(2, 2, figsize=(12.6, 10.2), dpi=200)
    for i, (sp_dir, sp_label) in enumerate(SPECIES):
        for j, (ar, ar_name) in enumerate(AREAS):
            ax = axes[i, j]
            sub = df_pairs[(df_pairs.base == 'infer') & (df_pairs.species == sp_label) &
                           (df_pairs.area == ar_name)]
            xs = sub.aa_r1.to_numpy()
            ys = sub.aa_r2.to_numpy()
            lim = np.nanmax(np.abs(np.concatenate([xs, ys]))) * 1.25
            lim = max(lim, 20)
            ax.axhline(0, color='#bbbbbb', linewidth=0.8)
            ax.axvline(0, color='#bbbbbb', linewidth=0.8)
            ax.plot([-lim, lim], [-lim, lim], color='#999999', linestyle=':', linewidth=1.0)
            ax.axhline(np.nanmean(ys), color=C_AREA[ar], linestyle='--', linewidth=1.0, alpha=0.7)
            ax.axvline(np.nanmean(xs), color=C_AREA[ar], linestyle='--', linewidth=1.0, alpha=0.7)
            for _, r in sub.iterrows():
                ax.scatter(r.aa_r1, r.aa_r2, s=90, color=C_AREA[ar], edgecolor='black',
                           linewidth=0.7, zorder=5)
                ax.annotate('coupon %d\n(%s $\\rightarrow$ %s)' % (r.coupon, r.time_r1, r.time_r2),
                            (r.aa_r1, r.aa_r2), textcoords='offset points', xytext=(6, -12),
                            fontsize=7.0, color='#333333')
            st = df_rep[(df_rep.base == 'infer') & (df_rep.species == sp_label) &
                        (df_rep.area == ar_name)]
            lab = ''
            if len(st):
                s0 = st.iloc[0]
                lab = ('Pearson r = %.2f (exact permutation p = %.2f, n = %d coupons)\n'
                       'mean |delta AA| = %.0f pp; field noise SD = %.0f pp'
                       % (s0.pearson_r, s0.perm_p_pearson, s0.n_coupons,
                          s0.mean_abs_dAA, s0.field_noise_sd))
            ax.set_xlim(-lim, lim)
            ax.set_ylim(-lim, lim)
            ax.set_xlabel("AA in repeat 1 (%) at the coupon's first timepoint", fontsize=9)
            ax.set_ylabel('AA in repeat 2 (%) at its other timepoint', fontsize=9)
            ax.set_title('(%s) %s - %s' % ('abcd'[i * 2 + j], sp_label, ar_name), fontsize=10.5)
            ax.text(0.975, 0.03, lab, transform=ax.transAxes, va='bottom', ha='right',
                    fontsize=7.4, color='#222222',
                    bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#cccccc', alpha=0.92))
            ax.grid(alpha=0.2)
    fig.suptitle('650 nm LIVE/DEAD - is a coupon\'s anti-adhesion reproducible across the rotating '
                 'timepoint assignment?\n(dotted = identical AA; dashed = the two repeat means; '
                 'S. aureus 7/24 h control estimated)', fontsize=11.5, y=0.98)
    fig.tight_layout(rect=(0, 0.03, 1, 0.945))
    p1 = os.path.join(a.out, '650nm_coupon_reproducibility_%s.png' % a.tag)
    fig.savefig(p1)
    plt.close(fig)
    print('figure:', p1)

    # per-coupon trajectories across timepoints
    fig, axes = plt.subplots(2, 2, figsize=(12.6, 8.6), dpi=200)
    cols = {1: '#111111', 2: '#C62828', 3: '#2E7D32', 4: '#6A1B9A'}
    for i, (sp_dir, sp_label) in enumerate(SPECIES):
        for j, (ar, ar_name) in enumerate(AREAS):
            ax = axes[i, j]
            sub = df_rows[(df_rows.base == 'infer') & (df_rows.species == sp_label) &
                          (df_rows.area == ar_name)]
            for coup in (1, 2, 3, 4):
                pts = []
                for _, r in sub[sub.coupon == coup].iterrows():
                    pts.append((TIMES.index(r.time), r.aa, r.repeat))
                pts.sort()
                ax.plot([p[0] for p in pts], [p[1] for p in pts], marker='o', markersize=6,
                        color=cols[coup], linewidth=1.4, label='coupon %d' % coup)
            ax.axhline(0, color='#999999', linewidth=0.9)
            ax.set_xticks(range(len(TIMES)))
            ax.set_xticklabels(TIMES, fontsize=9)
            ax.set_xlim(-0.4, len(TIMES) - 0.6)
            ax.set_ylabel('Anti-adhesion (%)', fontsize=9)
            ax.set_title('(%s) %s - %s' % ('abcd'[i * 2 + j], sp_label, ar_name), fontsize=10.5)
            ax.grid(alpha=0.22)
            if i == 0 and j == 0:
                ax.legend(frameon=False, fontsize=8, ncol=4, loc='lower left')
    fig.suptitle('650 nm LIVE/DEAD - each coupon appears at two different timepoints '
                 '(repeat 1 and repeat 2); a stable coupon would keep its rank/sign',
                 fontsize=11.5, y=0.975)
    note2 = ('Coupon -> timepoint follows the rotation: repeat 1 = 1,2,3,4 for 3/5/7/24 h; '
             'repeat 2 = 2,3,4,1. Only two of the four planned repeats exist, so the coupon identity '
             'is confounded with the timepoint inside each repeat and a coupon effect cannot be '
             'separated from a timepoint effect. S. aureus 7 h and 24 h controls in repeat 2 are '
             'estimates (treated:control ratio), so coupons 4 and 1 lean on that assumption.')
    fig.text(0.005, 0.008, textwrap.fill(note2, 168), ha='left', va='bottom',
             fontsize=6.8, color='#666666', style='italic')
    fig.tight_layout(rect=(0, 0.085, 1, 0.95))
    p2 = os.path.join(a.out, '650nm_coupon_trajectories_%s.png' % a.tag)
    fig.savefig(p2)
    plt.close(fig)
    print('figure:', p2)

    # ---------------- variance split (field level) ----------------
    try:
        import statsmodels.formula.api as smf
        vs = []
        for sp_dir, sp_label in SPECIES:
            for ar, ar_name in AREAS:
                sub = df_long[(df_long.base == 'infer') & (df_long.species == sp_label) &
                              (df_long.area == ar_name)].copy()
                if sub.empty:
                    continue
                sub['coupon'] = sub['coupon'].astype(str)
                try:
                    m = smf.mixedlm('aa ~ C(time)', sub, groups=sub['coupon']).fit(reml=True)
                    v_coup = float(m.cov_re.iloc[0, 0])
                    v_res = float(m.scale)
                except Exception:
                    v_coup = v_res = float('nan')
                vs.append(dict(species=sp_label, area=ar_name, n_fields=len(sub),
                               var_coupon=v_coup, var_field=v_res,
                               icc=v_coup / (v_coup + v_res) if (v_coup + v_res) else float('nan')))
        pd.DataFrame(vs).to_csv(os.path.join(a.out, 'coupon_variance_split_%s.csv' % a.tag),
                                index=False, encoding='utf-8-sig')
        print('\n== random-intercept split: AA ~ C(time) + (1|coupon), field-level data ==')
        for v in vs:
            print('%-9s %-5s  var(coupon)=%6.0f  var(field)=%6.0f  ICC=%+.2f'
                  % (v['species'], v['area'], v['var_coupon'], v['var_field'], v['icc']))
    except Exception as e:
        print('variance split skipped:', e)

    # sign agreement (how often a coupon keeps the sign of its AA)
    sa = []
    for sp_dir, sp_label in SPECIES:
        for ar, ar_name in AREAS:
            sub = df_pairs[(df_pairs.base == 'infer') & (df_pairs.species == sp_label) &
                           (df_pairs.area == ar_name)]
            for _, r in sub.iterrows():
                sa.append((np.sign(r.aa_r1), np.sign(r.aa_r2)))
    if sa:
        pos = float(np.mean([1 if v > 0 else 0 for pair in sa for v in pair]))
        same = sum(1 for a, b in sa if a == b)
        exp = pos ** 2 + (1 - pos) ** 2
        print('\n== sign agreement ==')
        print('same sign in %d/%d coupon-pairs (%.0f%%); expected under independence with a %.0f%% '
              'positive rate = %.0f%%'
              % (same, len(sa), 100.0 * same / len(sa), 100 * pos, 100 * exp))

    print('\n== reproducibility statistics ==')
    for _, r in df_rep.iterrows():
        print('%-9s %-5s base=%-6s n=%d  r=%+.2f (p_perm=%.2f)  rho=%+.2f (p=%.2f)  '
              'mean|dAA|=%.0f pp  field noise SD=%.0f pp'
              % (r.species, r.area, r.base, r.n_coupons, r.pearson_r, r.perm_p_pearson,
                 r.spearman_rho, r.perm_p_spearman, r.mean_abs_dAA, r.field_noise_sd))
    print('\n== per-coupon pairing (base=infer) ==')
    for _, r in df_pairs[df_pairs.base == 'infer'].iterrows():
        print('%-9s %-5s coupon %d: %s %+6.1f%%  ->  %s %+6.1f%%   (dAA %+6.1f pp)'
              % (r.species, r.area, r.coupon, r.time_r1, r.aa_r1, r.time_r2, r.aa_r2, r.d_aa))


if __name__ == '__main__':
    main()
