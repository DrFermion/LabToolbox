# -*- coding: utf-8 -*-
"""构建中文综述：《面向抗菌应用的激光织构金属表面：综述》。
输出：DOCX（A4、正文 Calibri+微软雅黑、深藏青标题、三线表、OMML 公式、页脚页码）
      + Markdown 同源。内容在下方 B 块列表中。

用法：  python build_laser_antibacterial_review_zh.py [output_dir]
         （默认输出到 scratch build 目录；传入归档目录可原地重建）

2026-10-07 建立（初稿 v1，中文版；v3 同日更新：§3.7 预测建模 + 图 4）。需要 python-docx。
"""
import os, re, sys
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import OxmlElement, parse_xml

OUTDIR = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:\Users\PC\AppData\Local\hermes\cache\scratch\review_20261007\build"
os.makedirs(OUTDIR, exist_ok=True)
STEM = "激光织构金属抗菌综述_中文版_20261007"
DOCX_PATH = os.path.join(OUTDIR, STEM + ".docx")
MD_PATH = os.path.join(OUTDIR, STEM + ".md")
FIGDIR = os.path.join(OUTDIR, "figures")

NAVY = RGBColor(0x1F, 0x36, 0x4D)
GRAY = RGBColor(0x59, 0x59, 0x59)
M = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'

# ---------------------------------------------------------------- OMML builders
def mr(t):
    return f'<m:r><m:t xml:space="preserve">{t}</m:t></m:r>'

def mu(t):
    return f'<m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t xml:space="preserve">{t}</m:t></m:r>'

def msub(b, s):
    return f'<m:sSub><m:e>{b}</m:e><m:sub>{s}</m:sub></m:sSub>'

def mfrac(n, d):
    return f'<m:f><m:num>{n}</m:num><m:den>{d}</m:den></m:f>'

def mrad(x):
    return f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{x}</m:e></m:rad>'

def mdelim(x, beg='(', end=')'):
    return (f'<m:d><m:dPr><m:begChr m:val="{beg}"/><m:endChr m:val="{end}"/></m:dPr>'
            f'<m:e>{x}</m:e></m:d>')

EQ1 = (msub(mr('λ'), mr('sp')) + mr(' = ') + msub(mr('λ'), mr('0')) + mr(' ') +
       mrad(mdelim(mfrac(msub(mr('ε'), mr('m')) + mr(' + ') + msub(mr('ε'), mr('d')),
                         msub(mr('ε'), mr('m')) + mr(' ') + msub(mr('ε'), mr('d'))))))
EQ1_TXT = "λ_sp = λ_0 √((ε_m + ε_d)/(ε_m ε_d))"
EQ2 = (mr('Λ') + mr(' = ') + mfrac(mr('λ'), mr('2 ') + mu('sin') + mr(' θ')))
EQ2_TXT = "Λ = λ / (2 sin θ)"
EQ3 = (mr('Λ') + mr(' ≈ ') + mfrac(mr('λ'), mr('1 ± ') + mu('sin') + mr(' θ')))
EQ3_TXT = "Λ ≈ λ / (1 ± sin θ)"

# ---------------------------------------------------------------- docx helpers
TOKEN = re.compile(r'(\*\*[^*]+\*\*|\*[^*\n]+\*|\^\{[^}]*\}|_\{[^}]*\})')

def rich(p, text, size=None, color=None, bold_all=False, italic_all=False):
    for seg in TOKEN.split(text):
        if not seg:
            continue
        if seg.startswith('**') and seg.endswith('**') and len(seg) > 4:
            r = p.add_run(seg[2:-2]); r.bold = True
        elif seg.startswith('*') and seg.endswith('*') and len(seg) > 2:
            r = p.add_run(seg[1:-1]); r.italic = True
        elif seg.startswith('^{') and seg.endswith('}'):
            r = p.add_run(seg[2:-1]); r.font.superscript = True
        elif seg.startswith('_{') and seg.endswith('}'):
            r = p.add_run(seg[2:-1]); r.font.subscript = True
        else:
            r = p.add_run(seg)
        if size is not None:
            r.font.size = size
        if color is not None:
            r.font.color.rgb = color
    if bold_all:
        for r in p.runs:
            r.bold = True
    if italic_all:
        for r in p.runs:
            r.italic = True
    return p

def body_para(doc, text, size=Pt(10.5), align=WD_ALIGN_PARAGRAPH.JUSTIFY, style=None,
              space_after=6, keep_next=False, indent=None):
    p = doc.add_paragraph(style=style)
    rich(p, text, size=size)
    p.paragraph_format.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    if keep_next:
        p.paragraph_format.keep_with_next = True
    if indent is not None:
        p.paragraph_format.left_indent = Cm(indent)
    return p

def heading(doc, text, level):
    p = doc.add_paragraph(style=f'Heading {level}')
    rich(p, text)
    return p

def add_eq(doc, inner):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(6)
    p._p.append(parse_xml(f'<m:oMathPara {M}><m:oMath>{inner}</m:oMath></m:oMathPara>'))
    return p

def _tbl_insert(tblPr, el, *succ):
    tblPr.insert_element_before(el, *succ)

def three_line(tbl):
    tblPr = tbl._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for tag, val, sz in (('top', 'single', '12'), ('bottom', 'single', '12'),
                         ('left', 'none', None), ('right', 'none', None),
                         ('insideH', 'none', None), ('insideV', 'none', None)):
        el = OxmlElement(f'w:{tag}')
        el.set(qn('w:val'), val)
        if sz:
            el.set(qn('w:sz'), sz); el.set(qn('w:space'), '0'); el.set(qn('w:color'), '000000')
        borders.append(el)
    _tbl_insert(tblPr, borders, 'w:shd', 'w:tblLayout', 'w:tblCellMar', 'w:tblLook')
    layout = OxmlElement('w:tblLayout'); layout.set(qn('w:type'), 'fixed')
    _tbl_insert(tblPr, layout, 'w:tblCellMar', 'w:tblLook')
    mar = OxmlElement('w:tblCellMar')
    for side, w in (('top', '28'), ('left', '108'), ('bottom', '28'), ('right', '108')):
        el = OxmlElement(f'w:{side}'); el.set(qn('w:w'), w); el.set(qn('w:type'), 'dxa')
        mar.append(el)
    _tbl_insert(tblPr, mar, 'w:tblLook')
    for cell in tbl.rows[0].cells:
        tcPr = cell._tc.get_or_add_tcPr()
        tcb = OxmlElement('w:tcBorders')
        b = OxmlElement('w:bottom')
        b.set(qn('w:val'), 'single'); b.set(qn('w:sz'), '6'); b.set(qn('w:space'), '0'); b.set(qn('w:color'), '000000')
        tcb.append(b)
        tcPr.insert_element_before(tcb, 'w:shd', 'w:noWrap', 'w:tcMar', 'w:textDirection', 'w:vAlign', 'w:hideMark')

def add_table_block(doc, num, cap, headers, rows, widths, center_cols=()):
    cp = doc.add_paragraph()
    rich(cp, f"**表 {num}.**  {cap}", size=Pt(9.5))
    cp.paragraph_format.space_after = Pt(3)
    cp.paragraph_format.keep_with_next = True
    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tbl.autofit = False
    total = int(round(sum(widths) * 566.93))
    tblPr = tbl._tbl.tblPr
    tw = tblPr.find(qn('w:tblW'))
    if tw is None:
        tw = OxmlElement('w:tblW')
        _tbl_insert(tblPr, tw, 'w:jc', 'w:tblCellSpacing', 'w:tblInd', 'w:tblBorders', 'w:shd', 'w:tblLayout')
    tw.set(qn('w:w'), str(total)); tw.set(qn('w:type'), 'dxa')
    all_rows = [headers] + rows
    for ri, row in enumerate(all_rows):
        for ci, txt in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.width = Cm(widths[ci])
            p = cell.paragraphs[0]
            rich(p, txt, size=Pt(9), bold_all=(ri == 0))
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.space_before = Pt(1)
            if ci in center_cols:
                p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        tr = tbl.rows[ri]._tr
        trPr = tr.get_or_add_trPr()
        cant = OxmlElement('w:cantSplit'); trPr.append(cant)
        if ri == 0:
            th = OxmlElement('w:tblHeader'); th.set(qn('w:val'), 'true'); trPr.append(th)
        if ri < len(all_rows) - 1:
            for cell in tbl.rows[ri].cells:
                for pp in cell.paragraphs:
                    pp.paragraph_format.keep_with_next = True
    three_line(tbl)
    return tbl

def add_figure_block(doc, fname, caption):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(os.path.join(FIGDIR, fname), width=Cm(15.5))
    cp = doc.add_paragraph()
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rich(cp, caption, size=Pt(9.5))
    cp.paragraph_format.space_after = Pt(9)
    return cp

def add_footer(doc, short):
    sec = doc.sections[0]
    p = sec.footer.paragraphs[0]
    p.text = ''
    p.paragraph_format.tab_stops.add_tab_stop(Cm(17.0), WD_TAB_ALIGNMENT.RIGHT)
    p.add_run(short + '\t')
    p.add_run('第 ')
    f1 = OxmlElement('w:fldSimple'); f1.set(qn('w:instr'), r' PAGE ')
    fr = OxmlElement('w:r'); ft = OxmlElement('w:t'); ft.text = '1'; fr.append(ft); f1.append(fr)
    p._p.append(f1)
    p.add_run(' 页，共 ')
    f2 = OxmlElement('w:fldSimple'); f2.set(qn('w:instr'), r' NUMPAGES ')
    fr2 = OxmlElement('w:r'); ft2 = OxmlElement('w:t'); ft2.text = '1'; fr2.append(ft2); f2.append(fr2)
    p._p.append(f2)
    p.add_run(' 页')
    for r in p.runs:
        r.font.size = Pt(8.5); r.font.color.rgb = GRAY

