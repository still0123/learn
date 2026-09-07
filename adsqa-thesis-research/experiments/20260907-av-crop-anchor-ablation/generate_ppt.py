#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "source_summary.json").read_text(encoding="utf-8"))
REPEAT = json.loads((ROOT / "repeat200_summary.json").read_text(encoding="utf-8"))
OUT = ROOT / "AdsQA_同Token消融实验结果_答辩汇报.pptx"
TABLE_OUT = ROOT / "AdsQA_实验对比表.md"

W, H = Inches(13.333), Inches(7.5)
BG = RGBColor(248, 250, 252)
INK = RGBColor(24, 35, 52)
MUTED = RGBColor(91, 105, 125)
LINE = RGBColor(218, 225, 233)
NAVY = RGBColor(41, 76, 112)
NAVY_LIGHT = RGBColor(222, 232, 242)
TEAL = RGBColor(35, 137, 140)
TEAL_LIGHT = RGBColor(220, 243, 241)
BLUE = RGBColor(71, 117, 173)
BLUE_LIGHT = RGBColor(227, 237, 248)
AMBER = RGBColor(191, 127, 45)
AMBER_LIGHT = RGBColor(250, 239, 218)
CORAL = RGBColor(190, 78, 74)
WHITE = RGBColor(255, 255, 255)
FONT_CN = "Microsoft YaHei"
FONT_EN = "Aptos"


def add_text(
    slide,
    text,
    x,
    y,
    w,
    h,
    size=16,
    color=INK,
    bold=False,
    font=FONT_CN,
    align=PP_ALIGN.LEFT,
    valign=MSO_ANCHOR.TOP,
    margin=0.04,
):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.clear()
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(margin)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = align
    p.font.name = font
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    return shape


def add_bullets(slide, items, x, y, w, h, size=15, color=INK, gap=8):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.clear()
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    for index, item in enumerate(items):
        p = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        p.text = item
        p.level = 0
        p.font.name = FONT_CN
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.space_after = Pt(gap)
        p.text = "• " + p.text
    return shape


def add_box(slide, x, y, w, h, fill=WHITE, line=LINE, radius=True):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = Pt(0.8)
    return shape


def add_line(slide, x1, y1, x2, y2, color=LINE, width=1.2):
    line = slide.shapes.add_connector(
        1, Inches(x1), Inches(y1), Inches(x2), Inches(y2)
    )
    line.line.color.rgb = color
    line.line.width = Pt(width)
    return line


def add_title(slide, title, eyebrow):
    add_text(slide, eyebrow.upper(), 0.65, 0.28, 4.5, 0.28, 9, TEAL, True, FONT_EN)
    add_text(slide, title, 0.65, 0.58, 12.0, 0.58, 26, INK, True)
    add_line(slide, 0.65, 1.24, 12.68, 1.24, LINE, 1)


def add_footer(slide, page):
    add_line(slide, 0.65, 7.12, 12.68, 7.12, LINE, 0.7)
    add_text(
        slide,
        "Source: qwen3_croponly10_anchorglobal10_confirm1000_v1 · provisional · not_human_gold=true",
        0.65,
        7.18,
        10.9,
        0.18,
        7,
        MUTED,
        False,
        FONT_EN,
    )
    add_text(slide, f"{page:02d}", 12.05, 7.16, 0.6, 0.2, 8, MUTED, False, FONT_EN, PP_ALIGN.RIGHT)


def add_notes(slide, text):
    try:
        slide.notes_slide.notes_text_frame.text = text
    except Exception:
        pass


def blank_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = BG
    return slide


def add_metric(slide, value, label, x, y, w, accent=TEAL):
    add_text(slide, value, x, y, w, 0.54, 25, accent, True, FONT_EN)
    add_text(slide, label, x, y + 0.55, w, 0.35, 11, MUTED)


def bar(slide, label, strict, relaxed, x, y, w, color):
    add_text(slide, label, x, y, 1.7, 0.28, 11, INK, True, FONT_EN)
    base_x = x + 1.72
    add_box(slide, base_x, y + 0.01, w, 0.16, RGBColor(232, 237, 242), RGBColor(232, 237, 242), False)
    add_box(slide, base_x, y + 0.01, w * strict / 70, 0.16, color, color, False)
    add_box(slide, base_x, y + 0.22, w, 0.16, RGBColor(232, 237, 242), RGBColor(232, 237, 242), False)
    light = (
        TEAL_LIGHT
        if color == TEAL
        else BLUE_LIGHT
        if color == BLUE
        else NAVY_LIGHT
        if color == NAVY
        else AMBER_LIGHT
    )
    add_box(slide, base_x, y + 0.22, w * relaxed / 70, 0.16, light, light, False)
    add_text(slide, f"{strict:.2f}", base_x + w + 0.08, y - 0.03, 0.55, 0.2, 9, color, True, FONT_EN)
    add_text(slide, f"{relaxed:.2f}", base_x + w + 0.08, y + 0.19, 0.55, 0.2, 9, MUTED, False, FONT_EN)


