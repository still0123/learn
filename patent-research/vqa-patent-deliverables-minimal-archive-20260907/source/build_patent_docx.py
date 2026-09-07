from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "广告视频问答专利申请候选稿.md"
OUTPUT = ROOT / "广告视频问答专利申请候选稿.docx"

BLUE = RGBColor(0x2E, 0x74, 0xB5)
DARK_BLUE = RGBColor(0x1F, 0x4D, 0x78)
BLACK = RGBColor(0x00, 0x00, 0x00)
GRAY = RGBColor(0x55, 0x55, 0x55)
MUTED = RGBColor(0x66, 0x66, 0x66)
LIGHT_FILL = "F2F4F7"
CALLOUT_FILL = "F7F8FA"
TABLE_WIDTH_DXA = 9360
TABLE_INDENT_DXA = 120
CELL_MARGINS_DXA = {"top": 80, "bottom": 80, "start": 120, "end": 120}


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in CELL_MARGINS_DXA.items():
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_table_geometry(table, widths: list[int]) -> None:
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    tbl_pr = table._tbl.tblPr

    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(TABLE_WIDTH_DXA))
    tbl_w.set(qn("w:type"), "dxa")

    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(TABLE_INDENT_DXA))
    tbl_ind.set(qn("w:type"), "dxa")

    layout = tbl_pr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tbl_pr.append(layout)
    layout.set(qn("w:type"), "fixed")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)

    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(widths[idx]))
            tc_w.set(qn("w:type"), "dxa")
            set_cell_margins(cell)


def choose_widths(rows: list[list[str]]) -> list[int]:
    columns = len(rows[0])
    if columns == 1:
        return [TABLE_WIDTH_DXA]
    if columns == 2:
        return [2500, 6860]
    if columns == 3:
        return [3000, 3000, 3360]
    if columns == 4:
        return [2500, 2100, 2100, 2660]
    if columns == 5:
        return [2200, 1600, 1600, 1900, 2060]
    if columns == 6:
        return [1950, 1350, 1350, 1350, 1680, 1680]
    if columns == 7:
        return [1650, 1280, 1280, 1280, 1280, 1295, 1295]
    base = TABLE_WIDTH_DXA // columns
    widths = [base] * columns
    widths[-1] += TABLE_WIDTH_DXA - sum(widths)
    return widths


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("第 ")
    run.font.name = "Calibri"
    run.font.size = Pt(9)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, end])
    tail = paragraph.add_run(" 页")
    tail.font.name = "Calibri"
    tail.font.size = Pt(9)


def set_run_font(run, size=None, color=BLACK, bold=None, italic=None, latin="Calibri", east_asia="Arial Unicode MS") -> None:
    run.font.name = latin
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), latin)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), latin)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), east_asia)
    if size is not None:
        run.font.size = Pt(size)
    run.font.color.rgb = color
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def set_style_font(
    style,
    size: float,
    color=BLACK,
    bold=False,
    italic=False,
    latin="Calibri",
    east_asia="Arial Unicode MS",
) -> None:
    style.font.name = latin
    style._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), latin)
    style._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), latin)
    style._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), east_asia)
    style.font.size = Pt(size)
    style.font.color.rgb = color
    style.font.bold = bold
    style.font.italic = italic


def paragraph_bottom_border(paragraph, color="2E74B5", size="12", space="8") -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is None:
        p_bdr = OxmlElement("w:pBdr")
        p_pr.append(p_bdr)
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), size)
    bottom.set(qn("w:space"), space)
    bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)


def add_inline(paragraph, text: str, size: float = 11, color=BLACK) -> None:
    pattern = re.compile(r"(\*\*.*?\*\*|`.*?`)")
    pos = 0
    for match in pattern.finditer(text):
        if match.start() > pos:
            run = paragraph.add_run(text[pos:match.start()])
            set_run_font(run, size=size, color=color)
        token = match.group(0)
        if token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            set_run_font(run, size=size, color=color, bold=True)
        else:
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, size=max(size - 0.5, 8), color=color, latin="Consolas", east_asia="Arial Unicode MS")
        pos = match.end()
    if pos < len(text):
        run = paragraph.add_run(text[pos:])
        set_run_font(run, size=size, color=color)


def add_native_numbering(paragraph, num_id: int, level: int = 0) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    num_pr = OxmlElement("w:numPr")
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), str(level))
    num_id_node = OxmlElement("w:numId")
    num_id_node.set(qn("w:val"), str(num_id))
    num_pr.extend([ilvl, num_id_node])
    p_pr.append(num_pr)


