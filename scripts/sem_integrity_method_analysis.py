# -*- coding: utf-8 -*-
"""sem_integrity_method_analysis.py — extra quantitative comparisons for the
cross-method SEM texture-integrity report.

Three questions the existing crosscheck tables do not answer directly:

1. How far apart are the six methods on the *same field* (not just on average)?
2. Which method is biased relative to the six-method consensus of each field?
3. Do the methods *rank* coupons in the same order?  (A method can be biased by a
   constant factor and still rank identically; ranking agreement is what matters
   when the metric is used to sort samples or to accept/reject a process.)

Outputs -> --outdir
  field_method_agreement.csv   per field: consensus, per-method deviation, spread
  method_bias_vs_consensus.csv per method: mean/SD deviation from consensus
  ranking_correlation.csv      per dataset: Spearman rho between methods over coupons
  summary.json                 scalars quoted in the report

Usage:
  env -u PYTHONPATH C:/Users/PC/miniconda3/python.exe scripts/sem_integrity_method_analysis.py \
      --dir515 "<...>/515_crosscheck" --dir650 "<...>/650_crosscheck" --outdir <out>
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np
import pandas as pd
from scipy import stats

METHODS = ['M0', 'M1', 'M2', 'M3', 'M4', 'M5']


def load(dir_):
    f = glob.glob(os.path.join(dir_, 'crosscheck_perfield.csv'))[0]
    df = pd.read_csv(f, encoding='utf-8-sig')
    cols = {m: f'{m}_period_nm' for m in METHODS}
    for c in cols.values():
        assert c in df.columns, c
    return df, cols


def agreement(df, cols, label):
    per = []
    for _, r in df.iterrows():
        vals = {m: r[cols[m]] for m in METHODS}
        finite = {m: v for m, v in vals.items() if v is not None and not pd.isna(v) and v > 0}
        if len(finite) < 3:
            continue
        arr = np.array(list(finite.values()))
        cons = float(np.median(arr))
        row = dict(dataset=label, coupon=r.get('coupon', r.get('file')), file=r['file'],
                   n_methods=len(arr), consensus_nm=cons,
                   spread_pct=(arr.max() - arr.min()) / cons * 100,
                   cv_pct=arr.std(ddof=1) / arr.mean() * 100)
        for m in METHODS:
            v = finite.get(m)
            row[f'{m}_dev_pct'] = (v - cons) / cons * 100 if v is not None else np.nan
        per.append(row)
    per = pd.DataFrame(per)
    bias = []
    for m in METHODS:
        d = per[f'{m}_dev_pct'].dropna()
        bias.append(dict(dataset=label, method=m, n=len(d), mean_dev_pct=d.mean(),
                         sd_dev_pct=d.std(ddof=1),
                         median_abs_dev_pct=d.abs().median()))
    return per, pd.DataFrame(bias)


def ranking(df, cols, label):
    """Spearman rho between methods computed on coupon medians (>=3 coupons)."""
    if 'group' not in df.columns or df['group'].nunique() < 3:
        return pd.DataFrame()
    med = df.groupby('group')[[cols[m] for m in METHODS]].median()
    rows = []
    for i, a in enumerate(METHODS):
        for b in METHODS[i + 1:]:
            x = med[cols[a]]
            y = med[cols[b]]
            ok = x.notna() & y.notna() & (x > 0) & (y > 0)
            if ok.sum() < 3:
                rows.append(dict(dataset=label, a=a, b=b, n=int(ok.sum()), rho=np.nan, p=np.nan))
                continue
            rho, p = stats.spearmanr(x[ok], y[ok])
            rows.append(dict(dataset=label, a=a, b=b, n=int(ok.sum()), rho=rho, p=p))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir515', required=True)
    ap.add_argument('--dir650', required=True)
    ap.add_argument('--outdir', required=True)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    all_per, all_bias, all_rank = [], [], []
    for dir_, label in [(a.dir515, '515nm_LIPSS'), (a.dir650, '650nm_nanopillars')]:
        df, cols = load(dir_)
        per, bias = agreement(df, cols, label)
        all_per.append(per)
        all_bias.append(bias)
        rank = ranking(df, cols, label)
        if len(rank):
            all_rank.append(rank)
        print(f'{label}: {len(per)} fields, {df["group"].nunique() if "group" in df else 0} groups')
    per = pd.concat(all_per, ignore_index=True)
    bias = pd.concat(all_bias, ignore_index=True)
    rank = pd.concat(all_rank, ignore_index=True) if all_rank else pd.DataFrame()
    per.to_csv(os.path.join(a.outdir, 'field_method_agreement.csv'), index=False,
               encoding='utf-8-sig')
    bias.to_csv(os.path.join(a.outdir, 'method_bias_vs_consensus.csv'), index=False,
                encoding='utf-8-sig')
    if len(rank):
        rank.to_csv(os.path.join(a.outdir, 'ranking_correlation.csv'), index=False,
                    encoding='utf-8-sig')

    summary = {}
    for label in per.dataset.unique():
        p = per[per.dataset == label]
        summary[label] = dict(
            n_fields=int(len(p)),
            median_spread_pct=float(p.spread_pct.median()),
            max_spread_pct=float(p.spread_pct.max()),
            median_cv_pct=float(p.cv_pct.median()))
        if len(rank):
            r = rank[rank.dataset == label]
            summary[label]['rho_median'] = float(r.rho.median())
            summary[label]['rho_min'] = float(r.rho.min())
            summary[label]['rho_max'] = float(r.rho.max())
            summary[label]['pairs_all_rho_gt_0.7'] = int((r.rho > 0.7).sum())
            summary[label]['n_pairs'] = int(len(r))
    json.dump(summary, open(os.path.join(a.outdir, 'summary.json'), 'w'), indent=2)
    print(json.dumps(summary, indent=2))
    print('\nbias table:')
    print(bias.round(2).to_string(index=False))
    if len(rank):
        print('\nranking (rho):')
        print(rank.round(3).to_string(index=False))


if __name__ == '__main__':
    main()
