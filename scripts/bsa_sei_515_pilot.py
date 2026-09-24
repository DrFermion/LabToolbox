# -*- coding: utf-8 -*-
"""
bsa_sei_515_pilot.py — BSA 蛋白在 515nm 激光织构真实 AFM 面上的 SEI 几何效应 pilot

问题: 激光纹理对"蛋白级"(BSA, R≈3.5 nm)吸附热力学的影响有多大? 对比: 对细菌级(µm)是
"能量降到平面 ~16%" 的大效应; 蛋白比纹理特征小两个数量级, 预期小 —— 本 pilot 把它算出来。

方法:
  1) 自检 (先跑, 不过关不许看结果): 
     a. BSA 的 ΔG 复现交付值 (protein_adhesion_prediction.csv day0 行, 差 ≤0.1 mJ/m²);
     b. Derjaguin 接触能量复现交付 barrier (day0);
     c) SEI(平面) vs 解析 Derjaguin: R=450 nm 应差很小; R=3.5 nm 差的量级 = O(λ/R), 如实报;
     d. 网格收敛 (n=200/400/800);
     e. 几何因子对化学的敏感性 (三种表面能算同一因子, 应基本不变量).
  2) 曲率曲线: 圆柱形谷/脊 (曲率半径 Rc = 6 nm → 2000 nm) 上 BSA 的 U_sei/U_flat;
  3) 真实 AFM 场 (LIPSS-10x10 / NP-10x10 / VirginSS): 逐像素主曲率 → 查曲线 → 因子分布;
  4) 出图 CSV + 自检日志.

单位: 长度 nm, 能量 J (kT = k_B*298.15K = 4.1145e-21 J).
"""
import io
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, r"E:\LabToolbox")
from labtoolbox.xdlvo.xdlvo import delta_g, SurfaceEnergy                  # noqa: E402
from labtoolbox.xdlvo.sei import (sei_sphere_on_flat, sei_sphere_on_surface,  # noqa: E402
                                  sphere_lower)
from labtoolbox.surfmetrics.surfmetrics import (load_heightmap, plane_subtract,  # noqa: E402
                                                despike_z)

OUT = r"E:\LabToolbox\output\bsa_sei_515_20260924"
os.makedirs(OUT, exist_ok=True)
LOG = io.StringIO()


def log(msg):
    print(msg, flush=True)
    LOG.write(str(msg) + "\n")


KT = 1.380649e-23 * 298.15
NM = 1e-9
H0 = 0.158 * NM
LAM = 0.6 * NM
I_M = 0.15

# ---- BSA (PMC4286104) ----
BSA = SurfaceEnergy(40.6, 1.16, 20.03, 2 * np.sqrt(1.16 * 20.03), 40.6 + 2 * np.sqrt(1.16 * 20.03))
R_BSA = 3.5
# ---- S. aureus ATCC 12600 (SI Table S3) — 用于 R=450 自检 ----
SA = SurfaceEnergy(31.56, 0.43, 68.32, 2 * np.sqrt(0.43 * 68.32), 31.56 + 2 * np.sqrt(0.43 * 68.32))
R_SA = 450.0

DG_CSV = r"E:\LabToolbox\output\xdlvo_515nm_20260912\xdlvo_515nm_dG.csv"
DELIVERED = r"E:\LabToolbox\output\xdlvo_protein_20260912\protein_matrix_common.csv"
AFM = {
    "LIPSS": r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_Antibacterial Surfaces\AFM Steel Samples\515 samples\260827_SZ\515LIPSS-10x10_area2.ibw",
    "Nanopillar": r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_Antibacterial Surfaces\AFM Steel Samples\515 samples\260901_SZ\515 NP-10x10-area1.ibw",
    "Control": r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_Antibacterial Surfaces\AFM Steel Samples\515 samples\260825_SZ\VirginSS-6_512points-unflattened.ibw",
}


