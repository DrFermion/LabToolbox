# -*- coding: utf-8 -*-
"""recount_650_minpx_imagej.py — 650 nm LIVE/DEAD 重计数：忽略最小像素限制

背景: 现行口径 Analyze Particles size = 3-500 px（最小 3 px 去噪点）。
本脚本用同一 ImageJ 宏（自适应阈值 = 背景众数 + 40、通道陷阱规则不变），
只把最小粒子面积下调，做一组 size 敏感性扫描:

    min ∈ {0, 2, 3, 5, 10, 20} px   (max 恒为 500 px)

  · min = 0  → 官方"无最小像素限制"口径（所有 ≥1 px 的阈值连通域都算）
  · min = 3  → 现行口径（必须与已交付的 livedead_raw_counts.csv 逐图一致）

输出:
  <DS>/imagej_counts_no_minpx/
      <species>/livedead_raw_counts.csv      (min=0 官方口径, 引擎同格式)
      <species>/livedead_summary.csv / livedead_anova.csv
      650nm_livedead_timecourse_summary.csv (+ 图, 由 plot_650_livedead_timecourse.py 生成)
      minpx_sensitivity.csv                   (各 min 的计数/存活率合计 + 逐图)
  E:/LabToolbox/output/650_minpx_20261018/    (镜像 + 运行日志)

用法: C:/Users/PC/miniconda3/python.exe scripts/recount_650_minpx_imagej.py [--variants 0,2,3,5,10,20]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import time

import numpy as np
import pandas as pd

DS = ('F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - '
      'Ruinong Pan_Antibacterial Surfaces/Live_Dead Bacteria Test/650nm-20261014')
OUT = os.path.join(DS, 'imagej_counts_no_minpx')
MIRROR = 'E:/LabToolbox/output/650_minpx_20261018'
BACKUP = os.path.join(MIRROR, 'backup')
IJ = 'E:/ImageJ/ImageJ'
MACRO = os.path.join(IJ, 'macros', 'count_livedead.ijm')
JAVA = os.path.join(IJ, 'jre', 'bin', 'java.exe')
IJAR = os.path.join(IJ, 'ij.jar')
AREA_UM2 = 46946.10
K_CM2 = 1e8 / AREA_UM2
SPECIES = [('E.coli', 'E. coli'), ('S.aureus', 'S. aureus')]
TIMES = ['3h', '5h', '7h', '24h']
REGIONS = ['c', '1', '2']
REG_NAME = {'c': 'Control', '1': 'LIPSS', '2': 'Nanopillar'}
SKIP_REPEATS = ['repeat 2', 'repeat 3']   # 目前为空 (数据未到)
MAXPX = 500


# ---------------------------------------------------------------- structure
def scan_dirs(species_dir):
    """-> list of (repeat, time, abs_dir) for every non-empty time folder"""
    out = []
    for rep in sorted(os.listdir(species_dir)):
        rp = os.path.join(species_dir, rep)
        if not (os.path.isdir(rp) and re.match(r'^repeat\s*\d+$', rep, re.I)):
            continue
        if rep.replace(' ', '').lower() in [s.replace(' ', '').lower() for s in SKIP_REPEATS]:
            continue
        for t in sorted(os.listdir(rp)):
            tp = os.path.join(rp, t)
            if not (os.path.isdir(tp) and re.search(r'\d+h$', t, re.I)):
                continue
            tifs = [f for f in os.listdir(tp) if f.lower().endswith('.tif')]
            if tifs:
                out.append((rep, t.lower(), tp, sorted(tifs)))
    return out


def pair_files(tifs):
    """{('1','g','1')...} -> {(area,num): {'g':f,'r':f}}"""
    pairs = {}
    for f in tifs:
        m = re.match(r'^([c12])[-_]([gr])(\d+)\.tif$', f, re.I)
        if not m:
            continue
        area, ch, num = m.group(1).lower(), m.group(2).lower(), int(m.group(3))
        pairs.setdefault((area, num), {})[ch] = f
    return pairs


# ---------------------------------------------------------------- ImageJ run
def run_imagej(directory, minpx, out_csv):
    fd, args_path = tempfile.mkstemp(suffix='.txt', prefix='ij650_')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(directory.replace('\\', '/') + '\n')
        f.write(out_csv.replace('\\', '/') + '\n')
        f.write('\n')                      # no QC images
        f.write(f'{minpx}\n{MAXPX}\n')
    env = dict(os.environ, JAVA_TOOL_OPTIONS='-Dfile.encoding=UTF-8')
    try:
        subprocess.run([JAVA, '-cp', IJAR, 'ij.ImageJ', '-batch', MACRO, args_path],
                       env=env, capture_output=True, text=True, timeout=1800)
    finally:
        try:
            os.unlink(args_path)
        except OSError:
            pass
    counts = {}
    if os.path.exists(out_csv):
        with open(out_csv, encoding='utf-8') as fh:
            for row in csv.DictReader(fh):
                fn = (row.get('filename') or '').strip()
                if not fn.lower().endswith('.tif'):
                    continue
                counts[fn] = int(float(row['count']))
        os.unlink(out_csv)
    return counts


# ---------------------------------------------------------------- stats
def build_raw(counts_by_dir, dirs):
    """counts_by_dir: {abs_dir: {fname: n}} -> per-field long table (min=0 layout)"""
    rows = []
    for rep, t, tp, _ in dirs:
        pairs = pair_files(os.listdir(tp))
        cts = counts_by_dir[tp]
        for (area, num), ch in sorted(pairs.items()):
            g, r = ch.get('g'), ch.get('r')
            live = cts.get(g) if g else None
            dead = cts.get(r) if r else None
            if live is None or dead is None:
                rows.append(dict(repeat=rep, time=t, area=area, num=num,
                                 g_image=g or '', r_image=r or '',
                                 live=np.nan, dead=np.nan, total=np.nan, dead_rate=np.nan))
                continue
            tot = live + dead
            rows.append(dict(repeat=rep, time=t, area=area, num=num,
                             g_image=g, r_image=r, live=live, dead=dead, total=tot,
                             dead_rate=(dead / tot if tot else np.nan)))
    df = pd.DataFrame(rows)
    return df


def summarize(df):
    rows = []
    for t in TIMES:
        for reg in REGIONS:
            g = df[(df.time == t) & (df.area == reg)].dropna(subset=['live', 'dead'])
            if g.empty:
                continue
            vf = (g.live / (g.live + g.dead) * 100).values
            rows.append(dict(
                species=None, time=t, region=reg, region_name=REG_NAME[reg], n=len(g),
                live_mean=g.live.mean(), live_sd=g.live.std(),
                dead_mean=g.dead.mean(), dead_sd=g.dead.std(),
                viability_pooled=g.live.sum() / g.total.sum() * 100,
                viability_mean=vf.mean(), viability_sd=vf.std(ddof=1),
                live_cm2=g.live.mean() * K_CM2, live_cm2_sd=g.live.std() * K_CM2,
                dead_cm2=g.dead.mean() * K_CM2, dead_cm2_sd=g.dead.std() * K_CM2))
    return pd.DataFrame(rows)


def anova_two_way(df, value='live'):
    from statsmodels.formula.api import ols
    import statsmodels.api as sm
    d = df.dropna(subset=[value]).copy()
    d['area_label'] = d.area.map(lambda a: 'Control' if a == 'c' else f'Area {a}')
    d['_val'] = np.log10(d[value].clip(lower=1) + 1)
    aov = sm.stats.anova_lm(ols('_val ~ C(area_label) * C(time)', data=d).fit(), typ=2)
    return aov.reset_index().rename(columns={'index': 'factor'})


def one_way_viability(df):
    from scipy import stats
    out = {}
    for t in TIMES:
        grps = []
        for reg in REGIONS:
            g = df[(df.time == t) & (df.area == reg)].dropna(subset=['live', 'dead'])
            if len(g) >= 2:
                grps.append(g.live / (g.live + g.dead) * 100)
        if len(grps) >= 2:
            F, p = stats.f_oneway(*grps)
            out[t] = dict(F=float(F), p=float(p))
    return out


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variants', default='0,2,3,5,10,20')
    args = ap.parse_args()
    variants = [int(v) for v in args.variants.split(',')]

    for d in (OUT, MIRROR):
        os.makedirs(d, exist_ok=True)

    all_dirs = {}
    for sp_dir, _ in SPECIES:
        all_dirs[sp_dir] = scan_dirs(os.path.join(DS, sp_dir))
        print(f'{sp_dir}: {len(all_dirs[sp_dir])} 个时间目录')
        for rep, t, tp, tifs in all_dirs[sp_dir]:
            print(f'   {rep}/{t}: {len(tifs)} tif')

    cache_path = os.path.join(MIRROR, 'counts_cache.json')
    cache = json.load(open(cache_path, encoding='utf-8')) if os.path.exists(cache_path) else {}

    t0 = time.time()
    for v in variants:
        for sp_dir, _ in SPECIES:
            for rep, t, tp, _tifs in all_dirs[sp_dir]:
                key = f'{v}|{tp}'
                if key in cache:
                    continue
                out_csv = os.path.join(MIRROR, f'_tmp_{v}.csv')
                cache[key] = run_imagej(tp, v, out_csv)
                m, s = divmod(int(time.time() - t0), 60)
                print(f'[+{m:02d}:{s:02d}] min={v:2d}px  {sp_dir}/{rep}/{t}: '
                      f'{sum(cache[key].values())} particles', flush=True)
                json.dump(cache, open(cache_path, 'w', encoding='utf-8'))
    print(f'计数完成, 用时 {time.time() - t0:.0f}s')

    # ---------------- per-variant tables
    sens_rows = []
    official = {}
    for v in variants:
        for sp_dir, sp_label in SPECIES:
            cbd = {tp: cache[f'{v}|{tp}'] for rep, t, tp, _ in all_dirs[sp_dir]}
            df = build_raw(cbd, all_dirs[sp_dir])
            df['species'] = sp_label
            official[(sp_dir, v)] = df
            for t in TIMES:
                for reg in REGIONS:
                    g = df[(df.time == t) & (df.area == reg)].dropna(subset=['live', 'dead'])
                    if g.empty:
                        continue
                    sens_rows.append(dict(
                        species=sp_label, min_px=v, time=t, region=reg,
                        n_fields=len(g), live_mean=g.live.mean(), dead_mean=g.dead.mean(),
                        total_mean=g.total.mean(),
                        viability_pooled=g.live.sum() / g.total.sum() * 100))
    sens = pd.DataFrame(sens_rows)

    # 每个变体 vs min=3 的差异（按 species×time×region 汇总）
    base = sens[sens.min_px == 3].set_index(['species', 'time', 'region'])
    cmp_rows = []
    for v in variants:
        if v == 3:
            continue
        cur = sens[sens.min_px == v].set_index(['species', 'time', 'region'])
        for idx in base.index:
            if idx not in cur.index:
                continue
            b, c = base.loc[idx], cur.loc[idx]
            cmp_rows.append(dict(
                species=idx[0], time=idx[1], region=REG_NAME[idx[2]], min_px=v,
                live_3=b.live_mean, live_v=c.live_mean,
                d_live_pct=(c.live_mean - b.live_mean) / b.live_mean * 100,
                dead_3=b.dead_mean, dead_v=c.dead_mean,
                d_dead_pct=(c.dead_mean - b.dead_mean) / b.dead_mean * 100,
                viab_3=b.viability_pooled, viab_v=c.viability_pooled,
                d_viab_pp=c.viability_pooled - b.viability_pooled))
    cmp_df = pd.DataFrame(cmp_rows)

    # ---------------- verify min=3 == delivered counts
    verify = []
    for sp_dir, sp_label in SPECIES:
        old = pd.read_csv(os.path.join(BACKUP, f'{sp_dir}_raw_counts_v3-500.csv'),
                          encoding='utf-8-sig')
        new = official[(sp_dir, 3)].copy()
        m = old.merge(new, on=['repeat', 'time', 'area', 'num'], how='outer',
                      suffixes=('_old', '_new'), indicator=True)
        both = m.dropna(subset=['live_old', 'live_new', 'dead_old', 'dead_new'])
        mism = both[(both.live_old != both.live_new) | (both.dead_old != both.dead_new)]
        verify.append((sp_label, len(old), len(new), len(both), len(mism)))
        if len(mism):
            print(mism.head(20).to_string())
    print('验证 (min=3 vs 已交付) [species, n_old, n_new, n_compared, n_mismatch]:', verify)
    assert all(v[1] == v[2] and v[4] == 0 for v in verify), \
        'min=3 未能复现已交付计数 — 停止'

    # ---------------- official min=0 outputs
    for sp_dir, sp_label in SPECIES:
        df0 = official[(sp_dir, 0)].dropna(subset=['live', 'dead']).copy()
        outdir = os.path.join(OUT, sp_dir)
        os.makedirs(outdir, exist_ok=True)
        df0[['repeat', 'time', 'area', 'num', 'g_image', 'r_image',
             'live', 'dead', 'total', 'dead_rate']].to_csv(
            os.path.join(outdir, 'livedead_raw_counts.csv'), index=False, encoding='utf-8-sig')
        summarize(df0).to_csv(os.path.join(outdir, 'livedead_summary.csv'),
                              index=False, encoding='utf-8-sig')
        anova_two_way(df0).to_csv(os.path.join(outdir, 'livedead_anova.csv'),
                                  index=False, encoding='utf-8-sig')
        print(f'{sp_label}: min=0 总 live {int(df0.live.sum())}, dead {int(df0.dead.sum())}, '
              f'存活率 {df0.live.sum() / df0.total.sum() * 100:.1f}%')

    # 每视野 <3 px 粒子数（= min0 - min3），用于量化"被最小尺寸挡掉"的部分
    sub_rows = []
    for sp_dir, sp_label in SPECIES:
        d0 = official[(sp_dir, 0)].dropna(subset=['live', 'dead']).set_index(['time', 'area', 'num'])
        d3 = official[(sp_dir, 3)].dropna(subset=['live', 'dead']).set_index(['time', 'area', 'num'])
        j = d0.join(d3, lsuffix='_0', rsuffix='_3', how='inner')
        for (t, reg, num), row in j.iterrows():
            sub_rows.append(dict(species=sp_label, time=t, region=reg, num=num,
                                 live_sub3=row.live_0 - row.live_3,
                                 dead_sub3=row.dead_0 - row.dead_3,
                                 live_pct_sub3=(row.live_0 - row.live_3) / row.live_0 * 100,
                                 dead_pct_sub3=(row.dead_0 - row.dead_3) / row.dead_0 * 100))
    pd.DataFrame(sub_rows).to_csv(os.path.join(OUT, 'sub3px_particles_per_field.csv'),
                                  index=False, encoding='utf-8-sig')

    # timecourse summary（与 650nm_livedead_timecourse_summary.csv 同结构）
    tc = []
    for sp_dir, sp_label in SPECIES:
        s = summarize(official[(sp_dir, 0)].dropna(subset=['live', 'dead']))
        s['species'] = sp_label
        tc.append(s)
    tcdf = pd.concat(tc, ignore_index=True)
    tcdf = tcdf[['species', 'time', 'region', 'region_name', 'n', 'live_mean', 'live_sd',
                 'dead_mean', 'dead_sd', 'viability_pooled', 'viability_mean',
                 'viability_sd', 'live_cm2', 'live_cm2_sd', 'dead_cm2', 'dead_cm2_sd']]
    tcdf.to_csv(os.path.join(OUT, '650nm_livedead_timecourse_summary.csv'),
                index=False, encoding='utf-8-sig')
    sens.to_csv(os.path.join(OUT, 'minpx_sensitivity.csv'), index=False, encoding='utf-8-sig')
    cmp_df.to_csv(os.path.join(OUT, 'minpx_vs_3-500_deltas.csv'), index=False, encoding='utf-8-sig')

    # ANOVA p per time (viability, min=0)
    pv = {}
    for sp_dir, sp_label in SPECIES:
        pv[sp_label] = one_way_viability(official[(sp_dir, 0)].dropna(subset=['live', 'dead']))
    json.dump(pv, open(os.path.join(OUT, 'viability_anova_p_min0.json'), 'w'), indent=2)
    print(json.dumps(pv, indent=2))

    # 汇总 sanity
    for v in variants:
        tot = {}
        for sp_dir, sp_label in SPECIES:
            d = official[(sp_dir, v)].dropna(subset=['live', 'dead'])
            tot[sp_label] = (int(d.live.sum()), int(d.dead.sum()),
                             round(d.live.sum() / d.total.sum() * 100, 2))
        print(f'min={v:2d}: ' + '  '.join(f'{k}: live {a} / dead {b} / {c}%' for k, (a, b, c) in tot.items()))

    print('done ->', OUT)


if __name__ == '__main__':
    main()
