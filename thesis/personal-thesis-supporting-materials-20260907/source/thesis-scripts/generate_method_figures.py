#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate thesis method SVG figures for the evidence-flow mainline."""
from pathlib import Path
import xml.sax.saxutils as sx

ROOT = Path('/Users/bytedance/vqa_thesis_continue')
FIG = ROOT / 'figures'
FIG.mkdir(parents=True, exist_ok=True)

STYLE = """
<style>
  .title { font: 700 22px 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif; fill: #17365D; }
  .subtitle { font: 500 14px 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif; fill: #4F5B66; }
  .box { fill: #EAF3F8; stroke: #2F75B5; stroke-width: 1.6; rx: 12; }
  .box2 { fill: #FCE4D6; stroke: #C55A11; stroke-width: 1.6; rx: 12; }
  .box3 { fill: #E2F0D9; stroke: #548235; stroke-width: 1.6; rx: 12; }
  .box4 { fill: #E4DFEC; stroke: #7030A0; stroke-width: 1.6; rx: 12; }
  .box5 { fill: #FFF2CC; stroke: #BF9000; stroke-width: 1.6; rx: 12; }
  .small { font: 13px 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif; fill: #222; }
  .label { font: 700 15px 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif; fill: #222; }
  .note { font: 12px 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif; fill: #555; }
  .arrow { stroke: #555; stroke-width: 2; fill: none; marker-end: url(#arrowhead); }
  .dash { stroke: #777; stroke-width: 1.6; stroke-dasharray: 6 4; fill: none; marker-end: url(#arrowhead); }
</style>
<defs>
  <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#555" />
  </marker>
</defs>
"""