def table_slide(slide, rows):
    x, y, w, h = 0.72, 1.55, 11.9, 3.9
    table = slide.shapes.add_table(len(rows) + 1, 5, Inches(x), Inches(y), Inches(w), Inches(h)).table
    widths = [2.75, 1.6, 1.6, 2.0, 3.95]
    for i, width in enumerate(widths):
        table.columns[i].width = Inches(width)
    headers = ["方法", "Strict", "Relaxed", "平均视觉 Token", "实验定位"]
    for col, value in enumerate(headers):
        cell = table.cell(0, col)
        cell.text = value
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        for p in cell.text_frame.paragraphs:
            p.alignment = PP_ALIGN.CENTER if col else PP_ALIGN.LEFT
            p.font.name = FONT_CN
            p.font.size = Pt(12)
            p.font.bold = True
            p.font.color.rgb = WHITE
    for r, row in enumerate(rows, 1):
        for c, value in enumerate(row):
            cell = table.cell(r, c)
            cell.text = str(value)
            cell.fill.solid()
            cell.fill.fore_color.rgb = TEAL_LIGHT if row[0] == "CropOnly10" else WHITE
            cell.margin_left = cell.margin_right = Inches(0.08)
            for p in cell.text_frame.paragraphs:
                p.alignment = PP_ALIGN.CENTER if c in (1, 2, 3) else PP_ALIGN.LEFT
                p.font.name = FONT_EN if c in (1, 2, 3) else FONT_CN
                p.font.size = Pt(12)
                p.font.bold = row[0] == "CropOnly10"
                p.font.color.rgb = INK