def hrule(doc):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    b = OxmlElement('w:bottom')
    b.set(qn('w:val'), 'single'); b.set(qn('w:sz'), '6'); b.set(qn('w:space'), '1'); b.set(qn('w:color'), 'BFBFBF')
    pbdr.append(b)
    pPr.append(pbdr)
    p.paragraph_format.space_after = Pt(8)
    return p

def set_ea(style, name='微软雅黑'):
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts'); rpr.append(rf)
    rf.set(qn('w:eastAsia'), name)

# ---------------------------------------------------------------- content
TITLE = "面向抗菌应用的激光织构金属表面：综述"
SUBTITLE = "制备工艺、LIPSS 形成物理、抗菌机理与工艺工程考量"
META = "初稿 — 2026 年 10 月 7 日"

ABSTRACT = [
 "器械相关感染与生物膜持续构成沉重的临床与经济负担，推动着不依赖抗生素释放的表面技术发展。"
 "对金属表面——其中以不锈钢最为突出——进行直接激光织构，已成为一种免涂层的策略：抗菌功能被"
 "内建于材料本身。本综述汇集该领域的四个方面。第一，概述如何用超快激光制备织构化金属表面："
 "试样准备、激光参数窗口，以及两类主要表面形貌——激光诱导周期性表面结构（LIPSS）与纳米柱/锥"
 "阵列。第二，阐明 LIPSS 的形成物理：入射光束与金属表面激发的表面电磁波相互干涉，因而结构"
 "周期由激光波长决定（通常为 0.7–0.9 λ），沟脊取向则跟随光束偏振。第三，综述织构金属已报道"
 "的抗菌机理——形貌驱动的抗黏附、高纵横比纳米结构上的机械杀菌膜破裂、表面化学效应与蛋白"
 "条件膜相互作用——并分析已发表结果为何差异巨大。最后，讨论工艺工程层面的推论：激光波长是一项"
 "离散的硬件属性（基频加谐波档位），而非连续可调参数，因此现实中可得到的 LIPSS 周期是量子化"
 "（离散）的；直接激光干涉图案化等替代路线可以把周期与波长解耦。综述还梳理了以预测结构本身为目标的计算方法——电磁效率因子的数值计算、能量沉积与熔体动力学的多物理场模拟，以及数据驱动模型——并说明这类预测对加工中表面光学状态的强烈依赖。综述最后给出当前塑造该领域的"
 "开放问题与标准化需求。",
]
KEYWORDS = ("关键词：激光表面织构；激光诱导周期性表面结构（LIPSS）；抗菌表面；细菌黏附；"
            "机械杀菌表面；不锈钢")

S1 = [
 ("h1", "1. 引言"),
 ("h2", "1.1 临床问题：器械相关感染与生物膜"),
 ("p", "器械相关感染——由导管、关节假体、牙种植体及其他留置器械引发的感染——是最具影响的"
       "医疗保健相关感染之一。仅在美国，医疗保健相关感染每年估计影响数百万患者，经济负担达"
       "数百亿美元 (Klevens et al., 2007; Stone, 2009)。其核心病理事件是器械表面的生物膜形成："
       "浮游细菌黏附、增殖为微菌落，并包埋于自身分泌的胞外聚合物基质中 (Flemming et al., "
       "2016)。生物膜的生活方式通过限制扩散、代谢休眠与持留细胞形成等途径，使菌群对抗生素、"
       "消毒剂和宿主免疫防御获得保护 (Hall and Mah, 2017)，因此生物膜相关的植入物感染往往"
       "迁延难愈，常需手术翻修 (Zimmerli and Sendi, 2017; Arciola et al., 2018; VanEpps "
       "and Younger, 2016)。由于这一过程始于黏附，能够阻止细菌建立立足点——或在接触时"
       "杀死细菌——的表面，可以在生物膜成熟之前打断感染链。在植入物上，细菌与宿主组织细胞"
       "在同一界面竞争，这被称为“表面之争” (Subbiahdoss et al., 2009)，使得最早期细胞–材料"
       "相互作用具有决定性意义。"),
 ("h2", "1.2 抗菌表面策略与激光织构的位置"),
 ("p", "抗菌表面的策略可分为几个大类（表 1）。抗菌释放型涂层把杀菌剂——如银纳米颗粒、"
       "抗生素或氯己定——装载于表面或聚合物储库中，逐渐释放并作用于浮游及早期黏附的细菌；"
       "其共性缺点包括载量有限、释放动力学难以精确控制，对抗生素而言还存在耐药性压力 "
       "(Cloutier et al., 2015; Wei et al., 2019)。接触杀菌型涂层——通常基于固定化的季铵盐"
       "化合物、抗菌肽或酶——在接触时破坏细菌膜；其耐久性与活性位点的持续可及性决定了器械"
       "整个寿命周期内的表现 (Siedenbiedel and Tiller, 2012)。防污策略，如聚乙二醇刷与"
       "两性离子聚合物层，则以另一种方式起作用：使界面在能量上不利于蛋白质与细胞的附着 "
       "(Magin et al., 2010)。第四类——本综述的主题——是形貌策略：把材料本身在微米与纳米"
       "尺度上结构化。由于这类表面将功能内建于基体而非涂层，不引入可浸出化合物、不受涂层"
       "剥落影响，并可经一步自动化加工完成 (Hasan et al., 2013; Vorobyev and Guo, 2013; "
       "Lutey et al., 2018)。混合路线将两种思路结合，例如在激光织构表面上叠加聚多巴胺–"
       "壳聚糖–银纳米复合涂层 (Wang et al., 2025; Wei et al., 2019)。"),
 ("p", "激光织构对 316L 不锈钢、钛及其合金等金属尤其具有吸引力——这些材料在植入物与手术"
       "器械中无处不在。利用超短激光脉冲可产生两种典型形貌：激光诱导周期性表面结构（LIPSS）"
       "——周期略低于激光波长的准周期沟脊；以及纳米柱或锥阵列，因其多尺度粗糙度能够陷光，"
       "也被称为“黑金属” (Vorobyev and Guo, 2013; Bonse et al., 2017)。两类形貌均已针对"
       "细菌进行了测试，结果因菌株、介质与织构几何而异 (Schwibbert et al., 2024)。"),
 ("h2", "1.3 综述范围"),
 ("p", "本综述整合四条线索：(i) 激光织构金属表面的制备；(ii) LIPSS 的形成物理，包括从材料与激光参数预测结构的计算方法；(iii) 抗菌"
       "机理及文献分歧的原因；(iv) 工艺工程，包括波长可得性及其对结构周期的后果。重点放在"
       "不锈钢，以及规划、实施与报告实验所需的实用细节层面。"),
]

S2 = [
 ("h1", "2. 激光织构金属表面的制备"),
 ("h2", "2.1 基材准备与样品设计"),
 ("p", "多数研究对奥氏体不锈钢（通常为 316L——医疗器械与食品加工设备的标准化合金）进行"
       "织构化；钛及其合金也广泛使用 (Hasan et al., 2013; Cunha et al., 2016; Wang "
       "et al., 2026)。试样先经机械抛光——常用逐级磨料抛至镜面——并在超声浴（丙酮、"
       "异丙醇、去离子水）中清洗，再用氮气流吹干。可重现的初始形貌很重要：首批激光脉冲"
       "与抛光划痕及其他不规则处相互作用，这些缺陷充当周期结构的种子并影响其均匀性。"
       "一种降低试样间波动的实用设计是在同一试样上加工多个区域——例如 A 结构区、B 结构区"
       "与未处理对照区——使所有比较共享同一基材、批次与时效历史。该方案有一点需注意："
       "烧蚀区相对原始表面下沉数微米，这一台阶会影响力学与成像分析，例如流场实验中的"
       "边缘效应或原子力显微镜测量 (Wang et al., 2026)。"),
 ("h2", "2.2 激光加工原理：从单脉冲到表面织构"),
 ("p", "织构加工使用飞秒至皮秒脉冲激光，偶尔用纳秒。采用超短脉冲的理由是能量局域化："
       "脉冲在显著热扩散发生之前将能量沉积于电子系统，从而减少熔化与附带热损伤，结构比"
       "纳秒脉冲更精细、更干净 (Bonse et al., 2012; Vorobyev and Guo, 2013)。实验变量"
       "包括波长 λ、脉宽 τ、重复频率 f、脉冲能量（换算为注量 F，即单位面积能量，"
       "J cm⁻²）、光斑直径 d、扫描速度 v、扫描间距与扫描遍数。结果主要取决于所施加注量"
       "与材料烧蚀阈值的比值，以及每点累积的脉冲数。对单条扫描线，累积脉冲数约为 "
       "N ≈ f·d/v；多遍扫描与搭接会相应提高单位面积剂量。织构形成涉及两种区间：接近"
       "阈值、脉冲累积充分的辐照产生 LIPSS（第 3 节），而远高于阈值、高搭接的辐照剧烈"
       "去除材料，塑造出柱–锥形貌（第 2.3 节）。脉冲累积之所以有效，是因为孵化效应："
       "重复辐照通过逐步的缺陷生成与表面粗糙化降低有效阈值 (Bonse et al., 2017)。加工"
       "气氛是另一个变量：空气中烧蚀材料再沉积并氧化，惰性或反应性气氛则同时改变化学与"
       "形貌 (Vorobyev and Guo, 2013)。图 1 将这些区间汇集为一张工艺图谱。"),
 ("h2", "2.3 结构库：LIPSS、纳米柱与干涉图案"),
 ("p", "表 2 梳理了加工窗口及其产生的形貌。LIPSS 形成于接近烧蚀阈值的注量，并在多次脉冲"
       "中生长；在不锈钢上表现为周期约 0.7–0.9 λ、起伏数十至数百纳米的准周期沟脊 (Bonse "
       "et al., 2012; Bonse et al., 2017)。当累积剂量远超阈值时形成纳米柱与锥；其形貌"
       "经由强烧蚀、熔体流动与再凝固发展，常经历从类 LIPSS 沟脊开始的两阶段过程。由于"
       "由此产生的多尺度织构在可见光范围内陷光，这类表面被称为“黑金属”；对硅在 SF₆ 等"
       "反应性气氛中加工，对应产物是“黑硅”，即经典机械杀菌研究采用的界面类型 (Vorobyev "
       "and Guo, 2013; Ivanova et al., 2013)。第三条路线不依赖自组织：直接激光干涉图案化"
       "（DLIP）让两束或多束相干光重叠，使强度分布到达样品前就具有周期性，周期由干涉角"
       "而非材料响应决定 (Peter et al., 2020; Schwibbert et al., 2024)。DLIP 将在第 5.2 节"
       "进一步讨论。"),
 ("h2", "2.4 验证与表征流程"),
 ("p", "加工后试样通常再次清洗——例如用溶剂超声——以去除碎屑。表面验证用扫描电子显微镜"
       "（SEM）观察形貌，其空间周期可通过对图像做二维傅里叶分析方便地提取；原子力显微镜"
       "（AFM）测量粗糙度与起伏；接触角测量表征润湿性。涉及表面化学时，能量色散 X 射线谱"
       "或 X 射线光电子能谱可补充形貌信息（第 4.4–4.5 节）。将全部激光参数与试样编号一并"
       "记录是标准做法，也是可比性的基础——因为相同的名义形貌可能由不同参数组合产生，其"
       "亚表面损伤与表面化学并不相同 (Engoor et al., 2025)。"),
]

