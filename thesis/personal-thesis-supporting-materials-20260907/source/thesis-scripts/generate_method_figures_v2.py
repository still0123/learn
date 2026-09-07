#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate revised thesis method SVG figures (2026-08-17, mainline v2).

对齐《完整论文_题目不变_证据选择与主动补看版_20260817.md》：
  figv2-0 总体框架（创新点一证据选择 + 创新点二主动补看与保守决策）
  figv2-1 创新点一详图（候选池→模态条件化融合→锚点→预算→证据包）
  figv2-2 创新点二详图（验证器训练 + 推理阶段缺口诊断/三动作/保守门控）
不覆盖旧图；输出至 figures/ 并附索引。
"""
from pathlib import Path
import xml.sax.saxutils as sx

ROOT = Path('/Users/bytedance/vqa_thesis_continue')
FIG = ROOT / 'figures'

STYLE = """
<style>
  .title { font: 700 22px 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif; fill: #17365D; }
  .subtitle { font: 500 14px 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif; fill: #4F5B66; }
  .zone1 { font: 700 17px 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif; fill: #2F75B5; }
  .zone2 { font: 700 17px 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif; fill: #C55A11; }
  .box { fill: #EAF3F8; stroke: #2F75B5; stroke-width: 1.6; }
  .box2 { fill: #FCE4D6; stroke: #C55A11; stroke-width: 1.6; }
  .box3 { fill: #E2F0D9; stroke: #548235; stroke-width: 1.6; }
  .box4 { fill: #E4DFEC; stroke: #7030A0; stroke-width: 1.6; }
  .box5 { fill: #FFF2CC; stroke: #BF9000; stroke-width: 1.6; }
  .small { font: 13px 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif; fill: #222; }
  .tiny { font: 12px 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif; fill: #555; }
  .label { font: 700 15px 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif; fill: #222; }
  .note { font: 12px 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif; fill: #555; }
  .arrow { stroke: #555; stroke-width: 2; fill: none; marker-end: url(#ah); }
  .dash { stroke: #777; stroke-width: 1.6; stroke-dasharray: 6 4; fill: none; marker-end: url(#ah); }
</style>
<defs>
  <marker id="ah" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#555" />
  </marker>
</defs>
"""


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">\n{STYLE}\n{body}\n</svg>\n')


def tl(x, y, lines, cls='small', anchor='middle', lh=19):
    return '\n'.join(
        f'<text x="{x}" y="{y + i * lh}" text-anchor="{anchor}" class="{cls}">{sx.escape(s)}</text>'
        for i, s in enumerate(lines))


def box(x, y, w, h, lines, cls='box', first_bold=True):
    r = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="{cls}"/>\n'
    if first_bold and lines:
        r += tl(x + w / 2, y + 24, lines[:1], 'label', lh=19)
        if len(lines) > 1:
            r += '\n' + tl(x + w / 2, y + 24 + 19, lines[1:], 'small', lh=18)
    else:
        r += tl(x + w / 2, y + (h - 18 * (len(lines) - 1)) / 2 + 4, lines, 'small', lh=18)
    return r


def arrow(x1, y1, x2, y2, cls='arrow'):
    return f'<path d="M{x1},{y1} L{x2},{y2}" class="{cls}"/>'


def zone_label(x, y, text, cls='zone1'):
    return f'<text x="{x}" y="{y}" text-anchor="middle" class="{cls}">{sx.escape(text)}</text>'


# ---------------------------------------------------------------- fig v2-0
W, H = 1400, 840
b = []
b.append('<text x="700" y="34" text-anchor="middle" class="title">方法总体框架：问题驱动的证据选择 — 证据缺口驱动的主动补看</text>')
b.append('<text x="700" y="58" text-anchor="middle" class="subtitle">题目不变：基于视觉特征压缩与链式反思的广告视频问答方法（“压缩”=预算约束下的证据组织，“反思”=选择性补看与保守决策）</text>')

# 输入
b.append(box(30, 130, 170, 120, ['输入 Inputs', '广告视频 V', '问题 q', 'OCR事件 / 分段ASR索引'], 'box'))
b.append(arrow(200, 190, 250, 190))

# 创新点一 zone
b.append(zone_label(430, 105, '创新点一：问题驱动的视听证据选择（第3章）'))
b.append('<rect x="250" y="118" width="470" height="330" rx="14" fill="none" stroke="#2F75B5" stroke-width="1.2" stroke-dasharray="8 5"/>')
b.append(box(260, 130, 200, 86, ['64帧候选池', '帧号+时间戳', 'OCR置信度/跨帧次数']))
b.append(arrow(460, 173, 500, 173))
b.append(box(500, 130, 200, 86, ['问题相关视觉评分', 'r(q, f)（冻结对齐模型）', 'ASR/OCR时间索引']))
b.append(arrow(700, 173, 715, 173))
b.append(box(270, 250, 210, 100, ['MMR 冗余受控选择', 'λ=0.70', '相关性最大 + 帧间冗余最小', '→ 8帧时间排序初始证据'], 'box'))
b.append(box(510, 250, 190, 100, ['MMR8 初始证据 S0', '8视图 / 1,024视觉Token', '关闭二次采样'], 'box'))
b.append(arrow(375, 216, 375, 250))
b.append(arrow(480, 300, 510, 300))
b.append(arrow(605, 350, 605, 390))
b.append(box(400, 390, 210, 86, ['基座模型生成初答 A0', 'Qwen3-VL / ReAd-R / Qwen2.5', 'ASR相关段落随文本提供'], 'box3'))

# 创新点二 zone
b.append(zone_label(1035, 105, '创新点二：主动补看与保守答案决策（第4章）'))
b.append('<rect x="760" y="118" width="560" height="560" rx="14" fill="none" stroke="#C55A11" stroke-width="1.2" stroke-dasharray="8 5"/>')
b.append(arrow(610, 433, 770, 433))
b.append(box(770, 390, 180, 86, ['声明—证据验证器', '正反声明+E+/E−对比校准训练', 'φ(A0) 支持度评分'], 'box2'))
b.append(arrow(950, 433, 990, 433))
b.append(box(990, 360, 150, 60, ['高支持 φ(A0)≥τt', '直接输出 A0'], 'box3'))
b.append(box(990, 445, 150, 60, ['低支持 φ(A0)<τt', '进入缺口诊断'], 'box5'))
b.append(arrow(1140, 505, 1140, 540))
b.append(box(900, 540, 250, 74, ['证据缺口诊断（answer-free）', '问题逻辑树 × 初始证据覆盖', 'missing_leaf / gap_reason'], 'box5'))
# 三动作
b.append(arrow(1000, 577, 960, 640))
b.append(arrow(1065, 614, 1065, 640))
b.append(arrow(1130, 577, 1170, 640))
b.append(box(790, 640, 180, 76, ['LOOK_TIME', '补看新时间位置', 'ASR段界/锚点邻域新帧'], 'box2'))
b.append(box(975, 640, 180, 76, ['LOOK_REGION', '补看证据锚点区域', '全帧+高分辨率视图'], 'box2'))
b.append(box(1160, 640, 150, 76, ['DIRECT', '无可定位缺口', '保留 A0'], 'box3'))
b.append(arrow(880, 678, 880, 692))
b.append(arrow(1065, 716, 1065, 700))
b.append(box(770, 692, 260, 74, ['12视图证据增强（3,104 Token）', '锚点全帧 + 自适应多尺度裁剪', '预算审计，超预算生成前拦截'], 'box2'))
b.append(arrow(1030, 712, 1080, 712))
b.append(box(1080, 690, 230, 46, ['独立候选生成 A2（第4.6节）'], 'box2'))
b.append(arrow(1195, 690, 1195, 660))
b.append(arrow(1300, 433, 1340, 433))

# 输出（右上）
b.append(box(1230, 260, 150, 100, ['输出 Outputs', '最终答案 A*', '审计轨迹', '（帧/时刻/动作/支持度）'], 'box3'))
b.append('<path d="M1305,360 L1305,390" class="arrow"/>')
# 门控说明
b.append(box(880, 250, 320, 100, ['充分性门控（保守替换）', 'φ(A2)≥τ 且 φ(A2)−φ(A0)≥margin', '通过→替换A2；未通过/格式失败→回退A0', '冻结参数按基座独立校准'], 'box4'))
b.append('<path d="M1195,690 C1300,690 1300,400 1305,360" class="dash"/>')
b.append('<text x="1332" y="520" text-anchor="middle" class="tiny">门控后输出</text>')

# 底注
b.append(tl(700, 730, ['训练仅限轻量验证器（真实声明数据），答案生成模型全程冻结；每题单轮最多一个补看动作，全部帧号/时间戳/OCR/ASR回指与支持度决策进入审计轨迹。'], 'note'))
b.append(tl(700, 754, ['冻结工作点示例：Qwen3 τ=0.960292（OOF-500校准）；ReAd-R τ=0.924142, margin=0；Qwen2.5 τ=0.392437, margin=0.25。'], 'note'))
b.append(tl(700, 778, ['主结果（Full-7844，机器裁判口径）：Uniform8 29.70/45.86 → MMR8 33.31/49.75 → 完整方法 40.31/59.87（Strict/Relaxed %）。'], 'note'))
(FIG / 'figv2-0_overall_framework.svg').write_text(svg(W, H, '\n'.join(b)), encoding='utf-8')

# ---------------------------------------------------------------- fig v2-1
W, H = 1400, 880
b = []
b.append('<text x="700" y="34" text-anchor="middle" class="title">创新点一：问题驱动的视听证据选择与证据锚点定位</text>')
b.append('<text x="700" y="58" text-anchor="middle" class="subtitle">目标：在受控视觉预算下定位最小且可靠的多模态证据集合（论文第3章）</text>')

# ① 候选池
b.append(zone_label(200, 105, '① 候选证据池 Candidate pool'))
b.append(box(30, 120, 340, 210, [], 'box', first_bold=False))
b.append(tl(200, 148, ['64 candidate frames（帧号+时间戳）', '视觉相关性：#0 0.00 · #1 0.95 · #3 2.85 · #63 59.05', '分段ASR：00:00-00:05 欢迎来到Fresh Cola！', '　　　　　　00:12-00:18 现在购买，第二件半价！', 'OCR+框：第二件半价 [x1,y1,w1,h1]', '　　　　　仅限本周末 [x2,y2,w2,h2]'], 'small', lh=22))
b.append('<text x="200" y="318" text-anchor="middle" class="tiny">跨帧出现次数与置信度构成OCR事件可靠性</text>')

# ② 融合
b.append(arrow(370, 225, 410, 225))
b.append(zone_label(565, 105, '② 模态条件化响应融合 Question-conditioned fusion'))
b.append(box(410, 120, 310, 210, [], 'box', first_bold=False))
b.append(tl(565, 148, ['按问题逻辑叶条件化（非固定权重）：', '文字/标识类问题 → OCR响应主导', '时序/语音类问题 → ASR响应主导', '对象/动作/场景类 → 视觉响应主导', '融合得分 S(t)；候选峰值如图', '去冗余：多样性抑制（抑制冗余峰值）'], 'small', lh=26))

# ③ 锚点
b.append(arrow(720, 225, 760, 225))
b.append(zone_label(930, 105, '③ 证据时刻定位 Temporal anchors'))
b.append(box(760, 120, 340, 210, [], 'box', first_bold=False))
b.append(tl(930, 148, ['融合得分候选峰值 → 选中两个锚点：', 'Anchor 1：#13，12.4s（OCR+视觉驱动）', 'Anchor 2：#46，43.7s（ASR驱动）', '约束：时间分散 · 不复用MMR8已选帧 · 来源互补', '不确定性 u(t)：0.24 / 0.28', '响应峰=空间中心；熵高→保全局，熵低→给细节'], 'small', lh=24))

# ④ 预算
b.append(arrow(600, 330, 600, 380))
b.append(zone_label(370, 408, '④ 预算分配 Budget allocation（二选一，不叠加）'))
b.append(box(30, 425, 640, 190, [], 'box5', first_bold=False))
b.append(tl(350, 455, ['高支持（A0，创新点一初始证据）：8全局视图 = 1,024 视觉Token', '触发补看（A2，供创新点二）：12视图 = 3,104 视觉Token（全帧+裁剪并存）', '自适应多尺度裁剪：候选框{0.4,0.6,0.8,1.0}，D(B)=ΣH/Area^ρ 选最佳锚框', 'Crop+上采样得局部细节视图；完整帧保留全局语境（响应熵调节尺度）', '仅触发题使用额外预算；不二次采样；每题Token台账（两预算二选一）'], 'small', lh=28))

# ⑤ 证据包
b.append(arrow(700, 520, 740, 520))
b.append(zone_label(1010, 408, '⑤ 可审计证据包 Auditable evidence package'))
b.append(box(740, 425, 360, 190, [], 'box3', first_bold=False))
b.append(tl(920, 455, ['帧索引 + 时间戳（frame, t）', 'OCR text + box；ASR segment + 时间段', '响应来源（visual / OCR / ASR）', '视图数 / 实际视觉Token / 二次采样状态', '→ 交由创新点二做缺口诊断与补看决策'], 'small', lh=28))

# 底部：MMR 选择准则
b.append(zone_label(700, 660, 'MMR 冗余受控选择准则（初始证据 S0，λ=0.70）'))
b.append(box(30, 675, 1070, 90, [], 'box', first_bold=False))
b.append(tl(565, 705, ['f^(k) = argmax_{f∈F\\S} [ λ·r(q,f) − (1−λ)·max_{f\'∈S} sim(f,f\') ]，λ=0.70，K=8，时间排序输出', '同预算对照（补充分区2,525题）：Uniform8 30.85/48.26 · CLIP TopK8 32.08/49.68 · MMR8 36.32/54.06（Strict/Relaxed %）'], 'small', lh=28))
b.append(tl(700, 800, ['组件归因（GroupCV-500）：固定中心26.80/43.90 → 响应中心27.00/44.00 → +自适应尺度27.20/44.40；4胜/496平/0负。'], 'note'))
(FIG / 'figv2-1_evidence_selection.svg').write_text(svg(W, H, '\n'.join(b)), encoding='utf-8')

# ---------------------------------------------------------------- fig v2-2
W, H = 1400, 950
b = []
b.append('<text x="700" y="34" text-anchor="middle" class="title">创新点二：证据缺口驱动的主动补看与保守答案决策</text>')
b.append('<text x="700" y="58" text-anchor="middle" class="subtitle">训练仅验证器（真实声明），答案模型冻结；推理阶段为“何时补看—补看什么—是否采纳”的显式决策链（论文第4章）</text>')

# 训练阶段
b.append(zone_label(180, 100, '训练阶段（仅轻量验证器）', 'zone2'))
b.append('<rect x="30" y="112" width="1340" height="180" rx="14" fill="none" stroke="#C55A11" stroke-width="1.2" stroke-dasharray="8 5"/>')
b.append(box(50, 128, 220, 140, ['正反声明构造（RealClaim985）', '真实回答→原子声明 c_i', '642 supported / 343 not-supported', '弱监督标签（自动推导）', '与校准/评测视频隔离'], 'box2'))
b.append(arrow(270, 198, 310, 198))
b.append(box(310, 128, 240, 140, ['反事实证据对（E+/E−）', 'E+ 完整证据（决定性+背景保留）', 'E− 最小破坏：删除关键帧', '模糊关键文字 / 语音错移±2s', '替换邻近干扰帧（保留背景）'], 'box2'))
b.append(arrow(550, 198, 590, 198))
b.append(box(590, 128, 250, 140, ['配对排序目标与支持判别', 'score(q,c,E+) > score(q,c,E−)+margin', '支持状态：支持 / 反驳 / 不足', '同题同声明下的证据对比监督'], 'box4'))
b.append(arrow(840, 198, 880, 198))
b.append(box(880, 128, 220, 140, ['Qwen3 LoRA 充分性验证器', '视觉编码器冻结', '语言侧 LoRA ≈0.03% 参数', '8视图+问题+声明+ASR输入'], 'box2'))
b.append(box(1140, 128, 210, 140, ['输出', 'P(充分 | q, c, E) ∈ [0,1]', 'φ(A)：声明级聚合', '三基座独立校准阈值'], 'box3'))
b.append(arrow(1100, 198, 1140, 198))
b.append('<text x="700" y="284" text-anchor="middle" class="note">路线选择：受控反事实适配器 AUROC 0.575 未达 0.70 门禁；真实正反声明直接训练成为主线（Calibration-240：冻结基座 0.541 → Qwen3 LoRA 0.660，+0.12，CI 全正）；E+/E- 保留为对比校准与证据扰动诊断。</text>')

# 推理阶段
b.append(zone_label(180, 330, '推理阶段——选择性补看与保守决策', 'zone2'))
b.append('<rect x="30" y="342" width="1340" height="470" rx="14" fill="none" stroke="#C55A11" stroke-width="1.2" stroke-dasharray="8 5"/>')
b.append(box(50, 360, 190, 100, ['初始答案 A0', 'MMR8 初始证据生成', '（第3章创新点一）'], 'box'))
b.append(arrow(240, 410, 280, 410))
b.append(box(280, 360, 230, 100, ['① 声明拆解与支持度', 'A0 → 声明 c_i', '验证器评分 φ(A0)'], 'box2'))
b.append(arrow(510, 410, 550, 410))
b.append(box(550, 360, 200, 100, ['② 触发判断', 'φ(A0) < τ_trigger ？', '否 → 输出 A0（结束）'], 'box5'))
b.append(arrow(750, 410, 790, 410))
b.append(box(790, 360, 270, 100, ['③ 证据缺口诊断（answer-free）', '问题逻辑树：OCR/ASR/动作/对象/场景叶', '× 初始证据覆盖 → 缺口记录', '{missing_leaf, gap_reason}'], 'box5'))
b.append(arrow(1060, 410, 1100, 410))
b.append(box(1100, 360, 250, 100, ['④ 动作决策（单轮单动作）', 'OCR叶缺失/定位分歧→LOOK_REGION', 'ASR/时序叶缺失→LOOK_TIME', '无可定位缺口→DIRECT'], 'box2'))
# 三动作行
b.append(box(50, 510, 400, 110, ['LOOK_TIME：补看新时间位置', 'ASR段首/段尾 · 锚点邻域新帧', '补看帧均不同于初始8帧与锚点帧', '附时间段ASR文本回指'], 'box2'))
b.append(box(480, 510, 400, 110, ['LOOK_REGION：补看锚点区域', '锚点全帧 + 高分辨率证据视图', '附该时刻OCR文本与ASR段落回指', '调用第3章锚点机制（响应峰/熵）'], 'box2'))
b.append(box(910, 510, 440, 110, ['DIRECT：保留 A0', '低支持但无可定位缺口时不做无目的补看', '与高支持未触发共用“回退/直出”路径', '每题输出动作、原因与调用记录'], 'box3'))
b.append('<path d="M1225,460 C1225,480 700,470 700,510" class="dash"/>')
b.append(arrow(250, 620, 250, 660))
b.append(arrow(680, 620, 680, 660))
b.append(box(50, 660, 800, 70, ['⑤ 证据增强输入（12视图 / 3,104 Token，预算审计） → ⑥ 独立候选生成 A2（不以A0为改写对象，直接在增强证据上作答）'], 'box2'))
b.append(arrow(850, 695, 890, 695))
b.append(box(890, 650, 460, 90, ['⑦ 保守门控：φ(A2) ≥ τ 且 φ(A2) − φ(A0) ≥ margin', '通过 → 替换为 A2；未通过 / 平票 / 格式失败 → 回退 A0', '（验证器不可用或评分失败一律回退）'], 'box4'))
b.append(arrow(1350, 695, 1370, 695))
b.append(box(1210, 760, 140, 40, ['最终答案 A*'], 'box3'))
b.append('<path d="M1120,740 C1120,780 1180,780 1210,780" class="arrow"/>')
b.append(box(50, 760, 500, 40, ['审计轨迹：动作 · 补看帧号/时间戳/区域 · φ(A0), φ(A2) · 替换决策'], 'box3'))

# 底注：冻结参数与边界
b.append(tl(700, 850, ['冻结门控参数（开发/校准集确定，评测集标签不参与）：Qwen3 τ=0.960292（OOF-500）；ReAd-R τ=0.924142, margin=0（Calibration-100）；Qwen2.5 τ=0.392437, margin=0.25（GroupCV-500五折）。'], 'note'))
b.append(tl(700, 874, ['不是自由思维链，也不是外部知识检索增强：补看只由低支持风险触发，并受视频内部证据约束。无门控反思 Strict −8.87 pp，门控后回到0；完整方法相对MMR8 +7.00/+10.12 pp（Full-7844）。'], 'note'))
b.append(tl(700, 898, ['零错误修改确认：ReAd-R Confirm-600 5胜/0负；E-VAds External-1000B 28胜/0负；Fresh-500 29胜/0负。'], 'note'))
(FIG / 'figv2-2_active_look_decision.svg').write_text(svg(W, H, '\n'.join(b)), encoding='utf-8')

print('generated:')
for f in sorted(FIG.glob('figv2-*.svg')):
    print(' -', f.name, f.stat().st_size, 'bytes')
