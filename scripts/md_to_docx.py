# -*- coding: utf-8 -*-
"""Minimal Markdown -> .docx converter for the LabToolbox reports.

Supports: ATX headings (#..####), paragraphs, unordered/ordered lists, GitHub pipe
tables, fenced code blocks, bold ``**x**``, inline code `` `x` `` and horizontal rules.
Enough for the project reports; not a general Markdown implementation.
"""
from __future__ import annotations

import os
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Inches

CJK_FONT = "Microsoft YaHei"
LATIN_FONT = "Calibri"


def _set_font(run, size=None, bold=None, mono=False):
    name = "Consolas" if mono else LATIN_FONT
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)
    rfonts.set(qn("w:eastAsia"), CJK_FONT)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold


INLINE = re.compile(r"(\*\*.+?\*\*|\*[^*\n]+?\*|`.+?`)")


def _add_inline(par, text, size=None, base_bold=False):
    for chunk in INLINE.split(text):
        if not chunk:
            continue
        if chunk.startswith("**") and chunk.endswith("**") and len(chunk) > 4:
            r = par.add_run(chunk[2:-2])
            _set_font(r, size, True)
        elif chunk.startswith("*") and chunk.endswith("*") and len(chunk) > 2:
            r = par.add_run(chunk[1:-1])
            _set_font(r, size, base_bold)
            r.font.italic = True
        elif chunk.startswith("`") and chunk.endswith("`") and len(chunk) > 2:
            r = par.add_run(chunk[1:-1])
            _set_font(r, (size or 10.5) - 0.5, base_bold, mono=True)
            r.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
        else:
            r = par.add_run(chunk)
            _set_font(r, size, base_bold)


def md_to_docx(md_path, docx_path, title=None):
    lines = open(md_path, encoding="utf-8").read().splitlines()
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = LATIN_FONT
    st.font.size = Pt(10.5)

    if title:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(title)
        _set_font(r, 20, True)

    i = 0
    n = len(lines)
    while i < n:
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1
            continue
        # fenced code block
        if ln.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            for b in buf:
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Pt(12)
                r = p.add_run(b)
                _set_font(r, 9, mono=True)
            continue
        # heading
        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            level = len(m.group(1))
            text = m.group(2)
            if level == 1:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _add_inline(p, text, size=17, base_bold=True)
            else:
                p = doc.add_paragraph()
                _add_inline(p, text, size={2: 13.5, 3: 12, 4: 11}[level], base_bold=True)
                p.paragraph_format.space_before = Pt(10)
                p.paragraph_format.space_after = Pt(4)
            i += 1
            continue
        # horizontal rule
        if re.match(r"^---+$", ln.strip()):
            doc.add_paragraph()
            i += 1
            continue
        # image: ![alt](path)
        m = re.match(r"^!\[(.*?)\]\((.+?)\)\s*$", ln.strip())
        if m:
            alt, src = m.group(1), m.group(2)
            cand = src if os.path.isabs(src) else os.path.join(os.path.dirname(md_path), src)
            if os.path.exists(cand):
                try:
                    doc.add_picture(cand, width=Inches(6.6))
                    if alt:
                        cap = doc.add_paragraph()
                        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        r = cap.add_run(alt)
                        _set_font(r, 9)
                except Exception:
                    p = doc.add_paragraph()
                    _add_inline(p, f"[image: {src}]", size=10)
            else:
                p = doc.add_paragraph()
                _add_inline(p, f"[missing image: {src}]", size=10)
            i += 1
            continue
        # table
        if ln.lstrip().startswith("|") and i + 1 < n and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            header = [c.strip() for c in ln.strip().strip("|").split("|")]
            i += 2
            body = []
            while i < n and lines[i].lstrip().startswith("|"):
                body.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            t = doc.add_table(rows=1, cols=len(header))
            t.style = "Light Grid Accent 1"
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            for j, h in enumerate(header):
                cell = t.rows[0].cells[j]
                cell.text = ""
                _add_inline(cell.paragraphs[0], h, size=9, base_bold=True)
            for row in body:
                cells = t.add_row().cells
                for j in range(len(header)):
                    val = row[j] if j < len(row) else ""
                    _add_inline(cells[j].paragraphs[0], val, size=9)
            doc.add_paragraph()
            continue
        # list item
        m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", ln)
        if m:
            text = m.group(3)
            marker = m.group(2)
            indent = len(m.group(1)) // 2
            if re.match(r"\d+\.", marker):
                # keep the document's own numbering: Word's "List Number" shares one
                # counter across the whole file, which renumbers references and controls
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Pt(30 + 18 * indent)
                p.paragraph_format.first_line_indent = Pt(-14)
                _add_inline(p, f"{marker} {text}", size=10.5)
            else:
                try:
                    p = doc.add_paragraph(style="List Bullet")
                except KeyError:
                    p = doc.add_paragraph(style="List Bullet")
                p.paragraph_format.left_indent = Pt(18 + 18 * indent)
                _add_inline(p, text, size=10.5)
            i += 1
            continue
        # paragraph
        buf = [ln.strip()]
        i += 1
        while i < n and lines[i].strip() and not re.match(
                r"^(#{1,4}\s|\||```|\s*[-*+]\s|\s*\d+\.\s|---+$)", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        _add_inline(p, " ".join(buf), size=10.5)

    doc.save(docx_path)
    return docx_path


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else None
    print(md_to_docx(src, dst, title))