S3 = [
 ("h1", "3. 激光诱导周期性表面结构的形成物理"),
 ("h2", "3.1 干涉图像：光在书写自己的光栅"),
 ("p", "LIPSS 的存在乍看似乎矛盾：一束强度分布平滑的激光竟写出周期图案，而没有任何掩模"
       "或模板施加周期性。答案出现在 1970 年代——Emmony 与合作者观察到锗镜面上的周期性"
       "损伤，将其归因于入射波与表面散射波的干涉 (Emmony et al., 1973)。Sipe 与合作者将"
       "这一图像形式化：其理论把入射光与表面粗糙度散射光场的干涉描述为非均匀能量沉积 "
       "(Sipe et al., 1983)。本质上，表面自己提供了“第二束光”：沟脊间距由光波长决定，"
       "图案之所以出现，是因为两波干涉。这一思想——图案由光书写，而非由力学强加——是随后"
       "一切的关键。"),
 ("h2", "3.2 表面电磁波与周期的起源"),
 ("p", "“第二束光”是一种表面电磁波。在金属上，光可以耦合为表面等离极化激元（SPP）："
       "束缚于金属–介质界面的光与电子密度混合振荡，其场在界面两侧指数衰减——金属侧为"
       "数十纳米量级。当金属的介电函数实部 ε_{m} 为负时（金属从可见光到中红外的普遍"
       "情形），这类波得以存在，且其波长比驱动光更短："),
 ("eq", EQ1, EQ1_TXT),
 ("p", "式中 λ_{0} 为激光波长，ε_{d} 为相邻介质的介电常数（空气：ε_{d} = 1）。对典型"
       "金属介电常数，λ_{sp}/λ_{0} 的取值约为 0.95（ε_{m} ≈ −10）、0.89（ε_{m} ≈ −5）、"
       "0.82（ε_{m} ≈ −3）、0.75（ε_{m} ≈ −2.3）。由于观测到的沟脊周期与该表面波波长"
       "密切相关，熟悉的实验结果自然随之而来：金属上 LIPSS 的周期大致落在激光波长的 "
       "0.7–0.9 倍区间。当有效光学常数在加工过程中演化——氧化、熔化与缺陷累积使 |ε_{m}| "
       "减小——所选周期本身还可能向下漂移 (Huang et al., 2009; Bonse et al., 2017)。"),
 ("h2", "3.3 动量匹配与自增强反馈"),
 ("p", "耦合还有一个条件：动量。理想光滑的金属无法把光直接吸收为 SPP，因为空气中的光子"
       "动量小于 SPP 动量——两条色散曲线永不相交。必须有机制补上缺失的动量，而表面粗糙度"
       "恰好做到这一点：粗糙表面散射光，散射波获得耦合为表面波所需的额外动量。这带来一个"
       "特征性结果——过程自举。最初几个脉冲使抛光表面粗糙化并激发弱表面波；随之而来的"
       "干涉以某个优选周期沉积能量；周期性改性加深为光栅；光栅更高效地把入射光耦合为"
       "表面波；图案随之锐化。这种正反馈正是 LIPSS 表现为自组织、准规则结构的原因——其"
       "取向与周期由光场选择——也是它们随脉冲数增加而锐化的原因 (Sipe et al., 1983; "
       "Huang et al., 2009; Bonse et al., 2017)。该序列见图 2。"),
 ("h2", "3.4 波长标度、准周期性与周期控制"),
 ("p", "两条实用规律来自上述物理。第一，波长标度：由于周期跟随表面波波长，改变激光波长"
       "会近似线性地缩放周期——这是控制结构尺寸最稳健的手段。以算术示例说明：0.75–0.85 λ "
       "的比例意味着 1030 nm 下周期约 770–880 nm、515 nm 下约 385–440 nm、343 nm 下约 "
       "255–290 nm。实验上，金属的这一比例通常落在 0.7–0.9 λ 区间 (Bonse et al., 2017)。"
       "第二，准周期性：实际上 LIPSS 并非完美周期。选择机制偏好一个波矢带宽，而材料不"
       "均匀性——晶粒、氧化物、缺陷密度——使分布展宽，所以实测周期带有百分之几的散布，"
       "“准周期”才是准确描述 (Bonse et al., 2017)。斜入射时，面内几何使所选周期近似按"
       "下式移动"),
 ("eq", EQ3, EQ3_TXT),
 ("p", "其中 θ 为入射角；该效应支持在单一波长内对周期做适度连续调节 (Bonse et al., "
       "2017)。"),
 ("h2", "3.5 取向规律与分类"),
 ("p", "沟脊方向是该机理最直接的实验指纹：对金属上的标准类型（LSFL-I），沟脊垂直于激光"
       "场的偏振方向，偏振旋转 90° 则图案旋转 90°。圆偏振光没有固定的面内场方向，会抑制"
       "沟脊形成——这是直接检验图案电磁起源的对照实验 (Bonse et al., 2017; Engoor "
       "et al., 2025)。按周期与取向，LIPSS 分为三类：LSFL-I（低空间频率 LIPSS），周期"
       "约 0.7–1 λ、取向垂直于偏振，是金属上的特征类型；LSFL-II，周期约 λ/n（n 为有效"
       "折射率）、取向平行于偏振，见于强吸收介质与氧化表面；以及 HSFL（高空间频率 "
       "LIPSS），周期 < λ/2，其成因仍有争议，常在低注量下形成 (Bonse et al., 2017)。"
       "按此分类，515 nm 下不锈钢上周期约 0.75 λ 的沟脊属于无疑义的 LSFL-I。"),
 ("h2", "3.6 从光图案到材料图案"),
 ("p", "光学图案随后被转化为物理织构。干涉极大处吸收的能量加热表面，依局部剂量不同，"
       "材料熔化、流动并部分汽化。在广泛接受的图像中，沟谷经历最强烧蚀，而脊由未被去除"
       "的材料、加之再凝固的熔体以及（空气中）氧化物与再沉积纳米颗粒组成 (Vorobyev and "
       "Guo, 2013; Bonse et al., 2017)。随脉冲重复，形貌逐步累积：初始浅沟脊经由上述反馈"
       "加深，直至烧蚀去除图案的速度超过其再生速度；又因每个脉冲都降低有效阈值（孵化"
       "效应），加工窗口在过程中漂移，需通过扫描策略与气氛控制来管理 (Bonse et al., "
       "2017)。简短概括：图案由光书写，结构由物质构筑。"),
 ("h2", "3.7 预测建模：从材料与激光属性到结构"),
 ("p", "前几节解释了 LIPSS 为何形成、取向由什么锁定；还有一个互补的定量问题：给定一种材料与"
       "一组激光参数，预期的周期——乃至最终形貌——是什么？有三类方法以逐渐增加的物理细节回答"
       "这个问题。第一类是解析方法：Sipe 理论可以数值地演化为效率因子 η(κx, κy)——它衡量表面"
       "粗糙度波矢 κ 把入射场耦合为空间调制能量沉积的效率；η 的极值给出被偏好的周期"
       "（κ = λ/Λ）与取向 (Sipe et al., 1983; Bonse et al., 2005)。计算的输入包括激光波长处"
       "的复介电常数、入射角、偏振，以及两个统计粗糙度参数（填充因子与形状因子）；在早期"
       "实现中的一处符号错误被识别之后，修正后的表述与开源实现已经发布 (Kaczmarek et al., "
       "2024)。一个密切相关的估计来自第 3.2 节的表面波色散：对强吸收的类金属表面，它给出的"
       "周期略低于激光波长，并随介电常数模量的减小向 ≈0.7 λ 移动 (Bonse et al., 2017)。"),
 ("p", "一个针对奥氏体不锈钢的示意计算能把这种相互作用具体化。以室温光学常数计算 (Karlsson "
       "and Ribbing, 1982)，515 nm、正入射下效率因子的极值位于 κ ≈ 1.02，即预测周期 "
       "≈504 nm（0.98 λ）——对一个强吸收的、未受扰动的表面而言，这接近波长本身。而同一波长"
       "下 316L 上已报道的实验周期明显更短（≈385 nm，即 0.75 λ；Wang et al., 2026）。这一"
       "差异是有信息量的：效率因子与色散估计都取决于加工过程中表面的光学状态——被电子激发、"
       "熔化与氧化所改变——而非原始块材本身。用同一模型做的敏感性分析（图 4）表明：把 "
       "|Re ε| 从 ≈8（515 nm 的块材钢）降到 ≈2.3、同时阻尼下降，预测周期会从 ≈0.98 λ 移到 "
       "≈0.74 λ，在 |Re ε| ≈ 2.3 附近穿过实测值；同一区间内效率因子峰值增强一个数量级以上，"
       "与实验中图案随累积剂量增加而锐化的现象一致。实践上的启示是双重的：正向预测周期需要把"
       "有效光学状态作为输入；反过来，实测周期可用于约束该状态——这一推断可以与加工表面的"
       "表面化学分析相互校验。参数敏感性是此类练习的注意事项：粗糙度因子会进入计算并可能"
       "移动峰位约 10%，因此这类数字是趋势性估计而非精确预言。"),
 ("p", "在解析路线之外，还有两类方法瞄准的是形貌本身而不只是周期。多物理场模拟把电磁场——在"
       "演化表面上用时域有限差分或有限元方法求解——与电子–晶格能量传递的双温描述、以及熔化、"
       "流动与再凝固的流体动力学或相场模型耦合起来，使浮雕形貌的逐脉冲演化乃至从沟脊向锥、柱"
       "的转变可以在计算机中再现 (Tsibidis et al., 2012; Bonse et al., 2017)。这类模型抓住了"
       "解析估计所排除的物理——自洽反馈、熔体动力学、多脉冲累积——代价是庞大的参数集"
       "（随温度变化的光学与热学性质、熔体流动参数）与可观的算力。数据驱动方法则处在另一端："
       "以实验或模拟得到的参数–形貌数据对训练，机器学习模型可以直接从加工参数预测表面形貌与"
       "反射谱，或识别能形成高质量 LIPSS 的工艺窗口 (Na et al., 2022; Wang et al., 2022)。"
       "这类模型不提供物理解释，但给出工艺规划所需的直接参数→结构映射；其精度随一致、完整"
       "报告的数据集的积累而提高——这也再次印证了第 5.3 节讨论的报告规范。"),
 ("h2", "3.8 操作条件与开放问题"),
 ("p", "实践上，LIPSS 在等于或略高于单脉冲阈值的注量下产生，需累积足够脉冲（每点几十"
       "至几百个）并保持扫描稳定；飞秒至皮秒脉冲有利于干净的沟脊，加工气氛与表面化学"
       "同时调制周期与深度 (Bonse et al., 2012; Bonse et al., 2017)。尽管干涉图像是该"
       "领域的共识框架——它解释了两个稳健特征：波长尺度的周期与偏振锁定的取向——对最终"
       "图案的定量预测仍不完整：早期脉冲动力学、氧化物与有效光学常数的作用、高空间频率"
       "沟脊的机制都仍在活跃研究中。文献将 LIPSS 形成称为“科学常青树”，正因这一主题"
       "持续生长 (Bonse et al., 2017)。"),
]

