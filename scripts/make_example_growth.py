# -*- coding: utf-8 -*-
"""生长曲线示例数据生成 (脱敏)"""
import numpy as np
import pandas as pd

# 模拟 E. coli 生长 (时间, OD600, CFU/mL)
t = [60, 120, 150, 182, 212, 242, 272, 302, 337, 367, 397, 427]
od = [0.03, 0.20, 0.45, 0.76, 1.05, 1.25, 1.39, 1.48, 1.47, 1.49, 1.48, 1.50]
cfu = [1.615e7, 1.905e7, 1.573e8, 2.228e8, 2.925e8, 5.200e8,
       4.450e8, 6.275e8, 5.400e8, 4.425e8, 5.750e8, 6.750e8]

df = pd.DataFrame({"time_min": t, "od600": od, "cfu_ml": cfu})
df.to_csv("data/examples/growth_Ecoli_example.csv", index=False, encoding="utf-8-sig")
print("✅ 生长曲线示例数据: data/examples/growth_Ecoli_example.csv")
