# -*- coding: utf-8 -*-
"""plot_650_multirepeat.py — 650 nm LIVE/DEAD figures for the NEWEST repeat plus an
N-repeat combined figure (replaces the 2-repeat-only plot_650_repeat2.py going forward).

Why this exists: plot_650_repeat2.py hard-codes "repeat 1 vs repeat 2". Repeat 3 is in,
so the combined figure has to average three repeats while still exposing each repeat's
own mean. Same counting rule, same colours, same layout; the plotting primitives are
imported from plot_650_repeat2 so the two never drift apart.

Counting rule: ImageJ 1.54, adaptive threshold (background mode + 40), size 3-500 px,
40x field area 46 946.10 um2 -> density = count / 46 946.10 um2 * 1e8.

Figures
  A  650nm_livedead_<focus>.png
     2 rows (species) x 2 cols: left = live/dead stacked density, right = total-cell
     density with anti-adhesion % over the treated bars.
  B  650nm_livedead_combined_<all>.png
     same layout, bars = mean of the per-repeat means, empty markers = each repeat.
  C  650nm_livedead_validation_<coupon>.png  (only when an area-3 coupon exists)

Data model: <count dir>/<species>/livedead_raw_counts.csv, columns
  repeat,time,area,num,g_image,r_image,live,dead,total,dead_rate
area codes: c = Control, 1 = LIPSS, 2 = Nanopillar, 3 = extra re-shot coupon (never
pooled, only figure C).

Per-repeat fixups (all optional, keyed by the repeat LABEL you pass in --rep):
  --drop     "species|time|area|label"      remove a superseded measurement from that repeat
  --borrow   "species|time|label=donor"     that repeat's control is missing -> borrow the
                                            whole control (total + viability) from donor
  --viabfrom "species|time|label=donor"     that repeat's control has no green channel
                                            (red counted as total): total stays local,
                                            viability/live-dead come from donor

Usage
  python plot_650_multirepeat.py --out <dir> --focus "repeat 3" \
      --rep "repeat 1=<...>/imagej_counts" \
      --rep "repeat 2=<...>/imagej_counts_repeat2" \
      --rep "repeat 3=<...>/imagej_counts_repeat3" \
      --borrow "S.aureus|7h|repeat 2=repeat 1" \
      --viabfrom "S.aureus|24h|repeat 2=repeat 1" \
      --drop "S.aureus|5h|2|repeat 1" --exclude-3
"""
from __future__ import annotations

import argparse
import os
import sys
import textwrap

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plot_650_repeat2 as base          # noqa: E402  (shared primitives / constants)

SPECIES = base.SPECIES
TIMES = base.TIMES
AREAS = base.AREAS
AREA_SHORT = base.AREA_SHORT
SURF_COLOR = base.SURF_COLOR
C_LIVE, C_DEAD = base.C_LIVE, base.C_DEAD
K = base.K
load_raw = base.load_raw
group_stats = base.group_stats
_xmap = base._xmap
_time_labels = base._time_labels
footer = base.footer
display_table = base.display_table

MARKERS = ['o', 's', '^', 'D', 'v']


# ---------------------------------------------------------------- helpers
def norm(x):
    return x.replace('.', '').replace(' ', '').lower()


def parse_rep(spec):
    if '=' not in spec:
        raise SystemExit('--rep wants "label=dir", got %r' % spec)
    lbl, d = spec.split('=', 1)
    return lbl.strip(), d.strip()


def parse_trip(spec, n=3):
    parts = spec.split('|')
    if len(parts) != n:
        raise SystemExit('%r: expected %d |-separated fields, got %d' % (spec, n, len(parts)))
    return [p.strip() for p in parts]


def load_repeat(dirpath, exclude_3):
    out = {}
    for sp_dir, sp_label in SPECIES:
        p = os.path.join(dirpath, sp_dir, 'livedead_raw_counts.csv')
        if not os.path.isfile(p):
            print('  ! missing %s' % p)
            continue
        raw = load_raw(p)
        if exclude_3:
            raw = raw[raw.area != '3']
        out[sp_label] = raw
    return out


