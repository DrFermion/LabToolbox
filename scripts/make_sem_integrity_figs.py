# -*- coding: utf-8 -*-
"""Figures for the SEM texture-integrity cross-method report (2026-11-12), v2.

Fixes after a layout check: short x labels (descriptions moved to the caption),
separate y ranges per sample type, an explicit annotation for the clipped M1 bar,
and adaptive label colour in the rank-correlation heat-map.
"""
from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = sys.argv[1] if len(sys.argv) > 1 else \
    'E:/LabToolbox/output/sem_integrity_crosscheck_20261111/method_analysis'
os.makedirs(OUT, exist_ok=True)

bias = pd.read_csv(os.path.join(OUT, 'method_bias_vs_consensus.csv'), encoding='utf-8-sig')
rank = pd.read_csv(os.path.join(OUT, 'ranking_correlation.csv'), encoding='utf-8-sig')
per = pd.read_csv(os.path.join(OUT, 'field_method_agreement.csv'), encoding='utf-8-sig')

METHODS = ['M0', 'M1', 'M2', 'M3', 'M4', 'M5']
LEGEND = ('M0 semtexture profile autocorrelation · M1 naive 2-D FFT maximum · '
          'M2 radial 2-D FFT (Hann + high-pass) · M3 1-D FFT of the rotated profile · '
          'M4 2-D autocorrelation side-lobe · M5 areal PSD (Welch)')

fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.3))
for ax, label, title, ylim in [
        (axes[0], '515nm_LIPSS', '515 nm LIPSS (6 fields)', 6),
        (axes[1], '650nm_nanopillars', '650 nm nanopillars (27 fields)', 22)]:
    b = bias[bias.dataset == label].set_index('method').loc[METHODS]
    x = np.arange(len(b))
    vals = np.clip(b.mean_dev_pct.values, -ylim, ylim)
    ax.bar(x, vals, color=['#2c7fb8' if v < 0 else '#d95f0e' for v in vals], alpha=0.85)
    for xi, (v, sd) in enumerate(zip(b.mean_dev_pct.values, b.sd_dev_pct.values)):
        lo, hi = v - sd, v + sd
        ax.plot([xi, xi], [max(lo, -ylim), min(hi, ylim)], color='0.25', lw=1)
        ax.plot([xi - 0.13, xi + 0.13], [min(hi, ylim)] * 2, color='0.25', lw=1)
        ax.plot([xi - 0.13, xi + 0.13], [max(lo, -ylim)] * 2, color='0.25', lw=1)
        if v > ylim:
            pass  # labelled once, in a box outside the bar (see below)
    ax.axhline(0, color='k', lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(METHODS, fontsize=9)
    ax.set_xlabel('period estimator')
    ax.set_ylabel('deviation from six-method consensus (%)')
    ax.set_ylim(-ylim, ylim)
    ax.set_title(title, fontsize=9.5)
    ax.grid(axis='y', ls=':', lw=0.5, alpha=0.6)
    if label.startswith('650'):
        ax.annotate('M1 = +180 ± 369 %\n(clipped, off scale)',
                    xy=(1.0, ylim * 0.95), xytext=(1.35, ylim * 0.45),
                    fontsize=7, color='k', ha='left',
                    bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='0.45', lw=0.6),
                    arrowprops=dict(arrowstyle='->', lw=0.7, color='0.35'))
fig.text(0.01, 0.005,
         'Bars = mean deviation of a method from the median of the six methods on the same '
         'field; whiskers = SD across fields.\n' + LEGEND + '\nM1 on the pillar lattice is '
         'clipped (+180 +/- 369 %) because of peak switching.', fontsize=6.2, color='0.35')
fig.tight_layout(rect=(0, 0.10, 1, 1))
fig.savefig(os.path.join(OUT, 'fig_method_bias.png'), dpi=220)
plt.close(fig)

fig, ax = plt.subplots(figsize=(6.2, 4.0))
data = [per[per.dataset == '515nm_LIPSS'].spread_pct.dropna().values,
        per[per.dataset == '650nm_nanopillars'].spread_pct.dropna().values]
bp = ax.boxplot(data, widths=0.45, patch_artist=True)
for patch, c in zip(bp['boxes'], ['#7fb3d5', '#f0b27a']):
    patch.set_facecolor(c)
    patch.set_alpha(0.8)
for i, vals in enumerate(data, start=1):
    ax.plot(np.full(len(vals), i) + np.random.default_rng(3).normal(0, 0.05, len(vals)),
            vals, 'o', ms=4, mfc='none', mec='k', mew=0.7)
ax.set_yscale('log')
ax.set_xticks([1, 2])
ax.set_xticklabels(['515 nm LIPSS\n(6 fields)', '650 nm nanopillars\n(27 fields)'])
ax.set_ylabel('spread across the six methods, same field (%)')
ax.grid(axis='y', ls=':', lw=0.5, alpha=0.6)
ax.set_title('Method-to-method spread on a single field', fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'fig_field_spread.png'), dpi=220)
plt.close(fig)

M = np.full((6, 6), np.nan)
for _, r in rank[rank.dataset == '650nm_nanopillars'].iterrows():
    i, j = METHODS.index(r.a), METHODS.index(r.b)
    M[i, j] = M[j, i] = r.rho
np.fill_diagonal(M, 1.0)
fig, ax = plt.subplots(figsize=(5.4, 4.6))
im = ax.imshow(M, vmin=-1, vmax=1, cmap='RdBu_r')
ax.set_xticks(range(6)); ax.set_xticklabels(METHODS)
ax.set_yticks(range(6)); ax.set_yticklabels(METHODS)
ax.set_xlabel('method'); ax.set_ylabel('method')
for i in range(6):
    for j in range(6):
        if not np.isnan(M[i, j]):
            ax.text(j, i, '%.2f' % M[i, j], ha='center', va='center', fontsize=8.5,
                    color='white' if abs(M[i, j]) > 0.55 else 'black')
ax.set_title("Spearman's rho between methods\nover 9 nanopillar coupons", fontsize=10)
fig.colorbar(im, ax=ax, shrink=0.8, label='rho')
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'fig_rank_correlation.png'), dpi=220)
plt.close(fig)

print('wrote', OUT)
