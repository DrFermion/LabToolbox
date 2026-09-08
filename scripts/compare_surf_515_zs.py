# -*- coding: utf-8 -*-
"""compare_surf_515_zs.py — 515 样品 ZS 通道: raw vs Gwyddion level 对比"""
import os, sys, glob
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from labtoolbox.surfmetrics.surfmetrics import load_heightmap, surface_metrics, gwy_batch_wsl

BASE = r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - Ruinong Pan_Antibacterial Surfaces\AFM Steel Samples\515 samples"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "surf_515_compare")

def main():
    os.makedirs(OUT, exist_ok=True)
    ibws = sorted(glob.glob(os.path.join(BASE, "*", "*.ibw")))
    print("ZS 通道 (ch3) 对比, %d 文件" % len(ibws))
    g_raw = {r["file"]: r for r in gwy_batch_wsl(ibws, level=False, channel=3)}
    print("raw done")
    g_lvl = {r["file"]: r for r in gwy_batch_wsl(ibws, level=True, channel=3)}
    print("level done")
    rows = []
    for p in ibws:
        name = os.path.basename(p)
        z, px_h, py_h = load_heightmap(p, channel=3)
        px = px_h if px_h else None
        m = surface_metrics(z, px, px) if px else {"Sa_nm": None, "Sq_nm": None, "Sz_nm": None}
        gr, gl = g_raw.get(name, {}), g_lvl.get(name, {})
        rows.append({"file": name,
                     "Sa_py_raw": m.get("Sa_nm"), "Sq_py_raw": m.get("Sq_nm"),
                     "Sa_gwy_raw": gr.get("Sa_nm"), "Sq_gwy_raw": gr.get("Sq_nm"),
                     "Sz_gwy_raw": gr.get("Sz_nm"),
                     "Sa_gwy_lvl": gl.get("Sa_nm"), "Sq_gwy_lvl": gl.get("Sq_nm"),
                     "Sz_gwy_lvl": gl.get("Sz_nm")})
    df = pd.DataFrame(rows)
    df["d_py_vs_gwy_raw_pct"] = ((df["Sa_gwy_raw"] - df["Sa_py_raw"]) / df["Sa_py_raw"] * 100).round(3)
    df["d_lvl_nm"] = (df["Sa_gwy_lvl"] - df["Sa_gwy_raw"]).round(2)
    df["d_lvl_pct"] = ((df["Sa_gwy_lvl"] - df["Sa_gwy_raw"]) / df["Sa_gwy_raw"] * 100).round(1)
    out_csv = os.path.join(OUT, "surf_515_ZS_comparison.csv")
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 200)
    show = df[["file", "Sa_py_raw", "Sa_gwy_raw", "Sa_gwy_lvl", "d_py_vs_gwy_raw_pct", "d_lvl_nm", "d_lvl_pct"]].copy()
    show.columns = ["file", "Sa_py", "Sa_gwy", "Sa_lvl", "py-vs-gwy%", "lvlΔnm", "lvlΔ%"]
    print(show.to_string(index=False))
    print()
    print("Python vs Gwyddion(raw) 一致: %d/%d" % ((df["d_py_vs_gwy_raw_pct"].abs() < 0.01).sum(), len(df)))
    big = df[df["d_lvl_nm"].abs() > 1]
    print("level 改变 >1nm 的文件: %d 个" % len(big))
    if len(big):
        for _, r in big.iterrows():
            print("   %s: Sa %.2f → %.2f nm (%.1f%%)" % (r["file"], r["Sa_gwy_raw"], r["Sa_gwy_lvl"], r["d_lvl_pct"]))
    print("明细:", out_csv)

if __name__ == "__main__":
    main()
