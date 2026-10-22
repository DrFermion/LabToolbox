# -*- coding: utf-8 -*-
"""recount_650_repeat2_imagej.py — 650 nm LIVE/DEAD: count repeat 2 with ImageJ.

Only "repeat 2" folders are counted (repeat 1 already has a delivered
imagej_counts/<species>/livedead_raw_counts.csv; repeat 3 is still empty).

Same macro and same counting rule as the delivered repeat-1 numbers:
ImageJ 1.54 headless, adaptive threshold (background mode + 40), Analyze
Particles size 3-500 px, 40x field area 46 946.10 um2.

Special case handled here (not a bug): S. aureus repeat 2 / 24 h has NO control
green channel — that control coupon was contaminated (nearly all dead), so the
user counted the red channel as TOTAL cells. Those rows are written with
live = NaN, dead = <red count>, total = <red count> so downstream code can use
the total but knows viability is unavailable.

Output
  <DS>/imagej_counts_repeat2/<species>/livedead_raw_counts.csv   (engine format)
  E:/LabToolbox/output/650_repeat2_20261022/                     (mirror + log)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import tempfile
import time

import numpy as np
import pandas as pd

DS = ('F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - '
      'Ruinong Pan_Antibacterial Surfaces/Live_Dead Bacteria Test/650nm-20261014')
OUT = os.path.join(DS, 'imagej_counts_repeat2')
MIRROR = 'E:/LabToolbox/output/650_repeat2_20261022'
IJ = 'E:/ImageJ/ImageJ'
MACRO = os.path.join(IJ, 'macros', 'count_livedead.ijm')
JAVA = os.path.join(IJ, 'jre', 'bin', 'java.exe')
IJAR = os.path.join(IJ, 'ij.jar')
SPECIES = [('E.coli', 'E. coli'), ('S.aureus', 'S. aureus')]
TIMES = ['3h', '5h', '7h', '24h']
KEEP_REPEATS = ['repeat 2']
MINPX = 3
MAXPX = 500


def scan_dirs(species_dir):
    out = []
    for rep in sorted(os.listdir(species_dir)):
        rp = os.path.join(species_dir, rep)
        if not (os.path.isdir(rp) and re.match(r'^repeat\s*\d+$', rep, re.I)):
            continue
        if rep.replace(' ', '').lower() not in [s.replace(' ', '').lower() for s in KEEP_REPEATS]:
            continue
        for t in sorted(os.listdir(rp)):
            tp = os.path.join(rp, t)
            if not (os.path.isdir(tp) and re.search(r'\d+h$', t, re.I)):
                continue
            tifs = [f for f in os.listdir(tp) if f.lower().endswith('.tif')]
            if tifs:
                out.append((rep, t.lower(), tp))
    return out


def pair_files(files):
    """{(area,num): {'g':f,'r':f}} — area c/1/2/3 (3 = extra re-shot coupon)."""
    pairs = {}
    for f in files:
        m = re.match(r'^([cC1-3])[-_]([gr])(\d+)\.tif$', f)
        if not m:
            continue
        pairs.setdefault((m.group(1).lower(), int(m.group(3))), {})[m.group(2).lower()] = f
    return pairs


def run_imagej(directory, out_csv):
    fd, args_path = tempfile.mkstemp(suffix='.txt', prefix='ij650r2_')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(directory.replace('\\', '/') + '\n')
        f.write(out_csv.replace('\\', '/') + '\n')
        f.write('\n')
        f.write('%d\n%d\n' % (MINPX, MAXPX))
    env = dict(os.environ, JAVA_TOOL_OPTIONS='-Dfile.encoding=UTF-8')
    try:
        r = subprocess.run([JAVA, '-cp', IJAR, 'ij.ImageJ', '-batch', MACRO, args_path],
                           env=env, capture_output=True, text=True, timeout=3600)
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
                if fn.lower().endswith('.tif'):
                    counts[fn] = int(float(row['count']))
        os.unlink(out_csv)
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='', help='e.g. S.aureus/5h to debug a single folder')
    a = ap.parse_args()
    for d in (OUT, MIRROR):
        os.makedirs(d, exist_ok=True)

    log_lines = []
    t0 = time.time()
    summary = []
    for sp_dir, sp_label in SPECIES:
        dirs = scan_dirs(os.path.join(DS, sp_dir))
        rows = []
        for rep, t, tp in dirs:
            if a.only and a.only.lower() not in (tp.replace('\\', '/').lower()):
                continue
            out_csv = os.path.join(MIRROR, '_tmp_counts.csv')
            cts = run_imagej(tp, out_csv)
            pairs = pair_files(os.listdir(tp))
            miss = []
            for (area, num), ch in sorted(pairs.items()):
                g, r = ch.get('g'), ch.get('r')
                gv = cts.get(g) if g else None
                rv = cts.get(r) if r else None
                if gv is None and rv is None:
                    miss.append('%s-%d' % (area, num))
                    continue
                if gv is None or rv is None:
                    # red-only (control contaminated, red counted as total) or green-only
                    rows.append(dict(repeat=rep, time=t, area=area, num=num,
                                     g_image=g or '', r_image=r or '',
                                     live=np.nan if gv is None else gv,
                                     dead=np.nan if rv is None else rv,
                                     total=(gv if rv is None else rv),
                                     dead_rate=np.nan))
                else:
                    tot = gv + rv
                    rows.append(dict(repeat=rep, time=t, area=area, num=num,
                                     g_image=g, r_image=r, live=gv, dead=rv, total=tot,
                                     dead_rate=(rv / tot if tot else np.nan)))
            n_tif = len([f for f in os.listdir(tp) if f.lower().endswith('.tif')])
            line = ('%s/%s/%s: %d tif -> %d counted fields (particles %d)%s'
                    % (sp_dir, rep, t, n_tif, len(pairs), sum(cts.values()),
                       ('  MISSING %s' % ','.join(miss)) if miss else ''))
            print(line, flush=True)
            log_lines.append(line)
        df = pd.DataFrame(rows)
        if df.empty:
            continue
        df['species'] = sp_label
        df = df.sort_values(['time', 'area', 'num']).reset_index(drop=True)
        od = os.path.join(OUT, sp_dir)
        os.makedirs(od, exist_ok=True)
        df.to_csv(os.path.join(od, 'livedead_raw_counts.csv'), index=False, encoding='utf-8-sig')
        for t in TIMES:
            for ar in ['c', '1', '2', '3']:
                g = df[(df.time == t) & (df.area == ar)]
                if g.empty:
                    continue
                full = g.dropna(subset=['live', 'dead'])
                summary.append(dict(species=sp_label, time=t, area=ar, n_rows=len(g),
                                    n_full=len(full),
                                    live_mean=full.live.mean() if len(full) else np.nan,
                                    dead_mean=g.dead.mean(), total_mean=g.total.mean(),
                                    viability=(full.live.sum() / full.total.sum() * 100)
                                    if len(full) else np.nan))
                print('   %s %-2s %s: n=%d live=%.0f dead=%.0f viab=%s'
                      % (sp_label, t, ar, len(g),
                         full.live.mean() if len(full) else np.nan,
                         g.dead.mean(),
                         ('%.1f%%' % (full.live.sum() / full.total.sum() * 100))
                         if len(full) else 'n/a (red=total)'), flush=True)
    pd.DataFrame(summary).to_csv(os.path.join(MIRROR, 'repeat2_counts_summary.csv'),
                                 index=False, encoding='utf-8-sig')
    with open(os.path.join(MIRROR, 'count_log.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines))
        f.write('\n\nelapsed %.0f s\n' % (time.time() - t0))
    print('done in %.0f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