def write_table_md():
    m = DATA["methods"]
    c = DATA["comparisons"]
    cost = DATA["cost"]
    rm = REPEAT["methods"]
    rc = REPEAT["comparisons"]
    ra = REPEAT["repeat_agreement"]
    text = f"""# AdsQA 同 Token 消融实验结果

> 数据口径：Confirm-1000，完整配对评估 {DATA['evaluated_question_count']}/{DATA['source_question_count']} 题；排除 {DATA['excluded_question_count']} 题。结果为 provisional，机器裁判不是人工金标准。

## 主结果

| 方法 | Strict | Relaxed | 平均视觉 Token | 说明 |
|---|---:|---:|---:|---|
| MMR8 | {m['MMR8']['strict']:.2%} | {m['MMR8']['relaxed']:.2%} | {cost['MMR8_visual_tokens']:,} | 8视图基线 |
| AdaptiveScale12 | {m['AdaptiveScale12']['strict']:.2%} | {m['AdaptiveScale12']['relaxed']:.2%} | {cost['AdaptiveScale12_average_selected_visual_tokens']:,.0f} | 8帧+2全景+2裁剪 |
| AnchorGlobal10 | {m['AnchorGlobal10']['strict']:.2%} | {m['AnchorGlobal10']['relaxed']:.2%} | {cost['AnchorGlobal10_average_selected_visual_tokens']:,.0f} | 8帧+2个896全景 |
| **CropOnly10** | **{m['CropOnly10']['strict']:.2%}** | **{m['CropOnly10']['relaxed']:.2%}** | **{cost['CropOnly10_average_selected_visual_tokens']:,.0f}** | **8帧+2个896裁剪** |

## 配对比较

| 对比 | Strict差值 | Relaxed差值 | 胜/平/负 | Strict 95% CI | Relaxed 95% CI |
|---|---:|---:|---:|---:|---:|
| CropOnly10 vs AnchorGlobal10 | {c['CropOnly10_vs_AnchorGlobal10']['mean_strict_delta']:+.2%} | {c['CropOnly10_vs_AnchorGlobal10']['mean_relaxed_delta']:+.2%} | {c['CropOnly10_vs_AnchorGlobal10']['wins']}/{c['CropOnly10_vs_AnchorGlobal10']['ties']}/{c['CropOnly10_vs_AnchorGlobal10']['losses']} | [{c['CropOnly10_vs_AnchorGlobal10']['video_cluster_bootstrap_ci95']['strict_delta'][0]:+.2%}, {c['CropOnly10_vs_AnchorGlobal10']['video_cluster_bootstrap_ci95']['strict_delta'][1]:+.2%}] | [{c['CropOnly10_vs_AnchorGlobal10']['video_cluster_bootstrap_ci95']['relaxed_delta'][0]:+.2%}, {c['CropOnly10_vs_AnchorGlobal10']['video_cluster_bootstrap_ci95']['relaxed_delta'][1]:+.2%}] |
| CropOnly10 vs AdaptiveScale12 | {c['CropOnly10_vs_AdaptiveScale12']['mean_strict_delta']:+.2%} | {c['CropOnly10_vs_AdaptiveScale12']['mean_relaxed_delta']:+.2%} | {c['CropOnly10_vs_AdaptiveScale12']['wins']}/{c['CropOnly10_vs_AdaptiveScale12']['ties']}/{c['CropOnly10_vs_AdaptiveScale12']['losses']} | [{c['CropOnly10_vs_AdaptiveScale12']['video_cluster_bootstrap_ci95']['strict_delta'][0]:+.2%}, {c['CropOnly10_vs_AdaptiveScale12']['video_cluster_bootstrap_ci95']['strict_delta'][1]:+.2%}] | [{c['CropOnly10_vs_AdaptiveScale12']['video_cluster_bootstrap_ci95']['relaxed_delta'][0]:+.2%}, {c['CropOnly10_vs_AdaptiveScale12']['video_cluster_bootstrap_ci95']['relaxed_delta'][1]:+.2%}] |
| CropOnly10 vs MMR8 | {c['CropOnly10_vs_MMR8']['mean_strict_delta']:+.2%} | {c['CropOnly10_vs_MMR8']['mean_relaxed_delta']:+.2%} | {c['CropOnly10_vs_MMR8']['wins']}/{c['CropOnly10_vs_MMR8']['ties']}/{c['CropOnly10_vs_MMR8']['losses']} | [{c['CropOnly10_vs_MMR8']['video_cluster_bootstrap_ci95']['strict_delta'][0]:+.2%}, {c['CropOnly10_vs_MMR8']['video_cluster_bootstrap_ci95']['strict_delta'][1]:+.2%}] | [{c['CropOnly10_vs_MMR8']['video_cluster_bootstrap_ci95']['relaxed_delta'][0]:+.2%}, {c['CropOnly10_vs_MMR8']['video_cluster_bootstrap_ci95']['relaxed_delta'][1]:+.2%}] |

## DeepSeek分层复评200题

| 方法 | 复评Strict | 复评Relaxed | 与原评分一致率 | Cohen's Kappa |
|---|---:|---:|---:|---:|
| MMR8 | {rm['MMR8']['strict']:.2%} | {rm['MMR8']['relaxed']:.2%} | {ra['MMR8']['exact_agreement']:.2%} | {ra['MMR8']['cohens_kappa']:.3f} |
| AdaptiveScale12 | {rm['AdaptiveScale12']['strict']:.2%} | {rm['AdaptiveScale12']['relaxed']:.2%} | {ra['AdaptiveScale12']['exact_agreement']:.2%} | {ra['AdaptiveScale12']['cohens_kappa']:.3f} |
| CropOnly10 | {rm['CropOnly10']['strict']:.2%} | {rm['CropOnly10']['relaxed']:.2%} | {ra['CropOnly10']['exact_agreement']:.2%} | {ra['CropOnly10']['cohens_kappa']:.3f} |
| AnchorGlobal10 | {rm['AnchorGlobal10']['strict']:.2%} | {rm['AnchorGlobal10']['relaxed']:.2%} | {ra['AnchorGlobal10']['exact_agreement']:.2%} | {ra['AnchorGlobal10']['cohens_kappa']:.3f} |

复评中CropOnly10相对AnchorGlobal10的Strict/Relaxed差值为`{rc['CropOnly10_vs_AnchorGlobal10']['mean_strict_delta']:+.2%}/{rc['CropOnly10_vs_AnchorGlobal10']['mean_relaxed_delta']:+.2%}`，两项Bootstrap区间均跨0。

## 结论边界

- CropOnly10与AnchorGlobal10同Token下基本持平，尚不能证明裁剪具有独立增益。
- 两个10视图方案均优于AdaptiveScale12，但该比较同时改变了视图构成和视图说明Prompt。
- 本实验为Confirm-1000上的事后消融，不属于新的独立确认。
- 19题因裁判输出连续不可解析而整题排除，需在最终论文中明确报告。
"""
    TABLE_OUT.write_text(text, encoding="utf-8")


