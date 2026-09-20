# -*- coding: utf-8 -*-
"""从 AFM 原始数据量取织构接触几何参数 (与 surfmetrics 同一套 ZSR 口径).

用于 AFM 处理流程的末端: 把实测的周期/纹深/尖峰间距/凸起高度交给 render.py 出示意图.
"""
import glob
import os
import re

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

from ..surfmetrics.surfmetrics import (despike_z, load_heightmap, plane_subtract,
                                       stripe_orientation, surface_metrics)

CLASS_LIPSS = "lipss"
CLASS_PILLAR = "nanopillar"

_KEY_LIPSS = re.compile(r"lipss", re.I)
_KEY_PILLAR = re.compile(r"\bnp\b|\bnano|nanopillar|pillar", re.I)


def classify(name):
    """按文件名判表面类型; 认不出返回 None."""
    n = os.path.basename(str(name))
    if _KEY_LIPSS.search(n):
        return CLASS_LIPSS
    if _KEY_PILLAR.search(n):
        return CLASS_PILLAR
    return None


def measure_file(path, channel="zsr", lam_nm=515.0, profile_band=0.5):
    """量一个 .ibw: 返回 dict (Sa/Sz + 按类型给出周期/纹深 或 尖峰间距/凸起高度)."""
    z, px, py = load_heightmap(path, channel=channel)
    z, _n_replaced = despike_z(plane_subtract(z))   # despike_z 返回 (z, 替换像素数)
    m = surface_metrics(z, px, py)
    cls = classify(path)
    rec = {"file": os.path.basename(path), "class": cls or "unknown",
           "px_nm": float(px), "Sa_nm": float(m.get("Sa_nm", np.nan)),
           "Sq_nm": float(m.get("Sq_nm", np.nan)), "Sz_nm": float(m.get("Sz_nm", np.nan))}

    if cls == CLASS_LIPSS:
        # 周期: 借 surfmetrics 的 FFT (物理窗口 0.5λ–1.5λ, 避开 ZSR 的大尺度扫描纹)
        try:
            # 物理窗口 (0.5λ, 1.5λ): 避开 ZSR 的大尺度扫描纹 (见 surfmetrics.stripe_orientation 文档)
            so = stripe_orientation(z, px, py, band_nm=(lam_nm * profile_band, lam_nm * (profile_band + 1.0)))
            rec["period_nm"] = float(so["period_nm"])
            rec["stripe_deg"] = float(so["ridge_deg"])
            band = True
        except Exception:
            so = stripe_orientation(z, px, py)
            rec["period_nm"] = float(so["period_nm"])
            rec["stripe_deg"] = float(so["ridge_deg"])
            band = False
        rec["period_banded"] = band
        # 纹深: 把条纹转到竖直后沿水平方向平均 → 剖面的 P98-P2 (比 Sz 稳定, Sz 会被孤立尖峰拉大)
        ny, nx = z.shape
        ang = -float(so["cross_deg"])          # 把周期方向转到 x 轴 → 沿条纹方向做平均
        zr = ndimage.rotate(z, ang, reshape=False, order=1, cval=np.nan)
        prof = np.nanmean(zr[ny // 4: 3 * ny // 4, :], axis=0)
        rec["depth_nm"] = float(np.nanpercentile(prof, 98) - np.nanpercentile(prof, 2))
        rec["feature_nm"] = rec["depth_nm"]
    elif cls == CLASS_PILLAR:
        # 尖峰间距: 局部极大值 (7x7) + 阈值 median+1.5σ → 最近邻距离中位数
        thr = float(np.median(z) + 1.5 * np.std(z))
        peaks = (z == ndimage.maximum_filter(z, size=7)) & (z > thr)
        ys, xs = np.nonzero(peaks)
        if len(ys) >= 5:
            pts = np.column_stack([ys * px, xs * px])
            d, _ = cKDTree(pts).query(pts, k=2)
            rec["spacing_nm"] = float(np.median(d[:, 1]))
            rec["n_peaks"] = int(len(ys))
            area_um2 = (z.shape[0] * px / 1000.0) ** 2
            rec["density_per_um2"] = float(len(ys) / area_um2) if area_um2 else np.nan
        else:
            rec["spacing_nm"] = np.nan
            rec["n_peaks"] = int(len(ys))
        # 凸起高度: P90 - 中位
        rec["height_nm"] = float(np.percentile(z, 90) - np.median(z))
        rec["feature_nm"] = rec["height_nm"]
    else:
        rec["feature_nm"] = np.nan
    return rec


def measure_geometry(paths, channel="zsr", lam_nm=515.0):
    """批量测量. paths: 文件列表或目录 (递归找 *.ibw)."""
    if isinstance(paths, (str, os.PathLike)):
        p = str(paths)
        if os.path.isdir(p):
            paths = sorted(glob.glob(os.path.join(p, "**", "*.ibw"), recursive=True))
        else:
            paths = sorted(glob.glob(p))
    recs = []
    for f in paths:
        try:
            recs.append(measure_file(f, channel=channel, lam_nm=lam_nm))
        except Exception as e:                     # 单个文件失败不拖垮整批
            recs.append({"file": os.path.basename(str(f)), "class": "error", "error": str(e)})
    return recs


def _stat(recs, cls, key):
    v = [r[key] for r in recs if r.get("class") == cls and isinstance(r.get(key), (int, float))
         and r.get(key) == r.get(key)]
    if not v:
        return {"n": 0, "mean": float("nan"), "sd": float("nan"), "median": float("nan"),
                "min": float("nan"), "max": float("nan")}
    return {"n": len(v), "mean": float(np.mean(v)), "sd": float(np.std(v, ddof=1)) if len(v) > 1 else 0.0,
            "median": float(np.median(v)), "min": float(np.min(v)), "max": float(np.max(v))}


def summarise(recs, lam_nm=515.0):
    """汇总成示意图需要的几何字典 (nm)."""
    lipss = {k: _stat(recs, CLASS_LIPSS, k) for k in ("period_nm", "depth_nm", "Sa_nm", "Sz_nm")}
    pillar = {k: _stat(recs, CLASS_PILLAR, k) for k in ("spacing_nm", "height_nm", "Sa_nm", "Sz_nm")}
    return {"lam_nm": lam_nm, "lipss": lipss, "nanopillar": pillar, "n_files": len(recs),
            "n_lipss": sum(1 for r in recs if r.get("class") == CLASS_LIPSS),
            "n_pillar": sum(1 for r in recs if r.get("class") == CLASS_PILLAR)}


def write_csv(recs, path):
    """写逐文件测量表."""
    import csv
    keys = ["file", "class", "px_nm", "Sa_nm", "Sq_nm", "Sz_nm", "period_nm", "depth_nm",
            "stripe_deg", "period_banded", "spacing_nm", "height_nm", "n_peaks",
            "density_per_um2", "feature_nm", "error"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["parameter", "value_nm", "note"])
        for cls, key, note in (("LIPSS", "period_nm", "2D-FFT 峰 (0.5λ–1.5λ 窗口)"),
                               ("LIPSS", "depth_nm", "垂直条纹剖面 P98-P2"),
                               ("Nanopillar", "spacing_nm", "局部极大值最近邻距离中位数"),
                               ("Nanopillar", "height_nm", "P90 - 中位")):
            st = _stat(recs, CLASS_LIPSS if cls == "LIPSS" else CLASS_PILLAR, key)
            f.write("") if False else None
            w.writerow([f"{cls}.{key}", f"{st['mean']:.1f} ± {st['sd']:.1f} (n={st['n']}; "
                                       f"{st['min']:.1f}–{st['max']:.1f})", note])
        w.writerow([])
        w.writerow(keys)
        for r in recs:
            w.writerow([("" if r.get(k) is None else (f"{r[k]:.4g}" if isinstance(r.get(k), float) else r.get(k)))
                        for k in keys])
    return path