S4 = [
 ("h1", "4. 织构金属表面的抗菌机理"),
 ("h2", "4.1 抗黏附与形貌"),
 ("p", "激光织构金属最有文献支持的抗菌效应是黏附减少——表面保留的细菌少于抛光对照。"
       "工作机制的解释是几何性的：细菌典型尺寸为 0.5–2 µm，远小于细胞的表面特征减少"
       "可及接触面积，从而相对平坦表面降低黏附能（附着点理论）；定量细胞–织构相互作用"
       "模型重现了这一图像 (Hasan et al., 2013; Lazzini et al., 2019)。实验上，飞秒"
       "织构表面减少钛上金黄色葡萄球菌的滞留 (Cunha et al., 2016)，纳米级沟脊抑制钢上"
       "生物膜生长 (Epperlein et al., 2017)，在 316L 不锈钢上黏附与早期生物膜形成均响应 "
       "LIPSS 几何 (Romoli et al., 2020; Capella et al., 2024)。若干细微之处值得注意。"
       "效应依赖结构尺寸：当周期或间距接近细胞尺度时，细胞可落入结构之间，滞留反而"
       "增加——不锈钢上已重现这种跨越：不同周期与深度的 LIPSS 对大肠杆菌黏附产生相反的"
       "调制 (Outón et al., 2024)，聚合物表面上沟脊间距决定大肠杆菌是否被排斥 (Richter "
       "et al., 2021)。效应也依赖菌株：杆状与球形细菌对同一织构的感受不同，系统比较"
       "报道纳米织构钢上菌种间偏好相反 (Epperlein et al., 2017; Schwibbert et al., "
       "2024)。近期对 316L 的工作表明，织构几何同时支配黏附与腐蚀性能，激光诱导的氧化"
       "状态对两者都有贡献 (Wang et al., 2026; Engoor et al., 2025)。一个已浮现的经验"
       "法则：远小于细菌尺寸的特征（约细胞尺度的一半及以下）利于抗黏附，而与细胞尺寸"
       "相当的特征促进捕获；任何效应的强度仍具体系特异性 (Schwibbert et al., 2024)。"),
 ("h2", "4.2 润湿性与表面能"),
 ("p", "第二个变量是表面能。织构改变润湿性有两条途径——几何上，粗糙度放大本征润湿"
       "行为；化学上，激光改性表层不同于基体。金属上新鲜织构的表面常呈强亲水，并随大气"
       "中有机物吸附在数天至数周内演化，因此接触角代表的是带时间戳的状态，而非永久属性 "
       "(Kietzig et al., 2009; Daskalova and Angelova, 2023)。在接触角之外，表面自由能"
       "可在 van Oss–Chaudhury–Good 框架内分解为 Lifshitz–van der Waals、酸碱与静电"
       "贡献 (van Oss et al., 1988)，细菌——或蛋白质——相对于表面的黏附势则表现为自由能–"
       "间距曲线，即扩展 DLVO 构造，已被用于固体表面上的蛋白质吸附 (Wang and Zhang "
       "Newby, 2014)。该框架提供了从润湿数据到生物学结果的定量桥梁；它同时解释了为什么"
       "单一接触角数值是细菌响应的弱预测因子，以及为什么某些体系中超疏水状态与滞留减少"
       "相关联 (Fadeeva et al., 2011)。"),
 ("h2", "4.3 机械杀菌作用"),
 ("p", "一个更直接的机理吸引了该领域大部分注意力：织构可以机械地杀死细菌。蝉翼撕裂铜绿"
       "假单胞菌细胞的发现——膜在相邻纳米柱之间被拉伸直至破裂——确立了纯物理形貌可以杀菌 "
       "(Ivanova et al., 2012)，其生物物理机制随后以柱间膜黏附能的模型描述 (Pogodin "
       "et al., 2013)。黑硅被证明可杀死革兰阴性与革兰阳性菌后，该概念被转移至人工基材 "
       "(Ivanova et al., 2013)。后续工作细化了图像：除膜拉伸外，纳米柱阵列还通过局部"
       "细胞压阻、促进氧化应激的穿透事件以及干扰细胞分裂起作用 (Jenkins et al., 2020)。"
       "设计原则——柱间距与高度同膜拉伸极限的关系——见 Linklater 等综述 (Linklater "
       "et al., 2021)。本语境下两点需注意。第一，机械杀菌需要高纵横比特征且间距匹配膜"
       "力学；对典型 LIPSS 这类浅形貌（起伏仅数十纳米），膜远未拉伸至破裂，因此对 LIPSS "
       "而言，抗菌贡献主要在于抗黏附与表面能，而非机械杀伤 (Linklater et al., 2021; "
       "Schwibbert et al., 2024)。高纳米柱与锥织构才是预期出现机械效应的形貌类别。"
       "第二，杀伤效率并非普适：它依赖物种，孢子等耐受形态基本不受影响 (Linklater "
       "et al., 2021)。"),
 ("h2", "4.4 表面化学贡献"),
 ("p", "激光加工改变的不仅是几何。在空气中，表面获得一层薄氧化膜，其成分、厚度与缺陷"
       "密度反映加工过程的快速非平衡氧化，不同于天然钝化膜；这些激光诱导表层已在钢上被"
       "表征 (Wang et al., 2026; Engoor et al., 2025)，也在钛上 (Barylyak et al., "
       "2024)。化学效应可以直接起作用：飞秒织构钛表现出光致反应活性，叠加于其测得的"
       "抗菌性能之上 (Barylyak et al., 2024)。它们也使解释复杂化：当织构样品优于抛光"
       "对照时，部分差异可能源于化学而非形貌——这正是细致研究在形貌之外同时报告表面"
       "分析（X 射线光电子能谱、能量色散 X 射线谱）的原因 (Schwibbert et al., 2024)。"),
 ("h2", "4.5 生物环境中的蛋白条件膜"),
 ("p", "真实生物环境会增加一层：蛋白条件膜。当表面接触血液、唾液或含血清培养基时，"
       "蛋白质在数秒内到达并按丰度与亲和力吸附——即 Vroman 序列——形成向接近的细菌展示"
       "新界面的膜 (Rabe et al., 2011)。蛋白质携带自身的表面能 (van Oss, 1990)，因此"
       "同一织构在缓冲液与富蛋白介质中可能表现不同；简单介质中得到的抗菌排序并不总能"
       "平移到生物流体；在任何转化声明之前，需要在相关介质中测试 (Schwibbert et al., "
       "2024)。"),
 ("h2", "4.6 已发表结果为何分歧"),
 ("p", "为什么已发表结果差异如此之大——一些织构大幅减少黏附，另一些无效应甚至增强？"
       "差异可追溯至至少六个因素：(i) 菌株与生理状态；(ii) 介质与蛋白条件膜的有无；"
       "(iii) 孵育时间及实验测量的是初始黏附、定殖还是成熟生物膜；(iv) 静态与流动条件；"
       "(v) 织构确切的特征尺寸、间距、深度与化学——往往报告欠缺；以及 (vi) 评价方法"
       "本身——黏附计数、菌落形成单位实验与活/死荧光染色测得的是不同的量，且活力染料"
       "有充分记录的陷阱，须以审慎的实验设计加以控制 (Robertson et al., 2019; Stiefel "
       "et al., 2015)。阅读这类研究的一条有用纪律：把抗黏附（附着细胞更少）与杀菌"
       "作用（附着细胞死亡）分开，并把每项主张锚定到特定参比表面——通常是同一试样的"
       "抛光对照 (Lutey et al., 2018; Hasan et al., 2013; Schwibbert et al., 2024)。"
       "图 3 展示上述四种机理，表 3 汇总其关键条件与注意事项。"),
]

