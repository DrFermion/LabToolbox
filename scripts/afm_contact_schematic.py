# -*- coding: utf-8 -*-
"""AFM 流程末端: 由实测几何出细菌-织构接触示意图 (薄封装, 真正逻辑在 labtoolbox.contact_schematic).

用法:
    python scripts/afm_contact_schematic.py --input "<AFM 数据目录>" --out "<输出目录>" --label "515 nm"
或直接:
    python -m labtoolbox.contact_schematic --input ... --out ...
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from labtoolbox.contact_schematic.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
