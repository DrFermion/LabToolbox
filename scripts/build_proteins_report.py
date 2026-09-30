# -*- coding: utf-8 -*-
"""build_proteins_report.py — 生成《人体体液环境中的蛋白质黏附》报告（docx + md）并分两处落位。

数据源（只读）: E:\\LabToolbox\\output\\proteins_environments_20260930\\*.csv
产物: 桌面 docx + 个人 OneDrive 归档夹（docx/md/图/CSV/README）
可重跑：所有数字从 CSV 读取, 不写死。
"""
import os
import io
import shutil
import datetime
import pandas as pd

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = r"E:\LabToolbox\output\proteins_environments_20260930"
BSA_OUT = r"E:\LabToolbox\output\bsa_sei_515_20260924"
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
ARCHIVE = r"F:\OneDrive - University of Dundee\Ruinong_Pan_Personal\蛋白质黏附_体液模拟_20260930"
BASENAME = "蛋白质黏附_方案与模拟报告_20260930"
EA_FONT = "Microsoft YaHei"
LATIN = "Calibri"

PROT_ORDER = ["Albumin (BSA A)", "Albumin (BSA B)", "Fibrinogen (human)", "Fibronectin (human)"]
SURF_ORDER = ["LIPSS", "Nanopillar", "Control 316L"]
EXCLUDE_DAYS = {7, 8, 9, 10}          # 接触角序列中疑似占位值, 见 §3.7

# ---------------------------------------------------------------- 读数据
mat = pd.read_csv(os.path.join(OUT, "protein_surface_matrix.csv"), encoding="utf-8-sig")
bact = pd.read_csv(os.path.join(OUT, "bacteria_on_films.csv"), encoding="utf-8-sig")
envs = pd.read_csv(os.path.join(OUT, "environments_composition.csv"), encoding="utf-8-sig")
sei5 = pd.read_csv(os.path.join(OUT, "sei_protein_scale_R5.csv"), encoding="utf-8-sig")
fld = pd.read_csv(os.path.join(BSA_OUT, "bsa_sei_field_stats.csv"), encoding="utf-8-sig")


def snap(day):
    q = mat[mat.day == day]
    rows = []
    for prot in PROT_ORDER:
        r = [prot]
        for surf in SURF_ORDER:
            v = q[(q.surface == surf) & (q.protein == prot)]
            r.append(f"{v.dG_ADH.iloc[0]:+.2f} / {v.barrier_kT.iloc[0]:+.1f}")
        rows.append(r)
    return rows


def day_stats():
    m2 = mat[~mat.day.isin(EXCLUDE_DAYS)]
    rows = []
    for surf in SURF_ORDER:
        for prot in PROT_ORDER:
            s = m2[(m2.surface == surf) & (m2.protein == prot)]
            neg = int((s.barrier_kT < 0).sum())
            rows.append([surf, prot, f"{s.barrier_kT.min():+.0f}", f"{s.barrier_kT.max():+.0f}",
                         f"{neg}/{len(s)}"])
    return rows


def neg_days():
    m2 = mat[~mat.day.isin(EXCLUDE_DAYS)]
    s = m2[(m2.surface == "LIPSS") & (m2.protein == "Fibrinogen (human)")]
    neg = sorted(s[s.barrier_kT < 0].day.tolist())
    pos = sorted(s[s.barrier_kT >= 0].day.tolist())
    return neg, pos


NEG_D, POS_D = neg_days()

# ---------------------------------------------------------------- 内容块
B = []
A = B.append

A(("title", "人体体液环境中的蛋白质黏附"))
A(("subtitle", "蛋白选型 · SDS 清洗验证方案 · XDLVO–SEI 模拟（针对 515 nm 激光织构 316L 不锈钢）"))
A(("meta", "2026-09-30 · 分析/方案文档（非论文正文）· 全部数字可由 E:\\LabToolbox\\scripts\\proteins_environments.py 重跑复现"))

