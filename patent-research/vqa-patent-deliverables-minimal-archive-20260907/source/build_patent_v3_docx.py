from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


SOURCE = Path(__file__).with_name("视频问答答案可靠性保障专利申请候选稿_V3_20260823.md")
OUTPUT = Path(__file__).with_name("视频问答答案可靠性保障专利申请候选稿_V3_20260823.docx")

# Resolved design system:
# - Base preset: narrative_proposal.
# - Named override "Chinese patent review manuscript": A4, Songti body,
#   Heiti headings, black hierarchy, 10.5 pt body, 1.33 line spacing.
PAGE_WIDTH_DXA = 11906
PAGE_HEIGHT_DXA = 16838
MARGIN_DXA = 1440
CONTENT_WIDTH_DXA = PAGE_WIDTH_DXA - 2 * MARGIN_DXA
TABLE_INDENT_DXA = 120
CELL_MARGIN_TOP_BOTTOM_DXA = 80
CELL_MARGIN_START_END_DXA = 120

BODY_EAST_ASIA = "Arial Unicode MS"
BODY_LATIN = "Arial Unicode MS"
HEADING_EAST_ASIA = "Arial Unicode MS"
HEADING_LATIN = "Arial Unicode MS"
MONO_FONT = "Arial Unicode MS"
BLACK = RGBColor(0x00, 0x00, 0x00)
MUTED = RGBColor(0x66, 0x66, 0x66)
LIGHT_GRAY = "F4F6F9"
TABLE_HEADER = "E8EEF5"
TABLE_BORDER = "AAB2BD"

PAGE_BREAK_HEADINGS = {
    "说明书摘要",
    "权利要求书",
    "说明书",
    "附录A：代理人审查与申请策略（非说明书提交正文）",
    "附录B：本地原始支持与实现证据（非说明书提交正文）",
    "附录C：附图制作稿（非说明书正文）",
}


def set_run_font(run, *, east_asia=BODY_EAST_ASIA, latin=BODY_LATIN, size=None,
                 bold=None, italic=None, color=BLACK):
    run.font.name = latin
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), latin)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), latin)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), east_asia)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def set_style_font(style, east_asia, latin, size, *, bold=False, color=BLACK):
    style.font.name = latin
    style._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), latin)
    style._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), latin)
    style._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), east_asia)
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = color


def set_cell_margins(cell):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for tag, value in (
        ("top", CELL_MARGIN_TOP_BOTTOM_DXA),
        ("bottom", CELL_MARGIN_TOP_BOTTOM_DXA),
        ("start", CELL_MARGIN_START_END_DXA),
        ("end", CELL_MARGIN_START_END_DXA),
    ):
        node = tc_mar.find(qn(f"w:{tag}"))
        if node is None:
            node = OxmlElement(f"w:{tag}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def shade_cell(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def mark_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    header = tr_pr.find(qn("w:tblHeader"))
    if header is None:
        header = OxmlElement("w:tblHeader")
        tr_pr.append(header)
    header.set(qn("w:val"), "true")


def set_table_borders(table):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = borders.find(qn(f"w:{edge}"))
        if tag is None:
            tag = OxmlElement(f"w:{edge}")
            borders.append(tag)
        tag.set(qn("w:val"), "single")
        tag.set(qn("w:sz"), "4")
        tag.set(qn("w:space"), "0")
        tag.set(qn("w:color"), TABLE_BORDER)


def set_table_geometry(table, widths):
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:type"), "dxa")
    tbl_w.set(qn("w:w"), str(sum(widths)))
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:type"), "dxa")
    tbl_ind.set(qn("w:w"), str(TABLE_INDENT_DXA))

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)

    for row in table.rows:
        for index, cell in enumerate(row.cells):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:type"), "dxa")
            tc_w.set(qn("w:w"), str(widths[index]))
            set_cell_margins(cell)


def add_field(paragraph, instruction):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, text, end])
    set_run_font(run, size=9, color=MUTED)