def build():
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    m, c, cost = DATA["methods"], DATA["comparisons"], DATA["cost"]

    slide = blank_slide(prs)
    add_text(slide, "ADSQA METHOD ABLATION", 0.72, 0.58, 4.8, 0.3, 10, TEAL, True, FONT_EN)
    add_text(slide, "主动证据补看\n同 Token 消融实验", 0.72, 1.18, 7.4, 1.45, 31, INK, True)
    add_text(slide, "CropOnly10 · AnchorGlobal10 · AdaptiveScale12", 0.75, 2.85, 7.4, 0.42, 15, NAVY, False, FONT_EN)
    add_box(slide, 8.55, 1.05, 3.75, 3.35, TEAL_LIGHT, TEAL, True)
    add_text(slide, "10", 9.18, 1.38, 2.5, 1.05, 48, TEAL, True, FONT_EN, PP_ALIGN.CENTER)
    add_text(slide, "视觉视图", 9.2, 2.45, 2.45, 0.4, 17, INK, True, FONT_CN, PP_ALIGN.CENTER)
    add_text(slide, "2,592 Token", 9.15, 3.12, 2.55, 0.45, 18, NAVY, True, FONT_EN, PP_ALIGN.CENTER)
    add_text(slide, "Confirm-1000 · 981题完整配对 · 200题DeepSeek复评", 0.75, 5.55, 9.3, 0.38, 13, MUTED)
    add_text(slide, "毕业论文实验汇报", 0.75, 6.06, 4.0, 0.3, 11, MUTED)
    add_footer(slide, 1)
    add_notes(slide, "本页说明汇报范围：比较两个10视图同Token方案与原12视图方案。结果来自Confirm-1000事后消融，当前为981题完整配对的暂定结果。")

    slide = blank_slide(prs)
    add_title(slide, "问题：每个锚点是否需要“全景+裁剪”两种视图？", "Research question")
    add_text(slide, "冻结 MMR8 初答与两个证据锚点，仅改变追加视图", 0.72, 1.42, 9.4, 0.35, 15, MUTED)
    add_box(slide, 0.78, 2.05, 2.3, 1.2, BLUE_LIGHT, BLUE)
    add_text(slide, "MMR8", 1.1, 2.28, 1.65, 0.35, 19, NAVY, True, FONT_EN, PP_ALIGN.CENTER)
    add_text(slide, "8 × 512", 1.15, 2.73, 1.55, 0.25, 11, MUTED, False, FONT_EN, PP_ALIGN.CENTER)
    add_line(slide, 3.1, 2.65, 4.05, 2.65, NAVY, 2)
    add_box(slide, 4.1, 1.75, 3.55, 1.72, AMBER_LIGHT, AMBER)
    add_text(slide, "AdaptiveScale12", 4.45, 2.0, 2.85, 0.35, 17, AMBER, True, FONT_EN, PP_ALIGN.CENTER)
    add_text(slide, "2个512全景 + 2个896裁剪", 4.4, 2.48, 2.95, 0.3, 12, INK, False, FONT_CN, PP_ALIGN.CENTER)
    add_text(slide, "3,104 Token", 4.78, 2.93, 2.2, 0.28, 13, AMBER, True, FONT_EN, PP_ALIGN.CENTER)
    add_box(slide, 8.2, 1.5, 4.15, 1.55, TEAL_LIGHT, TEAL)
    add_text(slide, "CropOnly10", 8.55, 1.74, 3.45, 0.34, 18, TEAL, True, FONT_EN, PP_ALIGN.CENTER)
    add_text(slide, "2个896自适应裁剪", 8.6, 2.22, 3.35, 0.3, 12, INK, False, FONT_CN, PP_ALIGN.CENTER)
    add_text(slide, "2,592 Token", 9.0, 2.63, 2.55, 0.26, 13, TEAL, True, FONT_EN, PP_ALIGN.CENTER)
    add_box(slide, 8.2, 3.35, 4.15, 1.55, BLUE_LIGHT, BLUE)
    add_text(slide, "AnchorGlobal10", 8.55, 3.59, 3.45, 0.34, 18, BLUE, True, FONT_EN, PP_ALIGN.CENTER)
    add_text(slide, "相同时间点的2个896全景", 8.55, 4.07, 3.45, 0.3, 12, INK, False, FONT_CN, PP_ALIGN.CENTER)
    add_text(slide, "2,592 Token", 9.0, 4.48, 2.55, 0.26, 13, BLUE, True, FONT_EN, PP_ALIGN.CENTER)
    add_box(slide, 0.78, 5.35, 11.57, 0.78, WHITE, LINE)
    add_text(slide, "核心检验：同一锚点、同一分辨率、同一Token下，局部裁剪是否优于完整全景？", 1.05, 5.58, 11.0, 0.3, 16, INK, True)
    add_footer(slide, 2)
    add_notes(slide, "旧方案每个锚点放入一个512全景和一个896裁剪。新实验把额外视图缩减为两个，并增加同Token的896全景对照，从而隔离空间裁剪的作用。")

    slide = blank_slide(prs)
    add_title(slide, "926题进入双臂推理，981题形成完整配对", "Evaluation design")
    stages = [
        ("1,000", "Confirm-1000来源"),
        ("926", "阈值触发"),
        ("1,852", "双臂候选"),
        ("981", "完整配对"),
    ]
    for i, (value, label) in enumerate(stages):
        x = 0.8 + i * 3.05
        add_box(slide, x, 1.78, 2.45, 1.28, WHITE, TEAL if i in (1, 3) else LINE)
        add_text(slide, value, x + 0.15, 1.98, 2.15, 0.48, 25, TEAL if i in (1, 3) else NAVY, True, FONT_EN, PP_ALIGN.CENTER)
        add_text(slide, label, x + 0.12, 2.55, 2.2, 0.25, 11, MUTED, False, FONT_CN, PP_ALIGN.CENTER)
        if i < 3:
            add_line(slide, x + 2.48, 2.42, x + 2.98, 2.42, NAVY, 1.8)
    add_box(slide, 0.8, 3.52, 7.1, 2.05, WHITE, LINE)
    add_text(slide, "冻结条件", 1.08, 3.78, 2.0, 0.3, 16, NAVY, True)
    add_bullets(slide, ["相同MMR8初答与触发集合", "相同锚点时间、OCR与ASR", "两臂均为10视图、2,592 Token"], 1.05, 4.2, 6.45, 1.15, 14, INK, 7)
    add_box(slide, 8.3, 3.52, 4.05, 2.05, AMBER_LIGHT, AMBER)
    add_text(slide, "裁判边界", 8.6, 3.78, 1.8, 0.3, 16, AMBER, True)
    add_bullets(slide, ["19题因输出连续不可解析而整题排除", "20个候选缺失，未继续重试", "机器裁判，不是人工金标准"], 8.57, 4.2, 3.45, 1.15, 13, INK, 6)
    add_text(slide, "统计：逐题配对 + 10,000次视频级Bootstrap", 0.86, 6.1, 8.5, 0.32, 13, MUTED)
    add_footer(slide, 3)
    add_notes(slide, "本实验在推理前冻结926题触发集合。两个新方法逐题配对。裁判首次1116次调用成功1095次，独立补评21次只恢复1次，因此依据停止规则整题排除19题。")

    slide = blank_slide(prs)
    add_title(slide, "10视图方案在981题完整配对中达到最高准确率", "Main results")
    rows = [
        ("MMR8", f"{m['MMR8']['strict']:.2%}", f"{m['MMR8']['relaxed']:.2%}", "1,024", "8视图基线"),
        ("AdaptiveScale12", f"{m['AdaptiveScale12']['strict']:.2%}", f"{m['AdaptiveScale12']['relaxed']:.2%}", f"{cost['AdaptiveScale12_average_selected_visual_tokens']:,.0f}", "2全景+2裁剪"),
        ("AnchorGlobal10", f"{m['AnchorGlobal10']['strict']:.2%}", f"{m['AnchorGlobal10']['relaxed']:.2%}", f"{cost['AnchorGlobal10_average_selected_visual_tokens']:,.0f}", "2个896全景"),
        ("CropOnly10", f"{m['CropOnly10']['strict']:.2%}", f"{m['CropOnly10']['relaxed']:.2%}", f"{cost['CropOnly10_average_selected_visual_tokens']:,.0f}", "2个896裁剪"),
    ]
    table_slide(slide, rows)
    add_box(slide, 0.78, 5.75, 11.6, 0.7, TEAL_LIGHT, TEAL)
    add_text(slide, "CropOnly10：Strict 45.16%，Relaxed 63.10%，平均视觉Token 2,476", 1.05, 5.95, 11.0, 0.28, 16, TEAL, True)
    add_text(slide, "所有准确率均采用相同981题完整配对口径", 0.82, 6.55, 5.8, 0.22, 9, MUTED)
    add_footer(slide, 4)
    add_notes(slide, "主表不能与Full-7844直接混排，因为本页采用排除19题后的Confirm-1000完整配对口径。CropOnly10点估计最高，但裁剪是否优于全景需要下一页的同Token配对检验。")

    slide = blank_slide(prs)
    add_title(slide, "两个10视图方案均高于旧AdaptiveScale12", "Accuracy comparison")
    add_text(slide, "Strict / Relaxed（%）", 0.75, 1.42, 2.3, 0.25, 10, MUTED, True, FONT_EN)
    chart_rows = [
        ("MMR8", m["MMR8"]["strict"] * 100, m["MMR8"]["relaxed"] * 100, NAVY),
        ("AdaptiveScale12", m["AdaptiveScale12"]["strict"] * 100, m["AdaptiveScale12"]["relaxed"] * 100, AMBER),
        ("AnchorGlobal10", m["AnchorGlobal10"]["strict"] * 100, m["AnchorGlobal10"]["relaxed"] * 100, BLUE),
        ("CropOnly10", m["CropOnly10"]["strict"] * 100, m["CropOnly10"]["relaxed"] * 100, TEAL),
    ]
    for i, (label, strict, relaxed, color) in enumerate(chart_rows):
        bar(slide, label, strict, relaxed, 0.82, 1.9 + i * 0.88, 7.0, color)
    add_box(slide, 9.55, 1.72, 2.7, 1.55, TEAL_LIGHT, TEAL)
    add_text(slide, "+6.73 pp", 9.82, 1.96, 2.15, 0.42, 24, TEAL, True, FONT_EN, PP_ALIGN.CENTER)
    add_text(slide, "CropOnly Strict\nvs AdaptiveScale12", 9.75, 2.47, 2.3, 0.52, 11, INK, False, FONT_CN, PP_ALIGN.CENTER)
    add_box(slide, 9.55, 3.55, 2.7, 1.55, BLUE_LIGHT, BLUE)
    add_text(slide, "+5.20 pp", 9.82, 3.79, 2.15, 0.42, 24, BLUE, True, FONT_EN, PP_ALIGN.CENTER)
    add_text(slide, "CropOnly Relaxed\nvs AdaptiveScale12", 9.75, 4.30, 2.3, 0.52, 11, INK, False, FONT_CN, PP_ALIGN.CENTER)
    add_text(slide, "深色：Strict    浅色：Relaxed", 0.82, 5.75, 3.5, 0.25, 10, MUTED)
    add_text(slide, "CropOnly10 vs AdaptiveScale12 的两项Bootstrap区间均完全为正", 0.82, 6.2, 9.6, 0.32, 15, INK, True)
    add_footer(slide, 5)
    add_notes(slide, "CropOnly10相对AdaptiveScale12提升Strict 6.73个百分点、Relaxed 5.20个百分点。AnchorGlobal10也有相似提升，因此新结果支持10视图配置，但不能把提升归因于裁剪本身。")

    slide = blank_slide(prs)
    add_title(slide, "裁剪与同锚点全景在同Token下基本持平", "Matched-token test")
    primary = c["CropOnly10_vs_AnchorGlobal10"]
    add_metric(slide, f"{primary['mean_strict_delta']:+.2%}", "Strict差值", 0.9, 1.55, 2.1, TEAL)
    add_metric(slide, f"{primary['mean_relaxed_delta']:+.2%}", "Relaxed差值", 3.05, 1.55, 2.1, BLUE)
    add_metric(slide, f"{primary['wins']}/{primary['ties']}/{primary['losses']}", "胜 / 平 / 负", 5.3, 1.55, 2.5, NAVY)
    add_metric(slide, "38 / 31", "wrong→right / right→wrong", 8.2, 1.55, 3.2, AMBER)
    axis_x, axis_w = 2.15, 8.55
    zero_x = axis_x + axis_w * 2 / 5
    add_line(slide, axis_x, 3.25, axis_x + axis_w, 3.25, MUTED, 1)
    add_line(slide, zero_x, 2.86, zero_x, 4.75, CORAL, 1.4)
    for tick in range(-2, 4):
        px = axis_x + axis_w * (tick + 2) / 5
        add_line(slide, px, 3.18, px, 3.34, MUTED, 0.7)
        add_text(slide, f"{tick:+d}", px - 0.25, 3.38, 0.5, 0.2, 8, MUTED, False, FONT_EN, PP_ALIGN.CENTER)
    cis = [
        ("Strict", primary["mean_strict_delta"] * 100, [v * 100 for v in primary["video_cluster_bootstrap_ci95"]["strict_delta"]], 4.0, TEAL),
        ("Relaxed", primary["mean_relaxed_delta"] * 100, [v * 100 for v in primary["video_cluster_bootstrap_ci95"]["relaxed_delta"]], 4.58, BLUE),
    ]
    for label, value, ci, yy, color in cis:
        add_text(slide, label, 0.85, yy - 0.13, 1.0, 0.25, 11, INK, True, FONT_EN)
        x1 = axis_x + axis_w * (ci[0] + 2) / 5
        x2 = axis_x + axis_w * (ci[1] + 2) / 5
        xp = axis_x + axis_w * (value + 2) / 5
        add_line(slide, x1, yy, x2, yy, color, 3)
        add_box(slide, xp - 0.07, yy - 0.07, 0.14, 0.14, color, color, False)
        add_text(slide, f"{value:+.2f} pp", 10.95, yy - 0.13, 1.25, 0.25, 10, color, True, FONT_EN, PP_ALIGN.RIGHT)
    add_box(slide, 0.82, 5.35, 11.45, 0.8, WHITE, LINE)
    add_text(slide, "两项置信区间均跨0：当前数据不能证明局部裁剪优于相同时间点的高分辨率全景。", 1.1, 5.58, 10.9, 0.3, 15, INK, True)
    add_footer(slide, 6)
    add_notes(slide, "CropOnly10和AnchorGlobal10的Relaxed差值只有0.05个百分点，Strict差值0.71个百分点，两项置信区间都跨0。论文应报告为同Token持平，而不是裁剪胜出。")

    slide = blank_slide(prs)
    add_title(slide, "10视图配置降低16.1% Token，并处于更优性能区间", "Efficiency")
    add_text(slide, "Relaxed准确率（%）", 0.8, 1.42, 2.4, 0.24, 10, MUTED, True)
    plot_x, plot_y, plot_w, plot_h = 1.15, 1.95, 7.4, 3.65
    add_line(slide, plot_x, plot_y + plot_h, plot_x + plot_w, plot_y + plot_h, MUTED, 1)
    add_line(slide, plot_x, plot_y, plot_x, plot_y + plot_h, MUTED, 1)
    points = [
        ("MMR8", 1024, m["MMR8"]["relaxed"] * 100, NAVY),
        ("AdaptiveScale12", cost["AdaptiveScale12_average_selected_visual_tokens"], m["AdaptiveScale12"]["relaxed"] * 100, AMBER),
        ("AnchorGlobal10", cost["AnchorGlobal10_average_selected_visual_tokens"], m["AnchorGlobal10"]["relaxed"] * 100, BLUE),
        ("CropOnly10", cost["CropOnly10_average_selected_visual_tokens"], m["CropOnly10"]["relaxed"] * 100, TEAL),
    ]
    for name, tokens, acc, color in points:
        px = plot_x + (tokens - 900) / 2200 * plot_w
        py = plot_y + plot_h - (acc - 45) / 20 * plot_h
        add_box(slide, px - 0.12, py - 0.12, 0.24, 0.24, color, color, False)
        add_text(slide, name, px + 0.13, py - 0.18, 1.55, 0.26, 9, color, True, FONT_EN)
    add_text(slide, "1,000", plot_x - 0.2, plot_y + plot_h + 0.18, 0.8, 0.2, 8, MUTED, False, FONT_EN)
    add_text(slide, "2,000", plot_x + plot_w * 0.46, plot_y + plot_h + 0.18, 0.8, 0.2, 8, MUTED, False, FONT_EN)
    add_text(slide, "3,000 Token", plot_x + plot_w - 0.7, plot_y + plot_h + 0.18, 1.1, 0.2, 8, MUTED, False, FONT_EN)
    add_box(slide, 9.15, 1.82, 3.05, 1.4, TEAL_LIGHT, TEAL)
    add_text(slide, "−474", 9.48, 2.02, 2.35, 0.48, 26, TEAL, True, FONT_EN, PP_ALIGN.CENTER)
    add_text(slide, "平均视觉Token/题", 9.42, 2.55, 2.5, 0.28, 11, INK, False, FONT_CN, PP_ALIGN.CENTER)
    add_box(slide, 9.15, 3.55, 3.05, 1.4, BLUE_LIGHT, BLUE)
    add_text(slide, "2.82 s", 9.48, 3.75, 2.35, 0.48, 25, BLUE, True, FONT_EN, PP_ALIGN.CENTER)
    add_text(slide, "CropOnly平均A2延迟", 9.4, 4.28, 2.55, 0.28, 11, INK, False, FONT_CN, PP_ALIGN.CENTER)
    add_text(slide, "成本比较不含验证器Token；延迟来自926题新推理审计", 0.86, 6.2, 8.9, 0.28, 11, MUTED)
    add_footer(slide, 7)
    add_notes(slide, "在相同92.6%触发率下，10视图方案平均视觉Token为2476，比AdaptiveScale12少474，下降16.1%。CropOnly10平均A2推理延迟2.82秒，AnchorGlobal10为3.01秒。")

    slide = blank_slide(prs)
    add_title(slide, "200题DeepSeek复评保留相同方法排序", "Repeat-judge robustness")
    rm, rc, ra = REPEAT["methods"], REPEAT["comparisons"], REPEAT["repeat_agreement"]
    rows = [
        ("MMR8", f"{rm['MMR8']['strict']:.2%}", f"{rm['MMR8']['relaxed']:.2%}", f"{ra['MMR8']['exact_agreement']:.1%}", f"{ra['MMR8']['cohens_kappa']:.3f}"),
        ("AdaptiveScale12", f"{rm['AdaptiveScale12']['strict']:.2%}", f"{rm['AdaptiveScale12']['relaxed']:.2%}", f"{ra['AdaptiveScale12']['exact_agreement']:.1%}", f"{ra['AdaptiveScale12']['cohens_kappa']:.3f}"),
        ("AnchorGlobal10", f"{rm['AnchorGlobal10']['strict']:.2%}", f"{rm['AnchorGlobal10']['relaxed']:.2%}", f"{ra['AnchorGlobal10']['exact_agreement']:.1%}", f"{ra['AnchorGlobal10']['cohens_kappa']:.3f}"),
        ("CropOnly10", f"{rm['CropOnly10']['strict']:.2%}", f"{rm['CropOnly10']['relaxed']:.2%}", f"{ra['CropOnly10']['exact_agreement']:.1%}", f"{ra['CropOnly10']['cohens_kappa']:.3f}"),
    ]
    x, y, w, h = 0.72, 1.55, 11.9, 3.55
    table = slide.shapes.add_table(5, 5, Inches(x), Inches(y), Inches(w), Inches(h)).table
    widths = [2.8, 1.75, 1.75, 2.6, 3.0]
    for i, width in enumerate(widths):
        table.columns[i].width = Inches(width)
    headers = ["方法", "复评Strict", "复评Relaxed", "原评分一致率", "Cohen's Kappa"]
    for col, value in enumerate(headers):
        cell = table.cell(0, col)
        cell.text = value
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        for p in cell.text_frame.paragraphs:
            p.alignment = PP_ALIGN.CENTER if col else PP_ALIGN.LEFT
            p.font.name = FONT_CN
            p.font.size = Pt(12)
            p.font.bold = True
            p.font.color.rgb = WHITE
    for r, row in enumerate(rows, 1):
        for col, value in enumerate(row):
            cell = table.cell(r, col)
            cell.text = value
            cell.fill.solid()
            cell.fill.fore_color.rgb = TEAL_LIGHT if row[0] == "CropOnly10" else WHITE
            for p in cell.text_frame.paragraphs:
                p.alignment = PP_ALIGN.CENTER if col else PP_ALIGN.LEFT
                p.font.name = FONT_EN if col else FONT_CN
                p.font.size = Pt(12)
                p.font.bold = row[0] == "CropOnly10"
                p.font.color.rgb = INK
    comp = rc["CropOnly10_vs_AnchorGlobal10"]
    add_box(slide, 0.78, 5.38, 5.65, 0.82, TEAL_LIGHT, TEAL)
    add_text(slide, f"Crop vs Global：{comp['mean_strict_delta']:+.2%} / {comp['mean_relaxed_delta']:+.2%}", 1.0, 5.57, 5.2, 0.3, 15, TEAL, True, FONT_EN)
    add_box(slide, 6.72, 5.38, 5.6, 0.82, WHITE, LINE)
    add_text(slide, "两项Bootstrap区间仍跨0，裁剪优势未成立", 6.98, 5.57, 5.05, 0.3, 14, INK, True)
    add_text(slide, "五类各40题；61个格式失败候选采用严格单行输出补评", 0.82, 6.48, 8.4, 0.24, 10, MUTED)
    add_footer(slide, 8)
    add_notes(slide, "复评样本从981题中分层随机抽取，五类各40题。方法排序保持不变。CropOnly和AnchorGlobal与原评分的一致率超过94%，两者同Token差异仍不显著。首次复评61个候选格式不可解析，使用同一评分标准但增加单行输出约束后完成。")

    slide = blank_slide(prs)
    add_title(slide, "当前证据支持10视图配置，但裁剪优势尚未成立", "Conclusion and boundary")
    add_box(slide, 0.78, 1.62, 5.72, 3.75, TEAL_LIGHT, TEAL)
    add_text(slide, "可以写入论文", 1.08, 1.95, 2.6, 0.35, 18, TEAL, True)
    add_bullets(slide, [
        "10视图方案准确率高于AdaptiveScale12",
        "平均视觉Token下降约16.1%",
        "CropOnly10与AnchorGlobal10同Token持平",
    ], 1.05, 2.55, 5.0, 1.7, 15, INK, 12)
    add_box(slide, 6.85, 1.62, 5.48, 3.75, AMBER_LIGHT, AMBER)
    add_text(slide, "仍需保留的边界", 7.15, 1.95, 3.0, 0.35, 18, AMBER, True)
    add_bullets(slide, [
        "Confirm-1000事后消融，非独立确认",
        "旧、新方案的视图说明Prompt同步变化",
        "19题排除，机器裁判未做人审",
        "200题复评中61个候选使用严格输出约束",
        "需Fresh视频隔离集确认最终配置",
    ], 7.12, 2.42, 4.75, 2.38, 13, INK, 7)
    add_box(slide, 0.78, 5.72, 11.55, 0.72, WHITE, LINE)
    add_text(slide, "建议论文口径：轻量化证据扩展提高了准确率与效率；局部裁剪相对同Token全景未显示稳定优势。", 1.05, 5.93, 11.0, 0.3, 15, INK, True)
    add_footer(slide, 9)
    add_notes(slide, "最终表述需要区分两个结论：第一，10视图轻量配置在当前数据上更优；第二，裁剪和全景持平，因此不能声称裁剪本身带来显著增益。下一步应在新的视频隔离确认集上冻结复验。")

    prs.save(OUT)
    write_table_md()
    print(OUT)
    print(TABLE_OUT)


if __name__ == "__main__":
    build()