# ============ 0 摘要
A(("h1", "0 摘要"))
A(("p", "本报告回答两件事：(1) 选哪两种属于人体血液环境的蛋白来做黏附实验——能否用现成的 kit 检测、SDS 能否彻底清洗（样品能否复用）；(2) 用现有的 XDLVO–SEI 数值机器模拟血液、组织液、关节间隙三种体液环境中的蛋白黏附。"))
A(("h2", "任务一：选型与清洗验证"))
A(("bullet", [
    "推荐两种蛋白：人血清白蛋白（HSA，血浆含量最高的蛋白，也是条件膜早期的主导者）与人纤维蛋白原（Fg，决定血液相容性、Vroman 效应和表面诱导凝血的核心蛋白）。两者都有成熟的商品化定量 kit，也都买得到荧光标记版本。",
    "关键 kit 事实：BCA 法耐受 5% SDS（Thermo TR0068 兼容性表），而 Bradford 法只耐受 0.016–0.5% SDS。用 SDS 洗样品时，洗脱液必须用 BCA（或经基质匹配的 ELISA），不能用 Bradford。",
    "SDS 能否“彻底”清理：文献显示 SDS 能洗掉大部分蛋白，但不能保证 100%。被吸附的蛋白会随时间转变成更难洗脱的状态（Rapoza & Horbett 1989），且 SDS 本身会把一部分分子“锚定”成不可洗脱形式（Zembala 等 1998, Langmuir）。因此“能不能彻底洗掉”必须对“你的表面 + 你的蛋白”实测；本报告给出可直接执行的验证协议与判据（质量平衡 BCA + 荧光成像 + 接触角回归；残留 ≤5% 或达检出限、连续 3 轮无累积）。",
]))
A(("h2", "任务二：三种体液环境中的黏附模拟（37 °C，0.15 M）"))
A(("bullet", [
    "计算对象：4 个蛋白参数组（白蛋白 BSA 两套文献参数、人纤维蛋白原、人纤连蛋白）× 3 种表面（LIPSS / 纳米柱 / 抛光对照 316L）× 表面时效 0–81 天。",
    "第 0 天（新鲜态）：LIPSS 与纳米柱对四个参数组全部排斥（势垒 +36…+161 kT，≫ 10 kT 吸附阈值）；对照 316L 对其中三个参数组排斥（+41…+83 kT），仅白蛋白参数组 A 已转为弱吸引（−17 kT）——抛光对照对参数选择更敏感。",
    "但表面状态不是单向老化：81 天序列里势垒在 −197…+161 kT 之间往返，多次出现深吸引态（LIPSS 上 Fg 在第 15/22/49/58/65/73 天为负势垒，势阱最深 −197 kT）。也就是说，样品“抗不抗蛋白”取决于它当下的表面（接触角/SFE）状态，而不是简单取决于“放了几天”。",
    "纤维蛋白原在吸引态下给出四者中最深的势阱（−197 kT），在排斥态下与纤连蛋白同属势垒最高的一档（142–161 kT）——与文献中 Fg 在血液接触材料上最表面活性的地位一致，也与 Vroman 效应（早期白蛋白主导 → 后期被高亲和蛋白替换）的方向一致。",
    "三种体液环境的差异不在热力学而在组成：三者离子强度都 ≈0.15 M，单蛋白的 ΔG/势垒在三环境中相同；差别是“有哪几种蛋白”（血浆有完整的 Vroman 级联，组织液与关节液以白蛋白为主、几乎无纤维蛋白原）。只要表面进入吸引态，三种环境里都会形成蛋白条件膜。",
    "纹理在蛋白尺度上不起“几何屏蔽”作用：SEI 几何因子中位 0.991–1.005（蛋白 R=3.5–5 nm vs 织构特征 47–53 nm），而同一方法对细菌尺度的几何屏蔽可达 −84%。蛋白会照常铺满沟槽内外——论文中“激光纹理抗菌”的论证不应写成“抗蛋白”机制。",
    "条件膜会把界面“缓冲”到相近水平：细菌（金黄色葡萄球菌 ATCC 12600 / 大肠杆菌 F1693）对三种亲水蛋白膜的非特异黏附能均为排斥（+15…+38 mJ/m²），介于新鲜裸面（+50）与老化裸面（−31…−33）之间；但真实体系还有特异性识别（不在模型内），净效应必须实验判定。",
]))
A(("h2", "三条可直接检验的预测"))
A(("bullet", [
    "P1：新鲜（亲水）LIPSS/纳米柱上的 BSA/Fg 吸附量应显著低于抛光对照；且两套白蛋白参数给出同向结论。",
    "P2：处于“老化态”（γ⁻ 坍塌、接触角升高）的表面吸附量接近饱和单层，且 Fg/白蛋白吸附比随时间上升（Vroman）。",
    "P3：2% SDS + 30–60 min（可加轻度超声）应能回收 ≥95% 的吸附蛋白，且残留比例随“吸附后放置时间”增加——这正好用 §2 的协议验证。",
]))

# ============ 1 选型
A(("h1", "1 任务一：两种血液环境蛋白的选型"))
A(("h2", "1.1 选择标准"))
A(("bullet", [
    "必须是人体血液环境中真实存在、且丰度有意义的蛋白；",
    "必须能用商品化 kit 定量（不需要自建检测方法）；",
    "必须能验证 SDS 清洗效果（既能测洗脱液、也能测表面残留）；",
    "与本研究相关、文献参数齐全（能进 XDLVO 模型，也便于与文献对比）。",
]))
A(("h2", "1.2 候选与推荐"))
A(("table", "表 1  候选蛋白对比（★ = 推荐）",
   ["蛋白", "血浆浓度", "分子量", "角色与意义", "结论"],
   [
       ["人血清白蛋白 HSA", "35–50 g/L（约占血浆总蛋白一半）", "66.5 kDa", "维持胶体渗透压、运输；条件膜早期主导者", "★ 推荐"],
       ["人纤维蛋白原 Fg", "2–4 g/L", "340 kDa", "凝血核心；Vroman 效应主角；材料血液相容性的关键蛋白", "★ 推荐"],
       ["免疫球蛋白 IgG", "10–15 g/L", "150 kDa", "二次免疫应答；表面补体/免疫相关", "备选（开放文献缺 XDLVO 分量）"],
       ["转铁蛋白", "2–3 g/L", "80 kDa", "铁运输", "备选（缺参数）"],
       ["纤连蛋白 Fn", "≈0.3 g/L", "≈440 kDa", "细胞黏附蛋白；介导细菌/细胞附着", "模拟中加入（参数已有）；实验可选"],
   ]))
