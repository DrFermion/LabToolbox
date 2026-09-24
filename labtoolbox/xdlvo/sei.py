# -*- coding: utf-8 -*-
"""XDLVO–SEI: 在真实/合成地形上做 Surface Element Integration.

物理定义 (与 Wang et al. 2026, Materials & Design 263, 115626, §2.7 一致):
    每个表面单元 dA 上, 局部间距 h(x,y) 处的单位面积自由能 ΔG(h),
    总相互作用能 U = ∫∫ ΔG(h(x,y)) dA
单位: 长度 nm, 能量 J, ΔG 接触值 mJ/m².

给定 ΔG(h0) 的分量 (LW/AB/EL, mJ/m²) 与随距离的衰减:
    ΔG_LW(h) = ΔG_LW(h0) · (h0/h)^2
    ΔG_AB(h) = ΔG_AB(h0) · exp((h0-h)/lambda_AB)
    ΔG_EL(h) = (kappa*eps0*eps_r/2)*[(z1^2+z2^2)(1-coth(kappa h)) + 2 z1 z2 csch(kappa h)]
"""
from __future__ import annotations

import numpy as np

from .xdlvo import PARAMS, PHYS, debye_length, delta_g, water_dielectric

H0 = PARAMS["h0"]              # 接触间距 (nm)


def dg_per_area(h_nm, dG, I_M=0.15, T_K=298.15, zeta_m=None, zeta_f=None):
    """单位面积自由能 ΔG(h) [J/m²]。h_nm 可为数组。"""
    h = np.asarray(h_nm, dtype=float)
    h = np.clip(h, H0, None)
    out = np.zeros_like(h)
    # LW: ΔG(h0)*(h0/h)^2  (mJ/m² → J/m²)
    out += (dG["LW"] * (H0 / h) ** 2) * 1e-3
    # AB: 指数衰减
    lam = PARAMS["lambda_ab"]
    out += (dG["AB"] * np.exp((H0 - h) / lam)) * 1e-3
    # EL
    if zeta_m is not None and zeta_f is not None and I_M:
        kappa = debye_length(I_M, T_K)          # 1/nm
        eps_r = water_dielectric(T_K)
        kh = np.clip(kappa * h, 1e-9, None)
        coth = 1.0 / np.tanh(kh)
        csch = 1.0 / np.sinh(kh)
        out += (kappa * PHYS["eps0"] * eps_r / 2.0) * (
            (zeta_m ** 2 + zeta_f ** 2) * (1 - coth) + 2 * zeta_m * zeta_f * csch) * 1e9
    return out


def sphere_lower(R_nm, n=None):
    """返回球下表面高度场 (相对球心): z = -sqrt(R^2-r^2) 的网格与坐标."""
    if n is None:
        n = int(np.clip(4 * R_nm, 200, 900))
    ax = np.linspace(-R_nm, R_nm, n)
    X, Y = np.meshgrid(ax, ax)
    rr2 = X ** 2 + Y ** 2
    mask = rr2 <= R_nm ** 2
    Z = np.full_like(X, np.nan)
    Z[mask] = -np.sqrt(R_nm ** 2 - rr2[mask])
    dx = ax[1] - ax[0]
    return X, Y, Z, dx, mask


