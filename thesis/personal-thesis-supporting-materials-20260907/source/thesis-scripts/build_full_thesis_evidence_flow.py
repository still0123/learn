#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the full evidence-flow thesis using closed-loop Chapter 3 and 4.

All outputs go to /Users/bytedance/vqa_thesis_continue.
"""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path('/Users/bytedance/vqa_thesis_continue')
DOCS = ROOT / 'docs'
DOCX = ROOT / 'docx'
TITLE = '基于视觉特征压缩与链式反思的广告视频问答方法'
OUT_MD = DOCS / '完整论文_题目不变_证据流闭环版.md'
OUT_DOCX = DOCX / '基于视觉特征压缩与链式反思的广告视频问答方法_完整论文_证据流闭环版.docx'

CH3 = DOCS / '第3章_闭环审查修订版.md'
CH4 = DOCS / '第4章_闭环审查修订版.md'
CH5 = DOCS / '第5章_闭环审查修订版.md'
REFS = DOCS / '真实参考文献核查清单.md'


def strip_front(md: str) -> str:
    lines = []
    for line in md.splitlines():
        if line.startswith('> 论文题目') or line.startswith('> 本章定位'):
            continue
        if line.strip() == '---':
            continue
        lines.append(line)
    return '\n'.join(lines).strip() + '\n'

ABSTRACT = f"""# {TITLE}

## 摘要

随着短视频平台、流媒体服务和数字营销产业的快速发展，广告视频已成为品牌传播和产品推广的重要内容形态。广告视频通常在较短时间内综合利用画面、旁白、字幕、音乐、品牌标识和场景变化传达产品卖点与营销意图，具有信息密度高、声画非严格同步、文字与 Logo 线索短时出现、语义表达隐含等特点。现有多模态大语言模型在通用视频问答任务中取得了较好效果，但在广告视频问答场景中仍面临关键视觉证据易丢失、视听语义难以对齐、广告领域知识不足以及生成答案缺乏证据约束等问题。

针对上述问题，本文提出一种基于视觉特征压缩与链式反思的广告视频问答方法。该方法围绕“证据定位—证据压缩—证据解释—证据校验”的主线展开。首先，针对广告视频中 Logo、字幕、价格和产品细节短时出现的问题，采用高频过采样与语义关键帧优选相结合的策略，减少关键帧遗漏风险；其次，构建由用户问题、ASR 语音文本和 OCR/Logo 文字显著性共同驱动的视听-文字时空响应图，并通过时序滑动窗口缓解广告旁白与画面之间的声画异步问题；在此基础上，基于响应密度自适应锚定局部高分辨率证据区域，同时保留全局视图以维持场景上下文，形成证据保留型全局—局部双流视觉输入。进一步地，本文构建广告营销知识库，将视觉、语音与文字证据转化为检索线索，获取与当前视频语境匹配的营销概念和策略解释，辅助模型完成从视觉感知到广告意图理解的推理。最后，设计证据回溯式链式反思机制，将初始答案中的核心声明回查至对应的视觉帧、局部区域、ASR 片段、OCR 文本和知识条目，从而降低无依据营销解释和事实性幻觉。

在 AdsQA 广告视频问答数据集上的阶段性实验表明，本文方法在整体准确率上优于多个多模态基线模型，并在情感分析、主题提取、营销策略和受众分析等高阶语义任务上取得更明显收益。进一步的消融实验将从视听-文字响应图、双流视觉压缩、广告知识检索和链式反思校验等方面验证各模块贡献，并通过压缩率、推理时延、幻觉率和证据一致性等指标评估方法的效率与可靠性。

**关键词：** 广告视频问答；视觉特征压缩；视听协同；证据定位；检索增强生成；链式反思；多模态大语言模型

---

## 目录

- 第1章 绪论
- 第2章 相关理论与技术基础
- 第3章 基于视觉特征压缩的广告视频证据定位方法
- 第4章 知识增强链式反思推理方法
- 第5章 实验设计与结果分析
- 第6章 总结与展望
- 参考文献

---
"""

CH1 = """# 第1章 绪论

## 1.1 研究背景