A(("p", "为何是这一对：白蛋白与纤维蛋白原分别对应条件膜的“早期/惰性化”与“成熟/促凝血”两个阶段，是最经典的一对标组合；两者也都是血液接触材料文献里出现频率最高的蛋白，便于与文献横向比较。" ))
A(("h2", "1.3 kit 矩阵（“能不能用现成的 kit 测”）"))
A(("table", "表 2  kit 矩阵与 SDS 兼容性",
   ["用途", "方法", "示例产品（订购前核对货号）", "与 SDS 兼容", "设备"],
   [
       ["总蛋白定量（洗脱液首选）", "BCA", "Pierce BCA 23225（低浓度用 Micro BCA 23235）", "✓ 耐 5% SDS", "562 nm 读数（酶标仪/分光光度计）"],
       ["总蛋白（替代）", "Bradford", "Bio-Rad 5000006 类", "✗ 只耐 0.016–0.5% SDS", "595 nm"],
       ["HSA 专用", "ELISA", "Abcam ab179887 / ab108787；Sigma RAB0603", "视产品说明", "450 nm"],
       ["Fg 专用", "ELISA", "Abcam ab108842；antibodies.com A79324；Cloud-Clone SEA193Hu", "视产品说明", "450 nm"],
       ["表面残留（主判据）", "荧光标记成像", "FITC-HSA / FITC-Fg，或 NHS-FITC 自标", "—", "荧光显微镜（已有）"],
       ["表面残留（辅助）", "接触角回归", "—", "—", "接触角仪（已有）"],
       ["表面残留（外送，如需要）", "XPS N 1s / ToF-SIMS", "—", "—", "外送"],
   ]))
A(("note", "注：读数波长需与手头仪器匹配；若实验室现成 kit 是其他类型（如 BCA 品牌不同），只要在 SDS 存在下做基质匹配标准曲线即可。"))
A(("h2", "1.4 采购建议"))
A(("table", "表 3  采购建议（示例，订购前核对规格与货号）",
   ["物品", "建议来源（示例）", "备注"],
   [
       ["HSA", "Sigma-Aldrich “Albumin from human serum”（如 A1653 / A3782 级）", "选 ≥96–99%；注意脂肪酸/球蛋白残留规格"],
       ["Fg", "Sigma-Aldrich “Fibrinogen from human plasma”（如 F3879 级）", "选 ≥95% clottable；避免反复冻融"],
       ["荧光标记蛋白", "FITC-HSA / FITC-Fg 商业品；或 NHS-FITC 自标", "标注度建议 2–4 mol FITC/mol 蛋白；自标需除游离染料"],
       ["定量试剂", "见 表 2", "BCA（23225）优先"],
   ]))
A(("h2", "1.5 实验浓度与条件"))
A(("bullet", [
    "HSA：0.1–2 mg/mL（PBS, pH 7.4），吸附 1–2 h，37 °C；",
    "Fg：0.05–0.5 mg/mL（高浓度易自聚集；用前 10,000 g 离心 5 min 去聚集体）；",
    "对照：PBS 空白、未处理 316L、以及“仅漂洗”样品（区分真吸附与本底）；",
    "每条件 n ≥ 3——模拟显示不同参数组之间可差 2–3 倍，实验的组间差异要能盖过参数不确定度。",
]))

# ============ 2 SDS
A(("h1", "2 任务一（续）：SDS 能否彻底清理？文献结论与验证协议"))
A(("h2", "2.1 文献结论：能洗掉大部分，但“彻底”需要实测"))
A(("bullet", [
    "SDS 洗脱是蛋白吸附领域的标准做法，但通常不完全：Rapoza & Horbett（J Biomater Sci Polym Ed 1989, 1(2):99–110）系统测量了纤维蛋白原从多种聚合物上的 SDS 洗脱——初始洗脱就不完全，且随吸附后放置时间延长、洗脱率进一步下降，作者归因于蛋白在表面的变性/铺展。",
    "SDS 会同时“清洗”和“锚定”：Zembala、Voegel 等（Langmuir 1998, 14(8), doi:10.1021/la971146n）发现 SDS 在洗脱纤维蛋白原的同时会把一部分分子转变成不可洗脱构象，洗脱动力学对 SDS 浓度呈非单调行为。",
    "器械再处理领域的做法可借鉴：残留蛋白定量已有标准方法（OPA 法；Sci. Rep. 2024, doi:10.1038/s41598-024-72473-1；限量思路见 ISO 15883-5:2021），其原则同样是“清洗后必须测残留”，而不是假定清洗完全。",
    "结论：把“SDS 能不能彻底清掉”当作一个要用你的样品实测的问题，而不是文献结论。",
]))
A(("h2", "2.2 验证协议（4 步 + 3 种检测 + 判据）"))
A(("table", "表 4  清洗验证流程",
   ["步骤", "操作", "记录"],
   [
       ["① 吸附", "样品 + 蛋白溶液（已知浓度 C₀、体积 V），37 °C、1–2 h", "C₀、时间、温度、批号"],
       ["② 漂洗", "PBS ×3；收集全部漂洗液（测“可漂洗移除”部分）", "漂洗次数/体积"],
       ["③ SDS 洗", "2% SDS 水溶液，室温 30–60 min；可加 10 min 轻度超声；保留洗液", "SDS 浓度、时间、是否超声"],
       ["④ 漂洗+干燥", "去离子水 ×3（务必充分——SDS 本身会吸附在钢面），N₂ 吹干", "—"],
   ]))
