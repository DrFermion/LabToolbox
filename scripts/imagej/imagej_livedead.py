#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
imagej_livedead.py — LIVE/DEAD 细菌计数 (ImageJ 引擎, headless 批处理)
方法学: 自适应阈值 (背景直方图众数 + 40) -> 通道陷阱修正 -> Analyze Particles size 3-500 px
引擎: 经典 ImageJ 1.54 (F:/ImageJ/ImageJ), 绕开 Fiji/ImageJ2 headless 兼容坑
关键修复: Image-Pro Plus 假校准 (inch/px) 会让 Analyze Particles 面积过滤失效 -> 处理前清校准
用法:
  python imagej_livedead.py <inputDir> [outputCSV]
  递归扫描 inputDir 下所有 *_g*/*_r* 命名 tif, 输出逐张计数 CSV + 同目录配对统计
依赖: 仅标准库 (引擎是 ImageJ, 无 python 图像库)
"""
import csv, os, subprocess, sys, tempfile, glob

IMAGEJ_DIR = r"F:/ImageJ/ImageJ"
MACRO = os.path.join(IMAGEJ_DIR, "macros", "count_livedead.ijm")
JAVA = os.path.join(IMAGEJ_DIR, "jre", "bin", "java.exe")
IJ_JAR = os.path.join(IMAGEJ_DIR, "ij.jar")


def count_dir(input_dir, out_csv=None):
    input_dir = os.path.abspath(input_dir)
    if out_csv is None:
        out_csv = os.path.join(input_dir, "imagej_counts.csv")
    # 参数文件 (UTF-8 两行) — ImageJ 命令行不能传中文路径, 必须走文件
    fd, args_path = tempfile.mkstemp(suffix=".txt", prefix="ij_args_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(input_dir.replace("\\", "/") + "\n")
        f.write(out_csv.replace("\\", "/") + "\n")
    env = dict(os.environ, JAVA_TOOL_OPTIONS="-Dfile.encoding=UTF-8")
    cmd = [JAVA, "-cp", IJ_JAR, "ij.ImageJ", "-batch", MACRO, args_path]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)
    os.unlink(args_path)
    if not os.path.exists(out_csv):
        raise RuntimeError("ImageJ 无输出: " + proc.stderr[-500:])
    rows = list(csv.DictReader(open(out_csv, encoding="utf-8")))
    return rows


def pair_summary(rows):
    """按 {area}-{g|r}{n} 配对 -> live/dead/total"""
    pairs = {}
    for r in rows:
        fn = r["filename"]
        import re
        m = re.match(r"^(.+?)-([grGR])(\d+)\.tif?$", fn, re.I)
        if not m:
            continue
        area, ch, n = m.group(1), m.group(2).lower(), m.group(3)
        key = (area, n)
        pairs.setdefault(key, {})[ch] = int(r["count"])
    out = []
    for (area, n), d in sorted(pairs.items()):
        live, dead = d.get("g", 0), d.get("r", 0)
        out.append({"area": area, "num": n, "live": live, "dead": dead, "total": live + dead})
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    d = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    print("ImageJ counting:", d)
    rows = count_dir(d, out)
    print(f"  files: {len(rows)}")
    for p in pair_summary(rows)[:8]:
        print(f"  {p}")