随着短视频平台、流媒体服务和数字营销产业的发展，广告视频已经成为品牌传播、产品推广和用户转化的重要载体。与一般视频相比，广告视频通常在较短时长内集中呈现商品、品牌、人物、场景、字幕、旁白、音乐和情绪节奏等多模态信息，并借助视觉隐喻、夸张对比、情绪共鸣和行动召唤等方式传达营销意图。广告视频问答任务要求模型根据给定视频和自然语言问题生成准确答案，不仅需要识别画面中出现的对象和动作，还需要理解广告背后的产品卖点、情绪诉求、说服策略和目标受众。

近年来，多模态大语言模型在图像问答、视频问答和开放式视觉理解任务中取得了显著进展。AdsQA 和 VideoAds 等广告视频理解基准表明，广告视频具有快节奏、高信息密度和高阶营销语义等特点，现有模型在视觉查找类问题上已有一定能力，但在广告意图、情绪诉求、说服策略和复杂叙事理解方面仍存在明显不足。面对广告视频这类高信息密度、强语义压缩和多模态非同步的内容，通用模型容易出现关键证据遗漏、声画语义错配、营销知识不足和生成幻觉等问题。

因此，广告视频问答需要一套围绕证据展开的多模态推理框架：首先从冗余视频输入中定位并保留关键视觉证据，再基于证据检索广告知识并进行结构化推理，最后对答案中的核心声明进行证据回溯式校验。本文即围绕“证据定位—证据压缩—证据解释—证据校验”的主线，研究基于视觉特征压缩与链式反思的广告视频问答方法。

## 1.2 研究意义

从理论意义上看，本文将广告视频问答中的“视觉特征压缩”重新定义为面向问题的证据保留型视觉输入重构，强调在有限上下文预算下保留与答案生成相关的关键视觉线索，而不是单纯减少帧数或图像 Token。通过引入用户问题、ASR 语音文本和 OCR/Logo 文字显著性共同构建视听-文字时空响应图，本文尝试解决广告视频中声画异步和局部细节易丢失的问题，为高信息密度视频理解中的证据定位提供一种新的研究思路。

从应用意义上看，广告视频问答可服务于广告创意分析、素材审核、投放效果评估、用户反馈理解和智能营销决策等场景。相比只输出表层视觉描述的模型，具备证据定位、广告知识解释和链式反思校验能力的问答系统能够提供更可靠、更可解释的分析结果，有助于提升广告内容理解和智能营销工具的实际可用性。

## 1.3 研究问题

本文围绕以下四个研究问题展开：

**RQ1：如何在高信息密度广告视频中定位与用户问题相关的关键视觉证据？** 广告视频中大量关键线索可能短暂出现在局部区域，本文通过高频过采样、语义关键帧优选、问题响应图、ASR 邻域响应图和 OCR/Logo 响应图定位关键证据。

**RQ2：如何在压缩视觉输入的同时保留全局语境和局部细节？** 本文基于响应密度选择局部高分辨率证据区域，同时保留全局视图，构建全局—局部双流视觉输入。

**RQ3：如何将广告营销知识用于解释视频证据，而不是引入无关幻觉？** 本文构建广告营销知识库，并基于视觉标签、ASR 文本、OCR 文本和用户问题进行证据驱动检索与重排序。

**RQ4：如何通过链式反思降低无依据回答和事实性幻觉？** 本文将初始答案拆分为视觉、文字、语音和营销推理声明，并回溯至多模态证据包进行校验。

## 1.4 主要研究内容

本文主要研究内容包括：

1. 面向广告视频问答的视听-文字协同证据定位方法；
2. 基于响应密度的证据保留型视觉特征压缩方法；
3. 证据驱动的广告知识增强推理方法；
4. 面向答案可靠性的证据回溯式链式反思机制；
5. 基于 AdsQA 数据集的有效性、效率、鲁棒性和可靠性实验评估。

## 1.5 本文创新点

**（1）提出面向声画异步广告视频的视听-文字协同证据定位方法。** 针对广告视频中旁白、画面和屏幕文字非严格同步，且 Logo、字幕、价格和产品细节等关键线索短时出现的问题，本文以用户问题为查询，融合邻域 ASR 语义响应和 OCR/Logo 文字显著性响应，构建视听-文字时空响应图，用于定位与问题相关的关键视觉证据。