A(("bullet", [
    "检测 A（溶液侧，质量平衡）：BCA 测 C₀ 与吸附后上清 → 吸附量；BCA 测 SDS 洗液 → 回收量；回收率 = 回收/吸附。SDS 洗液稀释 5–10× 后测并做基质匹配标准曲线。",
    "检测 B（表面侧，主判据）：用 FITC-蛋白重复 ①–④，同一视野记录洗前/洗后荧光强度，残留比 = I_after / I_before。",
    "检测 C（辅助）：清洗干燥后水接触角与“从未接触蛋白的同批样品”比较（±3° 内视为回到基线；更严格可测三液 SFE）。",
]))
A(("p", "判据（建议）：质量平衡回收率 ≥95% 或残留 ≤ 检出限；荧光残留 ≤5%；接触角在基线 ±3° 内；连续 3 个“吸附→清洗”循环后吸附量与第 1 轮相差 <10%（无累积污染）。"))
A(("h2", "2.3 复用判定建议"))
A(("table", "表 5  样品可否复用",
   ["情形", "建议"],
   [
       ["三条判据全部通过", "可复用；建立清洗次数台账，第 5 次复用前重做一次完整验证"],
       ["荧光残留 5–20%", "单次演示实验可用；不要用于痕量/竞争吸附实验（残留会改变后续吸附）"],
       ["残留 >20% 或接触角明显偏离", "不复用；升级清洗（如 0.1 M NaOH 短时浸泡，或回到实验室标准清洗流程后再洗一轮）"],
       ["任何情况", "SDS 清洗后必须再测一次接触角确认无表面活性剂残留（阴离子表面活性剂会留在钢面改变润湿性）"],
   ]))
A(("h2", "2.4 注意事项"))
A(("bullet", [
    "样品状态变量：激光样品的 SFE 本身随时间往返变化（见 §3.3），因此“清洗后接触角”必须与同一天实测的参照样品比较，不能用历史数据；",
    "织构藏液：LIPSS/纳米柱沟槽会滞留液体，漂洗要足量（≥3 次，可轻度超声）；",
    "蛋白形态：Fg 高浓度会自聚集，用前离心；否则会高估吸附量；",
    "对照设置：必须包括“未吸附样品”与“仅 SDS 无蛋白样品”（后者校正 SDS 对检测信号的本底贡献）。",
]))

# ============ 3 模拟
A(("h1", "3 任务二：三种体液环境中的蛋白黏附模拟"))
A(("h2", "3.1 方法与参数"))
A(("bullet", [
    "模型：van Oss XDLVO（LW + AB + EL），球–平面几何 + Derjaguin 积分；织构表面另用 SEI 数值积分核对几何效应。",
    "条件：37 °C（310.15 K）；离子强度 0.15 M（血浆/组织液/滑液都接近此值）；h₀ = 0.158 nm；λ_AB = 0.6 nm。",
    "表面：来自 515 nm 样品 81 天接触角序列换算的 SFE（xdlvo_515nm_dG.csv，三液法）。",
    "参数不确定度：白蛋白用两套文献参数（Set A / Set B），把文献值的离散显式带入结果；Fg 与 Fn 用 van Oss 的接触角测值。",
]))
A(("table", "表 6  蛋白参数（XDLVO 输入）",
   ["蛋白参数组", "γ^LW", "γ⁺", "γ⁻", "ζ (mV)", "半径 (nm)", "来源"],
   [
       ["白蛋白 BSA Set A", "40.60", "1.16", "20.03", "−13", "3.5", "Wang & Newby, Biointerphases 9, 041006 (2014)"],
       ["白蛋白 BSA Set B", "43.22", "1.065", "47.68", "−13", "3.5", "Membranes 2025（另一套文献值）"],
       ["人纤维蛋白原 Fg", "37.6", "0.1", "38.0", "−20", "5.0", "van Oss, J. Protein Chem. 9, 487 (1990)"],
       ["人纤连蛋白 Fn", "29.5", "3.9", "52.1", "−15", "5.0", "van Oss (1990), 同表"],
   ]))
A(("p", "关于 HSA 的说明：人血清白蛋白没有公认的 XDLVO 参数集，而 BSA 是蛋白吸附研究的标准模型蛋白（与 HSA 序列同源、表面性质相近）。本报告用两套 BSA 文献参数并把差异显式保留。独立对照：文献实测的 HSA 吸附层为 θ_water 62±8°、θ_DIM 48±9°、总表面能 48±11 mJ/m²，与 BSA Set A 的 γ^TOT = 50.2 mJ/m² 同量级。"))
A(("table", "表 7  自检（全部通过）",
   ["自检", "内容", "结果"],
   [
       ["a", "BSA 的 ΔG 复现此前交付值（day 0, 25 °C 口径）", "LW/AB/ADH 逐位一致 ✓"],
       ["b", "势垒复现（Derjaguin vs 交付值）", "差 3.2–3.4% ✓"],
       ["c", "EL 项量级（0.15 M）", "ΔG_EL = 0.34 mJ/m²（可忽略，结论由 LW+AB 主导）✓"],
       ["d", "SEI 数值解 vs Derjaguin（O(λ/R) 修正）", "R=3.5 nm：−17.5%；R=5 nm：−12.0% ✓（如实报告）"],
       ["e", "interaction_energy 量纲自检（本任务发现并修复了模块的一个量纲 bug）", "scripts/xdlvo_unit_check.py：PASS，与独立解析式 0.000% 偏差 ✓"],
   ]))
