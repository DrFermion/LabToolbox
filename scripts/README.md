# scripts/ — 独立脚本 (非模块)

模块化功能优先用 `labtoolbox.<module>` (见 [../README.md](../README.md))。
本目录只放**一次性/专用分析脚本** (保留原始工作流, 供复现)。

| 脚本 | 用途 | 备注 |
|---|---|---|
| `fdlc_livedead_analysis.py` | F-DLC LIVE/DEAD 分析: 配对 g/r 图、5 视野平均、CFU/cm²、双因素 ANOVA + Tukey 星号图 | 口径/结构见技能 labtoolbox `references/fdlc-livedead-csv-analysis.md` |
| `recount_fdlc.py` | F-DLC 荧光图像**重新计数** (2026-08-25 主人指示): 忽略旧 CSV, 从原始 .tif 重数 | 文件夹结构: F-DLC/{浓度}/{日期}/xxx.tif; 双因素 ANOVA + Tukey |
| `make_example_growth.py` | 生成生长曲线范例表格 (examples/example_growth_curve.xlsx) | 打包用 |
| `make_examples.py` | 生成其余范例数据 | 打包用 |
| `make_livedead_counter_demo.py` | 生成 LIVE/DEAD 细胞计数演示图 (examples/) | 打包用 |

> 注: 旧的 `surfmetrics.py` 已被正式模块 `labtoolbox/surfmetrics` 取代 (2026-08-27, commit deca43a), 已删除。