**（2）提出基于响应密度的证据保留型视觉特征压缩机制。** 针对广告视频视觉输入冗余与局部细节易丢失的问题，本文基于视听-文字响应图计算语义重心，并在多尺度候选锚框中选择归一化响应密度最高的局部区域作为高分辨率证据视图，同时保留全局视图以维持场景上下文。

**（3）提出证据驱动的广告知识增强推理与链式反思校验机制。** 针对通用多模态模型在广告营销语义理解中容易泛化解释和产生事实性幻觉的问题，本文基于视觉标签、ASR 文本、OCR 文本和用户问题检索广告营销知识，并将初始答案中的核心声明回溯到对应视频帧、局部裁剪区域、语音片段、OCR 文本和知识条目进行校验。

## 1.6 论文组织结构

本文共分为六章。第 1 章介绍研究背景、研究意义、研究问题、研究内容和创新点。第 2 章介绍广告视频问答、多模态大语言模型、视觉特征压缩、视听协同融合、检索增强生成和链式反思相关理论。第 3 章提出基于视觉特征压缩的广告视频证据定位方法。第 4 章提出知识增强链式反思推理方法。第 5 章设计实验并分析结果。第 6 章总结全文并展望未来工作。

---
"""

CH2 = """# 第2章 相关理论与技术基础

## 2.1 广告视频问答与广告视频理解

视频问答任务要求模型根据给定视频和自然语言问题生成答案，是衡量多模态理解能力的重要任务。与图像问答相比，视频问答还需要理解跨帧事件、时序关系、语音信息和动态场景。广告视频问答进一步引入广告意图、情绪表达、受众定位和营销策略等高层语义，对模型的证据定位和推理能力提出了更高要求。

AdsQA 面向广告视频理解构建了问答基准，覆盖视觉感知、情感分析、主题提取、营销策略和受众分析等任务，强调广告视频理解不仅需要识别可见事实，还需要理解商业意图和说服方式。VideoAds 则进一步指出广告视频具有快节奏和高信息密度特点，现有多模态模型与人类表现之间仍存在明显差距。这些研究说明，广告视频已经成为检验多模态模型高阶视频理解能力的重要场景。

## 2.2 多模态大语言模型与视频理解

多模态大语言模型通过视觉编码器、跨模态投影层和语言模型主体实现图像、视频、文本和语音信息的联合理解。LLaVA、Video-ChatGPT、Video-LLaVA、Qwen2-VL 和 Qwen2.5-VL 等模型展示了视觉指令跟随、视频对话、动态分辨率处理和长视频理解能力，为广告视频问答提供了基础模型支持。

然而，在广告视频问答场景中，通用多模态大语言模型仍存在不足。首先，视频帧输入带来大量视觉 Token，增加上下文和计算压力；其次，广告视频中的短时文字、Logo 和细节可能在全局缩放中丢失；再次，广告营销语义依赖领域知识，模型容易泛化解释或误用概念；最后，生成式答案可能缺少证据约束，产生多模态幻觉。

## 2.3 视觉特征压缩与视觉证据选择

视觉特征压缩旨在降低图像或视频输入的冗余度，常见方法包括均匀采样、关键帧选择、Token 剪枝、区域裁剪、特征聚合和问题引导的视觉选择。CLIP 等视觉语言预训练模型通过图文对齐学习，使文本查询与视觉内容之间的相似度计算成为可能，可用于语义关键帧选择和问题相关区域定位。

对于广告视频问答而言，压缩不能只追求输入规模最小，还需要保留 Logo、字幕、价格、产品细节和场景语境等关键证据。本文将视觉特征压缩理解为证据保留型视觉输入重构：先通过过采样降低关键帧遗漏风险，再通过语义关键帧优选和局部响应图定位与问题相关的证据区域，最终通过全局—局部双流输入兼顾整体语境和局部细节。

## 2.4 视听协同融合与声画异步建模