A(("h2", "3.2 极端状态下的黏附矩阵（新鲜 vs 深老化）"))
A(("p", "表 8 = 新鲜态（第 0 天）；表 9 = 深老化态（第 58 天，三种表面的 γ⁻ 均已坍塌到 ≤0.22 mJ/m²）。每格为 ΔG_ADH (mJ/m²) / 势垒 (kT)；负势垒表示没有势垒、直接落进吸引势阱。"))
A(("table", "表 8  新鲜态（day 0）：ΔG_ADH (mJ/m²) / 势垒 (kT)",
   ["蛋白", "LIPSS", "纳米柱", "对照 316L"],
   snap(0)))
A(("table", "表 9  深老化态（day 58）",
   ["蛋白", "LIPSS", "纳米柱", "对照 316L"],
   snap(58)))
A(("fig", os.path.join(OUT, "fig1_dGADH_matrix.png"),
   "图 1  蛋白黏附自由能 ΔG_ADH：4 个参数组 × 3 种表面 × 新鲜（左）/ 深老化（右）。正值 = 排斥，负值 = 吸引。"))
A(("h2", "3.3 时效效应：表面状态会往返变化"))
A(("p", "把 81 天全部时间点（剔除第 7–10 天可疑占位数据点）连起来看，势垒并不是单调衰减，而是**在排斥态与深吸引态之间往返**。以 LIPSS 上的纤维蛋白原为例：负势垒出现在第 " + "、".join(str(d) for d in NEG_D) + " 天（全局最深的势阱 −197 kT：纳米柱第 58 天；LIPSS 上最深 −193 kT，在第 22 天），而第 " + "、".join(str(d) for d in POS_D) + " 天又回到正势垒（最高 +161 kT）。"))
A(("table", "表 10  81 天序列统计（势垒 kT；“负/总”= 负势垒天数/总天数）",
   ["表面", "蛋白", "序列最小", "序列最大", "负/总"],
   day_stats()))
A(("bullet", [
    "新鲜/亲水态（第 0 天为代表）→ 全参数组排斥（+36…+161 kT；对照 316L 上的白蛋白 Set A 例外，−17 kT）；",
    "深吸引态（第 15、22、49、58、65、73 天为代表）→ 全参数组强吸引，势阱可深达 −197 kT（不可逆量级）；",
    "因此准确的表述是：能否抗蛋白取决于**当下的表面状态**（接触角/SFE），而不是简单取决于“放了几天”。建议每次实验当天测量接触角并用三液法换算 SFE，再对照表 8/9 判断预期行为。",
]))
A(("p", "另外，接触角序列的往返波动本身也提示测量流程要固定（同一操作者、同一批探测液体、同一天完成各区域测量），否则表面状态的时间趋势会被测量变异掩盖。"))
A(("fig", os.path.join(OUT, "fig2_barrier_vs_age.png"),
   "图 2  势垒随表面时效的变化（全 81 天序列；左：LIPSS，右：对照 316L）。横轴以上 = 排斥，以下 = 吸引势阱。"))
A(("h2", "3.4 三种体液环境"))
A(("table", "表 11  体液组成（pH 7.4；离子强度均 ≈0.15 M）",
   ["环境", "白蛋白", "纤维蛋白原", "IgG", "纤连蛋白", "其他 / 备注"],
   [
       ["血浆", "35–50 g/L", "2–4 g/L", "10–15 g/L", "≈0.3 g/L", "总蛋白 60–80 g/L"],
       ["组织液", "≈29 g/L（前臂皮下，wick 法）", "低", "≈6 g/L", "低", "不同组织差异大（肝≈血浆，CSF 极低）"],
       ["关节滑液", "≈11 g/L", "≈0（正常滑液不凝）", "≈7 g/L（球蛋白总量）", "低", "透明质酸 ≈3 g/L；含润滑素（PRG4）"],
   ]))
A(("bullet", [
    "三者的离子强度几乎相同，所以**同一蛋白在三环境中的 ΔG/势垒完全相同**——环境差异来自“存在哪些蛋白”：",
    "血浆：白蛋白摩尔通量约为 Fg 的 60 余倍 → 早期白蛋白主导；随后被表面亲和更高的蛋白替换（Vroman 效应），成熟条件膜以 Fg 为主（与文献一致，也与本模型“Fg 最表面活性”一致）；",
    "组织液：白蛋白主导（Fg 供给低）；",
    "滑液：白蛋白主导 + 透明质酸层（未建模）+ 关节运动的剪切（未建模）。",
    "结论：**在哪个体液环境不改变“会不会吸附”（进入吸引态的表面都会吸附），只改变“吸附成什么样”。**",
]))
A(("fig", os.path.join(OUT, "fig3_uh_profiles.png"),
   "图 3  LIPSS 在体液条件（37 °C, 0.15 M）下的 U(h) 曲线：左 = 新鲜态（接触处正势垒），右 = 深老化态（接触处深势阱）。横轴对数尺度（AB 作用衰减长度 0.6 nm，接触附近特征集中在 <2 nm）。"))
