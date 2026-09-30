# -*- coding: utf-8 -*-
"""proteins_environments.py — 体液环境（血浆 / 组织液 / 关节滑液）中的蛋白黏附：XDLVO + SEI 模拟

目标（主人 2026-09-29 任务 2）：模拟人体血液、组织液、关节间隙里的蛋白黏附
  - 蛋白: 白蛋白(BSA 两套文献参数) / 人纤维蛋白原 / 人纤连蛋白
  - 表面: 515 nm 样品 LIPSS / Nanopillar / Control 316L，按真实时效序列 (day 0→81)
  - 介质: 生理离子强度 0.15 M、pH 7.4、37 °C
  - 输出: ΔG_LW/AB/ADH、Derjaguin 接触能量(势垒)、体液条件膜对细菌黏附的影响

自检（先过自检再看结果）:
  a. BSA day-0 ΔG 复现 protein_matrix_common.csv (差 ≤0.15 mJ/m²)
  b. Derjaguin 接触能量复现交付 barrier_kT (差 <8%)
  c. EL 项数量级 (0.15 M 下应 ~1e-3 mJ/m²)
  d. SEI(平面) vs Derjaguin 的 O(λ/R) 修正 (如实报告)
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
from labtoolbox.xdlvo.xdlvo import SurfaceEnergy, delta_g, interaction_energy  # noqa: E402
from labtoolbox.xdlvo.sei import sei_sphere_on_flat, sei_sphere_on_surface, sphere_lower  # noqa: E402

OUT = r"E:\LabToolbox\output\proteins_environments_20260930"
os.makedirs(OUT, exist_ok=True)
LOG = io.StringIO()


def log(msg):
    print(msg, flush=True)
    LOG.write(str(msg) + "\n")


NM = 1e-9
H0 = 0.158 * NM
LAM = 0.6 * NM
I_M = 0.15                 # 生理离子强度 (血浆≈组织液≈滑液≈0.15 M)
T_BODY = 310.15            # 37 °C 体温
T_ROOM = 298.15            # 25 °C (与既往交付对齐用)

DG_CSV = r"E:\LabToolbox\output\xdlvo_515nm_20260912\xdlvo_515nm_dG.csv"
DELIVERED = r"E:\LabToolbox\output\xdlvo_protein_20260912\protein_matrix_common.csv"
SUSPECT_DAYS = {7, 8, 9, 10}   # 515-6 工作簿疑似公式填充值 (既往备注), 时间线图剔除

PROTEINS = {
    "Albumin (BSA A)":  dict(g=(40.60, 1.16, 20.03),  R=3.5, z=-13.0,
                             src="PMC4286104 Table I"),
    "Albumin (BSA B)":  dict(g=(43.22, 1.065, 47.68), R=3.5, z=-13.0,
                             src="Membranes 2025, 15, 277, Table 3"),
    "Fibrinogen (human)": dict(g=(37.6, 0.1, 38.0),   R=5.0, z=-20.0,
                               src="van Oss, Surface properties of fibrinogen and fibrin, Table II"),
    "Fibronectin (human)": dict(g=(29.5, 3.9, 52.1),  R=5.0, z=-15.0,
                                src="同上"),
}

# 体液组成 (用于报告; 浓度单位 g/L)
ENVIRONMENTS = {
    "Blood plasma": dict(albumin=40.0, fibrinogen=3.0, igg=12.0, fibronectin=0.3, ha=0.0,
                         note="总蛋白 60–80 g/L; 白蛋白约占一半"),
    "Interstitial fluid": dict(albumin=29.0, fibrinogen=0.5, igg=6.0, fibronectin=0.1, ha=0.0,
                               note="前臂皮下 wick 法白蛋白 29 g/L; 随组织差异大"),
    "Synovial fluid (joint)": dict(albumin=11.0, fibrinogen=0.0, igg=7.0, fibronectin=0.05, ha=3.0,
                                   note="滑液几乎不含纤维蛋白原(不凝); HA ≈3 g/L"),
}

BACTERIA = {
    "S. aureus 12600": dict(g=(31.56, 0.43, 68.32), R=450.0, src="M&D SI Table S3"),
    "E. coli F1693":   dict(g=(35.60, 0.14, 67.68), R=450.0, src="同上"),
}


def se(g):
    return SurfaceEnergy(g[0], g[1], g[2], 2 * np.sqrt(g[1] * g[2]), g[0] + 2 * np.sqrt(g[1] * g[2]))


def derjaguin_U(dG, R_nm, T_K):
    """显式 SI 单位 Derjaguin 球-平面接触能量 (J) —— 与既往交付同口径."""
    R = R_nm * NM
    u_lw = 2 * np.pi * R * dG["LW"] * 1e-3 * (H0 ** 2) / H0
    u_ab = 2 * np.pi * R * LAM * dG["AB"] * 1e-3 * np.exp(0.0)
    return u_lw + u_ab, 1.380649e-23 * T_K


def main():
    # ---------------- 表面能 ----------------
    raw = pd.read_csv(DG_CSV, encoding="utf-8-sig")
    surf = (raw.drop_duplicates(["surface", "day"])[["surface", "day", "gamma_LW", "gamma_plus", "gamma_minus"]]
            .sort_values(["surface", "day"]).reset_index(drop=True))
    surfaces = {}
    for s in surf["surface"].unique():
        sub = surf[surf["surface"] == s]
        surfaces[s] = {int(r["day"]): se((r["gamma_LW"], r["gamma_plus"], r["gamma_minus"]))
                       for _, r in sub.iterrows()}
    log("=== 表面 (SFE 来源: xdlvo_515nm_dG.csv) ===")
    for s, d in surfaces.items():
        log(f"  {s:>14}: days {sorted(d)[:6]}...{sorted(d)[-3:]} (共 {len(d)})")

    # ---------------- 自检 a/b ----------------
    log("\n=== 自检 a: BSA ΔG 复现交付值 (25 °C 口径) ===")
    deliv = pd.read_csv(DELIVERED, encoding="utf-8-sig")
    dd0 = deliv[(deliv["protein"].astype(str).str.contains("BSA")) & (deliv["day"] == 0)]
    ok_a = True
    for _, r in dd0.iterrows():
        dgc = delta_g(surfaces[r["surface"]][0], se(PROTEINS["Albumin (BSA A)"]["g"]), I_M, T_ROOM,
                      zeta_m=-25.0, zeta_f=-13.0)
        good = (abs(dgc["LW"] - r["dG_LW"]) < 0.15) and (abs(dgc["AB"] - r["dG_AB"]) < 0.15)
        ok_a &= good
        log(f"  {r['surface']:>14}: LW {dgc['LW']:+.3f} (交付 {r['dG_LW']:+.3f}) | AB {dgc['AB']:+.3f} "
            f"(交付 {r['dG_AB']:+.3f}) | ADH {dgc['ADH']:+.3f} {'✓' if good else '✗'}")
    ok_b = True
    log("  " + "-" * 60)
    for s, target in (("LIPSS", 40.7), ("Nanopillar", 38.4)):
        u, kt = derjaguin_U(delta_g(surfaces[s][0], se(PROTEINS["Albumin (BSA A)"]["g"]), I_M, T_ROOM,
                                    zeta_m=-25.0, zeta_f=-13.0), 3.5, T_ROOM)
        rel = abs(u / kt - target) / target
        ok_b &= rel < 0.08
        log(f"  自检 b {s:>14}: Derjaguin {u / kt:.1f} kT vs 交付 {target} kT 差 {rel * 100:.1f}% "
            f"{'✓' if rel < 0.08 else '✗'}")

    # ---------------- 自检 c/d ----------------
    dg_case = delta_g(surfaces["LIPSS"][0], se(PROTEINS["Fibrinogen (human)"]["g"]), I_M, T_BODY,
                      zeta_m=-25.0, zeta_f=-20.0)
    log(f"\n=== 自检 c: EL 项量级 (0.15 M): ΔG_EL = {dg_case['EL']:.3e} mJ/m² (应 ≪ |LW|,|AB|) ===")
    sei_flat = {}
    for pname, p in PROTEINS.items():
        dgp = delta_g(surfaces["LIPSS"][0], se(p["g"]), I_M, T_BODY, zeta_m=-25.0, zeta_f=p["z"])
        u_der, kt = derjaguin_U(dgp, p["R"], T_BODY)
        u_sei = sei_sphere_on_flat(p["R"], I_M=I_M, dG=dgp, n=600)
        sei_flat[pname] = u_sei / u_der
        log(f"  自检 d {pname:>18} (R={p['R']} nm): SEI/derjaguin = {u_sei / u_der:.4f} "
            f"({(u_sei / u_der - 1) * 100:+.1f}%, O(λ/R) 修正)")

    # ---------------- 主矩阵 ----------------
    rows = []
    for sname, days in surfaces.items():
        for day, sfe in sorted(days.items()):
            if day in SUSPECT_DAYS:
                continue
            for pname, p in PROTEINS.items():
                dgc = delta_g(sfe, se(p["g"]), I_M, T_BODY, zeta_m=-25.0, zeta_f=p["z"])
                u, kt = derjaguin_U(dgc, p["R"], T_BODY)
                rows.append(dict(surface=sname, day=day, protein=pname,
                                 dG_LW=round(dgc["LW"], 3), dG_AB=round(dgc["AB"], 3),
                                 dG_ADH=round(dgc["ADH"], 3), dG_EL_meV=round(dgc["EL"], 6),
                                 barrier_kT=round(u / kt, 2),
                                 barrier_SEIcorr_kT=round(u / kt * sei_flat[pname], 2)))
    m = pd.DataFrame(rows)
    m.to_csv(os.path.join(OUT, "protein_surface_matrix.csv"), index=False, encoding="utf-8-sig")

    log("\n=== 主矩阵: Day 0 (新鲜) 与 Day 58 (老化代表态; day81 的 LIPSS 为已知接触角尖峰异常) ===")
    for day in (0, 58):
        log(f"  -- day {day} --")
        for pname in PROTEINS:
            line = f"    {pname:>18}: "
            for sname in ("LIPSS", "Nanopillar", "Control 316L"):
                r = m[(m.surface == sname) & (m.day == day) & (m.protein == pname)]
                if len(r):
                    r = r.iloc[0]
                    line += f"{sname}: ΔG {r['dG_ADH']:+7.2f}, 势垒 {r['barrier_kT']:6.1f} kT | "
            log(line)

    # ---------------- 条件膜 → 细菌 ----------------
    log("\n=== 条件膜对细菌黏附的影响 (37 °C, 0.15 M) ===")
    films = {"bare LIPSS fresh (day 0)": ("surface", "LIPSS", 0),
             "bare LIPSS aged (day 58)": ("surface", "LIPSS", 58),
             "bare Control fresh (day 0)": ("surface", "Control 316L", 0),
             "bare Control aged (day 58)": ("surface", "Control 316L", 58)}
    for pname in ("Albumin (BSA A)", "Albumin (BSA B)", "Fibrinogen (human)", "Fibronectin (human)"):
        films[f"{pname} film"] = ("film", pname, None)
    brows = []
    for bname, b in BACTERIA.items():
        for fname, (kind, key, day) in films.items():
            sub = surfaces[key][day] if kind == "surface" else se(PROTEINS[key]["g"])
            dgc = delta_g(sub, se(b["g"]), I_M, T_BODY, zeta_m=-25.0, zeta_f=-20.0)
            u, kt = derjaguin_U(dgc, b["R"], T_BODY)
            brows.append(dict(bacterium=bname, substrate=fname, dG_ADH=round(dgc["ADH"], 2),
                              barrier_kT=round(u / kt, 1)))
    bdf = pd.DataFrame(brows)
    bdf.to_csv(os.path.join(OUT, "bacteria_on_films.csv"), index=False, encoding="utf-8-sig")
    for bname in BACTERIA:
        log(f"  -- {bname} --")
        for _, r in bdf[bdf.bacterium == bname].iterrows():
            log(f"    {r['substrate']:<28}: ΔG_ADH {r['dG_ADH']:+7.2f} mJ/m², 势垒 {r['barrier_kT']:6.1f} kT")

    # ---------------- 蛋白级 SEI 几何因子 (R=5 nm 补点) ----------------
    log("\n=== 蛋白级几何因子: R=5 nm 在曲率上 (LIPSS fresh 化学) ===")
    dg_fg = delta_g(surfaces["LIPSS"][0], se(PROTEINS["Fibrinogen (human)"]["g"]), I_M, T_BODY,
                    zeta_m=-25.0, zeta_f=-20.0)
    geom = []
    for rc in (8.0, 12.0, 20.0, 47.0, 100.0, 200.0):
        for concave, tag in ((True, "concave"), (False, "convex")):
            _, _, _, _, _ = sphere_lower(5.0, n=300)
            ax = np.linspace(-5.0, 5.0, 300)
            X, Y = np.meshgrid(ax, ax)
            r_eff = max(rc, 5.0 + 1e-6)
            zc = r_eff - np.sqrt(np.clip(r_eff ** 2 - X ** 2, 0.0, None))
            z = zc if concave else -zc
            f = sei_sphere_on_surface(5.0, z, I_M=I_M, dG=dg_fg, n=300) / \
                sei_sphere_on_flat(5.0, I_M=I_M, dG=dg_fg, n=300)
            geom.append(dict(R_nm=5.0, Rc_nm=rc, branch=tag, factor=round(float(f), 5)))
    gdf = pd.DataFrame(geom)
    gdf.to_csv(os.path.join(OUT, "sei_protein_scale_R5.csv"), index=False, encoding="utf-8-sig")
    for _, r in gdf.iterrows():
        log(f"  Rc={r['Rc_nm']:7.1f} nm {r['branch']:>8}: factor = {r['factor']:.5f}")

    # ---------------- 体液组成表 ----------------
    env = pd.DataFrame([dict(environment=k, **v) for k, v in ENVIRONMENTS.items()])
    env.to_csv(os.path.join(OUT, "environments_composition.csv"), index=False, encoding="utf-8-sig")

    # ---------------- 图 ----------------
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10.5, "figure.dpi": 200})

    # fig1: day0 vs day81 的 ΔG_ADH
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), sharey=True)
    sorder = ["LIPSS", "Nanopillar", "Control 316L"]
    porder = list(PROTEINS)
    colors = ["#4C72B0", "#9ecae1", "#DD8452", "#55A868"]
    for ax, day in zip(axes, (0, 58)):
        x = np.arange(len(sorder))
        w = 0.2
        for i, pname in enumerate(porder):
            vals = []
            for sname in sorder:
                r = m[(m.surface == sname) & (m.day == day) & (m.protein == pname)]
                vals.append(float(r.iloc[0]["dG_ADH"]) if len(r) else np.nan)
            ax.bar(x + (i - 1.5) * w, vals, w, label=pname if day == 0 else None, color=colors[i],
                   edgecolor="k", linewidth=0.4)
        ax.axhline(0, color="k", lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(sorder, fontsize=8.5)
        ax.set_title(f"Surface age: day {day}" + ("  (fresh)" if day == 0 else "  (aged)"))
        ax.set_ylabel("ΔG_ADH  (mJ m$^{-2}$)")
        ax.grid(axis="y", alpha=0.25)
    axes[0].legend(fontsize=8, frameon=False, ncol=2)
    fig.suptitle("Protein adhesion free energy on 515 nm laser-textured 316L — body-fluid conditions "
                 "(37 °C, 0.15 M)", fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(os.path.join(OUT, "fig1_dGADH_matrix.png"), bbox_inches="tight")
    plt.close(fig)

    # fig2: 势垒 vs 时效
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2), sharey=True)
    for ax, sname in zip(axes, ("LIPSS", "Control 316L")):
        for i, pname in enumerate(porder):
            sub = m[(m.surface == sname) & (m.protein == pname)].sort_values("day")
            ax.plot(sub["day"], sub["barrier_kT"], "-o", ms=3, color=colors[i], label=pname)
        ax.axhline(10, color="grey", ls=":", lw=1)
        ax.text(0.02, 0.06, "10 kT ≈ adsorption threshold", transform=ax.transAxes, fontsize=7.5,
                color="grey")
        ax.set_xlabel("Surface age (days after laser treatment)")
        ax.set_title(sname)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Energy barrier  (kT)")
    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle("Protein-adsorption barrier vs surface ageing (37 °C, 0.15 M, Derjaguin contact energy)",
                 fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(os.path.join(OUT, "fig2_barrier_vs_age.png"), bbox_inches="tight")
    plt.close(fig)

    # fig3: U(h) 曲线 (LIPSS fresh vs aged, 三蛋白)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), sharey=True)
    for ax, day in zip(axes, (0, 58)):
        for i, pname in enumerate(porder):
            p = PROTEINS[pname]
            dgc = delta_g(surfaces["LIPSS"][day], se(p["g"]), I_M, T_BODY, zeta_m=-25.0, zeta_f=p["z"])
            prof = interaction_energy(surfaces["LIPSS"][day], se(p["g"]), dgc, p["R"], I_M, T_BODY,
                                      zeta_m=-25.0, zeta_f=p["z"])
            h_arr = np.asarray(prof["h"], dtype=float)
            tot = np.asarray(prof["TOT"], dtype=float)
            ax.plot(h_arr, tot, "-", lw=1.6, color=colors[i], label=pname)
            if day == 0 and pname == "Albumin (BSA A)":
                log(f"  [fig3 sanity] day0 BSA-A: max U = {tot.max():.1f} kT @ h = {h_arr[int(tot.argmax())]:.3f} nm")
            if day == 58 and pname == "Albumin (BSA A)":
                log(f"  [fig3 sanity] day58 BSA-A: min U = {tot.min():.1f} kT @ h = {h_arr[int(tot.argmin())]:.3f} nm")
        ax.axhline(0, color="k", lw=0.8)
        ax.set_xscale("log")
        ax.set_xlim(0.1, 30)
        ax.set_ylim(-220, 180)
        ax.set_xlabel("Separation distance  h (nm, log scale)")
        ax.set_title(f"LIPSS, day {day}" + ("  (fresh)" if day == 0 else "  (aged)"))
        ax.grid(alpha=0.25, which="both")
    axes[0].set_ylabel("Interaction energy  U(h)  (kT)")
    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle("U(h) profiles on LIPSS in body-fluid conditions (37 °C, 0.15 M)", fontsize=11,
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(os.path.join(OUT, "fig3_uh_profiles.png"), bbox_inches="tight")
    plt.close(fig)

    # fig4: 细菌 vs 条件膜
    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    subs = list(dict.fromkeys(bdf["substrate"]))
    x = np.arange(len(subs))
    w = 0.38
    for i, bname in enumerate(BACTERIA):
        vals = [float(bdf[(bdf.bacterium == bname) & (bdf.substrate == s)].iloc[0]["dG_ADH"])
                for s in subs]
        ax.bar(x + (i - 0.5) * w, vals, w, label=bname, color=["#4C72B0", "#DD8452"][i],
               edgecolor="k", linewidth=0.4)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(subs, rotation=18, ha="right", fontsize=8)
    ax.set_ylabel("ΔG_ADH  (mJ m$^{-2}$)")
    ax.legend(fontsize=9, frameon=False)
    ax.grid(axis="y", alpha=0.25)
    ax.set_title("Bacterial adhesion energy onto bare surfaces vs protein conditioning films", fontsize=11,
                 fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig4_bacteria_on_films.png"), bbox_inches="tight")
    plt.close(fig)

    # ---------------- 汇总 ----------------
    log("\n=== 自检汇总 ===")
    log(f"  a. BSA ΔG 复现: {'通过 ✓' if ok_a else '未通过 ✗'}")
    log(f"  b. Derjaguin barrier 复现: {'通过 ✓' if ok_b else '未通过 ✗'}")
    log(f"  c. EL 项 (0.15 M): {dg_case['EL']:.1e} mJ/m² (可忽略; 结论由 LW+AB 主导)")
    log(f"  d. SEI/derjaguin 修正: " + "; ".join(f"{k} {v:.3f}" for k, v in sei_flat.items()))
    log(f"  输出目录: {OUT}")
    with io.open(os.path.join(OUT, "selfcheck_and_log.txt"), "w", encoding="utf-8") as f:
        f.write(LOG.getvalue())
    print("\nDONE", OUT)


if __name__ == "__main__":
    main()