广告视频通常同时包含画面、旁白、字幕、音效和音乐等多源信息。语音旁白常用于说明产品卖点、促销信息或品牌主张，视觉画面则提供商品、人物、场景和情绪线索。然而，在广告创作中，旁白与画面并不总是严格同步，可能存在语音领先、语音滞后或语音与画面弱相关的情况。

细粒度时间理解是视频大模型的重要方向。Momentor 和 VTimeLLM 等工作强调视频模型需要具备片段级或时刻级理解能力。本文关注广告视频中特有的旁白—画面错位问题，采用时序滑动窗口聚合邻域 ASR 语义，将语音从被动上下文转化为主动视觉定位信号，从而构建更鲁棒的视听-文字时空响应图。

## 2.5 检索增强生成与广告知识推理

检索增强生成通过从外部知识库检索相关内容并注入生成模型上下文，能够缓解大模型在专业领域中的知识不足和事实幻觉问题。经典 RAG 方法证明了将参数化生成模型与非参数化知识检索结合对于知识密集型任务具有价值。

在广告视频问答中，问题经常涉及稀缺效应、社会认同、权威背书、情绪共鸣、视觉隐喻和目标受众画像等营销概念，因此需要广告领域知识辅助解释。但普通 RAG 如果仅根据问题检索知识，可能引入与视频无关的概念，导致无依据营销解释。本文采用证据驱动的广告知识检索，将视觉标签、ASR 文本、OCR 文本和用户问题共同作为检索线索，并通过证据感知重排序降低知识误注入风险。

## 2.6 链式推理、反思机制与幻觉校验

链式推理通过显式组织中间推理过程，提高复杂问题回答的可解释性。Chain-of-Thought 提示证明了逐步推理示例能够提升大语言模型在复杂推理任务上的表现。Self-Refine 和 Reflexion 等工作进一步表明，模型可通过自反馈或语言反思在测试时改进输出。

然而，普通反思方法容易停留在让模型重新生成答案，缺乏对原始多模态证据的回溯。本文将链式反思定义为证据回溯式声明校验：首先将初始答案拆解为视觉声明、文字声明、语音声明和营销推理声明，再分别回查关键帧、局部视图、ASR 片段、OCR 文本和知识条目。该机制有助于降低 OCR 误读、ASR 错配、营销策略误归因和无依据推断。

## 2.7 本章小结

本章介绍了广告视频问答、多模态大语言模型、视觉特征压缩、视听协同融合、检索增强生成和链式反思相关理论。现有方法为广告视频问答提供了基础，但仍难以同时解决关键证据定位、声画异步、广告知识解释和答案证据校验问题。后续章节将在此基础上提出面向广告视频问答的证据流闭环方法。

---
"""

CH6 = """# 第6章 总结与展望

## 6.1 工作总结

本文围绕广告视频问答中的高信息密度、声画异步、领域知识不足和生成答案缺乏证据约束等问题，提出一种基于视觉特征压缩与链式反思的广告视频问答方法。不同于将视觉压缩、RAG 和反思机制简单并列组合，本文围绕“证据定位—证据压缩—证据解释—证据校验”的主线构建方法框架。

在视觉特征压缩方面，本文提出视听-文字协同证据定位方法，通过高频过采样、语义关键帧优选、问题响应图、ASR 邻域响应图和 OCR/Logo 响应图构建时空响应图，并基于响应密度自适应选择局部高分辨率证据区域，同时保留全局视图形成双流输入。在知识推理方面，本文构建广告营销知识库，并基于证据包进行广告知识检索和证据感知重排序。在链式反思方面，本文将初始答案拆解为不同类型的声明，并回溯至视觉、文字、语音和知识证据进行核查，从而提升答案可靠性。

## 6.2 主要创新点总结

本文主要创新点包括：第一，提出面向声画异步广告视频的视听-文字协同证据定位方法；第二，提出基于响应密度的证据保留型全局—局部双流视觉压缩机制；第三，提出证据驱动的广告知识增强推理与证据回溯式链式反思校验机制。

## 6.3 不足与未来工作

