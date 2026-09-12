# -*- coding: utf-8 -*-
"""实验室工具箱统一命令行入口 (可扩展: 注册新子命令即可)"""
import argparse
import json
import sys


def cmd_growth_curve(args):
    from .growth_curve import run as gc_run
    result = gc_run(path=args.data, output_dir=args.output)
    print(f"✅ 生长曲线分析完成")
    print(f"   拟合参数: {result['csv']}")
    print(f"   曲线图: {result['figure']}")
    return 0


def cmd_lipss_dloa(args):
    from .lipss_dloa import run as dloa_run
    result = dloa_run(folder=args.folder, output_dir=args.output,
                      pixel_size_um=1.0 / args.pixel_per_um)
    print(f"✅ LIPSS/DLOA 分析完成: {len(result['results'])} 张图像")
    for r in result["results"]:
        print(f"   {r['file']}: lipss_angle={r['lipss_angle_deg']:.1f}°, "
              f"spacing={r['spacing_nm']:.1f} nm, FWHM={r['fwhm_2dtheta_deg']:.1f}°")
    print(f"   CSV: {result['csv']}")
    return 0


def cmd_xdlvo(args):
    from .xdlvo import run as xd_run
    ca = json.loads(args.angles)
    result = xd_run(contact_angles=ca, radius_nm=args.radius, I_M=args.ionic,
                    zeta_m=args.zeta_m, zeta_f=args.zeta_f, output_dir=args.output)
    print(f"✅ XDLVO 分析完成")
    print(f"   表面能: {result['surface_energy']}")
    dg = result["delta_g"]
    print(f"   ΔG_LW={dg['LW']:.2f}, ΔG_AB={dg['AB']:.2f} mJ/m²")
    if "EL" in dg:
        print(f"   ΔG_EL={dg['EL']:.2f}, ΔG_TOT={dg['TOT']:.2f} mJ/m²")
    prof = result["profile"]
    if prof["barrier"] is not None:
        print(f"   能量势垒: {prof['barrier']:.2f} kT @ {prof['barrier_position']:.2f} nm")
    else:
        print("   能量势垒: 无 (全程吸引)")
    print(f"   能量曲线: {result['figure']}")
    return 0


def cmd_livedead(args):
    from .livedead import run as ld_run
    result = ld_run(path=args.file, sheet=args.sheet, output_dir=args.output)
    print(f"✅ LIVE/DEAD 分析完成")
    print(f"   存活率柱状图: {result['figure']}")
    print(f"   汇总: {result['summary_csv']}")
    if result["anova"] and result["anova"]["table"] is not None:
        aov = result["anova"]
        print(f"   双因素 ANOVA: Group p={aov['factor1_p']}, Time p={aov['factor2_p']}, "
              f"交互 p={aov['interaction_p']}")
    return 0


def cmd_contact_angle(args):
    from .contact_angle import run as ca_run
    result = ca_run(args.theta1, args.theta2, args.liquid1, args.liquid2)
    print(f"✅ 接触角/表面能计算完成")
    print(f"   {result['liquid1']} θ={args.theta1}°, {result['liquid2']} θ={args.theta2}°")
    print(f"   表面能: {result['surface_energy']}")
    return 0


def cmd_surfmetrics(args):
    from .surfmetrics import run as sm_run
    result = sm_run(file=args.file, folder=args.folder, channel=args.channel,
                    px=args.px, py=args.py, output_dir=args.output, z_mode=args.z_mode,
                    backend=args.backend, level=not args.no_level,
                    profiles=not args.no_profiles,
                    profile_row=args.profile_row, profile_col=args.profile_col)
    print(f"✅ 表面形貌分析完成: {len(result['results'])} 个文件")
    for r in result["results"]:
        tag = f" [{r.get('backend', 'python')}" + (", level]" if r.get("level") else "]")
        sa = f"{r['Sa_nm']:.2f}" if r.get("Sa_nm") is not None else "?"
        sq = f"{r['Sq_nm']:.2f}" if r.get("Sq_nm") is not None else "?"
        sz = f"{r['Sz_nm']:.1f}" if r.get("Sz_nm") is not None else "?"
        print(f"   {r['file']}: Sa={sa} nm, Sq={sq} nm, Sz={sz} nm{tag}")
    print(f"   汇总 CSV: {result['csv']}")
    if result["grid"]:
        print(f"   汇总 3D 网格图: {result['grid']}")
    return 0


