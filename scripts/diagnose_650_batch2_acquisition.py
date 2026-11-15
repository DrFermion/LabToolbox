# -*- coding: utf-8 -*-
"""diagnose_650_batch2_acquisition.py — acquisition QC for a 650 nm LIVE/DEAD batch.

Purpose: decide, with numbers rather than by eye, whether a field was acquired
under the same conditions as its siblings. It re-implements the counting rule of
macros/count_livedead.ijm (channel-trap rule -> histogram-mode background + 40 ->
connected components -> 15-500 px) only to obtain the *object-size distribution*
and the exposure time stored in the TIFF description. Counts used for the
analysis itself stay the ImageJ ones.

Outputs (in --outdir):
  acquisition_qc.csv          per image: exposure, background, threshold,
                              detected objects, median/p90 object area,
                              fraction of the field covered
  acquisition_qc_by_group.csv per species/repeat/time/area: n, mean count,
                              median object area, exposure range

Usage:
  env -u PYTHONPATH C:/Users/PC/miniconda3/python.exe scripts/diagnose_650_batch2_acquisition.py \
      --dataset "<650nm-2026xxxx root>" --outdir E:/LabToolbox/output/650_batch2_20261112_min15
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys

import numpy as np
import pandas as pd
import tifffile
from scipy import ndimage

MINPX, MAXPX = 15, 500
EXP_RE = re.compile(r'Exposure:\s*(\d+)\s*:\s*(\d+)\s*:\s*(\d+)\s*\.\s*(\d+)')


def exposure_seconds(desc: str) -> float:
    m = EXP_RE.search(desc or '')
    if not m:
        return float('nan')
    h, mi, s, frac = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(s) + int(frac) / (10 ** len(frac))


def analyse(path):
    with tifffile.TiffFile(path) as t:
        page = t.pages[0]
        arr = page.asarray()
        desc = ''
        if 'ImageDescription' in page.tags:
            desc = str(page.tags['ImageDescription'].value)
    if arr.ndim == 3 and arr.shape[2] >= 3:
        chans = {'r': arr[:, :, 0], 'g': arr[:, :, 1], 'b': arr[:, :, 2]}
        name = 'green' if '-g' in os.path.basename(path).lower() else 'red'
        key = 'g' if name == 'green' else 'r'
        if chans[key].max() < 30:                      # channel-trap fallback
            key = max(chans, key=lambda k: chans[k].max())
            name = 'auto-bright'
        img = chans[key]
    else:
        img = arr if arr.ndim == 2 else arr[:, :, 0]
        name = 'gray'
    hist = np.bincount(img.ravel(), minlength=256)
    bg = int(np.argmax(hist[:256]))
    th = bg + 40
    mask = img >= th
    lab, n = ndimage.label(mask)
    if n == 0:
        areas = np.array([])
    else:
        areas = np.bincount(lab.ravel())[1:]
    kept = areas[(areas >= MINPX) & (areas <= MAXPX)]
    return dict(chan=name, bg=bg, thresh=th,
                n_all=int(n), n_kept=int(len(kept)),
                area_med=float(np.median(kept)) if len(kept) else float('nan'),
                area_p90=float(np.percentile(kept, 90)) if len(kept) else float('nan'),
                cover_pct=float(kept.sum()) / img.size * 100 if len(kept) else 0.0,
                exposure_s=exposure_seconds(desc))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--outdir', required=True)
    ap.add_argument('--max-per-dir', type=int, default=0, help='0 = all images')
    a = ap.parse_args()
    root = a.dataset.replace(chr(92), '/')
    os.makedirs(a.outdir, exist_ok=True)
    rows = []
    for sp in sorted(os.listdir(root)):
        spd = os.path.join(root, sp)
        if not os.path.isdir(spd):
            continue
        for rep in sorted(os.listdir(spd)):
            rpd = os.path.join(spd, rep)
            if not (os.path.isdir(rpd) and re.match(r'^repeat\s*\d+$', rep, re.I)):
                continue
            for tm in sorted(os.listdir(rpd)):
                tmd = os.path.join(rpd, tm)
                if not os.path.isdir(tmd):
                    continue
                tifs = sorted(f for f in os.listdir(tmd) if f.lower().endswith('.tif'))
                if a.max_per_dir:
                    tifs = tifs[:a.max_per_dir]
                for f in tifs:
                    m = re.match(r'^([cC1-3])[-_]([gr])(\d+)\.tif$', f)
                    if not m:
                        continue
                    try:
                        d = analyse(os.path.join(tmd, f))
                    except Exception as exc:                       # noqa: BLE001
                        print('ERR', sp, rep, tm, f, exc, flush=True)
                        continue
                    d.update(species=sp, repeat=rep, time=tm.lower(),
                             area=m.group(1).lower(), num=int(m.group(3)), file=f)
                    rows.append(d)
                    print('%s/%s/%s/%s  exp=%.3fs  n=%d  med=%.1f px  cover=%.2f%%'
                          % (sp, rep, tm, f, d['exposure_s'], d['n_kept'],
                             d['area_med'], d['cover_pct']), flush=True)
    df = pd.DataFrame(rows)
    df = df[['species', 'repeat', 'time', 'area', 'num', 'file', 'chan', 'bg',
             'thresh', 'n_all', 'n_kept', 'area_med', 'area_p90', 'cover_pct',
             'exposure_s']]
    df.to_csv(os.path.join(a.outdir, 'acquisition_qc.csv'), index=False,
              encoding='utf-8-sig')
    g = (df.groupby(['species', 'repeat', 'time', 'area'])
           .agg(n=('file', 'count'), exp_min=('exposure_s', 'min'),
                exp_max=('exposure_s', 'max'), n_kept_mean=('n_kept', 'mean'),
                area_med_med=('area_med', 'median'),
                cover_mean=('cover_pct', 'mean'))
           .reset_index())
    g.to_csv(os.path.join(a.outdir, 'acquisition_qc_by_group.csv'), index=False,
             encoding='utf-8-sig')
    print('\nwrote', os.path.join(a.outdir, 'acquisition_qc.csv'), df.shape)


if __name__ == '__main__':
    main()