def configure_numbering(document):
    numbering = document.part.numbering_part.element

    def add_num(fmt, text, left, hanging, font=None):
        abstract_ids = [int(x.get(qn("w:abstractNumId"))) for x in numbering.findall(qn("w:abstractNum"))]
        abstract_id = max(abstract_ids, default=-1) + 1
        abstract = OxmlElement("w:abstractNum")
        abstract.set(qn("w:abstractNumId"), str(abstract_id))
        multi = OxmlElement("w:multiLevelType")
        multi.set(qn("w:val"), "singleLevel")
        abstract.append(multi)
        level = OxmlElement("w:lvl")
        level.set(qn("w:ilvl"), "0")
        start = OxmlElement("w:start")
        start.set(qn("w:val"), "1")
        level.append(start)
        num_fmt = OxmlElement("w:numFmt")
        num_fmt.set(qn("w:val"), fmt)
        level.append(num_fmt)
        lvl_text = OxmlElement("w:lvlText")
        lvl_text.set(qn("w:val"), text)
        level.append(lvl_text)
        suff = OxmlElement("w:suff")
        suff.set(qn("w:val"), "tab")
        level.append(suff)
        p_pr = OxmlElement("w:pPr")
        tabs = OxmlElement("w:tabs")
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "num")
        tab.set(qn("w:pos"), str(left))
        tabs.append(tab)
        p_pr.append(tabs)
        ind = OxmlElement("w:ind")
        ind.set(qn("w:left"), str(left))
        ind.set(qn("w:hanging"), str(hanging))
        p_pr.append(ind)
        level.append(p_pr)
        if font:
            r_pr = OxmlElement("w:rPr")
            r_fonts = OxmlElement("w:rFonts")
            r_fonts.set(qn("w:ascii"), font)
            r_fonts.set(qn("w:hAnsi"), font)
            r_pr.append(r_fonts)
            level.append(r_pr)
        abstract.append(level)
        numbering.append(abstract)

        nums = [int(x.get(qn("w:numId"))) for x in numbering.findall(qn("w:num"))]
        num_id = max(nums, default=0) + 1
        num = OxmlElement("w:num")
        num.set(qn("w:numId"), str(num_id))
        abs_ref = OxmlElement("w:abstractNumId")
        abs_ref.set(qn("w:val"), str(abstract_id))
        num.append(abs_ref)
        numbering.append(num)
        return num_id

    return {
        "claim": add_num("decimal", "%1.", 540, 360),
        "decimal": add_num("decimal", "%1.", 720, 360),
        "bullet": add_num("bullet", "•", 540, 270, "Arial"),
    }


def set_num(paragraph, num_id):
    p_pr = paragraph._p.get_or_add_pPr()
    num_pr = p_pr.find(qn("w:numPr"))
    if num_pr is None:
        num_pr = OxmlElement("w:numPr")
        p_pr.append(num_pr)
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    num_id_node = OxmlElement("w:numId")
    num_id_node.set(qn("w:val"), str(num_id))
    num_pr.extend([ilvl, num_id_node])


def configure_document(document):
    section = document.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    normal = document.styles["Normal"]
    set_style_font(normal, BODY_EAST_ASIA, BODY_LATIN, 10.5)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.33

    heading_tokens = {
        "Heading 1": (16, 18, 10),
        "Heading 2": (13, 12, 6),
        "Heading 3": (12, 8, 4),
        "Heading 4": (11, 6, 3),
    }
    for name, (size, before, after) in heading_tokens.items():
        style = document.styles[name]
        set_style_font(style, HEADING_EAST_ASIA, HEADING_LATIN, size, bold=True)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.keep_together = True

    for name in ("Caption",):
        style = document.styles[name]
        set_style_font(style, BODY_EAST_ASIA, BODY_LATIN, 9, color=MUTED)

    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    hp.paragraph_format.space_after = Pt(0)
    run = hp.add_run("发明专利新申请候选稿  |  V3.0  |  需代理人复核")
    set_run_font(run, size=8.5, color=MUTED)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    fr = fp.add_run("第 ")
    set_run_font(fr, size=9, color=MUTED)
    add_field(fp, "PAGE")
    fr = fp.add_run(" 页")
    set_run_font(fr, size=9, color=MUTED)


INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`)")


def add_inline(paragraph, text, *, base_size=10.5, base_bold=False, color=BLACK):
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            set_run_font(run, size=base_size, bold=True, color=color)
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            set_run_font(run, east_asia=BODY_EAST_ASIA, latin=MONO_FONT,
                         size=base_size - 0.5, color=color)
        else:
            run = paragraph.add_run(part)
            set_run_font(run, size=base_size, bold=base_bold, color=color)


def parse_table(lines, index):
    rows = []
    while index < len(lines) and lines[index].strip().startswith("|"):
        row = [c.strip() for c in lines[index].strip().strip("|").split("|")]
        rows.append(row)
        index += 1
    if len(rows) >= 2 and all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in rows[1]):
        rows.pop(1)
    return rows, index


def column_widths(rows):
    cols = len(rows[0])
    maxima = []
    for col in range(cols):
        longest = max(len(re.sub(r"[`*]", "", row[col])) if col < len(row) else 0 for row in rows)
        maxima.append(max(6, min(longest, 48)))
    if cols >= 3:
        for col in range(cols):
            numeric_ratio = sum(bool(re.fullmatch(r"[+\-\d.%/\[\],→ ]+", row[col])) for row in rows[1:]) / max(len(rows) - 1, 1)
            if numeric_ratio > 0.6:
                maxima[col] = min(maxima[col], 12)
    total = sum(maxima)
    widths = [max(900, round(CONTENT_WIDTH_DXA * w / total)) for w in maxima]
    difference = CONTENT_WIDTH_DXA - sum(widths)
    widths[max(range(cols), key=lambda i: maxima[i])] += difference
    return widths


def add_table(document, rows):
    if not rows:
        return
    cols = len(rows[0])
    table = document.add_table(rows=len(rows), cols=cols)
    widths = column_widths(rows)
    set_table_geometry(table, widths)
    set_table_borders(table)
    mark_table_header(table.rows[0])
    for r_index, row in enumerate(rows):
        for c_index in range(cols):
            cell = table.cell(r_index, c_index)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if r_index == 0:
                shade_cell(cell, TABLE_HEADER)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            if c_index < len(row):
                add_inline(p, row[c_index], base_size=8.8, base_bold=(r_index == 0))
            if r_index == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(2)


