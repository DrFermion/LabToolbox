# -*- coding: utf-8 -*-
"""xdlvo_unit_check.py — interaction_energy 量纲自检（对照独立实现的解析 Derjaguin）。

规则（2026-09-29 修正 interaction_energy 量纲后加入）：
  - 两种化学（排斥型/吸引型）× 两个尺度（R=450 nm 细菌 / R=3.5 nm 蛋白）；
  - U(h0) 数值解 必须与 独立解析式 2πR[ΔG_LW h0²/h + λΔG_AB exp((h0−h)/λ)] + U_EL(h) 吻合
    （R ≥ 100 nm 判 <1%；R = 3.5 nm 的 O(λ/R) 偏差只报告，不判失败）；
  - 同时打印 U_max/U_min 位置，确认极值出现在接触端而非网格中段。
"""
import sys
import numpy as np

sys.path.insert(0, r"E:\LabToolbox")
from labtoolbox.xdlvo.xdlvo import (  # noqa: E402
    SurfaceEnergy, delta_g, interaction_energy, PARAMS, PHYS)


def se(lw, gp, gm):
    return SurfaceEnergy(lw, gp, gm, 2 * np.sqrt(gp * gm), lw + 2 * np.sqrt(gp * gm))


def derjaguin_at(dG, R_nm, h_nm, T_K):
    """独立实现的解析球-平面 Derjaguin（LW + AB），单位 kT。"""
    a = R_nm * 1e-9
    h = h_nm * 1e-9
    h0 = PARAMS['h0'] * 1e-9
    lam = PARAMS['lambda_ab'] * 1e-9
    u = 2 * np.pi * a * (dG['LW'] * 1e-3 * h0 ** 2 / h
                         + lam * dG['AB'] * 1e-3 * np.exp((h0 - h) / lam))
    return u / (PHYS['k'] * T_K)


def main():
    I_M, T_K = 0.15, 310.15
    cases = [
        ("repulsive (fresh-like)", se(28.0, 57.0, 1.0), se(40.60, 1.16, 20.03)),
        ("attractive (aged-like)", se(35.0, 0.5, 0.2), se(40.60, 1.16, 20.03)),
    ]
    ok = True
    for label, m, f in cases:
        dg = delta_g(m, f, I_M, T_K, zeta_m=-25.0, zeta_f=-13.0)
        print(f"[{label}]  ΔG: LW {dg['LW']:+.3f} | AB {dg['AB']:+.3f} | EL {dg.get('EL', 0.0):+.4f} "
              f"| ADH {dg['ADH']:+.3f} mJ/m²")
        for R in (450.0, 3.5):
            E = interaction_energy(m, f, dg, R, I_M, T_K, zeta_m=-25.0, zeta_f=-13.0)
            h_first = float(E['h'][0])
            ana = derjaguin_at(dg, R, h_first, T_K) + float(E['EL'][0])
            mod = float(E['TOT'][0])
            diff = (mod - ana) / abs(ana) * 100.0 if abs(ana) > 1e-9 else float('nan')
            i_max = int(E['TOT'].argmax())
            i_min = int(E['TOT'].argmin())
            print(f"   R={R:6.1f} nm  U(h={h_first:.2f} nm): module {mod:+9.2f} kT vs analytic {ana:+9.2f} kT "
                  f"| diff {diff:+.3f}%  | U_max {E['TOT'][i_max]:+9.2f} @ {E['h'][i_max]:.2f} nm"
                  f" | U_min {E['TOT'][i_min]:+9.2f} @ {E['h'][i_min]:.2f} nm")
            if R >= 100.0 and abs(diff) > 1.0:
                ok = False
    print("UNIT CHECK:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
