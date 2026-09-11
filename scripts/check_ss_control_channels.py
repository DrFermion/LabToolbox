# -*- coding: utf-8 -*-
"""quick channel/QC check for ss-control tifs"""
import os, re, glob
import numpy as np, tifffile

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_"
        r"Antibacterial Surfaces\Live_Dead Bacteria Test\ss-control")

for rep in ["repeat 1", "repeat 2", "repeat 3"]:
    for tp in ["3h", "5h"]:
        d = os.path.join(BASE, rep, tp)
        files = sorted(glob.glob(os.path.join(d, "*.tif")),
                       key=lambda x: int(re.search(r"(\d+)\.tif$", x).group(1)))
        print(f"\n=== {rep}/{tp}: {len(files)} files ===")
        nums = [int(re.search(r"(\d+)\.tif$", os.path.basename(p)).group(1)) for p in files]
        print("  nums:", nums)
        for p in files:
            a = tifffile.imread(p)
            tf = tifffile.TiffFile(p)
            desc = tf.pages[0].tags.get("ImageDescription")
            dv = desc.value if desc else ""
            tf.close()
            m = re.search(r"Exposure:\s*000 : 00 : (\d+) \. (\d+)", dv)
            exp = f"{m.group(1)}.{m.group(2)}" if m else "?"
            red, green, blue = a[..., 0], a[..., 1], a[..., 2]
            print(f"  {os.path.basename(p):9s} {a.shape} max R/G/B={red.max():3d}/{green.max():3d}/{blue.max():3d} "
                  f"mean B={blue.mean():6.2f} nzB={int((blue>40).sum()):5d} nzG={int((green>40).sum()):5d} exp={exp}s")