A(("h2", "3.5 几何效应：纹理对蛋白“不存在”"))
A(("table", "表 12  SEI 几何因子（蛋白尺度 vs 细菌尺度）",
   ["体系", "特征曲率 Rc（中位）", "几何因子（中位）", "P1–P99", "|偏差|>5% 的像素"],
   [
       ["LIPSS（R = 3.5 nm 蛋白, 真实 AFM 场）", "47.2 nm", "0.991", "0.941–1.101", "12.4%"],
       ["纳米柱（R = 3.5 nm, 真实 AFM 场）", "52.5 nm", "1.005", "0.951–1.060", "3.8%"],
       ["对照 316L（R = 3.5 nm）", "687.6 nm", "1.000", "0.993–1.008", "0.0%"],
       ["R = 5 nm 蛋白在典型曲率（凹/凸）", "47 nm", "1.043 / 0.961", "—", "—"],
       ["参照：细菌尺度（前期工作，不同样本）", "—", "可低至 ≈0.16", "—", "—"],
   ]))
A(("p", "含义：蛋白（3.5–5 nm）比织构特征尺寸（沟距 ~412–466 nm、脊/柱 ~50 nm 尺度）小两个数量级，接触能量对形貌几乎不敏感（中位因子 ≈1），蛋白会进入沟内并贴壁铺满；而细菌尺度上同一套方法给出的几何屏蔽可达 −84%。因此：**纹理若要有“抗吸附”效果，必须靠化学（水化层/聚合物刷/两性离子等），不能靠形貌**——论文中“激光织构抗菌”的论证不要写成“抗蛋白”。"))
A(("h2", "3.6 条件膜对细菌黏附的影响"))
A(("table", "表 13  细菌对裸面与蛋白条件膜的非特异黏附能",
   ["基底", "S. aureus ΔG (mJ/m²) / 势垒 (kT)", "E. coli ΔG (mJ/m²) / 势垒 (kT)"],
   [
       ["裸 LIPSS（新鲜, day 0）", "+50.5 / +2.1×10⁴", "+50.1 / +2.1×10⁴"],
       ["裸 LIPSS（老化, day 58）", "−30.6 / −1.3×10⁴", "−32.6 / −1.4×10⁴"],
       ["裸对照 316L（新鲜, day 0）", "+27.3 / +1.1×10⁴", "+26.7 / +1.1×10⁴"],
       ["裸对照 316L（老化, day 58）", "−30.9 / −1.3×10⁴", "−33.0 / −1.4×10⁴"],
       ["白蛋白膜（Set A）", "+17.3 / +7.8×10³", "+15.5 / +7.4×10³"],
       ["白蛋白膜（Set B）", "+38.5 / +1.6×10⁴", "+37.9 / +1.6×10⁴"],
       ["纤维蛋白原膜", "+37.5 / +1.6×10⁴", "+36.7 / +1.6×10⁴"],
       ["纤连蛋白膜", "+37.4 / +1.5×10⁴", "+37.8 / +1.6×10⁴"],
   ]))
A(("bullet", [
    "极值对比：新鲜裸面 +50.5（强排斥）↔ 老化裸面 −30.6（吸引）——表面状态一变，结论直接翻转；",
    "三种亲水蛋白膜上细菌仍被排斥（+15…+38），即“条件膜把不同基底的界面缓冲到中间水平”；",
    "但真实体系中纤维蛋白原/纤连蛋白可通过特异性识别（细菌表面黏附素）促进黏附，这不在 XDLVO 框架内 → 条件膜的净效应必须实验判定；",
    "数值说明：细菌尺度的势垒数值巨大（10³–10⁴ kT）是 Derjaguin 线性化在 R=450 nm × 强 AB 项下的放大效应；判读只看符号与“是否 ≫10 kT”。",
]))
A(("fig", os.path.join(OUT, "fig4_bacteria_on_films.png"),
   "图 4  细菌黏附自由能：裸面（新鲜/老化）vs 蛋白条件膜。"))
A(("h2", "3.7 局限（必读）"))
A(("bullet", [
    "蛋白按刚性等效球处理；真实 Fg（长约 45–50 nm）会构象展开、多点接触 → 模型**低估** Fg/Fn 的吸附强度；",
    "没有竞争吸附动力学：Vroman 是定性引用文献，不是本模型算出来的；",
    "IgG、转铁蛋白、透明质酸、润滑素、脂质未建模（缺 XDLVO 参数）；",
    "ζ 电位：表面取 −25 mV（未实测），蛋白取文献值；0.15 M 下 EL 对本结果的贡献仅 0.34 mJ/m²，结论不敏感；",
    "温度口径：本报告 37 °C；此前交付的模拟为 25 °C，差异仅来自 kT 归一化（约 4%）；",
    "表面 SFE 由接触角三液法换算，已剔除第 7–10 天可疑数据点；第 81 天 LIPSS 为已知接触角尖峰异常（图中保留但已标注）；",
    "球–平面 Derjaguin 在 R=3.5–5 nm 有 −12…−17.5% 的系统偏差（SEI 数值解更准）；CSV 中另附 SEI 修正列；",
    "条件膜按天然态、连续、完全水合处理；实际吸附膜可能变性（更疏水）→ 条件膜对细菌的排斥可能被高估。",
]))