def create_numbering(doc: Document, start: int = 1) -> int:
    numbering = doc.part.numbering_part.element
    abstract_ids = [int(x.get(qn("w:abstractNumId"))) for x in numbering.findall(qn("w:abstractNum"))]
    num_ids = [int(x.get(qn("w:numId"))) for x in numbering.findall(qn("w:num"))]
    abstract_id = max(abstract_ids or [0]) + 1
    num_id = max(num_ids or [0]) + 1

    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    multi = OxmlElement("w:multiLevelType")
    multi.set(qn("w:val"), "singleLevel")
    abstract.append(multi)
    lvl = OxmlElement("w:lvl")
    lvl.set(qn("w:ilvl"), "0")
    start_node = OxmlElement("w:start")
    start_node.set(qn("w:val"), str(start))
    num_fmt = OxmlElement("w:numFmt")
    num_fmt.set(qn("w:val"), "decimal")
    lvl_text = OxmlElement("w:lvlText")
    lvl_text.set(qn("w:val"), "%1.")
    suff = OxmlElement("w:suff")
    suff.set(qn("w:val"), "space")
    p_pr = OxmlElement("w:pPr")
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "num")
    tab.set(qn("w:pos"), "720")
    tabs.append(tab)
    ind = OxmlElement("w:ind")
    ind.set(qn("w:left"), "720")
    ind.set(qn("w:hanging"), "360")
    p_pr.extend([tabs, ind])
    lvl.extend([start_node, num_fmt, lvl_text, suff, p_pr])
    abstract.append(lvl)
    numbering.append(abstract)

    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abstract_num_id = OxmlElement("w:abstractNumId")
    abstract_num_id.set(qn("w:val"), str(abstract_id))
    num.append(abstract_num_id)
    numbering.append(num)
    return num_id


def configure_document(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.38)
    section.footer_distance = Inches(0.45)

    normal = doc.styles["Normal"]
    set_style_font(normal, 11)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.10
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for name, size, color, before, after in [
        ("Heading 1", 16, BLUE, 16, 8),
        ("Heading 2", 13, BLUE, 12, 6),
        ("Heading 3", 12, DARK_BLUE, 8, 4),
    ]:
        style = doc.styles[name]
        set_style_font(style, size, color=color, bold=True, east_asia="Arial Unicode MS")
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    if "Code Block" not in doc.styles:
        code_style = doc.styles.add_style("Code Block", WD_STYLE_TYPE.PARAGRAPH)
    else:
        code_style = doc.styles["Code Block"]
    set_style_font(code_style, 9, color=BLACK, latin="Consolas", east_asia="Arial Unicode MS")
    code_style.paragraph_format.left_indent = Inches(0.25)
    code_style.paragraph_format.right_indent = Inches(0.15)
    code_style.paragraph_format.space_before = Pt(4)
    code_style.paragraph_format.space_after = Pt(6)
    code_style.paragraph_format.line_spacing = 1.0
    p_pr = code_style.element.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), "F6F7F9")
    p_pr.append(shd)

    if "Quote Box" not in doc.styles:
        quote_style = doc.styles.add_style("Quote Box", WD_STYLE_TYPE.PARAGRAPH)
    else:
        quote_style = doc.styles["Quote Box"]
    set_style_font(quote_style, 10.5, color=GRAY, italic=True)
    quote_style.paragraph_format.left_indent = Inches(0.2)
    quote_style.paragraph_format.right_indent = Inches(0.1)
    quote_style.paragraph_format.space_after = Pt(4)
    quote_style.paragraph_format.line_spacing = 1.05

    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hr = hp.add_run("发明专利申请候选稿  |  需专利代理师复核")
    set_run_font(hr, size=8.5, color=MUTED, bold=True)

    footer = section.footer
    add_page_number(footer.paragraphs[0])


def add_masthead(doc: Document, title: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.keep_with_next = True
    r = p.add_run("发明专利申请候选稿")
    set_run_font(r, size=12, color=BLUE, bold=True, east_asia="Arial Unicode MS")

    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(8)
    title_p.paragraph_format.keep_with_next = True
    title_run = title_p.add_run(title)
    set_run_font(title_run, size=23, color=BLACK, bold=True, east_asia="Arial Unicode MS")

    subtitle = doc.add_paragraph()
    subtitle.paragraph_format.space_before = Pt(0)
    subtitle.paragraph_format.space_after = Pt(5)
    sr = subtitle.add_run("方法、系统、设备及计算机可读存储介质")
    set_run_font(sr, size=13, color=GRAY, bold=False, east_asia="Arial Unicode MS")

    meta = [
        ("文档状态", "代理人复核稿，非可直接提交文本"),
        ("版本日期", "V1.0  |  2026-08-13"),
        ("核心主线", "统一证据标识贯穿定位、主动补看和声明级核验"),
    ]
    for label, value in meta:
        mp = doc.add_paragraph()
        mp.paragraph_format.space_before = Pt(0)
        mp.paragraph_format.space_after = Pt(2)
        lr = mp.add_run(f"{label}：")
        set_run_font(lr, size=10.5, color=BLACK, bold=True, east_asia="Arial Unicode MS")
        vr = mp.add_run(value)
        set_run_font(vr, size=10.5, color=BLACK)

    rule = doc.add_paragraph()
    rule.paragraph_format.space_before = Pt(6)
    rule.paragraph_format.space_after = Pt(8)
    paragraph_bottom_border(rule)


def parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    rows = []
    idx = start
    while idx < len(lines) and lines[idx].strip().startswith("|"):
        cells = [c.strip() for c in lines[idx].strip().strip("|").split("|")]
        if not all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells):
            rows.append(cells)
        idx += 1
    return rows, idx