S5 = [
 ("h1", "5. 工艺工程与转化考量"),
 ("h2", "5.1 波长：一项离散的硬件属性"),
 ("p", "对基于织构的研究设计而言，激光波长是决定性变量——也是一个常被误读的变量，因为"
       "它不是旋钮。固体超快激光器的发射波长由其增益介质固定：Nd:YAG 与 Nd:YVO₄ 系列为 "
       "1064 nm，Yb 系为 1030 nm，钛宝石约 800 nm。其他波长靠谐波产生获得——二、三次谐波"
       "给出 532 与 355 nm（Nd 系）、515 与 343 nm（Yb 系）、400 与 267 nm（钛宝石）"
       "——这些是离散档位而非连续谱：1064 nm 系统不能连续调到 650 nm，532 nm 输出也无法"
       "调成 515 nm，因为二者源自不同的激光家族。真正可调的光源——光学参量振荡器或"
       "放大器、染料激光器——可覆盖数百纳米，但此类仪器是面织构加工中罕用的专业设备 "
       "(Bonse et al., 2017)。在商业实践中，离散性体现于按波长组织的产品线：同一超快"
       "平台按波长分型号提供，输出功率从红外到紫外递减，谐波控制器把各波长路由到各自"
       "的输出口（表 4）。切换波长是硬件级重配置，并带来二阶成本：吸收率、焦斑尺寸与"
       "烧蚀阈值都随波长改变，每个新波长都需重新开发工艺窗口——注量扫描、阈值测定与"
       "扫描参数再优化——才能产出可比结构 (Bonse et al., 2017)。在一个项目周期内，"
       "可得的波长构成一份离散菜单，LIPSS 周期继承了这份离散性。"),
 ("h2", "5.2 超出波长的周期控制"),
 ("p", "由此产生两条结构设计推论。第一，周期量子化：由于 LIPSS 周期随波长缩放，给定"
       "加工条件下可达到的周期以每档波长约 0.7–0.9 λ 的离散带跳跃，把周期改变超过百分之"
       "几意味着更换硬件，而非调节参数。第二，存在连续替代方案：需要可调周期时，基于"
       "干涉的直接书写（DLIP）通过光束几何把周期与激光波长解耦，"),
 ("eq", EQ2, EQ2_TXT),
 ("p", "其中 θ 为干涉光束间半角。DLIP 已以抗菌为动机应用于不锈钢 (Peter et al., 2020)，"
       "其图案可方便地与 LIPSS 类织构及涂层组合，代价是更复杂的光路与受相干性及景深"
       "限制的图案场 (Schwibbert et al., 2024)。一条中间路线保留单光束，利用第 3.4 节"
       "所述的斜入射周期移动，支持单一波长内的适度连续调节 (Bonse et al., 2017)。相"
       "比之下，扫描速度与扫描间距等参数控制覆盖、深度与均匀性，但并不移动周期本身 "
       "(Bonse et al., 2017)。"),
 ("h2", "5.3 可重复性与报告规范"),
 ("p", "该领域的可重复性天生脆弱：工艺窗口狭窄（近阈值注量），结果依赖累积剂量历史，"
       "织构的生物学性能还会随表面时效漂移——润湿转变、氧化物演化——时间尺度为天至周 "
       "(Daskalova and Angelova, 2023; Kietzig et al., 2009)。两条做法已相当成熟。完整"
       "参数报告——设备型号、波长、脉宽、注量、重复频率、光斑尺寸、扫描速度、扫描间距、"
       "遍数、气氛——是使织构可复现、可跨实验室比较的前提；缺少其中任何一项（包括波长）"
       "都会改变产出的结构 (Bonse et al., 2017; Schwibbert et al., 2024)。表面状态则"
       "带时间戳记录：接触角与表面化学与生物测试并列记录，并在织构、表征与实验之间规定"
       "时效方案 (Daskalova and Angelova, 2023)。更广泛的领域仍缺少织构表面的标准化"
       "抗菌测试方案——这是公认的跨研究比较障碍，也是走向转化应用的前提 (Hasan et al., "
       "2013; Schwibbert et al., 2024)。"),
]

S6 = [
 ("h1", "6. 总结与开放问题"),
 ("p", "用超短激光脉冲织构金属表面，提供了通往抗菌界面的免涂层途径；过去十年已就物理"
       "与开放问题形成连贯图景："),
 ("bul", "**物理（大体已定）。** LIPSS 由入射光与激光激发的表面电磁波之间的干涉书写；"
         "周期以 ≈0.7–0.9 λ 跟随波长，取向锁定于偏振，结构在烧蚀阈值附近通过自增强"
         "光栅耦合生长 (Emmony et al., 1973; Sipe et al., 1983; Huang et al., 2009; "
         "Bonse et al., 2017)。"),
 ("bul", "**工程（结构上离散）。** 波长是硬件属性——基频加谐波档位——因此 LIPSS 周期"
         "以离散带出现；DLIP 通过光束几何把周期从这一约束中释放，代价是更复杂的光路 "
         "(Peter et al., 2020; Schwibbert et al., 2024)。"),
 ("bul", "**生物学（有条件的）。** 织构金属可显著减少细菌黏附，高的纳米结构可机械"
         "杀死附着细胞；结果依赖菌株、介质、特征尺度与表面化学，且当特征尺度接近细胞"
         "大小时存在从抗黏附到细胞捕获的跨越 (Ivanova et al., 2012; Ivanova et al., "
         "2013; Linklater et al., 2021; Outón et al., 2024; Wang et al., 2026)。"),
 ("p", "当前塑造该领域的开放问题：在富蛋白介质中从织构几何与表面能定量预测黏附与杀伤"
       "的模型；真实条件下形貌与化学的长期稳定性（灭菌、储存、磨损）；标准化、跨实验室"
       "比对的评价方案；以及织构通量放大到器件相关面积。在物理一侧，从给定材料与激光参数出发对结构本身（周期与形貌）进行定量预测，是另一片正在开拓的开放前沿——可从解析效率因子计算、多物理场模拟与数据驱动模型三条路线推进（第 3.7 节）。混合路线——激光织构结合抗菌"
       "涂层——弥补单一机理的部分有效性 (Wang et al., 2025)，而积累的机理理解使合理的"
       "织构设计（而非经验试错）成为现实目标。"),
]