# ============ 4 下一步
A(("h1", "4 建议下一步（按顺序）"))
A(("bullet", [
    "采购：BCA 试剂盒 + HSA/Fg 蛋白 + HSA/Fg ELISA（可选）+ FITC 标记蛋白（见 §1.3/1.4）；",
    "清洗验证实验：按 §2.2 协议先在标准抛光 316L 上做，再迁到 LIPSS/纳米柱；",
    "吸附等温线（BCA 质量法）：0.1–2 mg/mL HSA、0.05–0.5 mg/mL Fg；每块样品当天测接触角+SFE 记录“状态”；",
    "竞争实验（检验 Vroman 预测）：10/30/100% 血浆稀释液，吸附 5–120 min → 2% SDS 洗脱 → ELISA 测 Fg/白蛋白比随时间变化；",
    "产物路径：模拟数据与图 E:\\LabToolbox\\output\\proteins_environments_20260930\\；脚本 E:\\LabToolbox\\scripts\\proteins_environments.py（可重跑）；本报告归档于 F:\\OneDrive - University of Dundee\\Ruinong_Pan_Personal\\蛋白质黏附_体液模拟_20260930\\。",
]))

# ============ 附录
A(("h1", "附录 A  文件清单"))
A(("bullet", [
    "模拟脚本：E:\\LabToolbox\\scripts\\proteins_environments.py（参数集中在文件头部，可改蛋白/表面/介质后重跑）；",
    "量纲自检：E:\\LabToolbox\\scripts\\xdlvo_unit_check.py（对照独立解析 Derjaguin 校验 interaction_energy）；",
    "数据：protein_surface_matrix.csv（3 表面 × 20 天 × 4 蛋白全序列）、bacteria_on_films.csv、environments_composition.csv、sei_protein_scale_R5.csv；",
    "自检日志：selfcheck_and_log.txt；图：fig1–fig4（PNG, 300 dpi）。",
]))
A(("h1", "附录 B  参考文献"))
A(("bullet", [
    "Wang, H.; Zhang Newby, B.-m. Biointerphases 9, 041006 (2014). doi:10.1116/1.4904074（BSA 的 XDLVO 参数与球–平面公式）",
    "van Oss, C. J. J. Protein Chem. 9(4), 487–491 (1990). doi:10.1007/BF01024625（纤维蛋白原/纤维蛋白表面性质）",
    "Rapoza, R. J.; Horbett, T. A. J. Biomater. Sci. Polym. Ed. 1(2), 99–110 (1989). doi:10.1163/156856289X00091（SDS 洗脱纤维蛋白原）",
    "Zembala, M.; Voegel, J.-C.; Schaaf, P. Langmuir 14(8) (1998). doi:10.1021/la971146n（SDS 洗脱中的“清除与锚定”竞争）",
    "Design and validation of a method for evaluating medical device cleanliness… Sci. Rep. (2024). doi:10.1038/s41598-024-72473-1（残留蛋白定量，OPA 法）",
    "Thermo Fisher TR0068 蛋白定量试剂兼容性表（BCA 耐 5% SDS；Bradford 0.016–0.5%）",
    "Abcam 产品页 ab108842（人纤维蛋白原 ELISA）、ab179887/ab108787（人白蛋白 ELISA）",
    "Hahn, R. G.; Dull, R. O. Intensive Care Med. Exp. 9 (2021). doi:10.1186/s40635-021-00407-6（组织液白蛋白 ≈29 g/L）",
    "Stewart, R. H. Front. Vet. Sci. 7, 609583 (2020). doi:10.3389/fvets.2020.609583（间质空间综述）",
    "Synovial fluid / 关节液组成：J. Therm. Anal. Calorim. (2019). doi:10.1007/s10973-019-08151-6；Rheopexy of synovial fluid…（PMC1618490）；滑液不凝（JOSPT 1979, doi:10.2519/jospt.1979.1.2.83）",
    "Wang et al. Mater. Des. 263, 115626 (2026)（前期 XDLVO–SEI 复现所用论文）",
]))
A(("note", "本报告由荧荧生成（2026-09-30）；所有模型数字可由附录 A 的脚本重跑复现，如有任何数字需要核对请直接指出。"))

# ---------------------------------------------------------------- docx 渲染
def clean(t):
    return str(t).replace("**", "")


def set_font(run, size=10.5, bold=False, italic=False, color=None, name=LATIN):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)
    rPr = run._element.get_or_add_rPr()
    rf = rPr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rPr.append(rf)
    rf.set(qn("w:ascii"), name)
    rf.set(qn("w:hAnsi"), name)
    rf.set(qn("w:eastAsia"), EA_FONT)


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def add_page_number_footer(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    set_font(run, 9, color=(0x66, 0x66, 0x66))
    f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = "PAGE"
    f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "end")
    run._r.append(f1); run._r.append(it); run._r.append(f2)


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        lines.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(lines)


