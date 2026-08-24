# -*- coding: utf-8 -*-
"""生成 LabToolbox 所有表格输入模块的范例表格 (examples/)"""
import os
import numpy as np
import pandas as pd

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
os.makedirs(OUT, exist_ok=True)

# ========== 1. 生长曲线范例 ==========
rng = np.random.default_rng(42)
t = np.array([0, 60, 120, 180, 240, 300, 360, 420, 480, 540])
# 逻辑斯蒂生长: OD600
od = 0.1 + 1.2 / (1 + np.exp(-0.02 * (t - 250))) + rng.normal(0, 0.01, len(t))
# CFU/mL 对应
cfu = 1e5 * 10 ** (3.5 / (1 + np.exp(-0.02 * (t - 250)))) * rng.uniform(0.9, 1.1, len(t))
growth = pd.DataFrame({
    "time_min": t,
    "od600": od.round(3),
    "cfu_ml": cfu.astype(int),
})
growth.to_excel(os.path.join(OUT, "example_growth_curve.xlsx"), index=False)
print("✅ example_growth_curve.xlsx")

# ========== 2. LIVE/DEAD 范例 ==========
groups = ["Control", "5%F-DLC", "2%F-DLC"]
times = [0, 2, 5]
rows = []
for g in groups:
    for tm in times:
        for rep in range(1, 4):
            if g == "Control":
                live = rng.integers(90, 130)
                dead = rng.integers(5, 20)
            else:
                live = rng.integers(50, 90)
                dead = rng.integers(20, 60)
            rows.append({"group": g, "time": tm, "repeat": rep,
                         "live": int(live), "dead": int(dead)})
ld = pd.DataFrame(rows)
ld.to_excel(os.path.join(OUT, "example_livedead.xlsx"), index=False)
print("✅ example_livedead.xlsx")

# ========== 3. 使用说明 README ==========
readme = """# LabToolbox 范例表格 (examples/)

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
"""
with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as f:
    f.write(readme)
print("✅ README.md")

# 验证读取
for name in ["example_growth_curve.xlsx", "example_livedead.xlsx"]:
    df = pd.read_excel(os.path.join(OUT, name))
    print(f"   {name}: {df.shape[0]} 行 × {df.shape[1]} 列 | 列: {list(df.columns)}")
