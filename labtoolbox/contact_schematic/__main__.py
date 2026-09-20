# -*- coding: utf-8 -*-
"""命令行: python -m labtoolbox.contact_schematic --input <AFM 数据目录> --out <输出目录>

AFM 处理流程的末端步骤: 量取周期/纹深/尖峰间距/凸起高度 → 出
  fig1_LIPSS_adhesion.png/pdf      细菌在 LIPSS 上的 3D 黏附示意 (含取向/接触点)
  fig2_nanopillar_adhesion.png/pdf 同上, 纳米柱表面
  fig3_contact_geometry.png/pdf    接触几何 (球 SEI / 杆平行 / 杆跨越)
  geometry_measurements.csv        逐文件实测值 (可溯源)
  README.md                        自动生成的说明 (含实测值与假设)
"""
import argparse
import os
import sys

from .geometry import measure_geometry, summarise, write_csv
from .render import ECOLI_D, ECOLI_L, SAUREUS_D, render_all

README_TMPL = """# 细菌-织构接触示意图 ({label}) — 自动生成

由 `labtoolbox.contact_schematic` 在 AFM 处理流程末端生成 (ZSR 通道, 平面扣除 + 5σ 去尖峰).

## 实测几何 (nm)

| 参数 | 数值 (mean ± sd, n) |
|---|---|
| LIPSS 周期 | {p_mean:.1f} ± {p_sd:.1f} (n={p_n}) |
| LIPSS 纹深 (P98-P2) | {d_mean:.1f} ± {d_sd:.1f} (n={d_n}) |
| 纳米柱尖峰间距 (NN 中位) | {s_mean:.1f} ± {s_sd:.1f} (n={s_n}) |
| 纳米柱凸起高度 (P90-中位) | {h_mean:.1f} ± {h_sd:.1f} (n={h_n}) |

逐文件数值见 `geometry_measurements.csv`.

## 文件

- `fig1_LIPSS_adhesion.png/.pdf` — (a) 形貌+剖面尺寸; (b) 大肠杆菌平行 0°; (c) 45°; (d) 垂直 90°; (e) 金黄色葡萄球菌
- `fig2_nanopillar_adhesion.png/.pdf` — 同构
- `fig3_contact_geometry.png/.pdf` — 球形菌 SEI 几何 (R, r, θ, h, D(r)=h+R−√(R²−r²)); 杆平行 (与沟两侧斜坡相切); 杆跨越 (只碰脊顶)

## 假设 (必须与论文图注一致)

1. 细菌按**刚性**杆/球建模, 接触 = 几何搁置于凸起处, **不是**力学或 XDLVO 计算;
2. LIPSS 沟槽按正弦近似, 纳米柱按准周期阵列近似 (真实排布准随机);
3. D(r) 采用等效球-平面关系 (SEI 惯例), 对正弦脊顶为近似;
4. 细胞尺寸取**文献标称值** (E. coli {ec_l:.1f}×{ec_d:.1f} µm, S. aureus {sa:.1f} µm), 非本组实测;
5. 全部**严格同比例** (未夸大 z 轴).

重绘: `python -m labtoolbox.contact_schematic --input <数据目录> --out <输出目录>`
"""


def main(argv=None):
    ap = argparse.ArgumentParser(prog="labtoolbox.contact_schematic",
                                 description="AFM 末端步骤: 细菌-织构接触示意图")
    ap.add_argument("--input", required=True, help="AFM 原始数据 (.ibw 文件或目录, 递归)")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--label", default="515 nm", help="样品标签 (进标题), 如 '515 nm'")
    ap.add_argument("--channel", default="zsr", help=".ibw 通道 (默认 zsr)")
    ap.add_argument("--lambda", dest="lam", type=float, default=515.0, help="激光波长 nm (FFT 窗口用)")
    ap.add_argument("--dpi", type=int, default=190)
    ap.add_argument("--cell", default=f"{ECOLI_L}x{ECOLI_D}", help="E. coli 长x直径 µm")
    ap.add_argument("--coccus", type=float, default=SAUREUS_D, help="S. aureus 直径 µm")
    ap.add_argument("--no-render", action="store_true", help="只测量出表, 不画图")
    a = ap.parse_args(argv)

    try:
        L, D = (float(v) for v in a.cell.lower().replace(" ", "").split("x"))
    except Exception:
        L, D = ECOLI_L, ECOLI_D

    os.makedirs(a.out, exist_ok=True)
    print(f"[1/3] 测量: {a.input}")
    recs = measure_geometry(a.input, channel=a.channel, lam_nm=a.lam)
    csv_path = write_csv(recs, os.path.join(a.out, "geometry_measurements.csv"))
    g = summarise(recs, lam_nm=a.lam)
    print(f"      文件 {g['n_files']} 个 (LIPSS {g['n_lipss']} / 纳米柱 {g['n_pillar']}) → {csv_path}")

    if a.no_render:
        return 0
    print("[2/3] 渲染示意图")
    made = render_all(g, a.out, label=a.label, dpi=a.dpi, cell=(L, D), coccus=a.coccus)
    for m in made:
        print("      ", os.path.basename(m))

    print("[3/3] 写 README")
    rd = README_TMPL.format(
        label=a.label,
        p_mean=g["lipss"]["period_nm"]["mean"], p_sd=g["lipss"]["period_nm"]["sd"], p_n=g["lipss"]["period_nm"]["n"],
        d_mean=g["lipss"]["depth_nm"]["mean"], d_sd=g["lipss"]["depth_nm"]["sd"], d_n=g["lipss"]["depth_nm"]["n"],
        s_mean=g["nanopillar"]["spacing_nm"]["mean"], s_sd=g["nanopillar"]["spacing_nm"]["sd"],
        s_n=g["nanopillar"]["spacing_nm"]["n"],
        h_mean=g["nanopillar"]["height_nm"]["mean"], h_sd=g["nanopillar"]["height_nm"]["sd"],
        h_n=g["nanopillar"]["height_nm"]["n"],
        ec_l=L, ec_d=D, sa=a.coccus)
    with open(os.path.join(a.out, "README.md"), "w", encoding="utf-8") as f:
        f.write(rd)
    print("完成 →", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
