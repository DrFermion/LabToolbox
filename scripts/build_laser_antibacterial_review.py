# -*- coding: utf-8 -*-
"""Build the draft review: 'Laser-Textured Metal Surfaces for Antibacterial Applications'.
Outputs: DOCX (A4, Calibri 10.5, navy headings, three-line tables, OMML equations, page footer)
         + Markdown source.  Content lives in the B[] block list below.

Usage:  python build_laser_antibacterial_review.py [output_dir]
         (default: scratch build dir; pass the archive folder to rebuild in place)

Built 2026-10-07 (draft v1).  Requires python-docx.  Word rendering check done separately.
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
STEM = "Laser-Textured_Antibacterial_Surfaces_review_20261007"
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
    # header underline
    for cell in tbl.rows[0].cells:
        tcPr = cell._tc.get_or_add_tcPr()
        tcb = OxmlElement('w:tcBorders')
        b = OxmlElement('w:bottom')
        b.set(qn('w:val'), 'single'); b.set(qn('w:sz'), '6'); b.set(qn('w:space'), '0'); b.set(qn('w:color'), '000000')
        tcb.append(b)
        tcPr.insert_element_before(tcb, 'w:shd', 'w:noWrap', 'w:tcMar', 'w:textDirection', 'w:vAlign', 'w:hideMark')

def add_table_block(doc, num, cap, headers, rows, widths, center_cols=()):
    cp = doc.add_paragraph()
    rich(cp, f"**Table {num}.**  {cap}", size=Pt(9.5))
    cp.paragraph_format.space_after = Pt(3)
    cp.paragraph_format.keep_with_next = True
    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tbl.autofit = False
    # fixed total width
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
    r1 = p.add_run(short + '\t')
    r2 = p.add_run('Page ')
    f1 = OxmlElement('w:fldSimple'); f1.set(qn('w:instr'), r' PAGE ')
    fr = OxmlElement('w:r'); ft = OxmlElement('w:t'); ft.text = '1'; fr.append(ft); f1.append(fr)
    p._p.append(f1)
    r3 = p.add_run(' of ')
    f2 = OxmlElement('w:fldSimple'); f2.set(qn('w:instr'), r' NUMPAGES ')
    fr2 = OxmlElement('w:r'); ft2 = OxmlElement('w:t'); ft2.text = '1'; fr2.append(ft2); f2.append(fr2)
    p._p.append(f2)
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

# ---------------------------------------------------------------- content
TITLE = "Laser-Textured Metal Surfaces for Antibacterial Applications: A Review"
SUBTITLE = "Fabrication, LIPSS formation physics, antibacterial mechanisms, and process engineering"
META = "Draft — 7 October 2026"

ABSTRACT = [
 "Healthcare-associated infections and device-associated biofilms remain a persistent clinical and "
 "economic burden, motivating surface technologies that do not depend on antibiotic release. Direct "
 "laser texturing of metal surfaces — most prominently of stainless steels — has emerged as a "
 "coating-free strategy in which the antibacterial function is built into the material itself. This "
 "review brings together four aspects of the field. First, it summarises how textured metal surfaces "
 "are fabricated with ultrafast lasers: coupon preparation, laser parameter windows and the two "
 "principal classes of surface morphology — laser-induced periodic surface structures (LIPSS) and "
 "nanopillar/cone arrays. Second, it explains the formation physics of LIPSS, in which the incident "
 "beam interferes with surface electromagnetic waves excited on the metal, so that the structure "
 "period is governed by the laser wavelength (typically 0.7–0.9 λ) while the ripple orientation "
 "follows the beam polarisation. Third, it surveys the antibacterial mechanisms reported for textured "
 "metals — topography-driven anti-adhesion, mechano-bactericidal membrane rupture on high-aspect-ratio "
 "nanostructures, surface-chemistry effects and conditioning-film interactions — and analyses why "
 "published outcomes differ so widely across studies. Finally, it discusses the process-engineering "
 "consequences: laser wavelength is a discrete hardware property (a fundamental frequency with "
 "harmonic steps) rather than a continuously tunable parameter, so the attainable LIPSS period is, "
 "in practice, quantised; alternative approaches such as direct laser interference patterning "
 "decouple the period from the wavelength. The review closes with the open questions and "
 "standardisation needs that currently shape the field.",
]
KEYWORDS = ("Keywords: laser surface texturing; laser-induced periodic surface structures; "
            "antibacterial surfaces; bacterial adhesion; mechano-bactericidal surfaces; stainless steel")

S1 = [
 ("h1", "1. Introduction"),
 ("h2", "1.1. The clinical problem: device-associated infections and biofilms"),
 ("p", "Device-associated infections — those arising from catheters, joint prostheses, dental implants "
       "and other indwelling hardware — are among the most consequential healthcare-associated "
       "infections. In the United States alone, healthcare-associated infections have been estimated "
       "to affect millions of patients annually, with an economic burden in the tens of billions of "
       "dollars (Klevens et al., 2007; Stone, 2009). The central pathological event is biofilm "
       "formation on the device surface: planktonic bacteria adhere, proliferate into microcolonies, "
       "and embed themselves in a self-produced matrix of extracellular polymeric substances "
       "(Flemming et al., 2016). The biofilm lifestyle protects the community against antibiotics, "
       "disinfectants and host immune defences — through restricted diffusion, metabolic dormancy "
       "and persister-cell formation (Hall and Mah, 2017) — so biofilm-associated implant infections "
       "are persistent and frequently require surgical revision (Zimmerli and Sendi, 2017; Arciola "
       "et al., 2018; VanEpps and Younger, 2016). Because the process begins with adhesion, surfaces "
       "that prevent bacteria from establishing a foothold — or that kill cells on contact — "
       "interrupt the infection cascade before a biofilm matures. On an implant, bacteria and host "
       "tissue cells compete for the same interface in what has been termed “the race for the "
       "surface” (Subbiahdoss et al., 2009), which makes the earliest cell–material interactions "
       "decisive."),
 ("h2", "1.2. Antibacterial surface strategies and the place of laser texturing"),
 ("p", "Strategies for antibacterial surfaces fall into several broad families (Table 1). "
       "Antimicrobial-releasing coatings load the surface — or a polymer reservoir — with biocides "
       "such as silver nanoparticles, antibiotics or chlorhexidine, which are gradually released and "
       "act on planktonic and early-adherent bacteria; their generic drawbacks are finite loading, "
       "limited control of release kinetics and, for antibiotics, resistance pressure (Cloutier "
       "et al., 2015; Wei et al., 2019). Contact-killing coatings — typically based on immobilised "
       "quaternary ammonium compounds, antimicrobial peptides or enzymes — disrupt bacterial "
       "membranes on contact; their durability and continued accessibility determine performance "
       "over device lifetimes (Siedenbiedel and Tiller, 2012). Anti-fouling strategies, such as "
       "poly(ethylene glycol) brushes and zwitterionic polymer layers, work differently again: they "
       "make the interface energetically unfavourable for protein and cell attachment (Magin "
       "et al., 2010). A fourth family — the subject of this review — is topographical: structuring "
       "the material itself at the micro- and nanoscale. Because such surfaces carry their function "
       "inside the substrate rather than in a coating, they add no leachable compounds, are "
       "insensitive to coating delamination, and can be produced in a single automated processing "
       "step (Hasan et al., 2013; Vorobyev and Guo, 2013; Lutey et al., 2018). Hybrid approaches "
       "combine the two philosophies, for example by applying a polydopamine–chitosan–silver "
       "nanocomposite on top of a laser-textured surface (Wang et al., 2025; Wei et al., 2019)."),
 ("p", "Laser texturing is particularly attractive on metals such as 316L stainless steel, titanium "
       "and their alloys, which are ubiquitous in implants and surgical instruments. With ultrashort "
       "laser pulses, two characteristic morphologies are produced: laser-induced periodic surface "
       "structures (LIPSS) — quasi-periodic ripples with a period just below the laser wavelength — "
       "and nanopillar or cone arrays, sometimes described as “black metals” because their multiscale "
       "roughness traps light (Vorobyev and Guo, 2013; Bonse et al., 2017). Both classes have been "
       "tested against bacteria, with outcomes that vary across strains, media and texture geometries "
       "(Schwibbert et al., 2024)."),
 ("h2", "1.3. Scope of this review"),
 ("p", "This review synthesises four strands: (i) fabrication of laser-textured metal surfaces; "
       "(ii) the physics of LIPSS formation; (iii) antibacterial mechanisms and the reasons why the "
       "literature diverges; and (iv) process engineering, including wavelength availability and its "
       "consequences for structure periods. The emphasis is on stainless steel and on the practical "
       "level of detail involved in planning, performing and reporting experiments."),
]

S2 = [
 ("h1", "2. Fabrication of laser-textured metal surfaces"),
 ("h2", "2.1. Substrate preparation and sample design"),
 ("p", "Most studies texture austenitic stainless steel, typically grade 316L, the standard alloy "
       "for medical devices and food-processing equipment; titanium and its alloys are also widely "
       "used (Hasan et al., 2013; Cunha et al., 2016; Wang et al., 2026). Coupons are first "
       "mechanically polished — commonly to a mirror finish with successive abrasive media — and "
       "cleaned in an ultrasonic bath (acetone, isopropanol, deionised water), then dried in a "
       "nitrogen stream. Reproducible initial topography matters: the first laser pulses interact "
       "with polishing marks and other irregularities, which seed the periodic structures and "
       "influence their uniformity. A practical design that reduces coupon-to-coupon variance is to "
       "treat multiple zones on a single coupon — for example one zone of structure A, one zone of "
       "structure B and an untreated control area — so that all comparisons share the same substrate, "
       "batch and ageing history. One caveat of this scheme: ablated zones sit a few micrometres "
       "below the original surface, a step that factors into mechanical and imaging analyses such as "
       "edge effects in flow experiments or atomic force microscopy (Wang et al., 2026)."),
 ("h2", "2.2. Laser-processing principles: from single pulses to a surface texture"),
 ("p", "Texturing is performed with pulsed lasers in the femtosecond-to-picosecond range, "
       "occasionally nanoseconds. The rationale for ultrashort pulses is energy localisation: the "
       "pulse deposits its energy in the electron system before significant heat diffusion occurs, "
       "so melting and collateral thermal damage are reduced and structures are finer and cleaner "
       "than with nanosecond pulses (Bonse et al., 2012; Vorobyev and Guo, 2013). The experimental "
       "variables are the wavelength λ, pulse duration τ, repetition rate f, pulse energy (converted "
       "to fluence F, energy per unit area, J cm⁻²), spot diameter d, scanning speed v, hatch "
       "distance (line spacing) and number of passes. The outcome is controlled mainly by how the "
       "applied fluence compares with the material's ablation threshold and by the number of pulses "
       "accumulated at each point. For a single scan line the accumulated pulse number is "
       "approximately N ≈ f·d/v; with multiple passes and hatch overlap, the dose per unit area is "
       "correspondingly higher. Two regimes matter for texture formation: near-threshold irradiation "
       "with sufficient pulse accumulation produces LIPSS (Section 3), while irradiation well above "
       "threshold with high overlap removes material aggressively and sculpts pillar-and-cone "
       "morphology (Section 2.3). Pulse accumulation is effective because of incubation: repeated "
       "irradiation lowers the effective threshold through gradual defect generation and roughening "
       "(Bonse et al., 2017). The processing atmosphere is a further variable: in air, ablated "
       "material re-deposits and oxidises, while inert or reactive atmospheres modify both chemistry "
       "and morphology (Vorobyev and Guo, 2013). Figure 1 places these regimes in a single process "
       "map."),
 ("h2", "2.3. The structure library: LIPSS, nanopillars and interference patterns"),
 ("p", "Table 2 organises the processing windows and the morphologies they produce. LIPSS form at "
       "fluences close to the ablation threshold and grow over many pulses; on steels they appear as "
       "quasi-periodic ripples with spatial period ≈ 0.7–0.9 λ and relief from tens to a few hundred "
       "nanometres (Bonse et al., 2012; Bonse et al., 2017). Nanopillars and cones form when the "
       "accumulated dose far exceeds the threshold; the morphology develops through strong ablation, "
       "melt flow and re-solidification, often in a two-stage sequence that begins from LIPSS-like "
       "ripples. Because the resulting multiscale texture traps light across the visible range, such "
       "surfaces are known as “black metals”; on silicon processed in reactive atmospheres such as "
       "SF₆, the analogous result is “black silicon”, the interface class used in the classic "
       "mechano-bactericidal studies (Vorobyev and Guo, 2013; Ivanova et al., 2013). A third route "
       "does not rely on self-organisation: direct laser interference patterning (DLIP) overlaps two "
       "or more coherent beams so that the intensity profile is already periodic before it reaches "
       "the sample, and the period is set by the interference angle rather than by the material "
       "response (Peter et al., 2020; Schwibbert et al., 2024). DLIP is discussed further in "
       "Section 5.2."),
 ("h2", "2.4. Verification and characterisation pipeline"),
 ("p", "After processing, coupons are typically cleaned again — for instance by sonication in "
       "solvents — to remove debris. Surface verification uses scanning electron microscopy (SEM) "
       "for morphology, with the spatial period conveniently extracted by two-dimensional Fourier "
       "analysis of the images; atomic force microscopy (AFM) for roughness and relief; and "
       "contact-angle measurements for wetting. Where surface chemistry matters, energy-dispersive "
       "X-ray spectroscopy or X-ray photoelectron spectroscopy complements the morphological "
       "picture (Sections 4.4–4.5). Recording all laser parameters alongside the coupon identity is "
       "standard practice and underpins comparability, because the same nominal morphology can be "
       "produced by different parameter combinations with different subsurface damage and surface "
       "chemistry (Engoor et al., 2025)."),
]

S3 = [
 ("h1", "3. Formation physics of laser-induced periodic surface structures"),
 ("h2", "3.1. The interference picture: light writing its own grating"),
 ("p", "The existence of LIPSS is, at first sight, paradoxical: a single laser beam with a smooth "
       "intensity profile writes a periodic pattern, yet no mask or template imposes any "
       "periodicity. The resolution came in the 1970s, when Emmony and co-workers observed periodic "
       "damage on germanium mirrors and attributed it to interference between the incident wave and "
       "a surface-scattered wave (Emmony et al., 1973). The picture was formalised by Sipe and "
       "co-workers, whose theory treats the inhomogeneous energy deposition produced by the "
       "interference of the incident light with the field scattered by surface roughness (Sipe "
       "et al., 1983). In essence, the surface supplies its own second beam: the ripple spacing "
       "follows from the light wavelength, and the pattern appears only because the two waves "
       "interfere. This single idea — the pattern is written by light, not imposed by mechanics — "
       "is the key to everything that follows."),
 ("h2", "3.2. Surface electromagnetic waves and the origin of the period"),
 ("p", "The “second beam” is a surface electromagnetic wave. On a metal, light can couple to "
       "surface plasmon polaritons (SPPs): hybrid light–electron-density oscillations bound to the "
       "metal–dielectric interface, whose fields decay exponentially away from the interface over "
       "tens of nanometres on the metal side. Such waves exist when the metal's real permittivity "
       "ε_{m} is negative — the case for metals from the visible to the mid-infrared — and their "
       "wavelength is shorter than that of the driving light:"),
 ("eq", EQ1, EQ1_TXT),
 ("p", "where λ_{0} is the laser wavelength, ε_{d} the permittivity of the adjacent dielectric "
       "(air: ε_{d} = 1). For typical metal permittivities, λ_{sp}/λ_{0} takes values near 0.95 "
       "(ε_{m} ≈ −10), 0.89 (ε_{m} ≈ −5), 0.82 (ε_{m} ≈ −3) and 0.75 (ε_{m} ≈ −2.3). Because the "
       "observed ripple period is closely related to this surface-wave wavelength, the familiar "
       "experimental result follows naturally: LIPSS periods on metals fall within roughly "
       "0.7–0.9 of the laser wavelength. As the effective optical constants evolve during "
       "processing — oxidation, melting and defect accumulation reduce the magnitude of ε_{m} — "
       "the selected period can drift downward during formation itself (Huang et al., 2009; Bonse "
       "et al., 2017)."),
 ("h2", "3.3. Momentum matching and self-reinforcing feedback"),
 ("p", "There is one more condition for the coupling: momentum. A perfectly smooth metal cannot "
       "absorb light directly into an SPP, because the photon momentum in air is smaller than the "
       "SPP momentum — the two dispersion curves never cross. Something has to supply the missing "
       "momentum, and surface roughness does exactly that: a rough surface scatters light, and the "
       "scattered wave acquires the extra momentum needed to couple into a surface wave. This has a "
       "characteristic consequence — the process bootstraps itself. The first few pulses roughen a "
       "polished surface and excite weak surface waves; the resulting interference deposits energy "
       "with a preferred period; the periodic modification deepens into a grating; the grating "
       "couples incident light into surface waves even more efficiently; and the pattern sharpens. "
       "This positive feedback is why LIPSS emerge as self-organised, quasi-regular structures "
       "whose orientation and period are selected by the light field, and why they sharpen with "
       "increasing pulse number (Sipe et al., 1983; Huang et al., 2009; Bonse et al., 2017). The "
       "sequence is summarised in Figure 2."),
 ("h2", "3.4. Wavelength scaling, quasi-periodicity and period control"),
 ("p", "Two practical rules follow from the physics. First, wavelength scaling: because the period "
       "tracks the surface-wave wavelength, changing the laser wavelength scales the period "
       "approximately linearly — the most robust handle on structure size. As an arithmetic "
       "illustration, a ratio of ≈0.75–0.85 λ implies periods of ≈770–880 nm at 1030 nm, "
       "≈385–440 nm at 515 nm and ≈255–290 nm at 343 nm. Experimentally, ratios for metals "
       "typically fall in the range 0.7–0.9 λ (Bonse et al., 2017). Second, quasi-periodicity: in "
       "practice LIPSS are not perfectly periodic. The selection mechanism favours a band of "
       "wavevectors, and material inhomogeneity — grains, oxides, defect density — broadens the "
       "distribution, so measured periods carry a spread of a few per cent, and “quasi-periodic” "
       "is the accurate description (Bonse et al., 2017). For oblique incidence, the in-plane "
       "geometry shifts the selected period approximately as"),
 ("eq", EQ3, EQ3_TXT),
 ("p", "with θ the incidence angle; this effect supports modest continuous tuning of the period "
       "within a single wavelength (Bonse et al., 2017)."),
 ("h2", "3.5. Orientation rule and classification"),
 ("p", "The direction of the ripples is the most direct experimental fingerprint of the mechanism: "
       "for the standard type on metals (LSFL-I), the ripples run perpendicular to the "
       "polarisation of the laser field, and rotating the polarisation by 90° rotates the pattern "
       "by 90°. Circularly polarised light, which has no fixed in-plane field direction, suppresses "
       "ripple formation — a control experiment that directly tests the electromagnetic origin of "
       "the pattern (Bonse et al., 2017; Engoor et al., 2025). By period and orientation, LIPSS "
       "are classified into three types: LSFL-I (low-spatial-frequency LIPSS), with period "
       "≈ 0.7–1 λ and orientation perpendicular to the polarisation, characteristic of metals; "
       "LSFL-II, with period ≈ λ/n (n an effective index) and orientation parallel to the "
       "polarisation, found on strongly absorbing dielectrics and oxidised surfaces; and HSFL "
       "(high-spatial-frequency LIPSS), with period < λ/2, whose origin remains debated and which "
       "often forms at low fluence (Bonse et al., 2017). Under this classification, ripples with "
       "period ≈ 0.75 λ on stainless steel at 515 nm are unambiguously LSFL-I."),
 ("h2", "3.6. From the light pattern to the material pattern"),
 ("p", "The optical pattern is then converted into a physical texture. Energy absorbed in the "
       "interference maxima heats the surface and, depending on the local dose, the material "
       "melts, flows and partially vaporises. In the widely accepted picture, troughs experience "
       "the strongest ablation while ridges consist of material that was not removed, together "
       "with melt that re-solidified and — in air — with oxides and redeposited nanoparticles "
       "(Vorobyev and Guo, 2013; Bonse et al., 2017). With repeated pulses the morphology "
       "accumulates: shallow initial ripples deepen through the feedback described above, until "
       "ablation removes the pattern faster than it renews it; and because each pulse lowers the "
       "effective threshold (incubation), the process window shifts during processing and is "
       "managed through scanning strategy and atmosphere control (Bonse et al., 2017). The compact "
       "summary: the pattern is written by light while the structure is built by matter."),
 ("h2", "3.7. Operating conditions and open questions"),
 ("p", "In practice, LIPSS are produced with fluences at or slightly above the single-pulse "
       "threshold, with sufficient pulses accumulated (dozens to hundreds per point) and stable "
       "scanning; femtosecond-to-picosecond pulses favour clean ripples, and the processing "
       "atmosphere and surface chemistry modulate both period and depth (Bonse et al., 2012; Bonse "
       "et al., 2017). Although the interference-based picture is the field's consensus framework — "
       "it explains the two robust signatures, the wavelength-scale period and the "
       "polarisation-locked orientation — quantitative prediction of the final pattern remains "
       "incomplete: the early-pulse dynamics, the role of oxides and effective optical constants, "
       "and the mechanism of high-spatial-frequency ripples all remain under active study. The "
       "literature describes LIPSS formation as “a scientific evergreen” precisely because the "
       "subject continues to grow (Bonse et al., 2017)."),
]

S4 = [
 ("h1", "4. Antibacterial mechanisms of textured metal surfaces"),
 ("h2", "4.1. Anti-adhesion and topography"),
 ("p", "The best-documented antibacterial effect of laser-textured metals is reduced adhesion — "
       "fewer bacteria retained on the surface than on a polished control. The working explanation "
       "is geometric: bacteria are typically 0.5–2 µm in size, and features much smaller than a "
       "cell reduce the accessible contact area, lowering the adhesion energy relative to a flat "
       "surface (attachment-point theory); quantitative cell–texture interaction models reproduce "
       "this picture (Hasan et al., 2013; Lazzini et al., 2019). Experimentally, "
       "femtosecond-textured surfaces reduce the retention of *Staphylococcus aureus* on titanium "
       "(Cunha et al., 2016), nanoscale ripples suppress biofilm growth on steel (Epperlein "
       "et al., 2017), and on 316L stainless steel both adhesion and early biofilm formation "
       "respond to the LIPSS geometry (Romoli et al., 2020; Capella et al., 2024). Significant "
       "subtleties apply. The effect depends on structure size: when the period or spacing "
       "approaches the cell dimension, cells can settle between features and retention can "
       "increase — a crossover reproduced on stainless steel, where LIPSS of different periodicity "
       "and depth modulate *E. coli* adhesion in opposite directions (Outón et al., 2024), and on "
       "polymer surfaces, where ripple spacing determines whether *E. coli* is repelled (Richter "
       "et al., 2021). It also depends on strain: rod-shaped and spherical bacteria experience the "
       "same texture differently, and systematic comparisons report opposite preferences between "
       "species on nanotextured steel (Epperlein et al., 2017; Schwibbert et al., 2024). Recent "
       "work on 316L shows that the texture geometry governs adhesion and corrosion performance "
       "together, with the laser-induced oxidation state contributing to both (Wang et al., 2026; "
       "Engoor et al., 2025). A practical rule of thumb that has emerged: feature sizes well below "
       "the bacterial size (about half the cell dimension or less) favour anti-adhesion, while "
       "features comparable to the cell size promote capture; the strength of any effect remains "
       "system-specific (Schwibbert et al., 2024)."),
 ("h2", "4.2. Wettability and surface energetics"),
 ("p", "The second variable is surface energetics. Texturing changes wettability both "
       "geometrically — roughness amplifies the intrinsic wetting behaviour — and chemically, "
       "because the laser-modified surface layer differs from the bulk. On metals, freshly "
       "textured surfaces often show strongly hydrophilic behaviour that evolves over days to "
       "weeks in ambient air as airborne organic species adsorb onto the surface; contact angles "
       "therefore represent a time-stamped state rather than a permanent property (Kietzig "
       "et al., 2009; Daskalova and Angelova, 2023). Beyond the contact angle itself, the surface "
       "free energy can be decomposed into Lifshitz–van der Waals, acid–base and electrostatic "
       "contributions within the van Oss–Chaudhury–Good framework (van Oss et al., 1988), and the "
       "adhesion potential of a bacterium — or a protein — against the surface follows as a "
       "free-energy-versus-separation profile, the extended DLVO construction applied, for "
       "example, to protein adsorption on solid surfaces (Wang and Zhang Newby, 2014). This "
       "framework provides the quantitative bridge between wetting data and biological outcome; it "
       "also explains why a single contact-angle number is a weak predictor of bacterial response, "
       "and why superhydrophobic states have been associated with reduced retention in some "
       "systems (Fadeeva et al., 2011)."),
 ("h2", "4.3. Mechano-bactericidal action"),
 ("p", "A more direct mechanism has captured much of the field's attention: textures can kill "
       "bacteria mechanically. The discovery that cicada wings rupture *Pseudomonas aeruginosa* "
       "cells — the membrane is stretched between adjacent nanopillars until it fails — established "
       "that purely physical topography can be bactericidal (Ivanova et al., 2012), with the "
       "biophysical mechanism subsequently modelled in terms of membrane adhesion energy between "
       "pillars (Pogodin et al., 2013). The concept was transferred to synthetic substrates when "
       "black silicon was shown to kill both Gram-negative and Gram-positive bacteria (Ivanova "
       "et al., 2013). Subsequent work refined the picture: nanopillar arrays act through localised "
       "cell impedance, penetration events that promote oxidative stress and interference with cell "
       "division, in addition to membrane stretching (Jenkins et al., 2020). The design principles — "
       "pillar spacing and height relative to the membrane's stretch limit — are reviewed in "
       "Linklater et al. (2021). Two caveats matter in the present context. First, "
       "mechano-bactericidal action requires high-aspect-ratio features with spacings matched to "
       "membrane mechanics; on shallow morphologies such as typical LIPSS, where the relief is "
       "only tens of nanometres, the membrane is not stretched to rupture, so for LIPSS the "
       "dominant antibacterial contribution lies in anti-adhesion and surface energetics rather "
       "than mechanical killing (Linklater et al., 2021; Schwibbert et al., 2024). Tall nanopillar "
       "and cone textures are the morphology class where mechanical effects are expected. Second, "
       "killing efficiency is not universal: it is species-dependent, and resistant forms such as "
       "spores are largely unaffected (Linklater et al., 2021)."),
 ("h2", "4.4. Surface-chemistry contributions"),
 ("p", "Laser processing modifies more than geometry. In air, the surface acquires a thin oxide "
       "film whose composition, thickness and defect density reflect the rapid, non-equilibrium "
       "oxidation of the process and differ from the native passive film; these laser-induced "
       "surface layers have been characterised on stainless steel (Wang et al., 2026; Engoor "
       "et al., 2025) and on titanium (Barylyak et al., 2024). Chemical effects can act directly: "
       "femtosecond-textured titanium exhibits photo-induced reactivity that adds to its measured "
       "antibacterial performance (Barylyak et al., 2024). They also complicate interpretation: "
       "when a textured sample outperforms a polished control, part of the difference can originate "
       "from chemistry rather than topography, which is why detailed studies report surface "
       "analysis (X-ray photoelectron spectroscopy, energy-dispersive X-ray spectroscopy) alongside "
       "morphology (Schwibbert et al., 2024)."),
 ("h2", "4.5. Conditioning films in biological environments"),
 ("p", "Real biological environments add a further layer: a conditioning film. When a surface "
       "meets blood, saliva or serum-containing media, proteins arrive within seconds and adsorb "
       "according to their abundance and affinity — the Vroman sequence — forming a film that "
       "presents a new interface to approaching bacteria (Rabe et al., 2011). Proteins carry their "
       "own surface energetics (van Oss, 1990), so the same texture can perform differently in "
       "buffer and in protein-rich media, and antibacterial rankings obtained in simple media do "
       "not always transfer to biological fluids; testing in relevant media precedes any claim of "
       "translation (Schwibbert et al., 2024)."),
 ("h2", "4.6. Why published results diverge"),
 ("p", "Why do published results diverge so widely — some textures reduce adhesion by large "
       "margins, others show no effect or even enhancement? The differences trace to at least six "
       "factors: (i) bacterial strain and physiological state; (ii) the medium and the presence of "
       "a conditioning film; (iii) incubation time and whether the assay measures initial "
       "adhesion, colonisation or mature biofilm; (iv) static versus flow conditions; (v) the "
       "exact feature size, spacing, depth and chemistry of the texture, often under-reported; and "
       "(vi) the evaluation method itself — adhesion counting, colony-forming-unit assays and "
       "live/dead fluorescence stain different quantities, and viability dyes have well-documented "
       "pitfalls that are controlled through careful protocol design (Robertson et al., 2019; "
       "Stiefel et al., 2015). A useful discipline when reading such studies is to separate "
       "anti-adhesion (fewer cells attach) from bactericidal action (attached cells die) and to "
       "anchor each claim to a specific reference surface, usually the polished control of the "
       "same coupon (Lutey et al., 2018; Hasan et al., 2013; Schwibbert et al., 2024). Figure 3 "
       "illustrates the four mechanisms discussed above and Table 3 summarises them with their "
       "key conditions and caveats."),
]

S5 = [
 ("h1", "5. Process engineering and translation considerations"),
 ("h2", "5.1. Wavelength: a discrete hardware property"),
 ("p", "For the design of texture-based studies, the laser wavelength is a decisive variable — "
       "and a frequently misread one, because it is not a dial. Solid-state ultrafast lasers emit "
       "at wavelengths fixed by their gain medium: 1064 nm for the Nd:YAG and Nd:YVO₄ family, "
       "1030 nm for Yb-based systems and ≈800 nm for Ti:sapphire. Other wavelengths are obtained "
       "by harmonic generation — the second and third harmonics give 532 and 355 nm (Nd family), "
       "515 and 343 nm (Yb family) and 400 and 267 nm (Ti:sapphire) — and these are discrete "
       "steps, not a continuum: a 1064 nm system is not continuously tunable to 650 nm, and a "
       "532 nm output cannot be adjusted to 515 nm, because the two originate from different "
       "laser families. A truly tunable source — an optical parametric oscillator or amplifier, "
       "or a dye laser — covers hundreds of nanometres, but such instruments are specialist "
       "devices rarely used for area surface texturing (Bonse et al., 2017). In commercial "
       "practice the discreteness is visible in product lines organised by wavelength: the same "
       "ultrafast platform is offered as separate models per wavelength, with output power "
       "decreasing from infrared to ultraviolet, and harmonic controllers route each wavelength "
       "to its own output (Table 4). Switching wavelength is a hardware-level reconfiguration, "
       "and it carries a second-order cost: absorptivity, focus size and ablation threshold all "
       "change with wavelength, so each new wavelength involves a fresh process-window "
       "development — fluence scans, threshold determination and re-optimised scanning "
       "parameters — before comparable structures can be produced (Bonse et al., 2017). Over a "
       "project, the available wavelengths define a discrete menu, and LIPSS periods inherit that "
       "discreteness."),
 ("h2", "5.2. Period control beyond the wavelength"),
 ("p", "Two consequences for structure design follow. First, period quantisation: because the "
       "LIPSS period scales with the wavelength, the periods accessible at a given processing "
       "condition jump in discrete bands of roughly 0.7–0.9 λ per available wavelength, and "
       "changing the period by more than a few per cent involves changing hardware, not a "
       "parameter. Second, continuous alternatives exist: where an adjustable period is desired, "
       "interference-based direct writing (DLIP) decouples the period from the laser wavelength "
       "through the beam geometry,"),
 ("eq", EQ2, EQ2_TXT),
 ("p", "with θ the half-angle between the interfering beams. DLIP has been applied to stainless "
       "steel with antibacterial motivation (Peter et al., 2020), and its patterns combine readily "
       "with LIPSS-type textures and coatings, at the cost of a more elaborate optical setup and "
       "pattern fields limited by coherence and depth of field (Schwibbert et al., 2024). An "
       "intermediate route keeps a single beam and exploits the oblique-incidence shift of the "
       "selected period described in Section 3.4, which supports modest continuous tuning within "
       "one wavelength (Bonse et al., 2017). By contrast, scanning parameters such as speed and "
       "hatch distance control coverage, depth and uniformity but do not move the period itself "
       "(Bonse et al., 2017)."),
 ("h2", "5.3. Reproducibility and reporting"),
 ("p", "Reproducibility in this field is fragile by default: the process window is narrow "
       "(near-threshold fluences), outcomes depend on the accumulated dose history, and a "
       "texture's biological performance can shift with surface ageing — wetting transitions, "
       "oxide evolution — over days to weeks (Daskalova and Angelova, 2023; Kietzig et al., 2009). "
       "Two practices are well established. Complete parameter reporting — machine model, "
       "wavelength, pulse duration, fluence, repetition rate, spot size, scan speed, hatch, "
       "number of passes, atmosphere — is what makes a texture reproducible and comparable across "
       "laboratories; the absence of a single term, wavelength included, changes the structure "
       "that is produced (Bonse et al., 2017; Schwibbert et al., 2024). And surface state is "
       "recorded with a timestamp: contact angle and surface chemistry are documented alongside "
       "biological testing, with a defined ageing protocol between texturing, characterisation "
       "and assay (Daskalova and Angelova, 2023). The wider field still lacks standardised "
       "antibacterial-testing protocols for textured surfaces — a recognised obstacle to "
       "comparing studies and a precondition for translation (Hasan et al., 2013; Schwibbert "
       "et al., 2024)."),
]

S6 = [
 ("h1", "6. Summary and open questions"),
 ("p", "Texturing metal surfaces with ultrashort laser pulses offers a coating-free route to "
       "antibacterial interfaces, and the last decade has produced a coherent picture of both the "
       "physics and the open questions:"),
 ("bul", "**Physics (largely settled).** LIPSS are written by interference between the incident "
         "light and laser-excited surface electromagnetic waves; the period tracks the wavelength "
         "at ≈0.7–0.9 λ, the orientation is locked to the polarisation, and the structures grow "
         "through self-reinforcing grating coupling near the ablation threshold (Emmony "
         "et al., 1973; Sipe et al., 1983; Huang et al., 2009; Bonse et al., 2017)."),
 ("bul", "**Engineering (discrete by construction).** Wavelength is a hardware property — a "
         "fundamental frequency plus harmonic steps — so LIPSS periods arrive in discrete bands; "
         "DLIP releases the period from this constraint through beam geometry, at the cost of a "
         "more elaborate setup (Peter et al., 2020; Schwibbert et al., 2024)."),
 ("bul", "**Biology (conditional).** Textured metals can strongly reduce bacterial adhesion, and "
         "tall nanostructures can kill adherent cells mechanically; outcomes depend on strain, "
         "medium, feature scale and surface chemistry, with a crossover from anti-adhesion to "
         "cell capture as the feature scale approaches the cell size (Ivanova et al., 2012; "
         "Ivanova et al., 2013; Linklater et al., 2021; Outón et al., 2024; Wang et al., 2026)."),
 ("p", "Open questions that currently structure the field: quantitative models predicting "
       "adhesion and killing from texture geometry and surface energetics in protein-rich media; "
       "the long-term stability of both topography and chemistry under real conditions "
       "(sterilisation, storage, wear); standardised, ring-tested evaluation protocols; and "
       "scale-up of texturing throughput to device-relevant areas. Hybrid approaches — laser "
       "textures combined with antimicrobial coatings — compensate for the partial effectiveness "
       "of any single mechanism (Wang et al., 2025), and the accumulated mechanistic "
       "understanding makes rational texture design, rather than empirical trial, a realistic "
       "objective."),
]

REFERENCES = [
 "Arciola, C. R., Campoccia, D., & Montanaro, L. (2018). Implant infections: Adhesion, biofilm formation and immune evasion. Nature Reviews Microbiology, 16(7), 397–409. https://doi.org/10.1038/s41579-018-0019-y",
 "Barylyak, A., Wojnarowska-Nowak, R., Kus-Liśkiewicz, M., Krzemiński, P., Płoch, D., Cieniek, B., Bobitski, Y., & Kisała, J. (2024). Photocatalytic and antibacterial activity properties of Ti surface treated by femtosecond laser — a prospective study. Scientific Reports, 14, 20926. https://doi.org/10.1038/s41598-024-70103-4",
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
 "Kietzig, A.-M., Hatzikiriakos, S. G., & Englezos, P. (2009). Patterned superhydrophobic metallic surfaces. Langmuir, 25(8), 4821–4827. https://doi.org/10.1021/la8037582",
 "Klevens, R. M., Edwards, J. R., Richards, C. L., Horan, T. C., Gaynes, R. P., Pollock, D. A., & Cardo, D. M. (2007). Estimating health care-associated infections and deaths in U.S. hospitals, 2002. Public Health Reports, 122(2), 160–166. https://doi.org/10.1177/003335490712200205",
 "Lazzini, G., Romoli, L., Lutey, A. H. A., & Fuso, F. (2019). Modelling the interaction between bacterial cells and laser-textured surfaces. Surface and Coatings Technology, 375, 8–14. https://doi.org/10.1016/j.surfcoat.2019.06.078",
 "Linklater, D. P., Baulin, V. A., Juodkazis, S., Crawford, R. J., Stoodley, P., & Ivanova, E. P. (2021). Mechano-bactericidal actions of nanostructured surfaces. Nature Reviews Microbiology, 19(1), 8–22. https://doi.org/10.1038/s41579-020-0414-z",
 "Lutey, A. H. A., Gemini, L., Romoli, L., Lazzini, G., Fuso, F., Faucon, M., & Kling, R. (2018). Towards laser-textured antibacterial surfaces. Scientific Reports, 8, 10112. https://doi.org/10.1038/s41598-018-28454-2",
 "Magin, C. M., Cooper, S. P., & Brennan, A. B. (2010). Non-toxic antifouling strategies. Materials Today, 13(4), 36–44. https://doi.org/10.1016/S1369-7021(10)70058-4",
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
 "van Oss, C. J., Chaudhury, M. K., & Good, R. J. (1988). Interfacial Lifshitz-van der Waals and polar interactions in macroscopic systems. Chemical Reviews, 88(6), 927–941. https://doi.org/10.1021/cr00088a006",
 "van Oss, C. J. (1990). Surface properties of fibrinogen and fibrin. Journal of Protein Chemistry, 9(4), 487–491. https://doi.org/10.1007/BF01024625",
 "VanEpps, J. S., & Younger, J. G. (2016). Implantable device-related infection. Shock, 46(6), 597–608. https://doi.org/10.1097/SHK.0000000000000692",
 "Vorobyev, A. Y., & Guo, C. (2013). Direct femtosecond laser surface nano/microstructuring and its applications. Laser & Photonics Reviews, 7(3), 385–407. https://doi.org/10.1002/lpor.201200017",
 "Wang, H., & Zhang Newby, B. (2014). Applicability of the extended Derjaguin–Landau–Verwey–Overbeek theory on the adsorption of bovine serum albumin on solid surfaces. Biointerphases, 9(4), 041006. https://doi.org/10.1116/1.4904074",
 "Wang, Y., Dong, Y., Quan, Y., Wackerow, S., Abdolvand, A., Zolotovskaya, S. A., & Zhao, Q. (2025). Hybrid antibacterial surfaces: Combining laser-induced periodic surface structures with polydopamine-chitosan-silver nanoparticle nanocomposite coating. Advanced Materials Interfaces, 12(6), 2400660. https://doi.org/10.1002/admi.202400660",
 "Wang, Y., Olugbade, T. O., Zhao, Y.-Y., Dai, H., Zhang, S., Abdolvand, A., Zhao, Q., & Zolotovskaya, S. A. (2026). Geometry-driven control of bacterial adhesion and corrosion performance on LIPSS-textured 316L stainless steel. Materials & Design, 263, 115626. https://doi.org/10.1016/j.matdes.2026.115626",
 "Wei, T., Yu, Q., & Chen, H. (2019). Responsive and synergistic antibacterial coatings: Fighting against bacteria in a smart and effective way. Advanced Healthcare Materials, 8(3), 1801381. https://doi.org/10.1002/adhm.201801381",
 "Zimmerli, W., & Sendi, P. (2017). Orthopaedic biofilm infections. APMIS, 125(4), 353–364. https://doi.org/10.1111/apm.12687",
]

TABLE1 = ("Families of antibacterial surface strategies and their principal limitations (based on Hasan "
          "et al., 2013; Cloutier et al., 2015; Magin et al., 2010; Wei et al., 2019; Linklater "
          "et al., 2021; Wang et al., 2025).",
 ["Strategy", "Examples", "Mode of action", "Main limitations"],
 [["Antimicrobial-releasing coatings", "Silver nanoparticles, antibiotics, chlorhexidine",
   "Release of biocides that act on planktonic and early-adherent bacteria",
   "Finite loading; release-rate control; cytotoxicity trade-offs; resistance concerns"],
  ["Contact-killing coatings", "Immobilised quaternary ammonium compounds, antimicrobial peptides, enzymes",
   "Membrane disruption or oxidative damage on contact",
   "Durability and continued accessibility; limited reach into biofilm"],
  ["Anti-fouling coatings", "Poly(ethylene glycol) brushes, zwitterionic polymers, hydration-layer designs",
   "Thermodynamic barrier to protein and bacterial attachment",
   "Stability and mechanical robustness; batch reproducibility"],
  ["Topographical (laser-textured metals)", "LIPSS, nanopillar arrays, DLIP patterns",
   "Anti-adhesion (contact-area and surface-energy effects); mechano-bactericidal action for high-aspect-ratio structures",
   "Effect strength varies with strain and medium; throughput for large areas"],
  ["Hybrid", "Laser texture plus antimicrobial coating (e.g., polydopamine–chitosan–silver on LIPSS)",
   "Combined mechano-chemical action", "More process steps; both components require validation"]],
 [3.6, 4.0, 4.8, 4.6])

TABLE2 = ("Processing regimes of ultrafast laser texturing of metals and the resulting morphologies "
          "(based on Bonse et al., 2017; Vorobyev and Guo, 2013; Ivanova et al., 2013; Schwibbert "
          "et al., 2024).",
 ["Processing regime", "Resulting morphology", "Feature scale", "Notes"],
 [["Fluence near threshold; low accumulated dose", "Incipient ripples; surface modification",
   "Ripple nucleation", "Effective threshold decreases with pulse number (incubation)"],
  ["Slightly above threshold; moderate dose (≈10²–10³ pulses per spot)", "LIPSS (LSFL-I)",
   "Period ≈ 0.7–0.9 λ; relief of tens to a few hundred nanometres",
   "Orientation perpendicular to polarisation; quasi-periodic; areas tiled by scanning"],
  ["Well above threshold; high overlap and/or multiple passes", "Nanopillars and cones (“black metals”)",
   "Sub-micrometre spacing; high aspect ratio", "Multiscale roughness traps light; pronounced melt redeposition"],
  ["Interferometric (DLIP; two or more coherent beams)", "Periodic line or grid patterns",
   "Period = λ / (2 sin θ)", "Period set by the beam angle; interferometric setup, limited pattern field"]],
 [4.3, 3.5, 4.6, 4.6])

TABLE3 = ("Discrete wavelength sets of common solid-state ultrafast laser families. Each harmonic is "
          "a separate hardware configuration; wavelengths in parentheses are additional harmonic steps; periods are illustrative (Λ ≈ 0.75 λ), with the "
          "experimental range on metals spanning ≈0.7–0.9 λ.",
 ["Laser family", "Fundamental (nm)", "Discrete harmonics (nm)", "Illustrative LIPSS period at Λ ≈ 0.75 λ"],
 [["Nd:YAG / Nd:YVO_{4} (ps)", "1064", "532, 355 (266)", "≈800 / ≈400 / ≈270 nm"],
  ["Yb-based (fs–ps)", "1030", "515, 343 (257)", "≈770 / ≈385 / ≈260 nm"],
  ["Ti:sapphire (fs)", "≈800", "400 (267)", "≈600 / ≈300 / ≈200 nm"]],
 [4.2, 2.6, 4.4, 5.8], (1, 2, 3))

TABLE4 = ("Antibacterial mechanisms discussed in Section 4, with their key conditions and caveats.",
 ["Mechanism", "Key condition", "Reported evidence", "Caveats"],
 [["Anti-adhesion (topography)",
   "Features well below cell size; unfavourable surface energetics for attachment",
   "Reduced retention on sub-micrometre textures (titanium, steel, polymer)",
   "Reverses near cell-size features; strain- and medium-dependent"],
  ["Mechano-bactericidal action", "High aspect ratio; spacing within the membrane stretch limit",
   "Cicada wings; black silicon; nanopillars against S. aureus",
   "Small for shallow LIPSS; species-dependent; spores largely unaffected"],
  ["Surface chemistry", "Laser-induced oxide and charge state differing from the native surface",
   "Photo-active titania; laser-oxidised steel surfaces",
   "Secondary to topography; requires surface analysis"],
  ["Conditioning-film overprint", "Protein adsorption preceding bacterial arrival (Vroman sequence)",
   "Medium-dependent shifts in adhesion and viability outcomes",
   "Can override bare-surface behaviour in biological media"]],
 [3.6, 4.4, 4.6, 4.4])

FIG1_CAP = ("Figure 1.  Schematic process map of ultrafast laser texturing of metals: peak fluence "
            "(relative to the single-pulse ablation threshold) versus accumulated pulses per spot, with "
            "the principal regimes — no significant modification, LIPSS, strong ablation/melt and "
            "nanopillar–cone formation — and the incubation-driven lowering of the effective threshold.")
FIG2_CAP = ("Figure 2.  Formation physics of LIPSS: (a) coupling of incident light into a surface "
            "electromagnetic wave (SPP) at surface roughness; (b) interference between the incident "
            "light and the surface wave creates a periodic near-field energy distribution of period "
            "Λ; (c) the material response converts the energy pattern into quasi-periodic ripples "
            "with Λ ≈ 0.7–0.9 λ, running perpendicular to the electric field E; "
            "(d) positive feedback — the growing grating re-couples more light into the surface wave.")
FIG3_CAP = ("Figure 3.  Antibacterial mechanisms of textured metal surfaces: (a) anti-adhesion by "
            "geometry (contact points limited by feature scale); (b) mechano-bactericidal membrane "
            "rupture on high-aspect-ratio pillars; (c) surface-chemistry contributions (laser-induced "
            "oxide layer and charge state); (d) conditioning film — proteins adsorb first (Vroman "
            "sequence) and present a new interface to arriving bacteria.")

# ---------------------------------------------------------------- assemble docx
def build_docx_full():
    """Rebuild with tables inline at the right positions."""
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
    heading(doc, "Abstract", 1)
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

    # S1 with Table 1 after first paragraph of 1.2
    emit(S1[:3])  # h1, h2, p(1.1)
    emit(S1[3:4]) # h2 1.2
    emit([S1[4]]) # p (strategies) -> then table1
    add_table_block(doc, 1, TABLE1[0], TABLE1[1], TABLE1[2], TABLE1[3])
    emit(S1[5:])  # p(lipss metals), h2 scope, p

    i23p = next(i for i, b in enumerate(S2) if b[0] == 'h2' and b[1].startswith('2.3'))
    emit(S2[:i23p])
    emit([('fig', 'fig1_process_map_en.png', FIG1_CAP)])
    emit(S2[i23p:i23p + 2])
    add_table_block(doc, 2, TABLE2[0], TABLE2[1], TABLE2[2], TABLE2[3])
    emit(S2[i23p + 2:])

    i34 = next(i for i, b in enumerate(S3) if b[0] == 'h2' and b[1].startswith('3.4'))
    emit(S3[:i34])
    emit([('fig', 'fig2_lipss_mechanism_en.png', FIG2_CAP)])
    emit(S3[i34:])
    emit(S4)
    emit([('fig', 'fig3_antibacterial_en.png', FIG3_CAP)])
    add_table_block(doc, 3, TABLE4[0], TABLE4[1], TABLE4[2], TABLE4[3])
    emit(S5[:3])
    add_table_block(doc, 4, TABLE3[0], TABLE3[1], TABLE3[2], TABLE3[3], TABLE3[4])
    emit(S5[3:])
    emit(S6)

    heading(doc, "References", 1)
    for ref in REFERENCES:
        p = doc.add_paragraph()
        rich(p, ref, size=Pt(9.5))
        pf = p.paragraph_format
        pf.left_indent = Cm(0.75); pf.first_line_indent = Cm(-0.75)
        pf.space_after = Pt(3)
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT

    add_footer(doc, "Laser-textured antibacterial surfaces — review draft")
    doc.core_properties.title = TITLE
    doc.core_properties.comments = "Draft v1 — built 2026-10-07"
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
    L += ["## Abstract", ""]
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
                L.append(f"**Table {num}.** {t[0]}")
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
    emit_md([('fig', 'fig1_process_map_en.png', FIG1_CAP)])
    emit_md(S2[i23p:i23p + 2])
    emit_md([('table', 2)])
    emit_md(S2[i23p + 2:])
    i34 = next(i for i, b in enumerate(S3) if b[0] == 'h2' and b[1].startswith('3.4'))
    emit_md(S3[:i34])
    emit_md([('fig', 'fig2_lipss_mechanism_en.png', FIG2_CAP)])
    emit_md(S3[i34:])
    emit_md(S4)
    emit_md([('fig', 'fig3_antibacterial_en.png', FIG3_CAP)])
    emit_md([('table', 3)])
    emit_md(S5[:3])
    emit_md([('table', 4)])
    emit_md(S5[3:])
    emit_md(S6)
    L += ["## References", ""]
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
    banned = [w for w in ('should', 'recommend', 'propose', 'suggest', 'must',
                          'next step', 'future work', 'await') if w in raw.lower()]
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
