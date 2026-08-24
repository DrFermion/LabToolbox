# -*- coding: utf-8 -*-
"""生成 LIVE/DEAD 细胞计数模块的范例文件夹结构"""
import os
import shutil
import numpy as np
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples", "livedead_counter_demo")
if os.path.exists(OUT):
    shutil.rmtree(OUT)

rng = np.random.default_rng(7)

# 模拟: 3 repeats × 2 时间点 × (Control + Area1) × 2 通道 × 2 采样
for rep in ["repeat1", "repeat2", "repeat3"]:
    for t in ["1h", "3h"]:
        d = os.path.join(OUT, rep, t)
        os.makedirs(d, exist_ok=True)
        for area in ["c", "1"]:
            for ch, base_intensity in [("g", 160), ("r", 140)]:
                for n in [1, 2]:
                    # 生成模拟荧光图: 黑色背景 + 亮菌点
                    img = np.zeros((200, 200, 3), dtype=np.uint8)
                    for _ in range(15):
                        x, y = rng.integers(20, 180, 2)
                        r = rng.integers(3, 7)
                        if ch == "g":
                            img[max(0,y-r):y+r, max(0,x-r):x+r, 1] = base_intensity
                        else:
                            img[max(0,y-r):y+r, max(0,x-r):x+r, 0] = base_intensity
                    # control 菌少, area1 菌多
                    if area == "c" and rng.random() < 0.3:
                        img = np.zeros_like(img)
                    Image.fromarray(img).save(os.path.join(d, f"{area}-{ch}{n}.tif"))

readme = """# LIVE/DEAD 细胞计数模块 - 范例结构

## 文件夹结构 (输入)
```
livedead_counter_demo/
├── repeat1/            ← 重复实验 1
│   ├── 1h/             ← 采样时间 1h
│   │   ├── c-g1.tif    ← Control 区域, 绿色通道 (活菌), 采样1
│   │   ├── c-r1.tif    ← Control 区域, 红色通道 (死菌), 采样1
│   │   ├── 1-g1.tif    ← 测试区域 1, 绿色通道, 采样1
│   │   ├── 1-r1.tif    ← 测试区域 1, 红色通道, 采样1
│   │   └── ...         (1-g2/1-r2 等)
│   └── 3h/
├── repeat2/
└── repeat3/
```

## 文件名格式
`{区域}-{通道}{编号}.tif`
- **区域**: `c` = Control 对照区, `1`/`2`/`3` = 测试区域编号
- **通道**: `g` = green 绿色通道 (活菌), `r` = red 红色通道 (死菌)
- **编号**: 同区域内的采样编号 (1, 2, 3...)

## 处理逻辑
1. g 图和 r 图按 (区域, 编号) **配对** (如 1-g2 和 1-r2 是同一视野两通道)
2. g 图数绿色 → **活菌数**, r 图数红色 → **死菌数**
3. 所有 Control (3 repeat × 多采样) **合并**统计
4. 输出: 汇总表 (均值±标准差) + 柱状图 (带 ANOVA 标注) + ANOVA 表

## 输出文件
- `livedead_raw_counts.csv` — 每对图的原始计数
- `livedead_summary.csv` — 分组汇总 (Control/Area1/Area2 × 时间)
- `livedead_anova.csv` — 双因素 ANOVA
- `livedead_cell_count.png` — 柱状图
"""
with open(os.path.join(os.path.dirname(OUT), "README_livedead_counter.md"), "w", encoding="utf-8") as f:
    f.write(readme)
print(f"✅ 范例已生成: {OUT}")
print(f"✅ 说明文档: {os.path.join(os.path.dirname(OUT), 'README_livedead_counter.md')}")