# 子命令注册表: 新增模块在这里加一行即可
COMMANDS = {
    "growth-curve": (cmd_growth_curve, "生长曲线分析 (OD600/CFU 拟合)"),
    "lipss-dloa": (cmd_lipss_dloa, "LIPSS/DLOA 取向角分析"),
    "xdlvo": (cmd_xdlvo, "XDLVO 细菌粘附预测"),
    "livedead": (cmd_livedead, "LIVE/DEAD 存活率统计"),
    "contact-angle": (cmd_contact_angle, "接触角/表面能计算"),
    "surfmetrics": (cmd_surfmetrics, "AFM 表面形貌: 3D 图 + 粗糙度 (Sa/Sq/Sz) + 表面积 (Sdr)"),
}


def build_parser():
    parser = argparse.ArgumentParser(
        prog="labtoolbox",
        description="实验室工具箱 - Ruinong Pan's biomedical lab analysis tools",
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    p = sub.add_parser("growth-curve", help=COMMANDS["growth-curve"][1])
    p.add_argument("--data", required=True, help="Excel/CSV 数据文件")
    p.add_argument("--output", default="output", help="输出目录")

    p = sub.add_parser("lipss-dloa", help=COMMANDS["lipss-dloa"][1])
    p.add_argument("--folder", required=True, help="SEM 图像文件夹")
    p.add_argument("--pixel-per-um", type=float, default=32.0, help="每微米像素数 (默认 32)")
    p.add_argument("--output", default="output", help="输出目录")

    p = sub.add_parser("xdlvo", help=COMMANDS["xdlvo"][1])
    p.add_argument("--angles", required=True,
                   help='JSON: {"theta_diiodo":48.2,"theta_water":72.3,"theta_form":61.5}')
    p.add_argument("--radius", type=float, default=500.0, help="细菌半径 (nm)")
    p.add_argument("--ionic", type=float, default=0.01, help="离子强度 (M)")
    p.add_argument("--zeta-m", type=float, default=None, help="材料 zeta 电位 (V)")
    p.add_argument("--zeta-f", type=float, default=None, help="细菌 zeta 电位 (V)")
    p.add_argument("--output", default="output", help="输出目录")

    p = sub.add_parser("livedead", help=COMMANDS["livedead"][1])
    p.add_argument("--file", required=True, help="LIVE/DEAD Excel 文件")
    p.add_argument("--sheet", default=None, help="工作表名")
    p.add_argument("--output", default="output", help="输出目录")

    p = sub.add_parser("contact-angle", help=COMMANDS["contact-angle"][1])
    p.add_argument("--theta1", type=float, required=True, help="液体1 接触角 (度)")
    p.add_argument("--theta2", type=float, required=True, help="液体2 接触角 (度)")
    p.add_argument("--liquid1", default="water", help="液体1 (默认 water)")
    p.add_argument("--liquid2", default="diiodomethane", help="液体2 (默认 diiodomethane)")

    p = sub.add_parser("surfmetrics", help=COMMANDS["surfmetrics"][1])
    p.add_argument("--file", default=None, help="高度图文件 (.ibw/.tif/.txt/.xyz/.csv)")
    p.add_argument("--folder", default=None, help="批量: 文件夹内所有 .ibw (如 AFM 原始数据目录)")
    p.add_argument("--channel", type=int, default=None, help=".ibw 通道索引 (默认自动选 Height)")
    p.add_argument("--px", type=float, default=None, help="像素尺寸 X (nm; .ibw 自动读取, 其他格式建议给)")
    p.add_argument("--py", type=float, default=None, help="像素尺寸 Y (nm, 默认=px)")
    p.add_argument("--output", default="output", help="输出目录")
    p.add_argument("--z-mode", default="real", dest="z_mode",
                   help="3D 图 z 轴模式: real (默认, z 与 XY 同比例, 不做纵向夸张) / "
                        "auto (z 约 xy 尺度的 25%, 起伏扁平时看得清) / 数值放大系数")
    p.add_argument("--no-profiles", action="store_true",
                   help="不出参考线剖面图 (默认会出: 左 3D 等比例 + 横/纵参考线, 右 沿线的深度曲线)")
    p.add_argument("--profile-row", type=int, default=None, help="横参考线所在行 (默认正中)")
    p.add_argument("--profile-col", type=int, default=None, help="纵参考线所在列 (默认正中)")
    p.add_argument("--backend", default="python", choices=["python", "gwyddion"],
                   help="python (默认, 自研) / gwyddion (WSL Gwyddion 2.67 内核真处理)")
    p.add_argument("--no-level", action="store_true",
                   help="gwyddion backend 时跳过平面扣除 (默认 level)")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    if args.command not in COMMANDS:
        print(f"未知命令: {args.command}", file=sys.stderr)
        return 1
    try:
        return COMMANDS[args.command][0](args)
    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