def add_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    columns = len(rows[0])
    normalized = [r + [""] * (columns - len(r)) for r in rows]
    table = doc.add_table(rows=len(normalized), cols=columns)
    table.style = "Table Grid"
    set_table_geometry(table, choose_widths(normalized))
    set_repeat_table_header(table.rows[0])

    for r_idx, row in enumerate(normalized):
        for c_idx, text in enumerate(row[:columns]):
            cell = table.cell(r_idx, c_idx)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(1.5)
            p.paragraph_format.line_spacing = 1.0
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if c_idx == 0 else WD_ALIGN_PARAGRAPH.CENTER
            add_inline(p, text, size=8.5)
            if r_idx == 0:
                set_cell_shading(cell, LIGHT_FILL)
                for run in p.runs:
                    set_run_font(run, size=8.5, bold=True, east_asia="Arial Unicode MS")
    after = doc.add_paragraph()
    after.paragraph_format.space_before = Pt(0)
    after.paragraph_format.space_after = Pt(2)


def add_body_paragraph(doc: Document, text: str, indent: bool = True) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.10
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if indent and not text.startswith(("S1，", "S2，", "S3，", "S4，", "S5，", "S6，", "S7，")):
        p.paragraph_format.first_line_indent = Pt(22)
    add_inline(p, text)


def build() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    lines = text.splitlines()
    first_title = lines[0].removeprefix("# ").strip()

    doc = Document()
    configure_document(doc)
    add_masthead(doc, first_title)

    claims_num_id = create_numbering(doc, start=1)
    list_num_id = None
    in_claims = False
    in_code = False
    code_lines: list[str] = []
    idx = 1
    force_page_break_titles = {
        "说明书摘要",
        "权利要求书",
        "说明书",
        "附录A：专利附图绘制Prompt（制作附件，不作为说明书正文）",
        "附录B：实验支持材料（供代理人筛选，非默认提交）",
        "附录C：原始支持、实施状态与代理人复核清单",
    }

    while idx < len(lines):
        raw = lines[idx]
        stripped = raw.strip()

        if stripped.startswith("```"):
            if in_code:
                p = doc.add_paragraph(style="Code Block")
                for line_idx, code_line in enumerate(code_lines):
                    if line_idx:
                        p.add_run().add_break()
                    run = p.add_run(code_line)
                    set_run_font(run, size=9, latin="Consolas", east_asia="Arial Unicode MS")
                code_lines = []
                in_code = False
            else:
                in_code = True
            idx += 1
            continue
        if in_code:
            code_lines.append(raw)
            idx += 1
            continue

        if not stripped or stripped == "---":
            idx += 1
            continue

        if stripped.startswith("|") and idx + 1 < len(lines) and lines[idx + 1].strip().startswith("|"):
            rows, next_idx = parse_table(lines, idx)
            add_table(doc, rows)
            idx = next_idx
            continue

        heading = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            if level == 1 and title in force_page_break_titles:
                doc.add_page_break()
            p = doc.add_paragraph(title, style=f"Heading {level}")
            if level == 1:
                p.paragraph_format.page_break_before = False
            in_claims = title == "权利要求书" or (in_claims and title not in {"说明书"})
            idx += 1
            continue

        if stripped.startswith(">"):
            p = doc.add_paragraph(style="Quote Box")
            p.paragraph_format.space_before = Pt(2)
            add_inline(p, stripped.lstrip("> "), size=10.5, color=GRAY)
            idx += 1
            continue

        ordered = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if ordered:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.10
            add_native_numbering(p, claims_num_id if in_claims else create_numbering(doc, start=int(ordered.group(1))))
            add_inline(p, ordered.group(2))
            idx += 1
            continue

        bullet = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet:
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.10
            add_inline(p, bullet.group(1))
            idx += 1
            continue

        if raw.startswith("   "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.5)
            p.paragraph_format.first_line_indent = Inches(-0.25)
            p.paragraph_format.space_after = Pt(5)
            p.paragraph_format.line_spacing = 1.10
            add_inline(p, stripped)
            idx += 1
            continue

        add_body_paragraph(doc, stripped)
        idx += 1

    doc.core_properties.title = first_title
    doc.core_properties.subject = "发明专利申请候选稿"
    doc.core_properties.author = "论文项目组"
    doc.core_properties.comments = "需专利代理师复核，不构成授权保证。"
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
