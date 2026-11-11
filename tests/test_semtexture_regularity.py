# -*- coding: utf-8 -*-
"""Validity checks for the semtexture regularity tuple on synthetic fields.

A perfect grating must give R_lambda1d/R_lambda2d ~ 1, a tiny Gini and a small phase
scatter; pure noise must give low R and a large phase scatter.  This pins the sign and
the scale of the metrics, which is what the literature comparisons rely on.
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from labtoolbox.semtexture import analyse_image          # noqa: E402

PX_NM = 31.25
LAM_PX = 12.0            # ~375 nm at 31.25 nm/px, inside the 240-800 nm band


def _save(arr, path):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(path)


def grating(shape=(512, 512), period_px=LAM_PX, noise=2.0, phase_fn=None, seed=0):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    phase = 2 * np.pi * xx / period_px if phase_fn is None else phase_fn(xx, yy)
    img = 128 + 40 * np.sin(phase)
    return img + rng.normal(0, noise, img.shape)


def test_perfect_grating(tmpdir):
    p = os.path.join(tmpdir, "gratings", "perfect.png")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    _save(grating(), p)
    r = analyse_image(p, pixel_nm=PX_NM)
    assert abs(r["period_nm"] - LAM_PX * PX_NM) < 15, r["period_nm"]
    assert r["R_lambda1d"] > 0.9, r["R_lambda1d"]
    assert r["R_lambda2d"] > 0.9, r["R_lambda2d"]
    assert r["gini_period"] < 0.1, r["gini_period"]
    assert r["dloa_deg"] < 5.0, r["dloa_deg"]
    assert r["phase_rms_deg"] < 35.0, r["phase_rms_deg"]
    assert r["band_lo_nm"] == 240.0 and r["band_hi_nm"] == 800.0


def test_noise_scores_worse(tmpdir):
    rng = np.random.default_rng(1)
    p = os.path.join(tmpdir, "noise", "noise.png")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    _save(rng.normal(128, 40, (512, 512)), p)
    rn = analyse_image(p, pixel_nm=PX_NM)
    pg = os.path.join(tmpdir, "noise", "grating.png")
    _save(grating(), pg)
    rg = analyse_image(pg, pixel_nm=PX_NM)
    # a grating must not be penalised relative to noise on the dispersion metrics
    if np.isfinite(rn["R_lambda1d"]):
        assert rg["R_lambda1d"] >= rn["R_lambda1d"] - 0.05
    # orientation dispersion must be clearly worse for noise
    assert not np.isfinite(rn["dloa_deg"]) or rn["dloa_deg"] > rg["dloa_deg"]


def test_band_override(tmpdir):
    p = os.path.join(tmpdir, "band", "g.png")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    _save(grating(period_px=30.0), p)          # 937 nm: outside the default band
    r_def = analyse_image(p, pixel_nm=PX_NM)
    r_wide = analyse_image(p, pixel_nm=PX_NM, band_nm=(600, 1400))
    assert r_wide["band_hi_nm"] == 1400.0
    assert np.isfinite(r_wide["period_nm"])
    assert abs(r_wide["period_nm"] - 30.0 * PX_NM) < 60, r_wide["period_nm"]
    # with the default band this period is not admissible
    assert not np.isfinite(r_def["period_nm"]) or r_def["period_nm"] < 800


def test_phase_disorder_detected(tmpdir):
    """Random phase jumps every few tiles must raise phase_rms_deg."""
    def fn(xx, yy):
        block = (xx // 64) * 7 + (yy // 64) * 13
        return 2 * np.pi * xx / LAM_PX + block * 1.7

    p = os.path.join(tmpdir, "jump", "jump.png")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    _save(grating(phase_fn=fn, noise=1.0), p)
    rj = analyse_image(p, pixel_nm=PX_NM)
    pk = os.path.join(tmpdir, "jump", "flat.png")
    _save(grating(), pk)
    rk = analyse_image(pk, pixel_nm=PX_NM)
    assert rj["phase_rms_deg"] > rk["phase_rms_deg"] + 10, (rj["phase_rms_deg"], rk["phase_rms_deg"])


if __name__ == "__main__":
    import tempfile
    tmp = tempfile.mkdtemp(prefix="semtex_")
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn(tmp)
                print("PASS", name)
            except AssertionError as exc:
                print("FAIL", name, exc)
