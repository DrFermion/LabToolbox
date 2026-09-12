# -*- coding: utf-8 -*-
"""Verify the 650 nm workbook (incl. the 20 blank entry rows) and mirror the outputs."""
import os
import shutil

import openpyxl

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - "
        r"Ruinong Pan_Antibacterial Surfaces\Contact Angle and Surface energy\650")
MIRROR = r"E:\LabToolbox\output\ca_650_20260912"

wb = openpyxl.load_workbook(os.path.join(BASE, "650nm.xlsx"))          # formulas/styles
wv = openpyxl.load_workbook(os.path.join(BASE, "650nm.xlsx"), data_only=True)  # cached values

print("=== summary ===")
ws = wv["summary"]
for r in ws.iter_rows(min_row=1, max_row=ws.max_row):
    vals = [("" if c.value is None else str(c.value)) for c in r[:8]]
    while vals and vals[-1] == "":
        vals.pop()
    if vals:
        print(f"  r{r[0].row:<3}| " + " | ".join(vals))

print()
print("=== 每张 area 表: 数据尾行 + 20 行待填区 ===")
for g in ("area1", "area1-R90", "area2", "control"):
    wsv, wss = wv[g], wb[g]
    data_last = 0
    for r in range(3, wsv.max_row + 1):
        if any(wsv.cell(r, c).value is not None for c in (1, 2, 3, 4, 5)):
            data_last = r
    first = data_last + 1
    filled = 0
    for r in range(first, first + 20):
        c = wss.cell(r, 1)
        has_fill = c.fill is not None and c.fill.fgColor is not None and \
            c.fill.fgColor.rgb not in (None, "00000000")
        has_border = c.border is not None and c.border.bottom.style
        has_value = any(wsv.cell(r, k).value is not None for k in (1, 2, 3, 4, 5))
        if has_fill and has_border and not has_value:
            filled += 1
    print(f"  {g:<16} 数据到 r{data_last} | 待填区 r{first}-r{first + 19} "
          f"| 合格空白带框行 {filled}/20 | 末行 {wsv.max_row}")

os.makedirs(MIRROR, exist_ok=True)
for f in ("650nm.xlsx", "650nm_water_contact_angle.png",
          "650nm_water_contact_angle_first_repeat.png",
          "650nm_water_contact_angle_repeat_drift.png"):
    shutil.copy2(os.path.join(BASE, f), os.path.join(MIRROR, f))
print()
print("镜像到:", MIRROR, "->", sorted(os.listdir(MIRROR)))