REFERENCES = [
 "Arciola, C. R., Campoccia, D., & Montanaro, L. (2018). Implant infections: Adhesion, biofilm formation and immune evasion. Nature Reviews Microbiology, 16(7), 397–409. https://doi.org/10.1038/s41579-018-0019-y",
 "Barylyak, A., Wojnarowska-Nowak, R., Kus-Liśkiewicz, M., Krzemiński, P., Płoch, D., Cieniek, B., Bobitski, Y., & Kisała, J. (2024). Photocatalytic and antibacterial activity properties of Ti surface treated by femtosecond laser — a prospective study. Scientific Reports, 14, 20926. https://doi.org/10.1038/s41598-024-70103-4",
 "Bonse, J., Munz, M., & Sturm, H. (2005). Structure formation on the surface of indium phosphide irradiated by femtosecond laser pulses. Journal of Applied Physics, 97(1), 013538. https://doi.org/10.1063/1.1827919",
 "Bonse, J., Krüger, J., Höhm, S., & Rosenfeld, A. (2012). Femtosecond laser-induced periodic surface structures. Journal of Laser Applications, 24(4), 042006. https://doi.org/10.2351/1.4712658",
 "Bonse, J., Höhm, S., Kirner, S. V., Rosenfeld, A., & Krüger, J. (2017). Laser-induced periodic surface structures — a scientific evergreen. IEEE Journal of Selected Topics in Quantum Electronics, 23(3), 9000615. https://doi.org/10.1109/JSTQE.2016.2614183",
 "Capella, A. G., Silva, M. M., Simões, J. G. A. B., Andrade, V. M., Riva, R., & Conceição, K. (2024). Biofilm growth on laser-induced periodic surface structures (LIPSS) of AISI 316L stainless steel. Matéria (Rio de Janeiro), 29(3), e20240288. https://doi.org/10.1590/1517-7076-RMAT-2024-0288",
 "Cloutier, M., Mantovani, D., & Rosei, F. (2015). Antibacterial coatings: Challenges, perspectives, and opportunities. Trends in Biotechnology, 33(11), 637–652. https://doi.org/10.1016/j.tibtech.2015.09.002",
 "Cunha, A., Elie, A.-M., Plawinski, L., Serro, A. P., Botelho do Rego, A. M., Almeida, A., Urdaci, M. C., Durrieu, M.-C., & Vilar, R. (2016). Femtosecond laser surface texturing of titanium as a method to reduce the adhesion of Staphylococcus aureus and biofilm formation. Applied Surface Science, 360, 485–493. https://doi.org/10.1016/j.apsusc.2015.10.102",
 "Daskalova, A., & Angelova, L. (2023). Design of surfaces with persistent antimicrobial properties on stainless steel developed using femtosecond laser texturing for application in “high traffic” objects. Nanomaterials, 13(17), 2396. https://doi.org/10.3390/nano13172396",
 "Emmony, D. C., Howson, R. P., & Willis, L. J. (1973). Laser mirror damage in germanium at 10.6 µm. Applied Physics Letters, 23(11), 598–600. https://doi.org/10.1063/1.1654761",
 "Engoor, G. G., Selvaraj, S., Acharya, N., Muthuvijayan, V., Krishnan, S., Unni, S. N., & Vasa, N. J. (2025). Laser polarization induced surface structuring of 316L stainless steel and influence on biocompatibility and antibacterial performance. Results in Surfaces and Interfaces, 19, 100547. https://doi.org/10.1016/j.rsurfi.2025.100547",
 "Epperlein, N., Menzel, F., Schwibbert, K., Koter, R., Bonse, J., Sameith, J., Krüger, J., & Toepel, J. (2017). Influence of femtosecond laser produced nanostructures on biofilm growth on steel. Applied Surface Science, 418, 420–424. https://doi.org/10.1016/j.apsusc.2017.02.174",
 "Fadeeva, E., Truong, V. K., Stiesch, M., Chichkov, B. N., Crawford, R. J., Wang, J., & Ivanova, E. P. (2011). Bacterial retention on superhydrophobic titanium surfaces fabricated by femtosecond laser ablation. Langmuir, 27(6), 3012–3019. https://doi.org/10.1021/la104607g",
 "Flemming, H.-C., Wingender, J., Szewzyk, U., Steinberg, P., Rice, S. A., & Kjelleberg, S. (2016). Biofilms: An emergent form of bacterial life. Nature Reviews Microbiology, 14(9), 563–575. https://doi.org/10.1038/nrmicro.2016.94",
 "Hall, C. W., & Mah, T.-F. (2017). Molecular mechanisms of biofilm-based antibiotic resistance and tolerance in pathogenic bacteria. FEMS Microbiology Reviews, 41(3), 276–301. https://doi.org/10.1093/femsre/fux010",
 "Hasan, J., Crawford, R. J., & Ivanova, E. P. (2013). Antibacterial surfaces: The quest for a new generation of biomaterials. Trends in Biotechnology, 31(5), 295–304. https://doi.org/10.1016/j.tibtech.2013.01.017",
 "Huang, M., Zhao, F., Cheng, Y., Xu, N., & Xu, Z. (2009). Origin of laser-induced near-subwavelength ripples: Interference between surface plasmons and incident laser. ACS Nano, 3(12), 4062–4070. https://doi.org/10.1021/nn900654v",
 "Ivanova, E. P., Hasan, J., Webb, H. K., Truong, V. K., Watson, G. S., Watson, J. A., Baulin, V. A., Pogodin, S., Wang, J. Y., Tobin, M. J., Löbbe, C., & Crawford, R. J. (2012). Natural bactericidal surfaces: Mechanical rupture of Pseudomonas aeruginosa cells by cicada wings. Small, 8(16), 2489–2494. https://doi.org/10.1002/smll.201200528",
 "Ivanova, E. P., Hasan, J., Webb, H. K., Gervinskas, G., Juodkazis, S., Truong, V. K., Wu, A. H., Lamb, R. N., Baulin, V. A., Watson, G. S., Watson, J. A., Mainwaring, D. E., & Crawford, R. J. (2013). Bactericidal activity of black silicon. Nature Communications, 4, 2838. https://doi.org/10.1038/ncomms3838",
 "Jenkins, J., Mantell, J., Neal, C., Gholinia, A., Verkade, P., Nobbs, A. H., & Su, B. (2020). Antibacterial effects of nanopillar surfaces are mediated by cell impedance, penetration and induction of oxidative stress. Nature Communications, 11, 1626. https://doi.org/10.1038/s41467-020-15471-x",
 "Kaczmarek, D., Albert, T. J., Munz, M., Sturm, H., & Bonse, J. (2024). Erratum: “Structure formation on the surface of indium phosphide irradiated by femtosecond laser pulses” [J. Appl. Phys. 97, 013538 (2005)]. Journal of Applied Physics, 136(4), 049903. https://doi.org/10.1063/5.0222903",
 "Karlsson, B., & Ribbing, C. G. (1982). Optical constants and spectral selectivity of stainless steel and its oxides. Journal of Applied Physics, 53(9), 6340–6346. https://doi.org/10.1063/1.331503",
 "Kietzig, A.-M., Hatzikiriakos, S. G., & Englezos, P. (2009). Patterned superhydrophobic metallic surfaces. Langmuir, 25(8), 4821–4827. https://doi.org/10.1021/la8037582",
 "Klevens, R. M., Edwards, J. R., Richards, C. L., Horan, T. C., Gaynes, R. P., Pollock, D. A., & Cardo, D. M. (2007). Estimating health care-associated infections and deaths in U.S. hospitals, 2002. Public Health Reports, 122(2), 160–166. https://doi.org/10.1177/003335490712200205",
 "Lazzini, G., Romoli, L., Lutey, A. H. A., & Fuso, F. (2019). Modelling the interaction between bacterial cells and laser-textured surfaces. Surface and Coatings Technology, 375, 8–14. https://doi.org/10.1016/j.surfcoat.2019.06.078",
 "Linklater, D. P., Baulin, V. A., Juodkazis, S., Crawford, R. J., Stoodley, P., & Ivanova, E. P. (2021). Mechano-bactericidal actions of nanostructured surfaces. Nature Reviews Microbiology, 19(1), 8–22. https://doi.org/10.1038/s41579-020-0414-z",
 "Lutey, A. H. A., Gemini, L., Romoli, L., Lazzini, G., Fuso, F., Faucon, M., & Kling, R. (2018). Towards laser-textured antibacterial surfaces. Scientific Reports, 8, 10112. https://doi.org/10.1038/s41598-018-28454-2",
 "Magin, C. M., Cooper, S. P., & Brennan, A. B. (2010). Non-toxic antifouling strategies. Materials Today, 13(4), 36–44. https://doi.org/10.1016/S1369-7021(10)70058-4",
 "Na, H., Yoo, J., & Ki, H. (2022). Prediction of surface morphology and reflection spectrum of laser-induced periodic surface structures using deep learning. Journal of Manufacturing Processes, 84, 1274–1283. https://doi.org/10.1016/j.jmapro.2022.11.004",
 "Outón, J., Carbú, M., Domínguez, M., Ramírez-del-Solar, M., Alba, G., Vlahou, M., Stratakis, E., Matres, V., & Blanco, E. (2024). Size matters: How periodicity and depth of LIPSS influences E. coli adhesion on ferritic stainless steel. Applied Surface Science, 663, 160225. https://doi.org/10.1016/j.apsusc.2024.160225",
 "Peter, A., Lutey, A. H. A., Faas, S., Romoli, L., Onuseit, V., & Graf, T. (2020). Direct laser interference patterning of stainless steel by ultrashort pulses for antibacterial surfaces. Optics & Laser Technology, 123, 105954. https://doi.org/10.1016/j.optlastec.2019.105954",
 "Pogodin, S., Hasan, J., Baulin, V. A., Webb, H. K., Truong, V. K., Nguyen, S. H. P., Boshkovikj, V., Fluke, C. J., Watson, G. S., Watson, J. A., Crawford, R. J., & Ivanova, E. P. (2013). Biophysical model of bacterial cell interactions with nanopatterned cicada wing surfaces. Biophysical Journal, 104(4), 835–840. https://doi.org/10.1016/j.bpj.2012.12.046",
 "Rabe, M., Verdes, D., & Seeger, S. (2011). Understanding protein adsorption phenomena at solid surfaces. Advances in Colloid and Interface Science, 162(1–2), 87–106. https://doi.org/10.1016/j.cis.2010.12.007",
 "Richter, A. M., Buchberger, G., Stifter, D., Duchoslav, J., Hertwig, A., Bonse, J., Heitz, J., & Schwibbert, K. (2021). Spatial period of laser-induced surface nanoripples on PET determines Escherichia coli repellence. Nanomaterials, 11(11), 3000. https://doi.org/10.3390/nano11113000",
 "Robertson, J., McGoverin, C., Vanholsbeeck, F., & Swift, S. (2019). Optimisation of the protocol for the LIVE/DEAD BacLight bacterial viability kit for rapid determination of bacterial load. Frontiers in Microbiology, 10, 801. https://doi.org/10.3389/fmicb.2019.00801",
 "Romoli, L., Lazzini, G., Lutey, A. H. A., & Fuso, F. (2020). Influence of ns laser texturing of AISI 316L surfaces for reducing bacterial adhesion. CIRP Annals, 69(1), 529–532. https://doi.org/10.1016/j.cirp.2020.04.003",
 "Schwibbert, K., Richter, A. M., Krüger, J., & Bonse, J. (2024). Laser-textured surfaces: A way to control biofilm formation? Laser & Photonics Reviews, 18(1), 2300753. https://doi.org/10.1002/lpor.202300753",
 "Siedenbiedel, F., & Tiller, J. C. (2012). Antimicrobial polymers in solution and on surfaces: Overview and functional principles. Polymers, 4(1), 46–71. https://doi.org/10.3390/polym4010046",
 "Sipe, J. E., Young, J. F., Preston, J. S., & van Driel, H. M. (1983). Laser-induced periodic surface structure. I. Theory. Physical Review B, 27(2), 1141–1154. https://doi.org/10.1103/PhysRevB.27.1141",
 "Stiefel, P., Schmidt-Emrich, S., Maniura-Weber, K., & Ren, Q. (2015). Critical aspects of using bacterial cell viability assays with the fluorophores SYTO 9 and propidium iodide. BMC Microbiology, 15, 36. https://doi.org/10.1186/s12866-015-0376-x",
 "Stone, P. W. (2009). Economic burden of healthcare-associated infections: An American perspective. Expert Review of Pharmacoeconomics & Outcomes Research, 9(5), 417–422. https://doi.org/10.1586/erp.09.53",
 "Subbiahdoss, G., Kuijer, R., Grijpma, D. W., van der Mei, H. C., & Busscher, H. J. (2009). Microbial biofilm growth vs. tissue integration: “The race for the surface” experimentally studied. Acta Biomaterialia, 5(5), 1399–1404. https://doi.org/10.1016/j.actbio.2008.12.011",
 "Tsibidis, G. D., Barberoglou, M., Loukakos, P. A., Stratakis, E., & Fotakis, C. (2012). Dynamics of ripple formation on silicon surfaces by ultrashort laser pulses in subablation conditions. Physical Review B, 86(11), 115316. https://doi.org/10.1103/PhysRevB.86.115316",
 "van Oss, C. J., Chaudhury, M. K., & Good, R. J. (1988). Interfacial Lifshitz-van der Waals and polar interactions in macroscopic systems. Chemical Reviews, 88(6), 927–941. https://doi.org/10.1021/cr00088a006",
 "van Oss, C. J. (1990). Surface properties of fibrinogen and fibrin. Journal of Protein Chemistry, 9(4), 487–491. https://doi.org/10.1007/BF01024625",
 "VanEpps, J. S., & Younger, J. G. (2016). Implantable device-related infection. Shock, 46(6), 597–608. https://doi.org/10.1097/SHK.0000000000000692",
 "Vorobyev, A. Y., & Guo, C. (2013). Direct femtosecond laser surface nano/microstructuring and its applications. Laser & Photonics Reviews, 7(3), 385–407. https://doi.org/10.1002/lpor.201200017",
 "Wang, B., Wang, P., Song, J., Lam, Y. C., Song, H., Wang, Y., & Liu, S. (2022). A hybrid machine learning approach to determine the optimal processing window in femtosecond laser-induced periodic nanostructures. Journal of Materials Processing Technology, 308, 117716. https://doi.org/10.1016/j.jmatprotec.2022.117716",
 "Wang, H., & Zhang Newby, B. (2014). Applicability of the extended Derjaguin–Landau–Verwey–Overbeek theory on the adsorption of bovine serum albumin on solid surfaces. Biointerphases, 9(4), 041006. https://doi.org/10.1116/1.4904074",
 "Wang, Y., Dong, Y., Quan, Y., Wackerow, S., Abdolvand, A., Zolotovskaya, S. A., & Zhao, Q. (2025). Hybrid antibacterial surfaces: Combining laser-induced periodic surface structures with polydopamine-chitosan-silver nanoparticle nanocomposite coating. Advanced Materials Interfaces, 12(6), 2400660. https://doi.org/10.1002/admi.202400660",
 "Wang, Y., Olugbade, T. O., Zhao, Y.-Y., Dai, H., Zhang, S., Abdolvand, A., Zhao, Q., & Zolotovskaya, S. A. (2026). Geometry-driven control of bacterial adhesion and corrosion performance on LIPSS-textured 316L stainless steel. Materials & Design, 263, 115626. https://doi.org/10.1016/j.matdes.2026.115626",
 "Wei, T., Yu, Q., & Chen, H. (2019). Responsive and synergistic antibacterial coatings: Fighting against bacteria in a smart and effective way. Advanced Healthcare Materials, 8(3), 1801381. https://doi.org/10.1002/adhm.201801381",
 "Zimmerli, W., & Sendi, P. (2017). Orthopaedic biofilm infections. APMIS, 125(4), 353–364. https://doi.org/10.1111/apm.12687",
]