def build_docx(path):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    add_page_number_footer(sec)
    st = doc.styles["Normal"]
    st.font.name = LATIN
    st.font.size = Pt(10.5)
    _rpr = st.element.get_or_add_rPr()
    _rf = _rpr.find(qn("w:rFonts"))
    if _rf is None:
        _rf = OxmlElement("w:rFonts")
        _rpr.append(_rf)
    _rf.set(qn("w:eastAsia"), EA_FONT)

    for blk in B:
        kind = blk[0]
        if kind == "title":
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_font(p.add_run(blk[1]), 17, bold=True)
        elif kind == "subtitle":
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_font(p.add_run(blk[1]), 11.5, color=(0x33, 0x33, 0x33))
        elif kind == "meta":
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_font(p.add_run(blk[1]), 9, italic=True, color=(0x77, 0x77, 0x77))
            p.paragraph_format.space_after = Pt(14)
        elif kind == "h1":
            p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(14)
            set_font(p.add_run(blk[1]), 14, bold=True)
        elif kind == "h2":
            p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(9)
            set_font(p.add_run(blk[1]), 11.5, bold=True)
        elif kind == "p":
            p = doc.add_paragraph()
            set_font(p.add_run(clean(blk[1])), 10.5)
        elif kind == "note":
            p = doc.add_paragraph()
            set_font(p.add_run(clean(blk[1])), 9, italic=True, color=(0x66, 0x66, 0x66))
        elif kind == "bullet":
            for it in blk[1]:
                p = doc.add_paragraph(style="List Bullet")
                set_font(p.add_run(clean(it)), 10.5)
        elif kind == "table":
            _, cap, headers, rows = blk
            p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(8)
            set_font(p.add_run(cap), 10, bold=True)
            t = doc.add_table(rows=1 + len(rows), cols=len(headers))
            t.style = "Table Grid"
            for j, h in enumerate(headers):
                c = t.cell(0, j); c.text = ""
                set_font(c.paragraphs[0].add_run(str(h)), 9, bold=True)
                shade(c, "F2F2F2")
            for i, row in enumerate(rows, start=1):
                for j, val in enumerate(row):
                    c = t.cell(i, j); c.text = ""
                    set_font(c.paragraphs[0].add_run(str(val)), 9)
            p2 = doc.add_paragraph(); set_font(p2.add_run(""), 6)
        elif kind == "fig":
            _, img, cap = blk
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(img, width=Cm(16.0))
            pc = doc.add_paragraph(); pc.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_font(pc.add_run(cap), 9, color=(0x44, 0x44, 0x44))
            pc.paragraph_format.space_after = Pt(10)
    doc.save(path)


def build_md(path):
    lines = []
    for blk in B:
        kind = blk[0]
        if kind == "title":
            lines.append(f"# {blk[1]}\n")
        elif kind == "subtitle":
            lines.append(f"**{blk[1]}**\n")
        elif kind == "meta":
            lines.append(f"*{blk[1]}*\n")
        elif kind == "h1":
            lines.append(f"\n## {blk[1]}\n")
        elif kind == "h2":
            lines.append(f"\n### {blk[1]}\n")
        elif kind == "p":
            lines.append(blk[1] + "\n")
        elif kind == "note":
            lines.append(f"> {blk[1]}\n")
        elif kind == "bullet":
            for it in blk[1]:
                lines.append(f"- {it}")
            lines.append("")
        elif kind == "table":
            _, cap, headers, rows = blk
            lines.append(f"\n**{cap}**\n")
            lines.append(md_table(headers, rows) + "\n")
        elif kind == "fig":
            _, img, cap = blk
            lines.append(f"\n![{cap}]({img})\n\n*{cap}*\n")
    io.open(path, "w", encoding="utf-8").write("\n".join(lines))


def main():
    os.makedirs(ARCHIVE, exist_ok=True)
    docx_path = os.path.join(DESKTOP, BASENAME + ".docx")
    md_path = os.path.join(DESKTOP, BASENAME + ".md")
    build_docx(docx_path)
    build_md(md_path)
    print("docx:", docx_path, os.path.getsize(docx_path), "bytes")
    print("md  :", md_path, os.path.getsize(md_path), "bytes")

    # 归档：docx + md + 图 + CSV + README
    shutil.copy2(docx_path, os.path.join(ARCHIVE, os.path.basename(docx_path)))
    shutil.copy2(md_path, os.path.join(ARCHIVE, os.path.basename(md_path)))
    fig_dir = os.path.join(ARCHIVE, "figures")
    dat_dir = os.path.join(ARCHIVE, "data")
    os.makedirs(fig_dir, exist_ok=True)
    os.makedirs(dat_dir, exist_ok=True)
    for f in os.listdir(OUT):
        src = os.path.join(OUT, f)
        if f.endswith(".png"):
            shutil.copy2(src, os.path.join(fig_dir, f))
        elif f.endswith(".csv") or f.endswith(".txt"):
            shutil.copy2(src, os.path.join(dat_dir, f))
    readme = (
        "# 蛋白质黏附：方案与模拟（2026-09-30）\n\n"
        "本文件夹归档「人体体液环境中的蛋白质黏附」报告及相关数据。\n\n"
        "* 报告：蛋白质黏附_方案与模拟报告_20260930.docx（同 .md 纯文本版）\n"
        "* figures/：报告插图 fig1–fig4（300 dpi PNG）\n"
        "* data/：protein_surface_matrix.csv（3 表面 × 全时效 × 4 蛋白组）、bacteria_on_films.csv、"
        "environments_composition.csv、sei_protein_scale_R5.csv、selfcheck_and_log.txt\n\n"
        "重跑复现：E:\\LabToolbox\\scripts\\proteins_environments.py（模拟）与 "
        "scripts\\build_proteins_report.py（报告）。参见报告附录 A。\n\n"
        "---\n\n"
        "**Protein adhesion in body-fluid environments (2026-09-30)** — report + data archive. "
        "Report: docx/md; figures in figures/ (300 dpi); raw model data in data/ "
        "(protein-surface matrix over the full ageing series, bacteria-on-conditioning-film, "
        "fluid compositions, SEI factors, self-check log). "
        "Reproduce with E:\\LabToolbox\\scripts\\proteins_environments.py; see Appendix A.\n"
    )
    io.open(os.path.join(ARCHIVE, "README.md"), "w", encoding="utf-8").write(readme)
    print("archived to:", ARCHIVE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
