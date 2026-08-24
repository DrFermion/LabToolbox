# LabToolbox 范例表格 (examples/)

以下模块需要**表格数据输入**(Excel .xlsx / .csv),对应的范例文件:

## 📈 生长曲线 `example_growth_curve.xlsx`
| time_min | od600 | cfu_ml |
|---|---|---|
| 0 | 0.101 | 100000 |
| 60 | 0.142 | 152000 |
| ... | ... | ... |

- **列名必须精确**: `time_min`(分钟)、`od600`(吸光度)、`cfu_ml`(菌落数/mL)
- 每行 = 一个时间点的测量值

## 🦠 LIVE/DEAD 荧光统计 `example_livedead.xlsx`
| group | time | repeat | live | dead |
|---|---|---|---|---|
| Control | 0 | 1 | 112 | 9 |
| Control | 0 | 2 | 105 | 14 |
| ... | ... | ... | ... | ... |

- **必需列**: `live`(活菌数)、`dead`(死菌数)
- **可选列**: `group`(分组)、`time`(时间点/h)、`repeat`(重复编号)
- `live` 和 `dead` 必须是**非负整数** (细胞计数)
- 存活率自动按合并计数法计算: Σlive / Σ(live+dead) × 100%
- 每行 = 一个视野/样品的计数

## 🔬 其他模块 (不需要表格)
- **LIPSS/DLOA**: 直接选 SEM 图像文件夹
- **XDLVO / 接触角**: 在界面里填接触角数值

---
*范例数据为演示用途, 可直接替换为自己的实验数据。*