TABLE1 = ("抗菌表面策略的类别及其主要局限（依据 Hasan et al., 2013; Cloutier et al., 2015; "
          "Magin et al., 2010; Wei et al., 2019; Linklater et al., 2021; Wang et al., 2025）。",
 ["策略", "示例", "作用方式", "主要局限"],
 [["抗菌释放型涂层", "银纳米颗粒、抗生素、氯己定",
   "释放杀菌剂，作用于浮游及早期黏附的细菌",
   "载量有限；释放速率控制；细胞毒性权衡；耐药性担忧"],
  ["接触杀菌型涂层", "固定化季铵盐化合物、抗菌肽、酶",
   "接触时破坏膜或造成氧化损伤",
   "耐久性与活性位点可及性；难以深入生物膜"],
  ["防污涂层", "聚乙二醇刷、两性离子聚合物、水合层设计",
   "对蛋白质与细菌附着的热力学屏障",
   "稳定性与机械鲁棒性；批次重现性"],
  ["形貌策略（激光织构金属）", "LIPSS、纳米柱阵列、DLIP 图案",
   "抗黏附（接触面积与表面能效应）；高纵横比结构的机械杀菌作用",
   "效应强度随菌株与介质变化；大面积加工通量"],
  ["混合路线", "激光织构叠加抗菌涂层（如 LIPSS 上的聚多巴胺–壳聚糖–银）",
   "机械–化学联合作用", "工艺步骤更多；两个组分都需验证"]],
 [3.6, 4.0, 4.8, 4.6])

TABLE2 = ("金属超快激光织构的加工区间及所得形貌（依据 Bonse et al., 2017; Vorobyev and Guo, "
          "2013; Ivanova et al., 2013; Schwibbert et al., 2024）。",
 ["加工区间", "所得形貌", "特征尺度", "说明"],
 [["注量接近阈值；累积剂量低", "初生沟脊；表面改性",
   "沟脊萌生", "有效阈值随脉冲数下降（孵化效应）"],
  ["略高于阈值；中等剂量（每点约 10²–10³ 脉冲）", "LIPSS（LSFL-I）",
   "周期 ≈ 0.7–0.9 λ；起伏数十至数百纳米",
   "取向垂直于偏振；准周期；经扫描拼铺成面"],
  ["远高于阈值；高搭接与/或多遍扫描", "纳米柱与锥（“黑金属”）",
   "亚微米间距；高纵横比", "多尺度粗糙度陷光；熔体再沉积显著"],
  ["干涉法（DLIP；两束或多束相干光）", "周期线或网格图案",
   "周期 = λ / (2 sin θ)", "周期由光束夹角设定；需干涉光路，图案场有限"]],
 [4.3, 3.5, 4.6, 4.6])

TABLE3 = ("常见固态超快激光家族的离散波长集合。每个谐波档位都是一套独立硬件配置；"
          "括号中为额外的谐波步进；周期为示意值（Λ ≈ 0.75 λ），金属上的实验区间约为 0.7–0.9 λ。",
 ["激光家族", "基频（nm）", "离散谐波（nm）", "示意 LIPSS 周期（Λ ≈ 0.75 λ）"],
 [["Nd:YAG / Nd:YVO_{4}（ps）", "1064", "532, 355（266）", "≈800 / ≈400 / ≈270 nm"],
  ["Yb 系（fs–ps）", "1030", "515, 343（257）", "≈770 / ≈385 / ≈260 nm"],
  ["钛宝石（fs）", "≈800", "400（267）", "≈600 / ≈300 / ≈200 nm"]],
 [4.2, 2.6, 4.4, 5.8], (1, 2, 3))

TABLE4 = ("第 4 节讨论的抗菌机理及其关键条件与注意事项。",
 ["机理", "关键条件", "已报道证据", "注意事项"],
 [["抗黏附（形貌）",
   "特征远小于细胞尺寸；表面能不利于附着",
   "亚微米织构减少滞留（钛、钢、聚合物）",
   "接近细胞尺寸时反转；依赖菌株与介质"],
  ["机械杀菌作用", "高纵横比；间距在膜拉伸极限内",
   "蝉翼；黑硅；纳米柱对金黄色葡萄球菌",
   "对浅 LIPSS 作用小；依赖物种；孢子基本不受影响"],
  ["表面化学", "激光诱导的氧化物与电荷状态异于天然表面",
   "光活性二氧化钛；激光氧化钢表面",
   "次于形貌；需要表面分析"],
  ["蛋白条件膜叠加", "蛋白吸附先于细菌到达（Vroman 序列）",
   "介质依赖的黏附与活力结果漂移",
   "在生物介质中可覆盖裸表面行为"]],
 [3.6, 4.4, 4.6, 4.4])

FIG1_CAP = ("图 1.  金属超快激光织构的示意工艺图谱：峰值注量（相对单脉冲烧蚀阈值）对"
            "累积脉冲数（每点），标出主要工艺区间——无明显改性、LIPSS、强烧蚀/熔体回凝"
            "与纳米柱–锥形成——以及孵化效应引起的有效阈值下移。")
FIG2_CAP = ("图 2.  LIPSS 的形成物理：(a) 入射光在表面粗糙度处耦合为表面电磁波（SPP）；"
            "(b) 入射光与表面波的干涉产生周期为 Λ 的近场能量分布；(c) 材料响应把能量"
            "图案转化为 Λ ≈ 0.7–0.9 λ 的准周期沟脊，取向垂直于电场 E；(d) 正反馈"
            "——逐渐长成的光栅把更多光耦合回表面波。")
FIG3_CAP = ("图 3.  织构金属表面的抗菌机理：(a) 几何抗黏附（特征尺度限制接触点）；"
            "(b) 高纵横比柱上的机械杀菌膜破裂；(c) 表面化学贡献（激光诱导氧化层与"
            "电荷状态）；(d) 蛋白条件膜——蛋白质先行吸附（Vroman 序列），向到达的"
            "细菌呈现新界面。")