def sei_sphere_on_surface(R_nm, surf_z, I_M=0.15, dG=None, T_K=298.15,
                          zeta_m=None, zeta_f=None, n=None):
    """球在起伏地形上的 SEI 总能量 [J]。

    surf_z: 2D 高度场 [nm], 网格间距假定与球网格一致 (最近邻采样)。
    dG:     delta_g() 的输出 (接触值, mJ/m²)。若为 None 则抛错。
    """
    if dG is None:
        raise ValueError("需要 dG (来自 delta_g())")
    X, Y, Zs, dx, mask = sphere_lower(R_nm, n=n)
    # 地形最近邻重采样到球网格
    ny, nx = surf_z.shape
    ax = np.linspace(-R_nm, R_nm, Zs.shape[0])
    ys = np.linspace(0, ny - 1, Zs.shape[0]).astype(int)
    xs = np.linspace(0, nx - 1, Zs.shape[1]).astype(int)
    z_s = surf_z[np.ix_(ys, xs)]
    # 让球刚好接触最高点: h_min = H0
    gap_raw = Zs - z_s
    hmin = np.nanmin(gap_raw[mask])
    shift = (H0 - hmin)
    h = gap_raw + shift
    h_flat = h[mask]
    dA = (dx * 1e-9) ** 2                      # m²
    g = dg_per_area(h_flat, dG, I_M=I_M, T_K=T_K, zeta_m=zeta_m, zeta_f=zeta_f)  # J/m²
    return float(np.sum(g) * dA)


def sei_sphere_on_flat(R_nm, I_M=0.15, dG=None, T_K=298.15, zeta_m=None, zeta_f=None, n=None):
    """平面上的球 (SEI 解析积分, 用于自检)。"""
    X, Y, Zs, dx, mask = sphere_lower(R_nm, n=n)
    # 注意: Zs 在半球外为 NaN → 必须用 nanmin, 否则整个积分变成 NaN (2026-09-24 修复)
    h = (Zs - np.nanmin(Zs)) + H0
    h_flat = h[mask]
    dA = (dx * 1e-9) ** 2
    g = dg_per_area(h_flat, dG, I_M=I_M, T_K=T_K, zeta_m=zeta_m, zeta_f=zeta_f)
    return float(np.sum(g) * dA)


def lipss_field(period_nm, depth_nm, size_nm=2000.0, n=400, angle_deg=0.0):
    """解析 LIPSS: z = (depth/2) sin(2πx/Λ)  (与论文 Eq.5 同形)."""
    ax = np.linspace(0, size_nm, n)
    X, Y = np.meshgrid(ax, ax)
    th = np.radians(angle_deg)
    u = X * np.cos(th) + Y * np.sin(th)
    Z = (depth_nm / 2.0) * np.sin(2 * np.pi * u / period_nm)
    return Z


def sei_rod_on_surface(R_rod_nm, length_nm, surf_z, I_M=0.15, dG=None, T_K=298.15,
                       zeta_m=None, zeta_f=None, n_per_sphere=None):
    """杆状菌: 球链近似 (沿长轴排 N 个半径 R 的球, 间距 = R), 返回每根杆的总能量 (J)."""
    if dG is None:
        raise ValueError("需要 dG")
    R = R_rod_nm
    n_sphere = max(3, int(round(length_nm / R)) + 1)
    centres = np.linspace(-(length_nm - 2 * R) / 2.0, (length_nm - 2 * R) / 2.0, n_sphere)
    tot = 0.0
    X, Y, Zs, dx, mask = sphere_lower(R, n=n_per_sphere)
    dA = (dx * 1e-9) ** 2
    ny, nx = surf_z.shape
    ys = np.linspace(0, ny - 1, Zs.shape[0]).astype(int)
    xs = np.linspace(0, nx - 1, Zs.shape[1]).astype(int)
    z_s0 = surf_z[np.ix_(ys, xs)]
    for c in centres:
        # 沿 x 轴平移地形 (周期性外推用 np.roll)
        shift_px = int(round(c / (2 * R) * (Zs.shape[1] - 1)))
        z_s = np.roll(z_s0, shift_px, axis=1)
        gap_raw = Zs - z_s
        hmin = np.nanmin(gap_raw[mask])
        h = gap_raw + (H0 - hmin)
        g = dg_per_area(h[mask], dG, I_M=I_M, T_K=T_K, zeta_m=zeta_m, zeta_f=zeta_f)
        tot += float(np.sum(g) * dA)
    return tot


__all__ = ["dg_per_area", "sei_sphere_on_surface", "sei_sphere_on_flat",
           "lipss_field", "sei_rod_on_surface", "sphere_lower"]