本文仍存在以下不足。首先，广告营销知识库规模仍有限，后续可结合更系统的营销理论、行业知识和品牌知识进行扩充。其次，当前局部锚定主要基于响应图和候选框，对于多个分散关键区域的处理仍有提升空间。再次，OCR 和 ASR 错误会影响证据包质量，后续可引入更强的多帧文字融合和语音置信度建模。最后，链式反思会带来额外 Token 和推理延迟，未来可进一步研究轻量化校验器、动态触发策略和多模型协同验证机制。

## 6.4 展望

未来工作可从三个方向继续推进：一是构建更大规模、更细粒度的广告视频问答数据集，特别是标注声画异步、OCR/Logo 细节和营销策略证据；二是探索可训练的证据定位模块，使视听-文字响应图与最终问答目标更紧密结合；三是将证据回溯式链式反思扩展到广告审核、营销素材评估和多模态内容安全等应用场景。

---
"""

REFERENCES = """# 参考文献（已核查基础版，最终格式待学校模板统一）

[1] Long X, Tian K, Xu P, et al. AdsQA: Towards Advertisement Video Understanding. arXiv preprint arXiv:2509.08621, 2025.

[2] Zhang Z, Dou M, Peng L, Pan H, Bagci U, Gong B. VideoAds for Fast-Paced Video Understanding. arXiv preprint arXiv:2504.09282, 2025.

[3] Xu B, Feng J, Lin X, et al. AD-MIR: Bridging the Gap from Perception to Persuasion in Advertising Video Understanding via Structured Reasoning. arXiv preprint arXiv:2602.07625, 2026.

[4] Radford A, Kim J W, Hallacy C, et al. Learning Transferable Visual Models From Natural Language Supervision. arXiv preprint arXiv:2103.00020, 2021.

[5] Li J, Li D, Xiong C, Hoi S. BLIP: Bootstrapping Language-Image Pre-training for Unified Vision-Language Understanding and Generation. arXiv preprint arXiv:2201.12086, 2022.

[6] Lewis P, Perez E, Piktus A, et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. Advances in Neural Information Processing Systems, 2020.

[7] Wei J, Wang X, Schuurmans D, et al. Chain-of-Thought Prompting Elicits Reasoning in Large Language Models. arXiv preprint arXiv:2201.11903, 2022.

[8] Madaan A, Tandon N, Gupta P, et al. Self-Refine: Iterative Refinement with Self-Feedback. arXiv preprint arXiv:2303.17651, 2023.

[9] Shinn N, Cassano F, Berman E, Gopinath A, Narasimhan K, Yao S. Reflexion: Language Agents with Verbal Reinforcement Learning. arXiv preprint arXiv:2303.11366, 2023.

[10] Liu H, Li C, Wu Q, Lee Y J. Visual Instruction Tuning. Advances in Neural Information Processing Systems, 2023.

[11] Maaz M, Rasheed H, Khan S, Khan F S. Video-ChatGPT: Towards Detailed Video Understanding via Large Vision and Language Models. arXiv preprint arXiv:2306.05424, 2023.

[12] Lin B, Ye Y, Zhu B, et al. Video-LLaVA: Learning United Visual Representation by Alignment Before Projection. arXiv preprint arXiv:2311.10122, 2023.

[13] Wang P, et al. Qwen2-VL: Enhancing Vision-Language Model's Perception of the World at Any Resolution. arXiv preprint arXiv:2409.12191, 2024.

[14] Bai S, Chen K, Liu X, et al. Qwen2.5-VL Technical Report. arXiv preprint arXiv:2502.13923, 2025.

[15] Qian L, Li J, Wu Y, et al. Momentor: Advancing Video Large Language Model with Fine-Grained Temporal Reasoning. arXiv preprint arXiv:2402.11435, 2024.

[16] Huang B, Wang X, Chen H, Song Z, Zhu W. VTimeLLM: Empower LLM to Grasp Video Moments. arXiv preprint arXiv:2311.18445, 2023.

---

## 待核查文献