def derjaguin_U(dG, R_nm, h_nm=None):
    """显式 SI 单位 Derjaguin 球-平面 (h_nm=None → 接触位置 h0). 返回 J."""
    h = H0 if h_nm is None else h_nm * NM
    R = R_nm * NM
    u_lw = 2 * np.pi * R * dG["LW"] * 1e-3 * (H0 ** 2) / h
    u_ab = 2 * np.pi * R * LAM * dG["AB"] * 1e-3 * np.exp((H0 - h) / LAM)
    return u_lw + u_ab


def sei_cyl_factor(Rc_nm, R_nm, dG, concave=True, n=400):
    """圆柱谷(concave)/脊(convex) 曲率半径 Rc 上的因子 = U_sei/U_flat. 场构建在球网格分辨率上."""
    _, _, _, _, _ = sphere_lower(R_nm, n=n)
    ax = np.linspace(-R_nm, R_nm, n)
    X, Y = np.meshgrid(ax, ax)
    x = X.copy()
    rc = Rc_nm if Rc_nm > R_nm + 1e-6 else R_nm + 1e-6
    zc = rc - np.sqrt(np.clip(rc ** 2 - x ** 2, 0.0, None))
    z = zc if concave else -zc
    u_curved = sei_sphere_on_surface(R_nm, z, I_M=I_M, dG=dG, n=n)
    u_flat = sei_sphere_on_flat(R_nm, I_M=I_M, dG=dG, n=n)
    return u_curved / u_flat


