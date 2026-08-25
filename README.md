# 实验室工具箱 (LabToolbox)

> **English README**: [README_EN.md](README_EN.md) | **中文**: [README.md](README.md)

Ruinong Pan 的生物医学实验室分析工具集 — 将 OneDrive 共享文件夹中的零散程序整合为统一、模块化、可扩展的工具箱。

## 📦 已整合模块

| 模块 | 功能 | 依赖 |
|---|---|---|
| `growth_curve` | 细菌生长曲线拟合与 OD/CFU 分析 (E. coli, S. aureus) | numpy, scipy, matplotlib |
| `lipss_dloa` | SEM 图像 LIPSS 周期/取向角分析 (DLOA) | numpy, scipy, opencv, matplotlib |
| `xdlvo` | XDLVO 理论细菌粘附预测 (接触角 → 表面能 → ΔG) | numpy, scipy |
| `livedead` | LIVE/DEAD 荧光统计 (存活率, 双因素 ANOVA) | pandas, statsmodels, openpyxl |
| `livedead_cellcounter` | LIVE/DEAD 荧光图像细胞计数 (repeat/时间/区域, 汇总+ANOVA) | numpy, opencv, Pillow |
| `contact_angle` | 接触角/表面自由能计算 (OWRK 等) | numpy, scipy |

## 🚀 快速开始

```bash
pip install -e .
# 或带图像处理依赖
pip install -e ".[image]"

# 🖥️ 图形界面 (推荐! 点点点就能用)
python -m labtoolbox.gui

# 命令行入口
labtoolbox --help
labtoolbox growth-curve --data data/growth_Ecoli.xlsx
labtoolbox lipss-dloa --folder data/sem_images/
labtoolbox xdlvo --config data/xdlvo_inputs.csv
labtoolbox livedead --file data/livedead.xlsx --group 5%F-DLC
labtoolbox contact-angle --file data/contact_angles.csv
```

## 🖥️ GUI 界面 (tkinter, 零额外依赖)

```
🧪 实验室工具箱 LabToolbox
┌──────────────────────────────────────────────┐
│ [📈 生长曲线] [🔬 LIPSS/DLOA] [🧫 XDLVO] [🦠 LIVE/DEAD] [💧 接触角] [🔬 细胞计数] │
│                                                                      │
│  每个标签页 = 一个模块的配置面板                                     │
│  (选文件/填参数 → 点"运行" → 结果自动输出)                          │
└──────────────────────────────────────────────┘
```

- 启动: `python -m labtoolbox.gui`
- 每个模块独立标签页, 参数可视化填写
- 分析结果自动保存到输出目录, 完成弹窗提示

## 🧩 模块化设计 (为扩展而生)

```
labtoolbox/
├── common/          # 共享工具: 文件 IO, 拟合, 统计, 绘图
├── growth_curve/    # 生长曲线
├── lipss_dloa/      # LIPSS/DLOA
├── xdlvo/           # XDLVO
├── livedead/        # LIVE/DEAD
├── livedead_cellcounter/  # LIVE/DEAD 荧光图像细胞计数
├── contact_angle/   # 接触角/表面能
├── cli.py           # 统一命令行入口
└── __init__.py
```

**如何添加新模块**: 在 `labtoolbox/` 下新建包 (如 `raman/`), 实现 `run(config) -> dict` 接口, 在 `cli.py` 注册子命令即可 — 无需改动其他模块。

## 🔬 数据说明

- 原始数据保留在 OneDrive 共享文件夹 (不提交到仓库)
- `data/examples/` 提供示例数据 (脱敏)
- `examples/` 提供 GUI "打开范例表格" 按钮用到的范例文件 (生长曲线 / LIVE/DEAD)
- 所有模块支持 Excel/CSV 输入, 图表输出到 `output/`

## 📄 License

MIT (待定)