def add_cover(document, title):
    for _ in range(5):
        p = document.add_paragraph()
        p.paragraph_format.space_after = Pt(8)
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    r = p.add_run("发明专利新申请候选稿")
    set_run_font(r, east_asia=HEADING_EAST_ASIA, latin=HEADING_LATIN, size=13, bold=True, color=MUTED)

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(16)
    r = p.add_run(title)
    set_run_font(r, east_asia=HEADING_EAST_ASIA, latin=HEADING_LATIN, size=22, bold=True)

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(46)
    r = p.add_run("V3.0  |  2026-08-23")
    set_run_font(r, size=11, color=MUTED)

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.left_indent = Cm(2.2)
    p.paragraph_format.right_indent = Cm(2.2)
    p.paragraph_format.space_after = Pt(12)
    r = p.add_run("供发明人与专利代理师讨论、查新和修改；不构成授权预判或正式法律意见。")
    set_run_font(r, size=10.5, italic=True, color=MUTED)

    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run("建议路径：新申请候选  |  在先申请号：202610425757.8")
    set_run_font(r, size=10, color=MUTED)
    document.add_page_break()


def build():
    source_text = SOURCE.read_text(encoding="utf-8")
    lines = source_text.splitlines()
    if not lines or not lines[0].startswith("# "):
        raise RuntimeError("source must begin with a level-1 title")
    title = lines[0][2:].strip()

    document = Document()
    configure_document(document)
    nums = configure_numbering(document)
    add_cover(document, title)

    in_code = False
    code_lines = []
    index = 1
    while index < len(lines):
        raw = lines[index]
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code:
                in_code = True
                code_lines = []
            else:
                p = document.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.45)
                p.paragraph_format.right_indent = Cm(0.2)
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(8)
                p.paragraph_format.line_spacing = 1.05
                p_pr = p._p.get_or_add_pPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:fill"), LIGHT_GRAY)
                p_pr.append(shd)
                r = p.add_run("\n".join(code_lines))
                set_run_font(r, east_asia=BODY_EAST_ASIA, latin=MONO_FONT, size=9)
                in_code = False
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue

        if not stripped:
            index += 1
            continue
        if stripped == "---":
            index += 1
            continue

        if stripped.startswith("|"):
            rows, index = parse_table(lines, index)
            add_table(document, rows)
            continue

        heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            p = document.add_paragraph(style=f"Heading {min(level, 4)}")
            if level == 1 and text in PAGE_BREAK_HEADINGS and len(document.paragraphs) > 2:
                # Attach the break to the heading itself. A standalone break
                # paragraph can spill to the next page when the prior page is
                # full, producing an otherwise blank page.
                p.paragraph_format.page_break_before = True
            add_inline(p, text, base_size={1: 16, 2: 13, 3: 12, 4: 11}[level], base_bold=True)
            index += 1
            continue

        if stripped.startswith(">"):
            p = document.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.45)
            p.paragraph_format.right_indent = Cm(0.2)
            p.paragraph_format.space_after = Pt(4)
            p_pr = p._p.get_or_add_pPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:fill"), LIGHT_GRAY)
            p_pr.append(shd)
            add_inline(p, stripped.lstrip("> "), base_size=9.5, color=MUTED)
            index += 1
            continue

        claim_match = re.match(r"^\*\*(\d+)\.\*\*\s*(.*)$", stripped)
        if claim_match:
            p = document.add_paragraph()
            set_num(p, nums["claim"])
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True
            add_inline(p, claim_match.group(2), base_size=10.5)
            index += 1
            continue

        decimal_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if decimal_match:
            p = document.add_paragraph()
            set_num(p, nums["decimal"])
            p.paragraph_format.space_after = Pt(4)
            add_inline(p, decimal_match.group(2), base_size=10.5)
            index += 1
            continue

        if stripped.startswith("- "):
            p = document.add_paragraph()
            set_num(p, nums["bullet"])
            p.paragraph_format.space_after = Pt(4)
            add_inline(p, stripped[2:], base_size=10.5)
            index += 1
            continue

        p = document.add_paragraph()
        p.paragraph_format.widow_control = True
        if re.match(r"^(获取|在预设|将所述|当所述|在获取|由同一|当未触发|输出所述|多模态索引模块|初始证据与回答模块|支持度评分与触发模块|增量证据获取模块|候选生成模块|答案门控模块|审计记录模块)", stripped):
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.first_line_indent = Cm(-0.6)
        else:
            p.paragraph_format.first_line_indent = Cm(0.74)
        add_inline(p, stripped, base_size=10.5)
        index += 1

    core = document.core_properties
    core.title = title
    core.subject = "发明专利新申请候选稿"
    core.author = ""
    core.keywords = "视频问答; 声明证据支持度; 增量证据; 门控回退"
    core.comments = "V3.0 candidate draft; attorney review required."
    document.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
