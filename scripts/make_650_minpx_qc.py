# -*- coding: utf-8 -*-
"""make_650_minpx_qc.py — 650 nm「无最小像素限制」重计数的 QC 图

两件事:
  1) --mode ij     : 用 ImageJ 宏观（qcDir 模式）对 240 张图在 min=0 下生成官方 QC 图
                     （每张 <stem>_qc.png：底色=计数通道，蓝圈+蓝编号）→
                     imagej_counts_no_minpx/<species>/qc/<time>/
  2) --mode sheets : 生成"多出来的是什么"的诊断对比图（Python 复算，8-连通，阈值同宏）:
                     蓝圈 = 旧口径已计入的 ≥3 px 对象；品红方块 = 新口径新增的 1–2 px 对象；
                     右栏 = 该视野里 1–2 px 最密集区域的 4× 放大。
                     复算计数会与 ImageJ 结果逐张核对（min0 与 min3 两个口径都必须一致）。

用法: C:/Users/PC/miniconda3/python.exe scripts/make_650_minpx_qc.py --mode both
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import cv2

DS = ('F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - '
      'Ruinong Pan_Antibacterial Surfaces/Live_Dead Bacteria Test/650nm-20261014')
OUT = os.path.join(DS, 'imagej_counts_no_minpx')
CACHE = 'E:/LabToolbox/output/650_minpx_20261018/counts_cache.json'
IJ = 'E:/ImageJ/ImageJ'
MACRO = os.path.join(IJ, 'macros', 'count_livedead.ijm')
JAVA = os.path.join(IJ, 'jre', 'bin', 'java.exe')
IJAR = os.path.join(IJ, 'ij.jar')

SPECIES = [('E.coli', 'E. coli'), ('S.aureus', 'S. aureus')]
TIMES = ['3h', '5h', '7h', '24h']

# 诊断图选用的视野（都来自"多出来最多"的那几个）
SHEETS = [
    ('E. coli particle-size QC (1)', [
        ('E.coli', '3h', '2-r4.tif'),
        ('E.coli', '7h', 'c-g2.tif'),
        ('E.coli', '24h', '1-g4.tif')]),
    ('E. coli / S. aureus particle-size QC (2)', [
        ('E.coli', '24h', 'c-r5.tif'),
        ('S.aureus', '24h', '1-r1.tif'),
        ('S.aureus', '3h', '1-r2.tif')]),
]


# ------------------------------------------------------------------ ImageJ QC
def run_ij_qc():
    env = dict(os.environ, JAVA_TOOL_OPTIONS='-Dfile.encoding=UTF-8')
    for sp, _ in SPECIES:
        for t in TIMES:
            d = os.path.join(DS, sp, 'repeat 1', t)
            qc = os.path.join(OUT, sp, 'qc', t)
            os.makedirs(qc, exist_ok=True)
            fd, af = tempfile.mkstemp(suffix='.txt')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(d.replace(os.sep, '/') + '\n')
                f.write('C:/Users/PC/AppData/Local/hermes/cache/scratch/_qc_tmp.csv\n')
                f.write(qc.replace(os.sep, '/') + '\n')
                f.write('0\n500\n')
            subprocess.run([JAVA, '-cp', IJAR, 'ij.ImageJ', '-batch', MACRO, af],
                           env=env, capture_output=True)
            os.unlink(af)
            n = len([x for x in os.listdir(qc) if x.endswith('_qc.png')])
            print(f'{sp}/{t}: {n} QC png', flush=True)


# ------------------------------------------------------------------ helpers
def load_channel(path, fname):
    """读 tif → 单通道灰度 (与宏同规则: 文件名 -g/-r 定通道, max<30 时取最亮)"""
    buf = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise IOError(path)
    if img.ndim == 3 and img.shape[2] >= 3:
        b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]
        low = fname.lower()
        named = g if '-g' in low else r
        name = 'green' if '-g' in low else 'red'
        if int(named.max()) < 30:
            chans = {'red': r, 'green': g, 'blue': b}
            name = max(chans, key=lambda k: int(chans[k].max()))
            named = chans[name]
        return named, name
    return img, 'gray'


def detect(ch):
    hist = np.bincount(ch.ravel(), minlength=256)
    bg = int(np.argmax(hist))
    th = bg + 40
    mask = (ch >= th).astype(np.uint8)
    n, lab, stats, cents = cv2.connectedComponentsWithStats(mask, connectivity=8)
    areas = stats[1:, cv2.CC_STAT_AREA]
    return dict(th=th, bg=bg, n=n - 1, areas=areas, stats=stats[1:], cents=cents[1:])


def warm_rgb(ch, name):
    """绿色通道→绿底, 红色→红底 (与官方 QC 同约定), 并做温和拉伸"""
    lo, hi = np.percentile(ch, 0.5), np.percentile(ch, 99.7)
    v = np.clip((ch - lo) / max(hi - lo, 1), 0, 1)
    out = np.zeros((*ch.shape, 3), dtype=float)
    out[:, :, 1 if name == 'green' else 0] = v
    return out


def draw(img, det, min_px=3):
    """在 RGB 图上画: 蓝圈 = ≥min_px (旧口径已计), 品红方框 = 1..min_px-1 (新增)"""
    im = img.copy()
    areas, cents = det['areas'], det['cents']
    old = (areas >= min_px) & (areas <= 500)
    new = areas < min_px
    for (x, y), a in zip(cents[old], areas[old]):
        r = int(max(3, np.sqrt(a / np.pi) + 2))
        cv2.circle(im, (int(round(x)), int(round(y))), r, (0.25, 0.55, 1.0), 1, cv2.LINE_AA)
    for (x, y) in cents[new]:
        x, y = int(round(x)), int(round(y))
        cv2.rectangle(im, (x - 2, y - 2), (x + 2, y + 2), (1.0, 0.2, 0.85), 1)
    return im, int(old.sum()), int(new.sum())


def densest_window(cents, sizes, win=160, shape=None):
    """找 1–2 px 对象最密集的 win×win 窗口左上角"""
    sub = cents[sizes < 3]
    if len(sub) == 0:
        return None
    H, W = shape
    xs = np.clip(sub[:, 0].astype(int), 0, W - 1)
    ys = np.clip(sub[:, 1].astype(int), 0, H - 1)
    gx, gy = xs // win, ys // win
    key = pd.Series(list(zip(gx, gy))).value_counts().idxmax()
    in_cell = (gx == key[0]) & (gy == key[1])
    cx, cy = xs[in_cell].mean(), ys[in_cell].mean()   # 窗口以最密集单元的重心为中心
    x0 = int(np.clip(cx - win // 2, 0, max(W - win, 0)))
    y0 = int(np.clip(cy - win // 2, 0, max(H - win, 0)))
    return x0, y0, min(win, W), min(win, H)


# ------------------------------------------------------------------ sheets
def make_sheets():
    cache = json.load(open(CACHE, encoding='utf-8'))
    outdir = os.path.join(OUT, 'qc_sheets')
    os.makedirs(outdir, exist_ok=True)
    problems = []
    for title, fields in SHEETS:
        fig, axes = plt.subplots(len(fields), 2, figsize=(12.6, 4.5 * len(fields)), dpi=170)
        for row, (sp, t, fname) in enumerate(fields):
            d = os.path.join(DS, sp, 'repeat 1', t)
            ch, cname = load_channel(os.path.join(d, fname), fname)
            det = detect(ch)
            a = det['areas']
            n_all = int(((a >= 1) & (a <= 500)).sum())
            n_old = int(((a >= 3) & (a <= 500)).sum())
            # 与 ImageJ 对账
            ij0 = ij3 = None
            for k, v in cache.items():
                var, path = k.split('|', 1)
                norm = path.replace(os.sep, '/')
                if var == '0' and sp in norm and norm.rstrip('/').endswith(t):
                    ij0 = v.get(fname)
                if var == '3' and sp in norm and norm.rstrip('/').endswith(t):
                    ij3 = v.get(fname)
            if ij0 is not None and (ij0 != n_all or ij3 != n_old):
                problems.append((sp, t, fname, n_all, ij0, n_old, ij3))

            rgb = warm_rgb(ch, cname)
            img_all, n_o1, n_new = draw(rgb, det, 3)
            win = densest_window(det['cents'], det['areas'], 240, ch.shape)
            img_disp = img_all.copy()
            if win is not None:                      # 在整幅图上报出放大区域位置 (不进放大图)
                x0, y0, w, h = win
                cv2.rectangle(img_disp, (x0, y0), (x0 + w - 1, y0 + h - 1),
                              (1.0, 0.95, 0.2), 2)
            ax = axes[row, 0]
            ax.imshow(np.clip(img_disp, 0, 1))
            ax.set_title(f'{sp} · {t} · {fname} — full field (yellow box = zoom region)\n'
                         f'counted now: {n_all}  (= {n_old} old + {n_new} new)', fontsize=9)
            ax.set_xticks([]); ax.set_yticks([])
            ax = axes[row, 1]
            if win is None:
                ax.text(0.5, 0.5, 'no sub-3 px objects in this field', ha='center', va='center')
                ax.set_axis_off()
            else:
                x0, y0, w, h = win
                crop = img_all[y0:y0 + h, x0:x0 + w]
                crop = cv2.resize(crop, (w * 3, h * 3), interpolation=cv2.INTER_NEAREST)
                ax.imshow(np.clip(crop, 0, 1))
                sub = det['cents'][det['areas'] < 3]
                n_in = int(((sub[:, 0] >= x0) & (sub[:, 0] < x0 + w) &
                            (sub[:, 1] >= y0) & (sub[:, 1] < y0 + h)).sum())
                ax.set_title(f'zoom ×3 — densest region (yellow box in the full field)\n'
                             f'new 1–2 px objects in this crop: {n_in} of {n_new} in the field',
                             fontsize=9)
                for sp_ in ax.spines.values():      # 黄框 = 左侧整幅图中的放大区域
                    sp_.set_edgecolor('#FFD700'); sp_.set_linewidth(2.0)
                ax.set_xticks([]); ax.set_yticks([])
            for ax in axes[row]:
                ax.add_patch(plt.Rectangle((0.0, 0.0), 1, 1, transform=ax.transAxes,
                                           fill=False, lw=0.6, ec='#cccccc'))
        axes[0, 0].legend(handles=[
            Patch(facecolor='none', edgecolor=(0.25, 0.55, 1.0), label='≥3 px — counted before (blue circle)'),
            Patch(facecolor='none', edgecolor=(1.0, 0.2, 0.85), label='1–2 px — newly counted (magenta box)')],
            loc='upper right', fontsize=8, framealpha=0.85)
        fig.suptitle('650 nm — what removing the 3 px minimum adds: ' + title,
                     fontsize=12, fontweight='bold')
        fig.tight_layout(rect=(0, 0, 1, 0.965))
        p = os.path.join(outdir, title.replace(' ', '_').replace('/', '_') + '.png')
        fig.savefig(p)
        plt.close(fig)
        print('sheet:', p)
    if problems:
        print('⚠ 复算与 ImageJ 不一致:')
        for pr in problems:
            print('   ', pr)
    else:
        print('复算核对: 全部一致 (min0 与 min3 两个口径)')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', default='both', choices=['ij', 'sheets', 'both'])
    a = ap.parse_args()
    if a.mode in ('ij', 'both'):
        run_ij_qc()
    if a.mode in ('sheets', 'both'):
        make_sheets()