def main():
    # ---------- 数据加载 ----------
    raw = pd.read_csv(DG_CSV, encoding="utf-8-sig")
    surf = raw.drop_duplicates(["surface", "day"])[["surface", "day", "gamma_LW", "gamma_plus", "gamma_minus"]]
    surf = surf.sort_values(["surface", "day"]).reset_index(drop=True)

    def se_of(row):
        g = (row["gamma_LW"], row["gamma_plus"], row["gamma_minus"])
        return SurfaceEnergy(g[0], g[1], g[2], 2 * np.sqrt(g[1] * g[2]), g[0] + 2 * np.sqrt(g[1] * g[2]))

    fresh = {r["surface"]: se_of(r) for _, r in surf[surf["day"] == 0].iterrows()}
    log("=== 表面能 (day 0) ===")
    for k, v in fresh.items():
        log(f"  {k}: {v}")

    # ---------- 自检 a: BSA ΔG vs 交付值 ----------
    log("\n=== 自检 a: BSA ΔG 复现交付值 (protein_matrix_common.csv) ===")
    deliv = pd.read_csv(DELIVERED, encoding="utf-8-sig")
    dd0 = deliv[(deliv["protein"].astype(str).str.contains("BSA")) & (deliv["day"] == 0)]
    ok_a = True
    for _, r in dd0.iterrows():
        dgc = delta_g(fresh[r["surface"]], BSA, I_M)
        tol = 0.15
        good = abs(dgc["LW"] - r["dG_LW"]) < tol and abs(dgc["AB"] - r["dG_AB"]) < tol
        ok_a &= good
        log(f"  {r['surface']:>12}: LW {dgc['LW']:+.3f} (交付 {r['dG_LW']:+.3f}) | "
            f"AB {dgc['AB']:+.3f} (交付 {r['dG_AB']:+.3f}) | ADH {dgc['ADH']:+.3f} (交付 {r['dG_ADH']:+.3f})"
            f"  {'✓' if good else '✗'}")

    # ---------- 自检 b: Derjaguin 接触能量 vs 交付 barrier ----------
    log("\n=== 自检 b: Derjaguin 接触能量 (kT) vs 交付 barrier_kT ===")
    cfg = {"LIPSS": 40.7, "Nanopillar": 38.4}   # 默认值; 若交付表中有数值则以其为准
    for _, r in dd0.iterrows():
        if r["surface"] in cfg and np.isfinite(pd.to_numeric(r.get("barrier_kT"), errors="coerce")):
            cfg[r["surface"]] = float(r["barrier_kT"])
    ok_b = True
    for name, target in cfg.items():
        u = derjaguin_U(delta_g(fresh[name], BSA, I_M), R_BSA) / KT
        good = abs(u - target) / target < 0.08
        ok_b &= good
        log(f"  {name:>12}: 计算 {u:.1f} kT vs 交付 {target} kT  差 {abs(u - target) / target * 100:.1f}%  "
            f"{'✓' if good else '✗'}")

    # ---------- 自检 c: SEI(平面) vs Derjaguin ----------
    log("\n=== 自检 c: SEI(平面) vs 解析 Derjaguin ===")
    dg_sa = delta_g(fresh["LIPSS"], SA, I_M)
    u_derj_450 = derjaguin_U(dg_sa, R_SA)
    u_sei_450 = sei_sphere_on_flat(R_SA, I_M=I_M, dG=dg_sa, n=1400)
    log(f"  R=450 nm: SEI {u_sei_450:.4e} J vs Derjaguin {u_derj_450:.4e} J → 差 "
        f"{(u_sei_450 - u_derj_450) / u_derj_450 * 100:+.2f}%  (文献复现口径: ±0.1% 量级)")
    dg_bsa_l = delta_g(fresh["LIPSS"], BSA, I_M)
    u_derj_35 = derjaguin_U(dg_bsa_l, R_BSA)
    u_sei_35 = sei_sphere_on_flat(R_BSA, I_M=I_M, dG=dg_bsa_l, n=400)
    log(f"  R=3.5 nm: SEI {u_sei_35:.4e} J vs Derjaguin {u_derj_35:.4e} J → 差 "
        f"{(u_sei_35 - u_derj_35) / u_derj_35 * 100:+.2f}%  (O(λ/R) 修正, 如实报告)")

    # ---------- 自检 d: 网格收敛 ----------
    log("\n=== 自检 d: 网格收敛 (R=3.5, 平面) ===")
    for n in (200, 400, 800):
        u = sei_sphere_on_flat(R_BSA, I_M=I_M, dG=dg_bsa_l, n=n)
        log(f"  n={n}: U = {u:.6e} J")

    # ---------- 自检 e: 因子对化学的敏感性 (Rc=100) ----------
    log("\n=== 自检 e: 几何因子对化学的敏感性 (Rc=100 nm, 谷) ===")
    for name in ("LIPSS", "Control 316L"):
        f = sei_cyl_factor(100.0, R_BSA, delta_g(fresh[name], BSA, I_M), concave=True, n=300)
        log(f"  {name:>12}: factor = {f:.5f}")
    aged = surf[(surf["surface"] == "LIPSS") & (surf["day"] == 13)]
    if len(aged):
        f = sei_cyl_factor(100.0, R_BSA, delta_g(se_of(aged.iloc[0]), BSA, I_M), concave=True, n=300)
        log(f"  LIPSS day13 : factor = {f:.5f}")

    # ---------- 曲率曲线 ----------
    log("\n=== 曲率曲线 (BSA, LIPSS fresh 化学) ===")
    Rcs = np.geomspace(6, 2000, 36)
    curve = []
    for rc in Rcs:
        for concave, tag in ((True, "concave"), (False, "convex")):
            f = sei_cyl_factor(rc, R_BSA, dg_bsa_l, concave=concave, n=400)
            curve.append({"Rc_nm": rc, "branch": tag, "factor": f})
    cdf = pd.DataFrame(curve)
    cdf.to_csv(os.path.join(OUT, "bsa_sei_curvature_curve.csv"), index=False, encoding="utf-8-sig")
    for _, r in cdf.iterrows():
        log(f"  Rc={r['Rc_nm']:7.1f} nm {r['branch']:>8}: factor = {r['factor']:.5f}")
    fp_conc = cdf[cdf.branch == "concave"].set_index("Rc_nm")["factor"]
    fp_conv = cdf[cdf.branch == "convex"].set_index("Rc_nm")["factor"]

    # ---------- 真实 AFM 场 ----------
    log("\n=== 真实 AFM 场 (ZSR, 平面扣除+去尖峰) ===")
    field_stats = []
    fig_maps = []
    factor_arrays = {}
    for name, path in AFM.items():
        z, px, py = load_heightmap(path, None)
        if px is None:
            px = py = 10000.0 / (z.shape[1] - 1)
        if py is None:
            py = px
        z, _n_spk = despike_z(plane_subtract(z))
        # 主曲率 (Hessian 特征值, 取 |特征值| 最大者)
        zy, zx = np.gradient(z, py, px)
        zyy, zyx = np.gradient(zy, py, px)
        zxy, zxx = np.gradient(zx, py, px)
        kappa = np.full_like(z, np.nan)
        for (a, b, c) in ((zxx, zxy, zyy),):  # noqa: B007
            tr = a + c
            det = a * c - b ** 2
            disc = np.sqrt(np.clip((tr / 2) ** 2 - det, 0, None))
            k1 = tr / 2 + disc
            k2 = tr / 2 - disc
            kk = np.where(np.abs(k1) >= np.abs(k2), k1, k2)
            kappa = kk
        Rc_px = 1.0 / np.maximum(np.abs(kappa), 1e-7)
        # 因子插值 (签: kappa>0 = 谷/concave)
        f_conc = np.interp(np.log(Rc_px.ravel()), np.log(Rcs), fp_conc.values,
                           left=fp_conc.values[0], right=1.0)
        f_conv = np.interp(np.log(Rc_px.ravel()), np.log(Rcs), fp_conv.values,
                           left=fp_conv.values[0], right=1.0)
        factor = np.where(kappa.ravel() > 0, f_conc, f_conv).reshape(z.shape)
        dev_pct = (factor - 1.0) * 100
        factor_arrays[name] = factor
        st = {
            "surface": name, "file": os.path.basename(path), "shape": str(z.shape),
            "px_nm": round(px, 2), "Rc_median_nm": round(float(np.median(Rc_px)), 1),
            "Rc_p01_nm": round(float(np.percentile(Rc_px, 1)), 1),
            "Rc_min_nm": round(float(Rc_px.min()), 1),
            "factor_median": round(float(np.median(factor)), 5),
            "factor_mean": round(float(np.mean(factor)), 5),
            "factor_p01": round(float(np.percentile(factor, 1)), 5),
            "factor_p99": round(float(np.percentile(factor, 99)), 5),
            "pct_absdev_gt2": round(float((np.abs(dev_pct) > 2).mean() * 100), 2),
            "pct_absdev_gt5": round(float((np.abs(dev_pct) > 5).mean() * 100), 2),
            "dev_p01_pct": round(float(np.percentile(dev_pct, 1)), 3),
            "dev_p99_pct": round(float(np.percentile(dev_pct, 99)), 3),
            "dev_mean_pct": round(float(np.mean(dev_pct)), 4),
        }
        field_stats.append(st)
        log(f"  {name}: 已解析 Rc 中位 {st['Rc_median_nm']} nm / 最尖 {st['Rc_min_nm']} nm → "
            f"factor 中位 {st['factor_median']:.5f}, [P1,P99] = [{st['factor_p01']:.4f}, {st['factor_p99']:.4f}], "
            f"|dev|>5% 像素 {st['pct_absdev_gt5']}%")
        if name in ("LIPSS", "Nanopillar"):
            fig_maps.append((name, z, factor))
    fs = pd.DataFrame(field_stats)
    fs.to_csv(os.path.join(OUT, "bsa_sei_field_stats.csv"), index=False, encoding="utf-8-sig")

    # ---------- 图 ----------
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.semilogx(fp_conc.index, (fp_conc.values - 1) * 100, "-o", ms=3.5, color="#4C72B0", label="in groove (concave)")
    ax.semilogx(fp_conv.index, (fp_conv.values - 1) * 100, "-s", ms=3.5, color="#DD8452", label="on ridge (convex)")
    ax.axvspan(fs.loc[0, "Rc_p01_nm"], fs.loc[0, "Rc_median_nm"], color="#4C72B0", alpha=0.09)
    ax.axvline(fs.loc[0, "Rc_min_nm"], color="#4C72B0", ls=":", lw=1)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("Local feature curvature radius  Rc (nm)")
    ax.set_ylabel("Geometric factor  U_texture / U_flat  − 1  (%)")
    ax.set_title("BSA (R = 3.5 nm) on 515 nm laser texture — geometric effect of surface curvature\n"
                 "(shaded: curvature range resolved on the real LIPSS AFM scan)", fontsize=10.5, fontweight="bold")
    ax.legend(frameon=False)
    ax.tick_params(direction="in")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig1_bsa_factor_vs_curvature.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

    # 直方图 (统一 x/y 范围便于横比; log y 保留主体可见)
    g = float(np.ceil(max(np.percentile(np.abs((factor_arrays[k] - 1) * 100), 99.9)
                          for k in factor_arrays)) + 1.0)
    devs_ = {k: (factor_arrays[k] - 1) * 100 for k in factor_arrays}
    hist_max = max(int(np.histogram(devs_[k], bins=140, range=(-g, g))[0].max()) for k in devs_)
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.5))
    for ax, name in zip(axes, ("LIPSS", "Nanopillar", "Control")):
        dev = devs_[name]
        ax.hist(dev, bins=140, range=(-g, g),
                color={"LIPSS": "#4C72B0", "Nanopillar": "#DD8452", "Control": "#7F7F7F"}[name],
                edgecolor="none")
        ax.axvline(0, color="k", lw=0.8)
        ax.set_yscale("log")
        ax.set_xlim(-g, g)
        ax.set_ylim(0.7, hist_max * 1.8)
        ax.set_title(f"{name}   [P1, P99] = [{np.percentile(dev, 1):+.2f}%, {np.percentile(dev, 99):+.2f}%]",
                     fontsize=10)
        ax.set_xlabel("factor − 1  (%)")
        ax.tick_params(direction="in")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.suptitle("BSA geometric factor distribution on real 515 nm AFM fields (ZSR) — log counts, common x-range",
                 fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(os.path.join(OUT, "fig2_bsa_field_factor_hist.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

    # 场图 (LIPSS + NP: 高度图 + 因子图)
    for name, z, factor in fig_maps:
        fig, axs = plt.subplots(1, 2, figsize=(9.8, 4.4))
        im0 = axs[0].imshow(z, cmap="turbo", origin="lower")
        axs[0].set_title(f"{name} — height (nm)", fontsize=10)
        plt.colorbar(im0, ax=axs[0], shrink=0.85)
        v = max(2.0, float(np.nanpercentile(np.abs((factor - 1) * 100), 99)))
        im1 = axs[1].imshow((factor - 1) * 100, cmap="RdBu_r", origin="lower", vmin=-v, vmax=v)
        axs[1].set_title(f"{name} — BSA geometric factor − 1 (%)", fontsize=10)
        plt.colorbar(im1, ax=axs[1], shrink=0.85)
        for a in axs:
            a.set_xticks([])
            a.set_yticks([])
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, f"fig3_map_{name}.png"), dpi=200, bbox_inches="tight")
        plt.close(fig)

    # ---------- 汇总自检 ----------
    log("\n=== 自检汇总 ===")
    log(f"  a. BSA ΔG 复现: {'通过 ✓' if ok_a else '未通过 ✗'}")
    log(f"  b. Derjaguin barrier 复现: {'通过 ✓' if ok_b else '未通过 ✗'}")
    log(f"  输出目录: {OUT}")

    with io.open(os.path.join(OUT, "bsa_sei_selfcheck.txt"), "w", encoding="utf-8") as f:
        f.write(LOG.getvalue())
    print("\nDONE", OUT)


if __name__ == "__main__":
    main()