- AVAM: Universal Training-free Adaptive Visual Anchoring Embedded into Multimodal Large Language Model for Multi-image Question Answering. 当前未查到可靠 arXiv 页面，暂不进入正式参考文献。
- POPE、Woodpecker、CHAIR 等多模态幻觉评估/修正文献本轮因网络限制未完成核查，暂不进入正式参考文献。
"""


def clean_chapter(md: str) -> str:
    lines = []
    for line in md.splitlines():
        if line.startswith('>'):
            continue
        if line.strip() == '---':
            continue
        lines.append(line)
    return '\n'.join(lines).strip() + '\n'


def build_markdown():
    ch3 = clean_chapter(CH3.read_text(encoding='utf-8'))
    ch4 = clean_chapter(CH4.read_text(encoding='utf-8'))
    ch5 = clean_chapter(CH5.read_text(encoding='utf-8'))
    return '\n\n'.join([ABSTRACT, CH1, CH2, ch3, ch4, ch5, CH6, REFERENCES])


def build_docx(md: str):
    try:
        from docx import Document
        from docx.shared import Pt, Inches, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
    except Exception as e:
        return False, str(e)
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Inches(1)
    sec.bottom_margin = Inches(1)
    sec.left_margin = Inches(1)
    sec.right_margin = Inches(1)
    styles = doc.styles
    styles['Normal'].font.name = '宋体'
    styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    styles['Normal'].font.size = Pt(11)

    def set_run(run, font='宋体', size=11, bold=False, color='000000'):
        run.font.name = font
        run._element.rPr.rFonts.set(qn('w:eastAsia'), font)
        run._element.rPr.rFonts.set(qn('w:ascii'), 'Times New Roman')
        run._element.rPr.rFonts.set(qn('w:hAnsi'), 'Times New Roman')
        run.font.size = Pt(size)
        run.bold = bold
        run.font.color.rgb = RGBColor.from_string(color)

    def para(text, first=True, size=11, bold=False, align=None, font='宋体'):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.25
        if first:
            p.paragraph_format.first_line_indent = Pt(22)
        if align is not None:
            p.alignment = align
        r = p.add_run(text)
        set_run(r, font=font, size=size, bold=bold)

    in_code = False
    code = []
    table = []
    def flush_code():
        nonlocal code
        if code:
            para('\n'.join(code), first=False, size=8.5, font='Consolas')
            code = []
    def flush_table():
        nonlocal table
        if table:
            para('\n'.join(table), first=False, size=8, font='Consolas')
            table = []

    for raw in md.splitlines():
        line = raw.rstrip()
        if line.startswith('```'):
            if in_code:
                flush_code(); in_code=False
            else:
                flush_table(); in_code=True
            continue
        if in_code:
            code.append(line); continue
        if line.startswith('|') and line.endswith('|'):
            table.append(line); continue
        flush_table()
        if not line.strip():
            continue
        if line.startswith('# '):
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(18); p.paragraph_format.space_after = Pt(14)
            r = p.add_run(line[2:].strip()); set_run(r, font='黑体', size=18, bold=True)
        elif line.startswith('## '):
            p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(12); p.paragraph_format.space_after = Pt(8)
            r = p.add_run(line[3:].strip()); set_run(r, font='黑体', size=15, bold=True)
        elif line.startswith('### '):
            p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(8); p.paragraph_format.space_after = Pt(6)
            r = p.add_run(line[4:].strip()); set_run(r, font='黑体', size=12, bold=True)
        elif line.startswith('- '):
            para('• ' + line[2:].strip(), first=False)
        elif line.startswith('**') and line.endswith('**'):
            para(line.replace('**',''), first=False, bold=True)
        elif line.startswith('[') and re.match(r'^\[\d+\]', line):
            para(line, first=False, size=10)
        elif line.strip() == '---':
            continue
        else:
            para(line.replace('**',''))
    flush_code(); flush_table()
    footer = doc.sections[0].footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = footer.add_run(f'{TITLE} · 完整论文证据流闭环版')
    set_run(r, size=9, color='666666')
    DOCX.mkdir(parents=True, exist_ok=True)
    doc.save(OUT_DOCX)
    return True, str(OUT_DOCX)


def main():
    md = build_markdown()
    OUT_MD.write_text(md, encoding='utf-8')
    ok, msg = build_docx(md)
    print(OUT_MD)
    print(msg)

if __name__ == '__main__':
    main()