def svg(width, height, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
{STYLE}
{body}
</svg>
'''

def text_lines(x, y, lines, cls='small', anchor='middle', line_h=18):
    out=[]
    for i,line in enumerate(lines):
        out.append(f'<text x="{x}" y="{y+i*line_h}" text-anchor="{anchor}" class="{cls}">{sx.escape(line)}</text>')
    return '\n'.join(out)

def box(x,y,w,h,lines,cls='box'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="{cls}"/>\n{text_lines(x+w/2,y+28,lines,"label" if len(lines)<=2 else "small")}'

def arrow(x1,y1,x2,y2,cls='arrow'):
    return f'<path d="M{x1},{y1} L{x2},{y2}" class="{cls}"/>'

# Figure 3-1 Overall framework
body = f'''
<text x="600" y="34" text-anchor="middle" class="title">方法总体框架：证据定位—证据压缩—证据解释—证据校验</text>
<text x="600" y="58" text-anchor="middle" class="subtitle">题目不变：基于视觉特征压缩与链式反思的广告视频问答方法</text>
{box(40,110,150,88,['广告视频 V','用户问题 q'],'box')}
{arrow(190,154,250,154)}
{box(250,96,170,116,['多模态预处理','ASR / OCR','高频过采样','语义关键帧优选'],'box')}
{arrow(420,154,480,154)}
{box(480,96,190,116,['视听-文字','时空响应图','问题响应','ASR邻域响应','OCR/Logo响应'],'box2')}
{arrow(670,154,730,154)}
{box(730,96,180,116,['响应密度锚定','局部高分辨率证据','全局视图保留语境'],'box3')}
{arrow(910,154,970,154)}
{box(970,96,180,116,['多模态证据包','frame/time','crop/asr/ocr/tags'],'box5')}
{arrow(1060,212,1060,270)}
{box(970,270,180,110,['证据驱动','广告知识检索','营销概念','风险提示'],'box4')}
{arrow(970,325,910,325)}
{box(720,270,190,110,['结构化推理','观察','知识匹配','分析 / 答案'],'box')}
{arrow(720,325,660,325)}
{box(450,270,210,110,['声明级链式反思','视觉/OCR/ASR/营销声明','证据回溯校验'],'box2')}
{arrow(450,325,390,325)}
{box(210,270,180,110,['最终答案','支撑证据','置信度 / 修正说明'],'box3')}
<path d="M560,270 C560,238 815,238 815,212" class="dash"/>
<text x="688" y="240" text-anchor="middle" class="note">证据包贯穿检索、推理与校验</text>
'''
(FIG/'fig3-1_overall_framework.svg').write_text(svg(1200,430,body),encoding='utf-8')

# Figure 3-2 response map
body = f'''
<text x="560" y="34" text-anchor="middle" class="title">视听-文字时空响应图构建</text>
<text x="560" y="58" text-anchor="middle" class="subtitle">将 ASR 与 OCR 从被动上下文转化为主动视觉定位信号</text>
{box(50,110,150,80,['关键帧视觉特征','X_t'],'box')}
{box(50,230,150,80,['空间视觉网格','H × W × d'],'box')}
{arrow(200,150,280,150)}
{arrow(200,270,280,270)}
{box(280,80,180,80,['用户问题 q','问题—视觉响应 H_Q'],'box2')}
{box(280,190,180,100,['邻域 ASR 片段','时序窗口 Ω(t)','ASR—视觉响应 H_A'],'box3')}
{box(280,330,180,90,['OCR / Logo 线索','文字显著性响应 H_O'],'box5')}
{arrow(460,120,560,200)}
{arrow(460,240,560,240)}
{arrow(460,375,560,280)}
{box(560,180,180,120,['加权融合','H = αH_Q + βH_A + γH_O','任务类型调权'],'box4')}
{arrow(740,240,830,240)}
{box(830,170,210,140,['综合响应图 H(t)','定位问题相关区域','缓解声画异步','突出字幕/Logo/价格'],'box')}
<path d="M370,190 C370,150 515,145 595,180" class="dash"/>
<text x="500" y="150" text-anchor="middle" class="note">语音窗口：处理旁白领先/滞后</text>
'''
(FIG/'fig3-2_av_text_response_map.svg').write_text(svg(1120,470,body),encoding='utf-8')

# Figure 3-3 anchoring dual stream
body = f'''
<text x="560" y="34" text-anchor="middle" class="title">响应密度锚定与全局—局部双流视觉输入</text>
<text x="560" y="58" text-anchor="middle" class="subtitle">在保留整体语境的同时强化 Logo、字幕、价格等局部证据</text>
{box(60,120,170,90,['综合响应图 H(t)','语义响应分布'],'box')}
{arrow(230,165,300,165)}
{box(300,100,170,130,['语义重心定位','c_x, c_y','多尺度候选框','0.4 / 0.6 / 0.8 / 1.0'],'box2')}
{arrow(470,165,540,165)}
{box(540,100,180,130,['响应密度筛选','D(B)=ΣH/Area^ρ','选择最佳锚框 B*'],'box3')}
{arrow(720,165,790,165)}
{box(790,90,220,70,['局部高分辨率视图 L_t','Crop(B*) + Upsample'],'box5')}
{box(790,205,220,70,['全局语境视图 G_t','Resize(原始关键帧)'],'box')}
{arrow(900,160,900,205)}
{arrow(1010,125,1070,165)}
{arrow(1010,240,1070,205)}
{box(1070,145,140,80,['双流输入','Z_t=[G_t;L_t]'],'box4')}
<text x="630" y="285" text-anchor="middle" class="note">局部视图负责细节，全局视图负责场景与情绪</text>
'''
(FIG/'fig3-3_response_density_dual_view.svg').write_text(svg(1260,340,body),encoding='utf-8')

# Figure 4-1 evidence RAG
body = f'''
<text x="580" y="34" text-anchor="middle" class="title">证据驱动广告知识检索流程</text>
<text x="580" y="58" text-anchor="middle" class="subtitle">外部知识只解释视频中已有证据，避免普通 RAG 的无关知识误注入</text>
{box(40,110,180,120,['多模态证据包','ASR片段','OCR文本','视觉标签','局部证据描述'],'box')}
{arrow(220,170,300,170)}
{box(300,100,190,140,['复合查询 Q_R','用户问题 q','ASR / OCR / Tags','局部/全局描述','轻量查询扩展'],'box2')}
{arrow(490,170,570,170)}
{box(570,100,180,140,['广告营销知识库','营销理论','消费者心理','广告创意','合规风险'],'box5')}
{arrow(750,170,830,170)}
{box(830,90,220,160,['检索与重排序','语义相似度 Sem','关键词命中 Key','证据匹配 Ev','类别先验 Prior'],'box3')}
{arrow(940,250,940,310)}
{box(830,310,220,100,['高置信专家上下文','Top-M + 阈值过滤','不匹配则不注入'],'box4')}
{arrow(830,360,720,360)}
{box(520,310,200,100,['结构化推理','观察','知识匹配','分析 / 答案'],'box')}
<path d="M400,240 C450,290 520,310 590,310" class="dash"/>
<text x="475" y="290" text-anchor="middle" class="note">证据约束知识使用</text>
'''
(FIG/'fig4-1_evidence_driven_rag.svg').write_text(svg(1120,470,body),encoding='utf-8')

# Figure 4-2 reflection
body = f'''
<text x="610" y="34" text-anchor="middle" class="title">声明级证据回溯式链式反思</text>
<text x="610" y="58" text-anchor="middle" class="subtitle">不是让模型“再想一遍”，而是逐条声明回查多模态证据</text>
{box(50,115,160,85,['初始答案 y_0','观察-知识匹配-分析-答案'],'box')}
{arrow(210,157,285,157)}
{box(285,95,185,125,['声明拆解','视觉声明','文字声明','语音声明','营销推理声明'],'box2')}
{arrow(470,157,545,157)}
{box(545,70,190,80,['视觉声明校验','关键帧 / local crop'],'box3')}
{box(545,170,190,80,['文字声明校验','OCR文本 / 局部图'],'box5')}
{box(545,270,190,80,['语音声明校验','ASR片段 / 时间窗口'],'box')}
{box(545,370,190,80,['营销声明校验','视频证据 + 知识条目'],'box4')}
{arrow(735,110,820,230)}
{arrow(735,210,820,240)}
{arrow(735,310,820,250)}
{arrow(735,410,820,260)}
{box(820,190,180,120,['校验结果','CONFIRM','REVISE','REJECT','LOW_CONFIDENCE'],'box2')}
{arrow(1000,250,1075,250)}
{box(1075,205,150,90,['最终答案','修正/确认/拒答','证据说明'],'box3')}
<text x="640" y="475" text-anchor="middle" class="note">错误类型：视觉误读 / OCR误读 / ASR错配 / 时间错位 / 知识误用 / 过度推断</text>
'''
(FIG/'fig4-2_claim_level_reflection.svg').write_text(svg(1280,520,body),encoding='utf-8')

print('\n'.join(str(p) for p in sorted(FIG.glob('*.svg'))))