def apply_drop(store, label, drops):
    for sp_b, t_b, ar_b, lb in drops:
        if lb != label or sp_b not in store:
            continue
        d0 = store[sp_b]
        keep = ~((d0.time == t_b) & (d0.area == ar_b))
        n = int((~keep).sum())
        if n:
            store[sp_b] = d0[keep]
            print('  [%s] dropped %s %s area %s (%d rows) - superseded measurement'
                  % (label, sp_b, t_b, ar_b, n))


def panel_stacked_n(ax, cd, times, title, labels, marks=True):
    xs, groups = _xmap(times, AREAS)
    ymax = 0.0
    for col in ('live_cm2', 'dead_cm2', 'total_cm2'):
        v = cd[col].max(skipna=True)
        if np.isfinite(v):
            ymax = max(ymax, float(v))
    for col in cd.columns:
        if col.startswith('r_') and col.endswith('_live'):
            v = cd[col].max(skipna=True)
            if np.isfinite(v):
                ymax = max(ymax, float(v))
    for (t, a), x in xs.items():
        g = cd[(cd.time == t) & (cd.area == a)]
        if g.empty or not np.isfinite(float(g['live_cm2'].iloc[0])):
            continue
        lv, dd = float(g['live_cm2'].iloc[0]), float(g['dead_cm2'].iloc[0])
        ax.bar(x, lv, 0.9, color=C_LIVE, edgecolor='black', linewidth=0.45)
        ax.bar(x, dd, 0.9, bottom=lv, color=C_DEAD, edgecolor='black', linewidth=0.45)
        for j, lb in enumerate(labels):
            col = 'r_%d_live' % j
            if not marks or col not in g.columns:
                continue
            rv = float(g[col].iloc[0])
            if not np.isfinite(rv):
                continue
            ax.plot(x + mark_dx(len(labels), j), rv, marker=MARKERS[j % len(MARKERS)],
                    markersize=4.4, markerfacecolor='white', markeredgecolor='black',
                    markeredgewidth=0.9, zorder=5)
        if np.isfinite(float(g['viability'].iloc[0])):
            ax.text(x, lv + dd + ymax * 0.012, '%.0f%%' % float(g['viability'].iloc[0]),
                    ha='center', va='bottom', fontsize=6.8, color='#444444')
    ax.set_ylim(0, ymax * 1.14 if ymax else 1)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: '{:,.0f}'.format(v)))
    _time_labels(ax, times, xs, groups, AREAS)
    ax.set_ylabel('Cell density (cells/cm$^2$)', fontsize=9)
    ax.set_title(title, fontsize=10.2)
    ax.grid(axis='y', alpha=0.25)


def panel_total_n(ax, cd, times, title, labels, marks=True, notes=()):
    xs, groups = _xmap(times, AREAS)
    ymax = 0.0
    for (t, a), x in xs.items():
        g = cd[(cd.time == t) & (cd.area == a)]
        if g.empty:
            continue
        v = float(g['total_cm2'].iloc[0])
        e = float(g['total_cm2_sd'].iloc[0])
        if not np.isfinite(e):
            e = 0.0
        ax.bar(x, v, 0.9, color=SURF_COLOR[a], edgecolor='black', linewidth=0.45)
        if np.isfinite(e) and e > 0:
            ax.errorbar(x, v, yerr=e, fmt='none', ecolor='#333333', elinewidth=0.9, capsize=3)
        for j, lb in enumerate(labels):
            col = 'r_%d_total' % j
            if not marks or col not in g.columns:
                continue
            rv = float(g[col].iloc[0])
            if not np.isfinite(rv):
                continue
            ax.plot(x + mark_dx(len(labels), j), rv, marker=MARKERS[j % len(MARKERS)],
                    markersize=4.4, markerfacecolor='white', markeredgecolor='black',
                    markeredgewidth=0.9, zorder=5)
        if a != 'c':
            c = cd[(cd.time == t) & (cd.area == 'c')]
            aa_v = np.nan
            if 'aa' in cd.columns and np.isfinite(float(g['aa'].iloc[0])):
                aa_v = float(g['aa'].iloc[0])          # mean of the per-repeat AA values
            elif not c.empty:
                cc = float(c['total_cm2'].iloc[0])
                if cc and np.isfinite(cc):
                    aa_v = (cc - v) / cc * 100.0
            if np.isfinite(aa_v):
                lab = '0%' if abs(aa_v) < 0.5 else '%.0f%%' % aa_v
                ax.text(x, v + e + ymax * 0.02, lab, ha='center', va='bottom',
                        fontsize=7.0, color='#222222')
        ymax = max(ymax, v + e)
    for j, lb in enumerate(labels):
        col = 'r_%d_total' % j
        if col in cd.columns:
            v = cd[col].max(skipna=True)
            if np.isfinite(v):
                ymax = max(ymax, float(v))
    ax.set_ylim(0, ymax * 1.16 if ymax else 1)
    for t, a, msg in notes:                     # flags on individual columns
        if (t, a) in xs:
            ax.text(xs[(t, a)], ax.get_ylim()[1] * 0.99, msg, ha='center',
                    va='top', fontsize=9.5, fontweight='bold', color='#6A1B9A', zorder=8)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: '{:,.0f}'.format(v)))
    _time_labels(ax, times, xs, groups, AREAS)
    ax.set_ylabel('Total cells (live + dead), cells/cm$^2$', fontsize=9)
    ax.set_title(title, fontsize=10.2)
    ax.grid(axis='y', alpha=0.25)


