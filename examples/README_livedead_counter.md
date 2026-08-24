# LIVE/DEAD 细胞计数模块 - 范例结构

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
