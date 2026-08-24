# -*- coding: utf-8 -*-
"""
接触角/表面自由能模块
- OWRK (Owens-Wendt-Rabel-Kaelble) 法: 用两种液体接触角求分散/极性分量
- 支持水/二碘甲烷、水/甲酰胺等组合
"""
import numpy as np
from dataclasses import dataclass

# 探测液体表面能参数 (mJ/m²): (γ_LW, γ⁺, γ⁻)
PROBE_LIQUIDS = {
    "water": (21.8, 25.5, 25.5),
    "diiodomethane": (50.8, 0.0, 0.0),
    "formamide": (39.0, 2.28, 39.6),
    "glycerol": (34.0, 3.92, 57.4),
    "ethylene_glycol": (29.0, 1.92, 47.0),
}


@dataclass
class SurfaceEnergy:
    gamma_lw: float      # 色散/LW 分量
    gamma_p: float       # 极性分量
    gamma_total: float   # 总表面能

    def __repr__(self):
        return (f"γ^LW={self.gamma_lw:.2f}, γ^P={self.gamma_p:.2f}, "
                f"γ^TOT={self.gamma_total:.2f} mJ/m²")


def _liquid_params(name):
    if name not in PROBE_LIQUIDS:
        raise ValueError(f"未知液体: {name}, 可选: {list(PROBE_LIQUIDS)}")
    return PROBE_LIQUIDS[name]


def owrk_surface_energy(theta1, theta2, liquid1="water", liquid2="diiodomethane"):
    """OWRK 法: 由两种液体接触角求固体表面能 (分散+极性分量)。
    theta1/theta2: 接触角 (度). 注意液体顺序要与参数对应。
    求解: (1+cosθ)γ_L / (2√γ_L^LW) = √γ_S^LW + √γ_S^P · √(γ_L^P/γ_L^LW)
    """
    l1 = _liquid_params(liquid1)
    l2 = _liquid_params(liquid2)
    t1, t2 = np.radians(theta1), np.radians(theta2)

    # 修正 OWRK 线性化: y = √γ_S^LW + √γ_S^P · x
    # 其中 y = (1+cosθ)γ_L/(2√γ_L^LW), x = √(γ_L^P/γ_L^LW)
    def y_from(theta, lp):
        gamma_L = lp[0] + 2 * np.sqrt(lp[1] * lp[2])  # 液体总表面能
        return gamma_L * (1 + np.cos(theta)) / (2 * np.sqrt(lp[0]))

    def x_from(lp):
        return np.sqrt((lp[1] + lp[2]) / lp[0]) if lp[0] > 0 else 0

    y1, y2 = y_from(t1, l1), y_from(t2, l2)
    x1, x2 = x_from(l1), x_from(l2)

    if abs(x2 - x1) < 1e-10:
        raise ValueError("病态矩阵: 两种液体极性差异太小, 无法求解")

    # 线性拟合: y = a + b·x, a=√γ^LW, b=√γ^P
    b = (y2 - y1) / (x2 - x1)
    a = y1 - b * x1

    if a < 0:
        # √γ^LW 为负无物理意义: 试试仅用 LW 液体的简化法
        # 退化为: γ_S^LW = γ_L^LW·(1+cosθ)²/4 (用二碘甲烷)
        nonpolar = l1 if lp_is_nonpolar(l1) else (l2 if lp_is_nonpolar(l2) else None)
        if nonpolar is not None:
            gamma_lw = nonpolar[0] * (1 + np.cos(np.radians(45))) ** 2 / 4  # 占位
            raise ValueError(f"求解失败 (√LW={a:.3f}<0), 请检查接触角或液体组合")
        raise ValueError(f"求解失败 (√LW={a:.3f}<0), 请检查接触角或液体组合")

    gamma_lw = a**2
    gamma_p = max(b, 0) ** 2
    return SurfaceEnergy(gamma_lw, gamma_p, gamma_lw + gamma_p)


def lp_is_nonpolar(lp):
    return lp[1] + lp[2] < 0.01


def contact_angle_from_surface_energy(se, liquid="water"):
    """由固体表面能反推某液体在其上的接触角 (OWRK)"""
    l = _liquid_params(liquid)
    cos = 2 * (np.sqrt(se.gamma_lw * l[0]) + np.sqrt(se.gamma_p * (l[1] + l[2]))) / l[0] - 1
    cos = np.clip(cos, -1, 1)
    return float(np.degrees(np.arccos(cos)))


def run(theta1, theta2, liquid1="water", liquid2="diiodomethane", output_dir="output"):
    """一键计算表面能"""
    se = owrk_surface_energy(theta1, theta2, liquid1, liquid2)
    return {
        "surface_energy": se,
        "theta1_deg": theta1, "liquid1": liquid1,
        "theta2_deg": theta2, "liquid2": liquid2,
        "result": repr(se),
    }