def mark_dx(n, j):
    """Horizontal offset for the n per-repeat markers inside one bar."""
    if n <= 1:
        return 0.0
    step = 0.42 / (n - 1)
    return (j - (n - 1) / 2.0) * step


def legend_n(fig, labels, y=0.062):
    h = [Patch(facecolor=C_LIVE, edgecolor='black', label='Live (green channel)'),
         Patch(facecolor=C_DEAD, edgecolor='black', label='Dead (red channel)'),
         Patch(facecolor=SURF_COLOR['c'], edgecolor='black', label='Control area'),
         Patch(facecolor=SURF_COLOR['1'], edgecolor='black', label='LIPSS area'),
         Patch(facecolor=SURF_COLOR['2'], edgecolor='black', label='Nanopillar area')]
    for j, lb in enumerate(labels):
        h.append(plt.Line2D([], [], marker=MARKERS[j % len(MARKERS)], linestyle='none',
                            markerfacecolor='white', markeredgecolor='black',
                            label='%s mean' % lb))
    fig.legend(handles=h, loc='lower center', bbox_to_anchor=(0.5, y), ncol=len(h),
               frameon=False, fontsize=8.6, handlelength=1.6, columnspacing=1.4)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rep', action='append', default=[], help='"label=count dir" (repeatable)')
    ap.add_argument('--focus', default='', help='repeat label drawn on its own (default: last)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--drop', action='append', default=[], help='"species|time|area|label"')
    ap.add_argument('--borrow', action='append', default=[], help='"species|time|label=donor"')
    ap.add_argument('--viabfrom', action='append', default=[], help='"species|time|label=donor"')
    ap.add_argument('--infer', action='append', default=[], help='"species|label" (control estimate)')
    ap.add_argument('--exclude-3', action='store_true')
    ap.add_argument('--no-marks', action='store_true')
    ap.add_argument('--plain', action='store_true')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    reps = [parse_rep(s) for s in a.rep]
    if not reps:
        raise SystemExit('need at least one --rep "label=dir"')
    labels = [lb for lb, _ in reps]
    focus = a.focus or labels[-1]
    if focus not in labels:
        raise SystemExit('--focus %r is not one of %s' % (focus, labels))
    # input order is kept for the combined figure (repeat 1, 2, 3 ...); --focus only picks
    # which repeat gets its own figure
    dirs = dict(reps)
    drops = [parse_trip(s, 4) for s in a.drop]
    borrows = [parse_trip(s, 3) for s in a.borrow]
    viabs = [parse_trip(s, 3) for s in a.viabfrom]
    infers = [parse_trip(s, 2) for s in a.infer]

    print('repeats:', ', '.join('%s <- %s' % (lb, dirs[lb]) for lb in labels))
    store = {lb: load_repeat(dirs[lb], a.exclude_3) for lb in labels}
    for lb in labels:
        print('  [%s] %s' % (lb, ', '.join('%s: %d rows' % (sp, len(d)) for sp, d in store[lb].items())))
        apply_drop(store, lb, drops)

    # views: total (red-as-total kept) + viability (both channels counted)
    tot_view, viab_view = {}, {}
    for lb in labels:
        tot_view[lb], viab_view[lb] = {}, {}
        for sp, raw in store[lb].items():
            tot_view[lb][sp] = raw
            viab_view[lb][sp] = raw[raw.live.notna()].copy()

    # ---------------- infer a control that was never measured / was contaminated -------
    # Same method as the repeat-2 delivery (references/livedead-multi-repeat-figures.md
    # §10.2): ratios treated:control taken only from timepoints whose control is a real,
    # non-red-only measurement; pooled ratio -> control estimate at the broken timepoint.
    EST = {}
    for sp_b, lb in infers:
        if lb not in labels:
            print('  ! --infer: unknown label %r' % lb)
            continue
        for sp_label in list(store[lb].keys()):
            if norm(sp_b) != norm(sp_label):
                continue
            pristine = store[lb][sp_label]                 # before borrow/viabfrom
            ratios = []
            for t in TIMES:
                c = pristine[(pristine.time == t) & (pristine.area == 'c')]
                if len(c) == 0:
                    continue
                if 'red_only' in c.columns and bool(c['red_only'].any()):
                    continue                                # contaminated: not a real control
                cm = float(c['total'].mean())
                if not cm:
                    continue
                for ar in ('1', '2'):
                    g = pristine[(pristine.time == t) & (pristine.area == ar)]
                    if len(g):
                        ratios.append((t, ar, float(g['total'].mean()) / cm))
            if not ratios:
                continue
            R = float(np.mean([r[2] for r in ratios]))
            lo = float(np.min([r[2] for r in ratios]))
            hi = float(np.max([r[2] for r in ratios]))
            for t in TIMES:
                tv = tot_view[lb][sp_label]
                cc = tv[(tv.time == t) & (tv.area == 'c')]
                real = len(cc) and not ('red_only' in cc.columns and bool(cc['red_only'].any()))
                if real:
                    continue
                vals = [float(pristine[(pristine.time == t) & (pristine.area == ar)]['total'].mean())
                        for ar in ('1', '2') if len(pristine[(pristine.time == t) & (pristine.area == ar)])]
                if not vals:
                    continue
                mt = float(np.mean(vals))
                est = mt / R
                tv = tv[~((tv.time == t) & (tv.area == 'c'))]
                row = dict(repeat='%s (control inferred)' % lb, time=t, area='c', num=0,
                           g_image='', r_image='', live=np.nan, dead=est, total=est,
                           dead_rate=np.nan, red_only=True)
                tot_view[lb][sp_label] = pd.concat([tv, pd.DataFrame([row])], ignore_index=True)
                EST[(lb, sp_label, t)] = dict(
                    treated=mt, ratio=R, lo=lo, hi=hi, n_pairs=len(ratios), est=est,
                    lo_c=mt / hi, hi_c=mt / lo,
                    basis='; '.join('%s@%s %.3f' % ('LIPSS' if r[1] == '1' else 'Nano', r[0], r[2])
                                    for r in ratios))
                print('  [%s] %s %s control inferred -> %.0f cells/field (range %.0f-%.0f); '
                      'pooled treated:control ratio %.3f from %d pairs'
                      % (lb, sp_label, t, est, mt / hi, mt / lo, R, len(ratios)))
    if EST:
        pd.DataFrame([dict(species=k[1], time=k[2], repeat=k[0], treated_mean=v['treated'],
                           ratio_mean=v['ratio'], ratio_min=v['lo'], ratio_max=v['hi'],
                           n_pairs=v['n_pairs'], control_est=v['est'],
                           control_lo=v['lo_c'], control_hi=v['hi_c'], basis=v['basis'])
                      for k, v in sorted(EST.items())]).to_csv(
            os.path.join(a.out, '650nm_control_inference.csv'), index=False, encoding='utf-8-sig')

    # borrow the whole control / only the viability of a contaminated control
    for kind, specs, target in (('borrow', borrows, (tot_view, viab_view)),
                                ('viabfrom', viabs, (viab_view,))):
        for sp_b, t_b, rest in specs:
            if '=' not in rest:
                raise SystemExit('%s wants "label=donor", got %r' % (kind, rest))
            lb, donor = [x.strip() for x in rest.split('=', 1)]
            if lb not in labels or donor not in labels:
                print('  ! %s: unknown label in %r' % (kind, rest))
                continue
            for sp_label in list(store[lb].keys()):
                if norm(sp_b) != norm(sp_label):
                    continue
                for views in target:
                    have = views[lb][sp_label]
                    if len(have[(have.time == t_b) & (have.area == 'c')]):
                        continue
                    d0 = store[donor].get(sp_label)
                    if d0 is None:
                        continue
                    src = d0 if views is tot_view[lb] else d0[d0.live.notna()]
                    donor_rows = src[(src.time == t_b) & (src.area == 'c')].copy()
                    if not len(donor_rows):
                        continue
                    donor_rows['repeat'] = '%s (borrowed from %s)' % (lb, donor)
                    views[lb][sp_label] = pd.concat([views[lb][sp_label], donor_rows],
                                                    ignore_index=True)
                    if views is target[-1]:
                        print('  [%s] %s %s control <- %s (%d fields, %s)'
                              % (lb, sp_label, t_b, donor, len(donor_rows), kind))

    # per-repeat display tables (what figure A uses, focus repeat only)
    tables = {lb: {} for lb in labels}
    for lb in labels:
        for sp in store[lb]:
            times = [t for t in TIMES if t in set(tot_view[lb][sp].time)]
            tables[lb][sp] = display_table(tot_view[lb][sp], viab_view[lb][sp], times)

    # ---------------- A. focus repeat ----------------
    fig, axes = plt.subplots(2, 2, figsize=(14.2, 9.6), dpi=200)
    rows = []
    for i, (sp_dir, sp_label) in enumerate(SPECIES):
        if sp_label not in tables[focus]:
            continue
        st = tables[focus][sp_label]
        times = [t for t in TIMES if t in set(st.time)]
        rows.append(st.assign(species=sp_label))
        base.panel_stacked(axes[i, 0], st, times, AREAS,
                           '(%s) %s - live + dead density (stacked)' % ('ac'[i], sp_label))
        base.panel_total(axes[i, 1], tot_view[focus][sp_label], st, times, AREAS,
                         '(%s) %s - total-cell adhesion (labels = anti-adhesion %%)'
                         % ('bd'[i], sp_label))
    fix = []
    for kind, specs in (('borrowed control', borrows), ('borrowed viability', viabs)):
        fix += ['%s %s %s <- %s' % (s, t, kind, r.split('=')[-1]) for s, t, r in specs
                if r.split('=')[0].strip() == focus]
    ttl = '650 nm textured stainless steel - LIVE/DEAD, %s' % focus
    fig.suptitle(ttl + (' (control borrowed: ' + '; '.join(fix) + ')' if fix else ''),
                 fontsize=12.5, y=0.975)
    base.figure_legend(fig, y=0.062)
    note = ('ImageJ 1.54 adaptive threshold (background mode + 40), size 3-500 px; 40x field area '
            '46 946 um2; bars = mean of 5 fields; % over stacked bars = pooled viability; '
            'error bars = SD of the 5 fields; % over adhesion bars = anti-adhesion vs the '
            'control of the same timepoint.')
    if fix:
        note += '  Borrowed values: ' + '; '.join(fix) + ' (different coupon batch, qualitative only).'
    if a.exclude_3:
        note += '  Extra re-shot coupon (sample 3) excluded from every statistic.'
    footer(fig, note, False)
    fig.tight_layout(rect=(0, 0.085, 1, 0.95))
    pA = os.path.join(a.out, '650nm_livedead_%s.png' % focus.replace(' ', ''))
    fig.savefig(pA)
    plt.close(fig)
    pd.concat(rows).to_csv(os.path.join(a.out, '650nm_livedead_%s_summary.csv'
                                        % focus.replace(' ', '')), index=False,
                           encoding='utf-8-sig')
    print('figure:', pA)

    # ---------------- B. combined over all repeats ----------------
    comb_rows, aa_rows = [], []
    for sp_dir, sp_label in SPECIES:
        have = [lb for lb in labels if sp_label in tables[lb]]
        if not have:
            continue
        times = [t for t in TIMES if any(t in set(tables[lb][sp_label].time) for lb in have)]
        for t in times:
            for ar in AREAS:
                per = {}
                for lb in have:
                    st = tables[lb][sp_label]
                    g = st[(st.time == t) & (st.area == ar)]
                    if g.empty:
                        continue
                    per[lb] = dict(live=float(g['live_cm2'].iloc[0]),
                                   dead=float(g['dead_cm2'].iloc[0]),
                                   total=float(g['total_cm2'].iloc[0]),
                                   viab=float(g['viability'].iloc[0]))
                if not per:
                    continue
                def mn(key):
                    v = [x[key] for x in per.values() if np.isfinite(x[key])]
                    return (float(np.mean(v)) if v else np.nan,
                            float(np.std(v, ddof=1)) if len(v) > 1 else np.nan, len(v))
                live, live_sd, _ = mn('live')
                dead, dead_sd, _ = mn('dead')
                total, total_sd, n_tot = mn('total')
                viab, _, _ = mn('viab')
                row = dict(species=sp_label, time=t, area=ar, n_repeats=n_tot,
                           live_cm2=live, live_sd=live_sd, dead_cm2=dead, dead_sd=dead_sd,
                           total_cm2=total, total_cm2_sd=total_sd, viability=viab,
                           repeats=','.join(per))
                for j, lb in enumerate(labels):
                    p = per.get(lb, {})
                    row['r_%d_live' % j] = p.get('live', np.nan)
                    row['r_%d_total' % j] = p.get('total', np.nan)
                    row['r_%d_viab' % j] = p.get('viab', np.nan)
                comb_rows.append(row)
        # per-repeat + combined anti-adhesion (total cells)
        cd = pd.DataFrame([r for r in comb_rows if r['species'] == sp_label])
        for t in times:
            cc = cd[(cd.time == t) & (cd.area == 'c')]
            if cc.empty:
                continue
            c_tot = float(cc['total_cm2'].iloc[0])
            for ar in ('1', '2'):
                row = dict(species=sp_label, time=t, area=ar)
                for j, lb in enumerate(labels):
                    col = 'r_%d_total' % j
                    v = float(cd[(cd.time == t) & (cd.area == ar)][col].iloc[0])
                    vc = float(cd[(cd.time == t) & (cd.area == 'c')][col].iloc[0])
                    row['%s_AA%%' % lb] = ((vc - v) / vc * 100.0) if (vc and np.isfinite(vc)
                                                                     and np.isfinite(v)) else np.nan
                g = cd[(cd.time == t) & (cd.area == ar)]
                v = float(g['total_cm2'].iloc[0])
                row['combined_AA%'] = ((c_tot - v) / c_tot * 100.0) if c_tot else np.nan
                aa_rows.append(row)

    COMB = pd.DataFrame(comb_rows)
    AA = pd.DataFrame(aa_rows)
    # Anti-adhesion is averaged over the per-repeat values (each repeat against its OWN
    # control) instead of one AA from the pooled totals: repeat batches differ by up to 2x
    # in absolute density, so a pooled control mixes coupons that are not comparable.
    if len(AA):
        aa_cols = [c for c in AA.columns if c.endswith('_AA%') and c != 'combined_AA%']
        AA['aa'] = AA[aa_cols].mean(axis=1)
        AA['aa_sd'] = AA[aa_cols].std(axis=1, ddof=1)
        AA['n_aa'] = AA[aa_cols].notna().sum(axis=1)
        COMB = COMB.merge(AA[['species', 'time', 'area', 'aa', 'aa_sd', 'n_aa']],
                          on=['species', 'time', 'area'], how='left')
    COMB.to_csv(os.path.join(a.out, '650nm_livedead_combined_summary.csv'), index=False,
                encoding='utf-8-sig')
    AA.to_csv(os.path.join(a.out, '650nm_livedead_perrepeat_aa.csv'),
              index=False, encoding='utf-8-sig')
    if len(labels) > 1:
        fig, axes = plt.subplots(2, 2, figsize=(14.2, 9.6), dpi=200)
        for i, (sp_dir, sp_label) in enumerate(SPECIES):
            cd = COMB[COMB.species == sp_label].copy()
            if cd.empty:
                continue
            times = [t for t in TIMES if t in set(cd.time)]
            marks = not a.no_marks
            panel_stacked_n(axes[i, 0], cd, times,
                            '(%s) %s - live + dead density, %s combined'
                            % ('ac'[i], sp_label, ' + '.join(labels)), labels, marks=marks)
            notes = []
            if not a.plain:
                for kind, specs in (('b', borrows), ('v', viabs)):
                    for s_b, t_b, rest in specs:
                        if norm(s_b) == norm(sp_label) and rest.split('=')[0].strip() in labels:
                            notes.append((t_b, 'c', '$\\ast$' if kind == 'b' else '$\\ddagger$'))
                for s_b, lb in infers:
                    if norm(s_b) == norm(sp_label) and lb in labels:
                        for t_b in times:
                            if any(k0 == lb and norm(k1) == norm(sp_label) and k2 == t_b
                                   for k0, k1, k2 in EST):
                                notes.append((t_b, 'c', '$\\S$'))
            panel_total_n(axes[i, 1], cd, times,
                          '(%s) %s - total-cell adhesion, %s combined'
                          % ('bd'[i], sp_label, ' + '.join(labels)), labels, marks=marks,
                          notes=notes)
        fig.suptitle('650 nm textured stainless steel - LIVE/DEAD, %s combined'
                     % ' + '.join(labels), fontsize=12.5, y=0.975)
        legend_n(fig, labels if not a.no_marks else [])
        note = ('Bars = mean of the per-repeat means (each repeat weighted equally); markers = '
                'the individual repeat means; error bars on the adhesion panels = SD across '
                'repeats; % over stacked bars = mean viability; % over adhesion bars = mean of '
                'the per-repeat anti-adhesion values, each repeat against its OWN control '
                '(batches differ in absolute density; pooling the controls would mix '
                'non-comparable coupons). ImageJ 1.54, adaptive '
                'threshold, size 3-500 px, 40x field area 46 946 um2, n = 5 fields per '
                'condition and repeat.')
        if not a.plain and (borrows or viabs):
            note += ('  Control taken from another repeat where the local control was missing or '
                     'contaminated (marked on the axis); those bars are qualitative only.')
        if not a.plain and EST:
            bits = ['%s %s (%s): control not measurable -> estimated %.0f-%.0f cells/field'
                    % (k[1], k[2], k[0], v['lo_c'], v['hi_c']) for k, v in sorted(EST.items())]
            note += ('  section sign = control inferred from the treated:control ratio at the '
                     'timepoints with a real control - estimate, not a measurement ('
                     + '; '.join(bits) + '); those bars are qualitative only.')
        if drops and not a.plain:
            note += '  One repeat-1 measurement was a staining artefact and is excluded from that bar.'
        footer(fig, note, False)
        fig.tight_layout(rect=(0, 0.085, 1, 0.95))
        pB = os.path.join(a.out, '650nm_livedead_combined_%s.png'
                          % ''.join(lb.replace('repeat', 'r').replace(' ', '') for lb in labels))
        fig.savefig(pB)
        plt.close(fig)
        print('figure:', pB)

    # ---------------- C. validation coupon (area 3), only if one exists ----------------
    any3 = any('3' in set(raw.area) for lb in labels for raw in store[lb].values())
    if any3:
        print('area-3 coupon present - see the repeat-2 validation figure for the comparison')


if __name__ == '__main__':
    main()