FIG4_CAP = ("图 4.  奥氏体不锈钢、515 nm 的示意性预测计算。(a) 用室温光学常数计算的 Sipe "
            "效率因子图（正入射，s 偏振）：极值位于 κ ≈ 1.02，对应预测周期 ≈504 nm（0.98 λ）。"
            "(b) 预测周期随假定表面介电常数实部的变化（虚部随序列缩放）：316L 上报道的实测 "
            "周期 385 nm（0.75 λ；Wang et al., 2026）对应约 −2.3 的有效介电常数——即光学上被 "
            "改性过的表面状态，而非原始合金。")

# ---------------------------------------------------------------- assemble docx
def build_docx_full():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.0)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    st = doc.styles['Normal']; st.font.name = 'Calibri'; st.font.size = Pt(10.5)
    h1 = doc.styles['Heading 1']
    h1.font.name = 'Calibri'; h1.font.size = Pt(14); h1.font.bold = True; h1.font.color.rgb = NAVY
    h1.paragraph_format.space_before = Pt(14); h1.paragraph_format.space_after = Pt(4)
    h1.paragraph_format.keep_with_next = True
    h2 = doc.styles['Heading 2']
    h2.font.name = 'Calibri'; h2.font.size = Pt(11.5); h2.font.bold = True; h2.font.color.rgb = NAVY
    h2.paragraph_format.space_before = Pt(10); h2.paragraph_format.space_after = Pt(3)
    h2.paragraph_format.keep_with_next = True
    for s in (st, h1, h2):
        set_ea(s)

    tp = doc.add_paragraph(); tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = tp.add_run(TITLE); r.bold = True; r.font.size = Pt(17); r.font.color.rgb = NAVY
    tp.paragraph_format.space_after = Pt(2)
    sp = doc.add_paragraph(); sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sp.add_run(SUBTITLE); r.italic = True; r.font.size = Pt(11); r.font.color.rgb = GRAY
    sp.paragraph_format.space_after = Pt(2)
    mp = doc.add_paragraph(); mp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = mp.add_run(META); r.font.size = Pt(9); r.font.color.rgb = GRAY
    mp.paragraph_format.space_after = Pt(4)
    hrule(doc)
    heading(doc, "摘要", 1)
    for para in ABSTRACT:
        body_para(doc, para, space_after=6)
    kp = doc.add_paragraph()
    rich(kp, KEYWORDS, size=Pt(10), color=GRAY, italic_all=True)
    kp.paragraph_format.space_after = Pt(8)

    def emit(blocks):
        for blk in blocks:
            kind = blk[0]
            if kind == 'h1':
                heading(doc, blk[1], 1)
            elif kind == 'h2':
                heading(doc, blk[1], 2)
            elif kind == 'p':
                body_para(doc, blk[1])
            elif kind == 'bul':
                p = doc.add_paragraph(style='List Bullet')
                rich(p, blk[1]); p.paragraph_format.space_after = Pt(4)
                p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            elif kind == 'eq':
                add_eq(doc, blk[1])
            elif kind == 'fig':
                add_figure_block(doc, blk[1], blk[2])
            elif kind == 'table':
                num = blk[1]
                if num == 1:
                    t = TABLE1
                elif num == 2:
                    t = TABLE2
                elif num == 3:
                    t = TABLE3
                else:
                    t = TABLE4
                add_table_block(doc, num, t[0], t[1], t[2], t[3], t[4] if len(t) > 4 else ())

    emit(S1[:3])
    emit(S1[3:4])
    emit([S1[4]])
    add_table_block(doc, 1, TABLE1[0], TABLE1[1], TABLE1[2], TABLE1[3])
    emit(S1[5:])

    i23p = next(i for i, b in enumerate(S2) if b[0] == 'h2' and b[1].startswith('2.3'))
    emit(S2[:i23p])
    emit([('fig', 'fig1_process_map_zh.png', FIG1_CAP)])
    emit(S2[i23p:i23p + 2])
    add_table_block(doc, 2, TABLE2[0], TABLE2[1], TABLE2[2], TABLE2[3])
    emit(S2[i23p + 2:])

    i34 = next(i for i, b in enumerate(S3) if b[0] == 'h2' and b[1].startswith('3.4'))
    i38 = next(i for i, b in enumerate(S3) if b[0] == 'h2' and b[1].startswith('3.8'))
    emit(S3[:i34])
    emit([('fig', 'fig2_lipss_mechanism_zh.png', FIG2_CAP)])
    emit(S3[i34:i38])
    emit([('fig', 'fig4_predictive_models_zh.png', FIG4_CAP)])
    emit(S3[i38:])
    emit(S4)
    emit([('fig', 'fig3_antibacterial_zh.png', FIG3_CAP)])
    add_table_block(doc, 3, TABLE4[0], TABLE4[1], TABLE4[2], TABLE4[3])
    emit(S5[:3])
    add_table_block(doc, 4, TABLE3[0], TABLE3[1], TABLE3[2], TABLE3[3], TABLE3[4])
    emit(S5[3:])
    emit(S6)

    heading(doc, "参考文献", 1)
    for ref in REFERENCES:
        p = doc.add_paragraph()
        rich(p, ref, size=Pt(9.5))
        pf = p.paragraph_format
        pf.left_indent = Cm(0.75); pf.first_line_indent = Cm(-0.75)
        pf.space_after = Pt(3)
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT

    add_footer(doc, "激光织构金属抗菌综述 — 中文初稿")
    doc.core_properties.title = TITLE
    doc.core_properties.comments = "中文版初稿 v3 — 2026-10-07（双语、含图）"
    doc.save(DOCX_PATH)
    return doc


# ---------------------------------------------------------------- markdown builder
def _mds(s):
    s = re.sub(r'\^\{([^}]*)\}', r'^\1', s)
    s = re.sub(r'_\{([^}]*)\}', r'_\1', s)
    return s


def build_md():
    L = []
    L += [f"# {TITLE}", "", f"*{SUBTITLE}*", "", f"*{META}*", "", "---", ""]
    L += ["## 摘要", ""]
    for para in ABSTRACT:
        L += [para, ""]
    L += [f"*{KEYWORDS}*", ""]

    def emit_md(blocks):
        for blk in blocks:
            k = blk[0]
            if k == 'h1':
                L.append(f"## {blk[1]}")
            elif k == 'h2':
                L.append(f"### {blk[1]}")
            elif k == 'p':
                L.append(_mds(blk[1]))
            elif k == 'bul':
                L.append("- " + _mds(blk[1]))
            elif k == 'eq':
                L.append(f"> {blk[2]}")
            elif k == 'fig':
                L.append(f"![{blk[1]}](figures/{blk[1]})")
                L.append(f"*{blk[2]}*")
            elif k == 'table':
                num = blk[1]
                t = {1: TABLE1, 2: TABLE2, 3: TABLE4, 4: TABLE3}[num]
                L.append(f"**表 {num}.** {t[0]}")
                L.append("")
                hdr, rows = t[1], t[2]
                L.append("| " + " | ".join(_mds(h) for h in hdr) + " |")
                L.append("|" + "---|" * len(hdr))
                for r in rows:
                    L.append("| " + " | ".join(_mds(c) for c in r) + " |")
            L.append("")

    emit_md(S1[:3]); emit_md(S1[3:4]); emit_md([S1[4]])
    emit_md([('table', 1)])
    emit_md(S1[5:])
    i23p = next(i for i, b in enumerate(S2) if b[0] == 'h2' and b[1].startswith('2.3'))
    emit_md(S2[:i23p])
    emit_md([('fig', 'fig1_process_map_zh.png', FIG1_CAP)])
    emit_md(S2[i23p:i23p + 2])
    emit_md([('table', 2)])
    emit_md(S2[i23p + 2:])
    i34 = next(i for i, b in enumerate(S3) if b[0] == 'h2' and b[1].startswith('3.4'))
    i38 = next(i for i, b in enumerate(S3) if b[0] == 'h2' and b[1].startswith('3.8'))
    emit_md(S3[:i34])
    emit_md([('fig', 'fig2_lipss_mechanism_zh.png', FIG2_CAP)])
    emit_md(S3[i34:i38])
    emit_md([('fig', 'fig4_predictive_models_zh.png', FIG4_CAP)])
    emit_md(S3[i38:])
    emit_md(S4)
    emit_md([('fig', 'fig3_antibacterial_zh.png', FIG3_CAP)])
    emit_md([('table', 3)])
    emit_md(S5[:3])
    emit_md([('table', 4)])
    emit_md(S5[3:])
    emit_md(S6)
    L += ["## 参考文献", ""]
    for ref in REFERENCES:
        L.append(f"- {ref}")
        L.append("")

    with open(MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(L) + "\n")
    print("MD  :", MD_PATH)


# ---------------------------------------------------------------- main + self-check
def main():
    build_docx_full()
    build_md()
    d = Document(DOCX_PATH)
    ntab = len(d.tables)
    nmath = len(d.element.body.findall('.//' + qn('m:oMath')))
    raw = "\n".join(t.text or '' for t in d.element.body.iter(qn('w:t')))
    stray = {k: raw.count(k) for k in ('^{', '_{', '**') if k in raw}
    banned = [w for w in ('建议', '下一步', '未来工作', '读者应', 'should', 'recommend')
              if w in raw.lower()]
    maths = ["".join(t.text or '' for t in m.findall('.//' + qn('m:t')))
             for m in d.element.body.findall('.//' + qn('m:oMath'))]
    nH1 = sum(1 for p in d.paragraphs if p.style.name == 'Heading 1')
    nH2 = sum(1 for p in d.paragraphs if p.style.name == 'Heading 2')
    nfig = len(d.inline_shapes)
    print("DOCX:", DOCX_PATH)
    print("tables:", ntab, "| figures:", nfig, "| oMath:", nmath, "| H1:", nH1, "| H2:", nH2,
          "| refs:", len(REFERENCES))
    print("stray markers:", stray or "none")
    print("banned words:", banned or "none")
    print("math:", maths)
    print("paras:", len(d.paragraphs))


if __name__ == "__main__":
    main()
