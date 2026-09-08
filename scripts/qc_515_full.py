# -*- coding: utf-8 -*-
"""
qc_515_full.py — 515nm 两组 LIVE/DEAD 全量 QC 图生成 (ImageJ 圈+编号)
与 recount_livedead_515_imagej.py 相同的数据范围:
  515nm repeat1 (skip repeat2/3) + 515nm-filter_paper repeat1, 各 1h/3h/5h
QC PNG 输出: scripts/output/recount_livedead_515/qc/<组名>/<时间目录>/<file>_qc.png
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from labtoolbox.livedead_cellcounter.cellcounter import ImageJEngine

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_"
        r"Antibacterial Surfaces\Live_Dead Bacteria Test")
GROUPS = [
    {"name": "515nm_coverslip", "root": os.path.join(BASE, "515nm"), "skip": ("repeat2",)},
    {"name": "515nm_filter_paper", "root": os.path.join(BASE, "515nm-filter_paper"), "skip": ()},
]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output",
                   "recount_livedead_515", "qc")


def main():
    os.makedirs(OUT, exist_ok=True)
    total_qc = 0
    for g in GROUPS:
        qc_root = os.path.join(OUT, g["name"])
        os.makedirs(qc_root, exist_ok=True)
        eng = ImageJEngine(qc_dir=qc_root)
        root = g["root"]
        n_files = 0
        for rep in sorted(os.listdir(root)):
            if g["skip"] and rep.lower() in g["skip"]:
                print("跳过:", rep)
                continue
            rp = os.path.join(root, rep)
            if not os.path.isdir(rp):
                continue
            for t in sorted(os.listdir(rp)):
                tp = os.path.join(rp, t)
                if not os.path.isdir(tp):
                    continue
                tifs = sorted(glob.glob(os.path.join(tp, "*.tif")))
                if not tifs:
                    continue
                # 触发整目录批处理 (每目录一次 ImageJ; QC 图同时产出)
                eng.count_live_dead(tifs[0])  # 触发 _batch_dir(该目录)
                n_qc = len(glob.glob(os.path.join(qc_root, t, "*_qc.png")))
                n_files += len(tifs)
                total_qc += n_qc
                print("%s/%s/%s: %d tif, %d QC png" % (g["name"], rep, t, len(tifs), n_qc))
        print("组 %s 完成: %d 文件" % (g["name"], n_files))
    print("全部完成, QC 图总数: %d -> %s" % (total_qc, OUT))


if __name__ == "__main__":
    main()
