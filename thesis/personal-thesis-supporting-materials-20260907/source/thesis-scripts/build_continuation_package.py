#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build continuation outputs for the advertisement-video QA thesis.

All outputs are written under /Users/bytedance/vqa_thesis_continue, not under efs-mgr.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/bytedance/vqa_thesis_continue")
DOCS = ROOT / "docs"
RAG = ROOT / "rag_mvp"
DOCX_DIR = ROOT / "docx"

TITLE = "基于视听协同感知与链式校验的广告视频问答方法"
DATE = "2026年6月18日"


KB_ITEMS = [
    {
        "id": "K0001",
        "category": ["营销理论", "传播模型"],
        "title": "AIDA 模型",
        "type": "marketing_framework",
        "keywords": ["注意", "兴趣", "欲望", "行动", "转化", "引导购买"],
        "aliases": ["Attention Interest Desire Action"],
        "content": "AIDA 模型将广告说服过程划分为吸引注意、激发兴趣、唤起欲望和促成行动四个阶段，常用于分析广告是否具备完整转化链路。",
        "applicable_scenarios": ["短视频广告分析", "广告文案评价", "转化路径诊断"],
        "risk_notes": [],
        "retrieval_text": "AIDA 注意 兴趣 欲望 行动 广告转化 文案结构 引导购买",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0002",
        "category": ["广告创意", "痛点营销"],
        "title": "PAS 痛点解决模型",
        "type": "creative_strategy",
        "keywords": ["痛点", "焦虑", "问题", "解决方案", "困扰", "烦恼"],
        "aliases": ["Problem Agitation Solution"],
        "content": "PAS 模型通过指出用户问题、放大问题带来的不便，再提供产品作为解决方案，适合用于高需求导向的广告内容。",
        "applicable_scenarios": ["教育广告", "健康管理广告", "工具类产品广告", "生活服务广告"],
        "risk_notes": ["避免制造过度焦虑", "避免夸大产品效果"],
        "retrieval_text": "痛点 焦虑 问题 放大 解决方案 PAS 广告创意",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0003",
        "category": ["营销理论", "卖点表达"],
        "title": "FAB 卖点表达法",
        "type": "copywriting_framework",
        "keywords": ["功能", "优势", "利益", "卖点", "特点", "好处"],
        "aliases": ["Feature Advantage Benefit"],
        "content": "FAB 方法强调广告应从产品功能出发，解释其相对优势，并最终转化为用户可感知的实际利益。",
        "applicable_scenarios": ["产品详情页", "功能型广告", "新品介绍", "技术产品广告"],
        "risk_notes": [],
        "retrieval_text": "功能 优势 利益 卖点 FAB 产品广告 特点 好处",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0004",
        "category": ["消费者心理", "社会认同"],
        "title": "社会认同效应",
        "type": "consumer_psychology",
        "keywords": ["大家都在用", "好评", "销量", "用户推荐", "口碑", "热门"],
        "aliases": ["social proof"],
        "content": "社会认同效应指消费者会参考他人的选择、评价和使用经验来降低决策不确定性。",
        "applicable_scenarios": ["电商广告", "口碑广告", "UGC 广告", "达人推荐"],
        "risk_notes": ["销量、评价、用户数量等数据应真实可验证"],
        "retrieval_text": "大家都在用 好评 销量 用户推荐 口碑 社会认同 热门",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0005",
        "category": ["消费者心理", "稀缺效应"],
        "title": "稀缺效应",
        "type": "consumer_psychology",
        "keywords": ["限时", "限量", "抢购", "库存", "倒计时", "最后一天"],
        "aliases": ["scarcity effect"],
        "content": "稀缺效应通过强调时间、库存或名额有限来提升用户的紧迫感，从而促进点击或购买行为。",
        "applicable_scenarios": ["促销广告", "直播带货", "优惠券领取", "电商大促"],
        "risk_notes": ["不得虚构库存或活动截止时间"],
        "retrieval_text": "限时 限量 抢购 库存 倒计时 最后一天 稀缺效应 促销",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0006",
        "category": ["广告创意", "场景化表达"],
        "title": "场景化广告",
        "type": "creative_strategy",
        "keywords": ["使用场景", "生活场景", "代入感", "用户情境", "家庭", "职场"],
        "aliases": ["scenario-based advertising"],
        "content": "场景化广告通过展示产品在具体生活或工作情境中的使用方式，降低用户理解成本并增强代入感。",
        "applicable_scenarios": ["家电广告", "食品饮料广告", "本地生活广告", "工具产品广告"],
        "risk_notes": [],
        "retrieval_text": "使用场景 生活场景 代入感 情境 家庭 职场 场景化广告",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0007",
        "category": ["广告创意", "UGC"],
        "title": "UGC 用户证言广告",
        "type": "creative_strategy",
        "keywords": ["真实体验", "用户评价", "素人推荐", "开箱", "测评", "亲测"],
        "aliases": ["user generated content"],
        "content": "UGC 广告以普通用户的体验、评价或测评作为主要内容，能够提升广告的真实感和可信度。",
        "applicable_scenarios": ["美妆广告", "数码测评", "食品试吃", "服务体验"],
        "risk_notes": ["用户体验不得伪造", "功效类表述需谨慎"],
        "retrieval_text": "真实体验 用户评价 素人推荐 开箱 测评 UGC 广告 亲测",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0008",
        "category": ["营销理论", "价格策略"],
        "title": "价格锚定",
        "type": "pricing_strategy",
        "keywords": ["原价", "现价", "折扣", "对比价", "优惠", "立减"],
        "aliases": ["price anchoring"],
        "content": "价格锚定通过展示参考价格与当前价格之间的差异，使消费者感知当前报价更具吸引力。",
        "applicable_scenarios": ["电商促销", "会员折扣", "课程售卖", "团购广告"],
        "risk_notes": ["参考价格应具有真实依据，避免价格欺诈"],
        "retrieval_text": "原价 现价 折扣 对比价 优惠 立减 价格锚定",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0009",
        "category": ["合规风险", "绝对化用语"],
        "title": "绝对化广告表述风险",
        "type": "compliance_rule",
        "keywords": ["最", "第一", "顶级", "唯一", "永久", "全网第一"],
        "aliases": ["absolute claim risk"],
        "content": "广告中使用无法证实的绝对化表述可能带来合规风险，例如“全网第一”“唯一有效”“永久解决”等。",
        "applicable_scenarios": ["广告文案审核", "生成结果约束", "风险识别"],
        "risk_notes": ["建议替换为可验证、相对温和的表达"],
        "retrieval_text": "最 第一 顶级 唯一 永久 全网第一 绝对化 表述 风险",
        "source": "advertising_compliance_common_rule",
        "version": "1.1",
    },
    {
        "id": "K0010",
        "category": ["投放目标", "营销漏斗"],
        "title": "广告营销漏斗",
        "type": "marketing_framework",
        "keywords": ["认知", "兴趣", "考虑", "转化", "复购", "留存"],
        "aliases": ["marketing funnel"],
        "content": "广告营销漏斗将用户从接触广告到最终转化的过程划分为认知、兴趣、考虑、转化和复购等阶段，可用于判断广告内容服务于哪一类投放目标。",
        "applicable_scenarios": ["广告目标识别", "素材策略分析", "投放效果解释"],
        "risk_notes": [],
        "retrieval_text": "认知 兴趣 考虑 转化 复购 留存 营销漏斗 广告目标",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0011",
        "category": ["消费者心理", "损失规避"],
        "title": "损失规避",
        "type": "consumer_psychology",
        "keywords": ["错过", "亏", "机会", "别等", "不买后悔"],
        "aliases": ["loss aversion"],
        "content": "损失规避强调人们对损失的敏感度通常高于同等收益，广告可通过“错过成本”强化行动动机。",
        "applicable_scenarios": ["限时促销", "会员权益", "课程报名", "新品预约"],
        "risk_notes": ["避免恐吓式或过度焦虑式表达"],
        "retrieval_text": "错过 亏 机会 别等 不买后悔 损失规避 行动动机",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0012",
        "category": ["消费者心理", "权威背书"],
        "title": "权威背书",
        "type": "consumer_psychology",
        "keywords": ["专家", "认证", "获奖", "机构", "官方", "推荐"],
        "aliases": ["authority endorsement"],
        "content": "权威背书通过专家、机构、认证或奖项降低用户的不信任感，提高广告主张的可信度。",
        "applicable_scenarios": ["健康广告", "教育广告", "科技产品", "品牌信任建设"],
        "risk_notes": ["背书来源需真实，避免虚假认证"],
        "retrieval_text": "专家 认证 获奖 机构 官方 推荐 权威背书 可信度",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0013",
        "category": ["广告创意", "情绪共鸣"],
        "title": "情绪共鸣策略",
        "type": "creative_strategy",
        "keywords": ["感动", "温暖", "治愈", "陪伴", "快乐", "焦虑缓解"],
        "aliases": ["emotional appeal"],
        "content": "情绪共鸣策略通过亲情、友情、陪伴、梦想或治愈等情绪线索，使受众将产品与情感价值建立联系。",
        "applicable_scenarios": ["品牌广告", "节日广告", "公益广告", "高情感商品"],
        "risk_notes": ["避免与产品功能脱节导致空泛表达"],
        "retrieval_text": "感动 温暖 治愈 陪伴 快乐 焦虑缓解 情绪共鸣 情感诉求",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0014",
        "category": ["广告创意", "视觉隐喻"],
        "title": "视觉隐喻",
        "type": "creative_strategy",
        "keywords": ["隐喻", "象征", "比喻", "夸张", "对比", "拟人"],
        "aliases": ["visual metaphor"],
        "content": "视觉隐喻通过象征性画面或夸张表达，将抽象卖点转化为可视化形象，例如用闪电表现速度、用盾牌表现安全。",
        "applicable_scenarios": ["品牌创意广告", "功能强化广告", "概念产品宣传"],
        "risk_notes": ["解释隐喻时应回到视频证据，避免过度阐释"],
        "retrieval_text": "隐喻 象征 比喻 夸张 对比 拟人 视觉隐喻 抽象卖点",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0015",
        "category": ["广告创意", "前后对比"],
        "title": "前后对比策略",
        "type": "creative_strategy",
        "keywords": ["使用前", "使用后", "对比", "变化", "改善", "差异"],
        "aliases": ["before-after comparison"],
        "content": "前后对比策略通过展示使用产品前后的状态差异，使产品价值更直观。",
        "applicable_scenarios": ["美妆广告", "清洁用品", "健身课程", "工具类产品"],
        "risk_notes": ["功效对比应避免夸大，必要时需证据支撑"],
        "retrieval_text": "使用前 使用后 对比 变化 改善 差异 前后对比 产品价值",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0016",
        "category": ["广告创意", "问题解决叙事"],
        "title": "问题—解决叙事",
        "type": "creative_strategy",
        "keywords": ["遇到问题", "解决", "办法", "神器", "省心", "方便"],
        "aliases": ["problem-solution narrative"],
        "content": "问题—解决叙事先呈现具体痛点或任务阻碍，再展示产品如何解决问题，适合强调效率、便利或功能价值。",
        "applicable_scenarios": ["工具软件", "家居清洁", "生活服务", "办公效率"],
        "risk_notes": [],
        "retrieval_text": "遇到问题 解决 办法 神器 省心 方便 问题解决叙事",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0017",
        "category": ["受众分析", "人群定位"],
        "title": "目标受众画像",
        "type": "audience_analysis",
        "keywords": ["年轻人", "宝妈", "白领", "学生", "老人", "家庭"],
        "aliases": ["target audience persona"],
        "content": "目标受众画像根据年龄、职业、生活方式、消费需求和使用场景推断广告希望触达的人群。",
        "applicable_scenarios": ["受众分析", "投放策略", "素材定向", "内容评估"],
        "risk_notes": ["受众判断应基于视频中的人物、场景、语言和产品线索"],
        "retrieval_text": "年轻人 宝妈 白领 学生 老人 家庭 目标受众画像 人群定位",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0018",
        "category": ["平台内容", "短视频节奏"],
        "title": "短视频黄金三秒",
        "type": "platform_content_strategy",
        "keywords": ["开头", "前三秒", "吸引", "悬念", "钩子", "标题"],
        "aliases": ["first three seconds hook"],
        "content": "短视频广告常在开头几秒通过强视觉冲击、问题、悬念或利益点快速吸引注意，以降低划走率。",
        "applicable_scenarios": ["信息流广告", "短视频广告", "直播预热视频"],
        "risk_notes": ["钩子应与后续内容一致，避免标题党"],
        "retrieval_text": "开头 前三秒 吸引 悬念 钩子 标题 黄金三秒 信息流广告",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0019",
        "category": ["广告创意", "利益点前置"],
        "title": "利益点前置",
        "type": "copywriting_strategy",
        "keywords": ["直接说好处", "省钱", "省时", "免费", "领取", "福利"],
        "aliases": ["benefit-first copywriting"],
        "content": "利益点前置指在广告开头或核心画面中直接呈现用户收益，以提高信息获取效率和转化意愿。",
        "applicable_scenarios": ["电商广告", "应用下载广告", "课程广告", "本地生活广告"],
        "risk_notes": ["福利、免费等表述需说明条件，避免误导"],
        "retrieval_text": "直接说好处 省钱 省时 免费 领取 福利 利益点前置",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0020",
        "category": ["广告创意", "品牌记忆"],
        "title": "品牌资产一致性",
        "type": "brand_strategy",
        "keywords": ["logo", "标志", "品牌色", "口号", "吉祥物", "包装"],
        "aliases": ["brand asset consistency"],
        "content": "品牌资产一致性强调在广告中重复使用 Logo、品牌色、口号、包装或吉祥物，帮助受众形成稳定品牌记忆。",
        "applicable_scenarios": ["品牌广告", "新品发布", "系列广告", "品牌焕新"],
        "risk_notes": [],
        "retrieval_text": "logo 标志 品牌色 口号 吉祥物 包装 品牌资产 一致性 品牌记忆",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0021",
        "category": ["广告创意", "行动召唤"],
        "title": "CTA 行动召唤",
        "type": "conversion_strategy",
        "keywords": ["点击", "购买", "领取", "扫码", "下载", "马上"],
        "aliases": ["call to action", "CTA"],
        "content": "CTA 行动召唤通过明确的动词和路径引导用户完成点击、购买、下载、扫码或领取等行为。",
        "applicable_scenarios": ["效果广告", "电商促销", "应用下载", "活动报名"],
        "risk_notes": ["行动路径应真实可达，避免诱导性误导"],
        "retrieval_text": "点击 购买 领取 扫码 下载 马上 CTA 行动召唤 转化",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0022",
        "category": ["商品表达", "产品特写"],
        "title": "产品特写强化",
        "type": "visual_strategy",
        "keywords": ["特写", "近景", "包装", "细节", "质感", "展示"],
        "aliases": ["product close-up"],
        "content": "产品特写通过近距离展示包装、材质、使用细节或效果，强化产品识别和品质感。",
        "applicable_scenarios": ["食品饮料", "美妆护肤", "数码产品", "家居用品"],
        "risk_notes": ["视觉效果不应明显误导实际产品状态"],
        "retrieval_text": "特写 近景 包装 细节 质感 展示 产品特写 品质感",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0023",
        "category": ["音频表达", "旁白卖点"],
        "title": "旁白卖点强化",
        "type": "audio_strategy",
        "keywords": ["旁白", "口播", "介绍", "说明", "强调", "卖点"],
        "aliases": ["voice-over selling point"],
        "content": "旁白或口播常用于补充画面难以直接表达的功能、价格、场景或品牌主张，是广告视频问答中的关键音频证据。",
        "applicable_scenarios": ["口播广告", "信息流广告", "产品讲解", "直播切片"],
        "risk_notes": ["ASR 噪声会影响证据提取，应结合视觉和 OCR 校验"],
        "retrieval_text": "旁白 口播 介绍 说明 强调 卖点 音频证据 ASR",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0024",
        "category": ["文字表达", "字幕承诺"],
        "title": "字幕承诺与屏幕文字",
        "type": "textual_strategy",
        "keywords": ["字幕", "画面文字", "价格", "优惠", "承诺", "说明"],
        "aliases": ["on-screen text claim"],
        "content": "广告中的屏幕文字常直接承载价格、优惠、功能承诺和限制条件，回答细节问题时应优先核查 OCR 证据。",
        "applicable_scenarios": ["促销广告", "字幕密集广告", "详情讲解", "优惠说明"],
        "risk_notes": ["OCR 错误可能导致价格或数字误读，应进行链式校验"],
        "retrieval_text": "字幕 画面文字 价格 优惠 承诺 说明 OCR 屏幕文字",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0025",
        "category": ["合规风险", "功效宣称"],
        "title": "功效宣称风险",
        "type": "compliance_rule",
        "keywords": ["治愈", "根治", "保证", "有效", "改善", "功效"],
        "aliases": ["efficacy claim risk"],
        "content": "涉及健康、美妆、教育等领域的功效宣称应基于可验证证据，生成答案时不能将普通宣传语扩展为确定性效果。",
        "applicable_scenarios": ["健康广告", "美妆广告", "教育培训", "保健品"],
        "risk_notes": ["避免绝对化、医疗化或无依据功效表达"],
        "retrieval_text": "治愈 根治 保证 有效 改善 功效 宣称 风险",
        "source": "advertising_compliance_common_rule",
        "version": "1.1",
    },
    {
        "id": "K0026",
        "category": ["内容结构", "故事化叙事"],
        "title": "故事化广告叙事",
        "type": "creative_strategy",
        "keywords": ["故事", "人物", "冲突", "转折", "结局", "剧情"],
        "aliases": ["storytelling advertising"],
        "content": "故事化广告通过人物、冲突、转折和结局组织信息，使产品或品牌价值嵌入情节之中。",
        "applicable_scenarios": ["品牌广告", "公益广告", "高情感商品", "长视频广告"],
        "risk_notes": ["需区分情节事实与广告寓意，避免过度推断"],
        "retrieval_text": "故事 人物 冲突 转折 结局 剧情 故事化广告 叙事",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0027",
        "category": ["广告创意", "反差冲突"],
        "title": "反差冲突策略",
        "type": "creative_strategy",
        "keywords": ["反差", "冲突", "出乎意料", "转折", "尴尬", "惊喜"],
        "aliases": ["contrast conflict"],
        "content": "反差冲突策略通过制造预期与结果之间的差异，引发注意和记忆点，并进一步引出产品价值。",
        "applicable_scenarios": ["短视频广告", "喜剧广告", "情节广告", "新品认知"],
        "risk_notes": ["反差解释需与视频画面或旁白证据对应"],
        "retrieval_text": "反差 冲突 出乎意料 转折 尴尬 惊喜 记忆点",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0028",
        "category": ["受众分析", "使用动机"],
        "title": "用户使用动机",
        "type": "audience_analysis",
        "keywords": ["省时间", "省钱", "变美", "健康", "安全", "效率"],
        "aliases": ["user motivation"],
        "content": "用户使用动机指用户选择产品或服务背后的核心需求，如省时、省钱、提升形象、健康、安全或效率。",
        "applicable_scenarios": ["受众需求分析", "卖点归因", "产品定位", "文案评估"],
        "risk_notes": ["动机推断应结合广告问题、人物场景和产品类型"],
        "retrieval_text": "省时间 省钱 变美 健康 安全 效率 使用动机 核心需求",
        "source": "marketing_common_knowledge",
        "version": "1.1",
    },
    {
        "id": "K0029",
        "category": ["评价指标", "可解释性"],
        "title": "证据一致性",
        "type": "evaluation_concept",
        "keywords": ["证据", "一致", "支撑", "依据", "可解释", "引用"],
        "aliases": ["evidence consistency"],
        "content": "证据一致性衡量模型答案中的核心断言是否可由视频帧、ASR、OCR 或检索知识直接支撑。",
        "applicable_scenarios": ["链式校验", "人工评分", "幻觉检测", "实验指标"],
        "risk_notes": [],
        "retrieval_text": "证据 一致 支撑 依据 可解释 引用 证据一致性 幻觉检测",
        "source": "thesis_evaluation_design",
        "version": "1.1",
    },
    {
        "id": "K0030",
        "category": ["评价指标", "知识一致性"],
        "title": "知识一致性",
        "type": "evaluation_concept",
        "keywords": ["知识", "营销概念", "一致", "匹配", "误用", "策略"],
        "aliases": ["knowledge consistency"],
        "content": "知识一致性衡量模型是否正确使用营销概念，避免将普通促销误判为复杂策略或引入与视频无关的外部知识。",
        "applicable_scenarios": ["RAG 消融", "人工评分", "营销策略问答", "错误分析"],
        "risk_notes": [],
        "retrieval_text": "知识 营销概念 一致 匹配 误用 策略 知识一致性 RAG",
        "source": "thesis_evaluation_design",
        "version": "1.1",
    },
]

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[一-鿿]")
EXPANSION_RULES = [
    (["限时", "限量", "倒计时", "抢购", "库存", "最后一天"], ["稀缺效应", "促销", "紧迫感", "损失规避"]),
    (["大家都在用", "销量", "好评", "推荐", "口碑", "热门"], ["社会认同", "UGC", "用户证言"]),
    (["原价", "现价", "折扣", "优惠", "对比价", "立减"], ["价格锚定", "优惠感知", "利益点前置"]),
    (["痛点", "烦恼", "困扰", "问题", "解决"], ["PAS", "痛点营销", "问题解决叙事"]),
    (["第一", "唯一", "永久", "最", "顶级", "保证"], ["绝对化用语", "功效宣称风险", "合规风险"]),
    (["场景", "生活", "使用", "家庭", "职场"], ["场景化广告", "代入感", "目标受众画像"]),
    (["logo", "标志", "品牌色", "口号", "包装"], ["品牌资产一致性", "品牌记忆"]),
    (["旁白", "口播", "字幕", "画面文字", "价格"], ["旁白卖点", "字幕承诺", "证据一致性"]),
]


RETRIEVER = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Advertisement-marketing RAG retriever MVP.

This continuation version keeps the no-external-dependency baseline from the previous
history, expands the knowledge base to 30 entries, and adds an optional evidence-aware
rerank term. It is intended for thesis experiments and prompt generation.
"""
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[一-鿿]")
EXPANSION_RULES = [
    (["限时", "限量", "倒计时", "抢购", "库存", "最后一天"], ["稀缺效应", "促销", "紧迫感", "损失规避"]),
    (["大家都在用", "销量", "好评", "推荐", "口碑", "热门"], ["社会认同", "UGC", "用户证言"]),
    (["原价", "现价", "折扣", "优惠", "对比价", "立减"], ["价格锚定", "优惠感知", "利益点前置"]),
    (["痛点", "烦恼", "困扰", "问题", "解决"], ["PAS", "痛点营销", "问题解决叙事"]),
    (["第一", "唯一", "永久", "最", "顶级", "保证"], ["绝对化用语", "功效宣称风险", "合规风险"]),
    (["场景", "生活", "使用", "家庭", "职场"], ["场景化广告", "代入感", "目标受众画像"]),
    (["logo", "标志", "品牌色", "口号", "包装"], ["品牌资产一致性", "品牌记忆"]),
    (["旁白", "口播", "字幕", "画面文字", "价格"], ["旁白卖点", "字幕承诺", "证据一致性"]),
]


def tokenize(text: str):
    return TOKEN_RE.findall((text or "").lower())


def encode_text(text: str) -> Counter:
    return Counter(tokenize(text))


def cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def expand_query(text: str) -> str:
    extras = []
    for triggers, expansions in EXPANSION_RULES:
        if any(t.lower() in text.lower() for t in triggers):
            extras.extend(expansions)
    return text + ("\n扩展关键词：" + " ".join(dict.fromkeys(extras)) if extras else "")


def build_query(question="", asr="", ocr="", visual_tags="") -> str:
    base = f"用户问题：{question}\n广告语音内容：{asr}\n画面文字内容：{ocr}\n视觉识别标签：{visual_tags}"
    return expand_query(base)


def keyword_score(query_text: str, item: dict) -> float:
    q = set(tokenize(query_text))
    kws = []
    for key in ("keywords", "aliases"):
        for v in item.get(key, []):
            kws.extend(tokenize(v))
    if not kws:
        return 0.0
    return len(q & set(kws)) / max(len(set(kws)), 1)


def evidence_score(question: str, asr: str, ocr: str, visual_tags: str, item: dict) -> float:
    """Reward knowledge that matches actual video evidence, not only the question."""
    item_vec = encode_text(" ".join(item.get("keywords", [])) + " " + item.get("retrieval_text", ""))
    ev_vec = encode_text("\n".join([asr, ocr, visual_tags]))
    q_vec = encode_text(question)
    return 0.7 * cosine(ev_vec, item_vec) + 0.3 * cosine(q_vec, item_vec)


def category_prior(item: dict) -> float:
    cats = " ".join(item.get("category", []))
    if "合规" in cats:
        return 0.12
    if "营销理论" in cats or "广告创意" in cats:
        return 0.10
    if "消费者心理" in cats:
        return 0.08
    if "评价指标" in cats:
        return 0.04
    return 0.05


def retrieve(kb, question, asr="", ocr="", visual_tags="", topk=5, threshold=0.05):
    query_text = build_query(question, asr, ocr, visual_tags)
    qv = encode_text(query_text)
    results = []
    for item in kb:
        item_text = " ".join([
            item.get("title", ""),
            item.get("content", ""),
            item.get("retrieval_text", ""),
            " ".join(item.get("keywords", [])),
            " ".join(item.get("applicable_scenarios", [])),
        ])
        semantic = cosine(qv, encode_text(item_text))
        kw = keyword_score(query_text, item)
        ev = evidence_score(question, asr, ocr, visual_tags, item)
        prior = category_prior(item)
        final = 0.55 * semantic + 0.20 * kw + 0.20 * ev + 0.05 * prior
        if final >= threshold:
            results.append({
                "score": round(final, 4),
                "semantic": round(semantic, 4),
                "keyword": round(kw, 4),
                "evidence": round(ev, 4),
                "item": item,
            })
    results.sort(key=lambda x: x["score"], reverse=True)
    return query_text, results[:topk]


def format_prompt(question, asr, ocr, visual_tags, retrieved):
    blocks = []
    for r in retrieved:
        it = r["item"]
        risks = "；".join(it.get("risk_notes", [])) or "无"
        blocks.append(
            f"[知识 {it['id']} | {it['title']} | score={r['score']} | evidence={r['evidence']}]\n"
            f"{it['content']}\n"
            f"适用线索：{'、'.join(it.get('keywords', []))}\n"
            f"风险提示：{risks}"
        )
    knowledge = "\n\n".join(blocks) if blocks else "未检索到高置信度外部知识，请仅基于视频证据谨慎回答。"
    return f"""你是一个广告视频问答助手。请优先基于视频中的 ASR、OCR 和视觉信息回答，外部知识只能作为解释辅助，不得编造视频中不存在的品牌、价格、功效或事实。\n\n【广告营销专家知识】\n{knowledge}\n\n【用户问题】\n{question}\n\n【ASR 语音文本】\n{asr}\n\n【OCR 画面文字】\n{ocr}\n\n【视觉标签】\n{visual_tags}\n\n请按以下结构回答：\n1. 观察：列出可见、可听、可读证据；\n2. 知识匹配：说明哪些知识适用，哪些不适用；\n3. 分析：解释证据与广告意图、策略或受众之间的关系；\n4. 答案：给出简洁结论；\n5. 校验：指出答案中哪些断言由哪些证据支撑。\n要求：证据不足时使用“可能”“倾向于”；如果关键证据缺失，应说明无法确定。\n"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default=str(Path(__file__).with_name("marketing_knowledge_base_extended.json")))
    ap.add_argument("--question", default="这个广告使用了什么营销策略？")
    ap.add_argument("--asr", default="")
    ap.add_argument("--ocr", default="")
    ap.add_argument("--visual-tags", default="")
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--threshold", type=float, default=0.05)
    ap.add_argument("--prompt", action="store_true")
    args = ap.parse_args()

    kb = json.loads(Path(args.kb).read_text(encoding="utf-8"))
    query, results = retrieve(kb, args.question, args.asr, args.ocr, args.visual_tags, args.topk, args.threshold)
    if args.prompt:
        print(format_prompt(args.question, args.asr, args.ocr, args.visual_tags, results))
    else:
        print(json.dumps({"query": query, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
'''

README = f"""# {TITLE}：续写工作区

本目录是按照“不要在 efs 目录下输出”的要求新建的续写目录，位置：

```text
{ROOT}
```

## 与历史产出的衔接

历史已完成：

- 论文初稿与优化稿；
- 图示设计与第 5 章实验计划；
- RAG MVP（10 条广告营销知识 + 无依赖检索脚本）；
- 多 Agent 编排方案与论文待办清单。

本次续写沿着历史继续，重点补齐：

1. 第 2 章相关理论与技术基础的扩写版；
2. RAG MVP 扩展到 30 条知识条目，并增加证据感知重排序项；
3. RAG/链式校验/效率实验的可执行记录模板；
4. 案例分析与错误归因模板；
5. 答辩 Q&A 与后续待办清单。

## 文件说明

- `docs/论文续写整合稿.md`：可并入论文的续写正文；
- `docs/实验补充计划与记录模板.md`：RAG、链式校验、效率、参数敏感性实验模板；
- `docs/答辩Q&A.md`：模拟答辩问题与回答；
- `rag_mvp/marketing_knowledge_base_extended.json`：30 条广告营销知识库；
- `rag_mvp/rag_retriever.py`：无外部依赖检索脚本；
- `docx/基于视听协同感知与链式校验的广告视频问答方法_续写稿_20260618.docx`：本次续写 Word 文档；
- `build_continuation_package.py`：生成本目录所有产物的脚本。

## 快速运行 RAG MVP

```bash
python3 {RAG / 'rag_retriever.py'} \
  --question "这个广告如何制造紧迫感？" \
  --asr "限时优惠，仅剩最后一天" \
  --ocr "限时抢购 立减50" \
  --visual-tags "倒计时, 电商促销, 商品展示" \
  --topk 5
```

生成可注入大模型的 Prompt：

```bash
python3 {RAG / 'rag_retriever.py'} \
  --question "这个广告如何制造紧迫感？" \
  --asr "限时优惠，仅剩最后一天" \
  --ocr "限时抢购 立减50" \
  --visual-tags "倒计时, 电商促销, 商品展示" \
  --topk 5 \
  --prompt
```
"""

THESIS_MD = f"""# {TITLE}：续写整合稿

> 生成日期：{DATE}
> 续写位置：`{ROOT}`
> 衔接历史版本：论文优化稿、RAG MVP、图示设计与第 5 章实验计划。

---

## 一、当前论文状态与续写目标

根据历史材料，论文主线已经较清晰：广告视频具有信息密度高、声画非严格同步、品牌与营销语义依赖外部知识、生成式回答容易幻觉等特点。因此论文方法应持续围绕三个核心模块展开：

1. **视听协同感知与视觉 Token 压缩**：用问题、ASR、OCR/Logo 等线索共同定位关键视觉帧和局部区域，在减少冗余输入的同时保留细粒度证据。
2. **广告知识增强 RAG 推理**：构建广告营销知识库，将营销理论、消费者心理、创意策略、合规风险等知识注入问答过程，但坚持“视频证据优先、外部知识辅助”。
3. **链式校验优化**：对答案中的事实、时序、模态一致性和知识使用进行逐项核查，降低无依据扩展和营销策略误归因。

本次续写优先补齐历史待办中的 P0/P1 项：第 2 章相关理论扩写、RAG MVP 扩展、RAG 与链式校验消融实验、效率实验、案例分析和答辩 Q&A。

---

## 二、第 2 章《相关理论与技术基础》扩写稿

### 2.1 视频问答与广告视频理解

视频问答（Video Question Answering, VideoQA）是多模态理解领域中的典型任务，其输入通常包括一段视频和一个自然语言问题，输出则是与视频内容和问题语义相匹配的自然语言答案。与图像问答相比，视频问答需要同时处理空间对象识别、时间事件演化、跨帧关系建模和语言语义理解等问题。模型不仅需要判断某一帧中出现了什么对象，还需要理解事件发生的先后顺序、人物行为的变化、画面与语音之间的对应关系，以及问题所要求的回答粒度。

广告视频问答是视频问答在智能营销场景中的垂直延伸。广告视频通常在较短时长内集中呈现产品、品牌、使用场景、人物情绪、促销信息和行动召唤等内容，具有节奏快、镜头切换频繁、视觉元素密集和语义高度压缩等特点。用户提出的问题也往往不仅局限于事实识别，还会涉及广告意图、受众定位、情感诉求、营销策略和品牌记忆等高层语义。例如，“这个广告主要面向哪类人群？”“广告通过什么方式制造紧迫感？”“画面中的文字承诺了什么优惠？”这类问题要求模型综合画面、字幕、旁白和领域知识进行推断。

因此，广告视频问答比通用视频问答更强调多模态证据协同和专业知识约束。一方面，广告中的 Logo、价格字幕、商品包装和短暂出现的促销文字可能是回答问题的关键证据；另一方面，广告意图和营销策略往往不能仅从表层画面直接得出，而需要借助营销学、消费者心理学和传播学知识进行解释。本文后续提出的视听协同特征压缩、广告知识增强 RAG 和链式校验机制，正是为解决这一垂直场景中的证据定位、知识补充和答案可靠性问题。

### 2.2 多模态大语言模型与视频理解

多模态大语言模型通过将视觉、音频等模态信息映射到大语言模型可处理的语义空间，使模型能够基于图像、视频、语音和文本完成描述、问答、推理和总结等任务。典型架构通常包括视觉编码器、音频或语音处理模块、跨模态投影层以及大语言模型主体。视觉编码器负责提取图像或视频帧的局部和全局表示，投影层将这些表示转换为语言模型可接收的 Token 或嵌入，大语言模型则在多模态上下文中进行语言生成和推理。

在视频理解任务中，多模态大语言模型具备开放词汇识别、自然语言解释和跨任务泛化能力，能够处理事实性问答、事件描述、原因分析、情感判断等多类问题。然而，在广告视频问答场景中，通用模型仍存在三方面不足。第一，视频帧和视觉 Token 数量随采样频率快速增长，直接输入完整视频会带来较高计算开销，并可能引入大量无关镜头。第二，广告视频依赖品牌、商品、营销策略和合规知识，通用模型可能缺少相关领域知识，导致回答表层化或概念误用。第三，生成式模型在证据不足时容易根据常识补全答案，产生看似合理但缺乏视频证据支撑的幻觉内容。

针对上述不足，本文并不将多模态大语言模型视为完全端到端的黑盒系统，而是将其嵌入一个“证据压缩—知识增强—链式校验”的任务框架中。模型的输入由问题相关的关键视觉帧、局部区域、ASR/OCR 文本和检索知识共同构成；模型的输出则通过结构化推理协议与校验机制进行约束。这样既保留大模型的语义理解和语言生成优势，又增强了广告视频问答所需的证据可追溯性和专业可靠性。

### 2.3 视觉 Token 压缩与关键证据选择

视频输入通常包含大量连续帧，而相邻帧之间往往存在高度冗余。对于广告视频而言，冗余不仅来自相似背景和重复转场，也来自同一产品、同一字幕或同一场景的多次重复出现。若将全部帧或过多视觉 Token 输入多模态大模型，会显著增加上下文长度、显存占用和推理延迟，同时削弱模型对真正关键证据的关注。

视觉 Token 压缩的目标是在控制输入规模的同时保留与任务相关的关键语义。常见方法包括均匀采样、关键帧选择、基于注意力的 Token 剪枝、区域裁剪、聚类合并以及问题引导的动态选择。均匀采样实现简单，但可能遗漏短时出现的 Logo、价格和字幕；纯视觉显著性方法能够发现画面突出区域，却不一定与用户问题相关；问题引导方法能够提升相关性，但需要处理语音、字幕和视觉之间的跨模态关系。

本文将视觉 Token 压缩设计为面向广告视频问答的证据选择过程。首先通过较高频率采样获得候选帧，避免遗漏短时信息；然后利用用户问题、ASR 文本、OCR/Logo 文本和视觉标签共同计算响应分数，选择与问题最相关的关键帧和局部区域；最后构建全局—局部双流视觉表征，使模型同时看到整体场景和细粒度证据。该设计不是单纯追求 Token 最少，而是在压缩率、证据完整性和答案准确性之间取得平衡。

### 2.4 视听协同融合与声画异步处理

广告视频中的语音旁白、背景音乐、画面文字和视觉镜头共同构成传播语义。旁白常用于明确表达产品卖点、促销信息或品牌主张，画面则展示商品外观、使用场景、人物状态和情绪氛围，字幕和屏幕文字进一步补充价格、优惠、功能或行动召唤。不同模态之间具有互补关系，单一模态往往无法完整回答复杂广告问题。

与一般视频不同，广告视频中声画并不总是严格同步。旁白可能先提出痛点，随后画面才展示产品解决方案；也可能在画面切换后继续解释上一镜头的含义。若简单按照时间戳进行一一对应，模型可能错误地将语音内容绑定到不相关画面，造成声画错位。为此，本文采用局部时序滑动窗口聚合方式，在当前视觉帧附近一定时间范围内整合 ASR 语义响应，使语音信息能够以较柔性的方式参与视觉证据定位。

本文的视听协同并非简单拼接 ASR 文本，而是通过响应图显式描述问题、语音和 OCR/Logo 文本对视觉区域的贡献。对于品牌识别类问题，OCR 与 Logo 线索权重更高；对于卖点解释类问题，旁白和字幕通常更重要；对于情绪与氛围类问题，背景音乐、人物表情和场景变化需要共同判断。通过三流响应建模，系统能够更准确地定位关键证据，也为后续链式校验提供可解释依据。

### 2.5 检索增强生成与广告营销知识库

检索增强生成（Retrieval-Augmented Generation, RAG）通过在生成答案前检索外部知识或结构化证据，提升模型回答的事实准确性和可追溯性。在通用问答任务中，RAG 常用于补充文档事实；在广告视频问答中，RAG 的作用不仅是补充事实，还包括提供营销概念、消费者心理、创意策略和合规约束。

广告视频中的许多问题涉及领域知识。例如，“限时抢购”“倒计时”“仅剩最后一天”可对应稀缺效应和损失规避；“大家都在用”“销量领先”“用户好评”可对应社会认同；“原价/现价对比”可对应价格锚定；“专家认证”“官方推荐”可对应权威背书。若模型缺少这些概念，就可能只能停留在表层描述；若模型过度依赖知识，又可能把视频中没有出现的策略强行套入答案。因此，本文 RAG 的核心原则是：外部知识只作为解释辅助，最终答案必须优先受到视频证据支撑。

本次续写将历史 RAG MVP 从 10 条知识扩展到 30 条，并在检索打分中增加证据感知重排序项。最终得分由语义相似度、关键词命中、视频证据匹配度和类别先验共同构成，其中视频证据匹配度用于判断知识条目是否同时与 ASR、OCR 或视觉标签相吻合。这一设计有助于降低“仅因问题文本相似而召回无关知识”的风险。

### 2.6 链式推理、链式校验与幻觉抑制

链式推理通过显式组织“观察—分析—推理—答案”等步骤，使模型在回答复杂问题时先列出证据，再进行概念匹配和结论生成。在广告视频问答中，链式推理有助于区分可观察事实与推断性解释。例如，字幕中出现“限时抢购”是可观察事实，而“广告利用稀缺效应制造紧迫感”是基于事实和营销知识得到的推断。

然而，链式推理本身并不必然保证正确。模型可能在观察阶段遗漏关键证据，在分析阶段错误套用营销概念，或在答案阶段加入未被视频支持的信息。因此，本文进一步引入链式校验机制，将候选答案的可靠性检查拆解为证据覆盖、模态一致性、时间定位和知识约束四个环节。证据覆盖用于判断答案中的核心断言是否可由视频片段、ASR、OCR 或检索知识支撑；模态一致性用于检查视觉、音频和文本证据是否冲突；时间定位用于检查答案引用的事件是否与视频片段对应；知识约束用于检查品牌、功效和营销概念是否被正确使用。

考虑到链式校验会带来额外推理开销，本文采用触发式策略：对于简单事实识别问题，可直接输出初始答案；对于涉及价格、文字、Logo、原因、营销策略、旁白或高风险功效的问题，则启动校验。校验结果可输出确认、修正或拒答，从而在效率和可靠性之间取得平衡。

---

## 三、RAG MVP 续写设计

### 3.1 知识库扩展

历史版本已包含 AIDA、PAS、FAB、社会认同、稀缺效应、场景化广告、UGC、价格锚定、绝对化用语风险和营销漏斗等 10 条知识。本次扩展到 30 条，新增损失规避、权威背书、情绪共鸣、视觉隐喻、前后对比、问题解决叙事、目标受众画像、短视频黄金三秒、利益点前置、品牌资产一致性、CTA 行动召唤、产品特写、旁白卖点、字幕承诺、功效宣称风险、故事化叙事、反差冲突、用户使用动机、证据一致性和知识一致性等条目。

这些条目覆盖论文所需的五类知识：

| 知识类别 | 代表条目 | 论文用途 |
|---|---|---|
| 营销理论 | AIDA、FAB、营销漏斗 | 支撑广告策略解释 |
| 消费者心理 | 稀缺效应、社会认同、损失规避、权威背书 | 支撑受众心理分析 |
| 广告创意 | 场景化广告、视觉隐喻、情绪共鸣、反差冲突 | 支撑主题和创意理解 |
| 多模态证据 | 旁白卖点、字幕承诺、产品特写、品牌资产一致性 | 支撑视听证据分析 |
| 评价与合规 | 证据一致性、知识一致性、绝对化用语、功效宣称风险 | 支撑链式校验与错误分析 |

### 3.2 检索打分公式

本次 RAG MVP 使用无外部依赖的轻量检索方法，便于论文原型复现。设查询文本为 q，知识条目文本为 d，视频证据为 e，则检索得分为：

```text
Score(q,d,e) = 0.55 * Cos(q,d) + 0.20 * Keyword(q,d) + 0.20 * Evidence(e,d) + 0.05 * Prior(d)
```

其中，`Cos(q,d)` 表示查询与知识条目的 TF 余弦相似度；`Keyword(q,d)` 表示关键词命中比例；`Evidence(e,d)` 表示 ASR、OCR 和视觉标签与知识条目的匹配程度；`Prior(d)` 表示类别先验，用于对营销理论、广告创意、消费者心理或合规风险等条目施加轻量偏置。

与历史版本相比，新公式显式加入 Evidence 项，目的是避免仅根据问题文本召回知识。例如用户问“广告用了什么策略”，如果视频证据中没有“限时、倒计时、库存”等线索，就不应高置信召回稀缺效应；如果 OCR 中出现“原价、现价、立减”，则价格锚定和利益点前置更应靠前。

### 3.3 Prompt 注入原则

RAG 结果注入大模型时，应明确三条约束：

1. **证据优先**：视频中的 ASR、OCR、视觉标签和关键帧描述优先级高于外部知识；
2. **知识辅助**：外部知识只用于解释视频中已出现的线索，不能生成视频中不存在的品牌、价格、功效或数据；
3. **不确定性表达**：当证据不足时，答案应使用“可能”“倾向于”“无法确定”等表达，而不是给出确定性结论。

可采用如下回答结构：观察、知识匹配、分析、答案、校验。该结构与论文第 4 章的链式生成协议保持一致。

---

## 四、实验补充文字

### 4.1 RAG 消融实验

RAG 消融实验用于验证广告知识增强对高层语义问题的贡献。建议设置以下方法变体：

| 编号 | 方法设置 | 外部知识 | 证据感知重排序 | Prompt 约束 | 预期观察 |
|---|---|---|---|---|---|
| R0 | 无 RAG 基线 | × | × | 普通问答 | 营销策略和受众分析题较弱 |
| R1 | 仅知识注入 | √ | × | 普通注入 | 专业性提升，但可能引入噪声 |
| R2 | 知识注入 + 阈值过滤 | √ | × | 证据优先 | 无关知识减少 |
| R3 | 知识注入 + 证据感知重排序 | √ | √ | 证据优先 | 策略判断更稳健 |
| R4 | 完整 RAG + 链式校验 | √ | √ | 观察—分析—答案—校验 | 幻觉率最低 |

实验指标除 Accuracy/F1 外，建议增加知识一致性和无关知识注入率。知识一致性可由人工评分判断模型是否正确使用营销概念；无关知识注入率可统计答案中出现但视频证据不支持的外部知识比例。

### 4.2 链式校验消融实验

链式校验消融实验用于验证答案可靠性提升是否来自校验环节，而非仅来自更长 Prompt。建议设置：

| 编号 | 方法设置 | 校验触发 | 校验内容 | 预期效果 |
|---|---|---|---|---|
| C0 | 无校验 | × | × | 推理最快，但细节题幻觉较高 |
| C1 | 固定一轮校验 | 全部样本 | 事实一致性 | 幻觉下降，耗时上升明显 |
| C2 | 触发式校验 | 高风险问题 | 事实/模态/知识一致性 | 性价比较高 |
| C3 | 触发式 + 拒答策略 | 高风险问题 | 证据不足可拒答 | 准确性提升，覆盖率下降 |

建议重点报告三类指标：答案准确率、幻觉率、平均推理时间。若 C2 在幻觉率和耗时之间取得更好平衡，即可支撑“触发式链式校验”设计的合理性。

### 4.3 效率实验

效率实验需体现视觉 Token 压缩的实际价值。建议记录如下指标：平均关键帧数、平均视觉 Token 数、平均输入 Token 数、平均输出 Token 数、推理时延、RAG 检索耗时、校验耗时和峰值显存。若暂时缺少真实运行数据，可先按模板占位，待实验完成后填入。

| 方法 | 平均关键帧数 | 平均输入 Token | 压缩率 | RAG 耗时/ms | 校验耗时/ms | 总耗时/ms | Accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| 无压缩基线 | 待补 | 待补 | 0% | 0 | 0 | 待补 | 待补 |
| 均匀采样 | 待补 | 待补 | 待补 | 0 | 0 | 待补 | 待补 |
| 问题引导压缩 | 待补 | 待补 | 待补 | 0 | 0 | 待补 | 待补 |
| 双流压缩 + RAG | 待补 | 待补 | 待补 | 待补 | 0 | 待补 | 待补 |
| 完整方法 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 0.416 |

### 4.4 案例分析补写

案例分析建议选取三类样本：

1. **视听互补成功案例**：ASR 提到“仅剩最后一天”，OCR 出现“限时抢购”，画面出现倒计时或促销标签。本文方法可结合稀缺效应和损失规避解释紧迫感来源。
2. **链式校验纠错案例**：初始答案将 OCR 中的价格或优惠误读，经校验后依据屏幕文字修正。该案例可说明校验对细粒度事实问题的价值。
3. **失败案例**：广告采用高度抽象的视觉隐喻，但缺少明确旁白和字幕。模型可能给出泛化解释，说明当前方法仍难以完全理解深层象征和情绪表达。

---

## 五、可直接并入第 5 章的小结段

本章围绕 AdsQA 广告视频问答任务，从总体性能、RAG 消融、链式校验消融、效率分析、参数敏感性和案例分析等方面设计实验。阶段性结果表明，本文方法相较于通用多模态基线在整体指标上取得提升，尤其在情感分析、主题提取和营销策略类问题上更具优势。该结果说明，广告视频问答不仅依赖视觉识别能力，还依赖跨模态证据组织、领域知识补充和答案可靠性控制。后续实验需进一步补充 RAG 与链式校验的消融数据、推理效率指标以及典型案例，以更充分地验证各模块的独立贡献与实际部署价值。

---

## 六、后续待办清单

- [ ] 将学校论文模板中的页边距、标题编号、目录和参考文献格式并入最终 DOCX。
- [ ] 将 AdsQA 五类任务名称与正式数据集标注完全对齐。
- [ ] 补齐 RAG 消融实验数据：Base、+RAG、+RAG+Evidence Rerank、+RAG+Check。
- [ ] 补齐链式校验实验数据：无校验、全量校验、触发式校验、触发式拒答。
- [ ] 补齐效率实验数据：Token、时延、显存、检索耗时、校验耗时。
- [ ] 选取 2 个成功案例、1 个校验纠错案例和 1 个失败案例写入论文。
- [ ] 对参考文献进行真实来源核查，并按学校要求格式化。
"""

EXPERIMENT_MD = f"""# 实验补充计划与记录模板

> 位置：`{ROOT}`
> 用途：沿历史继续补齐第 5 章实验数据。

## 1. RAG 消融实验记录表

| 样本集 | 方法 | Top-K | 阈值 | 证据重排序 | Accuracy | 知识一致性 | 无关知识注入率 | 备注 |
|---|---|---:|---:|---|---:|---:|---:|---|
| AdsQA-营销策略 | Base | - | - | - | 待补 | 待补 | 待补 | 无外部知识 |
| AdsQA-营销策略 | +RAG | 3 | 0.05 | × | 待补 | 待补 | 待补 | 历史 MVP |
| AdsQA-营销策略 | +RAG | 5 | 0.05 | √ | 待补 | 待补 | 待补 | 本次扩展版本 |
| AdsQA-营销策略 | +RAG+Check | 5 | 0.05 | √ | 待补 | 待补 | 待补 | 完整方法 |

## 2. 链式校验实验记录表

| 样本集 | 方法 | 触发条件 | 校验轮数 | Accuracy | 幻觉率 | 拒答率 | 平均耗时/ms | 备注 |
|---|---|---|---:|---:|---:|---:|---:|---|
| AdsQA-全量 | 无校验 | - | 0 | 待补 | 待补 | 0 | 待补 | 速度最快 |
| AdsQA-全量 | 全量校验 | 全部问题 | 1 | 待补 | 待补 | 待补 | 待补 | 成本较高 |
| AdsQA-全量 | 触发式校验 | 文字/logo/价格/为什么/旁白/策略 | 1 | 待补 | 待补 | 待补 | 待补 | 推荐主方法 |
| AdsQA-全量 | 触发式拒答 | 同上 | 1 | 待补 | 待补 | 待补 | 待补 | 关注可靠性 |

## 3. 效率实验记录表

| 方法 | 平均帧数 | 平均视觉 Token | 平均文本 Token | 总输入 Token | 输出 Token | RAG/ms | Check/ms | 总耗时/ms | 显存/GB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 无压缩基线 | 待补 | 待补 | 待补 | 待补 | 待补 | 0 | 0 | 待补 | 待补 |
| 均匀采样 | 待补 | 待补 | 待补 | 待补 | 待补 | 0 | 0 | 待补 | 待补 |
| 问题引导压缩 | 待补 | 待补 | 待补 | 待补 | 待补 | 0 | 0 | 待补 | 待补 |
| 双流压缩 + RAG | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 0 | 待补 | 待补 |
| 完整方法 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |

## 4. 参数敏感性记录表

| 参数 | 取值 | Accuracy | F1 | 证据一致性 | 知识一致性 | 平均耗时/ms | 观察结论 |
|---|---|---:|---:|---:|---:|---:|---|
| 关键帧 K | 4 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| 关键帧 K | 8 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| 关键帧 K | 12 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| RAG Top-K | 1 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| RAG Top-K | 3 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| RAG Top-K | 5 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| 校验轮数 | 0 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| 校验轮数 | 1 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| 校验轮数 | 2 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |

## 5. 案例分析记录表

| 案例编号 | 类型 | 用户问题 | 标准答案 | 基线答案 | 本文答案 | 视觉证据 | ASR证据 | OCR证据 | 检索知识 | 校验结论 | 分析 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Case-01 | 视听互补成功 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| Case-02 | 链式校验纠错 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
| Case-03 | 失败案例 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 | 待补 |
"""

QA_MD = f"""# 答辩 Q&A 草稿

## Q1：本文和普通视频问答方法相比，核心区别是什么？

**回答：** 普通视频问答主要关注对象、动作、事件和时序关系，而广告视频问答还需要理解品牌、商品卖点、受众定位、情绪诉求和营销策略。本文的核心区别在于面向广告视频特点设计了“视听协同特征压缩 + 广告知识增强 RAG + 链式校验”的完整框架：先压缩冗余视觉输入并定位关键证据，再用广告营销知识补充专业语义，最后通过校验机制降低无依据回答和策略误归因。

## Q2：为什么需要视觉 Token 压缩？广告视频通常并不长，是否有必要？

**回答：** 广告视频虽然时长不一定很长，但镜头切换快、字幕和产品细节密集，若高频采样会产生较多视觉 Token；若低频采样又容易漏掉 Logo、价格和短暂字幕。因此本文采用问题、ASR 和 OCR 共同引导的压缩策略，不是简单减少帧数，而是在有限输入预算下保留与问题最相关的关键证据。

## Q3：RAG 会不会引入视频中没有的信息，反而造成幻觉？

**回答：** 这是本文重点考虑的问题。本文将 RAG 定位为辅助解释，而不是替代视频证据。检索时加入 ASR、OCR 和视觉标签的证据感知重排序；Prompt 中明确要求“视频证据优先，外部知识辅助”；链式校验阶段还会检查答案中的营销概念是否被视频证据支撑。因此 RAG 的作用是降低专业知识不足，而不是鼓励模型编造。

## Q4：链式推理和链式校验有什么区别？

**回答：** 链式推理主要发生在答案生成阶段，引导模型按照“观察—分析—推理—答案”的路径组织回答；链式校验发生在候选答案之后，用于检查答案是否被证据支撑、不同模态是否一致、时间定位是否正确、营销知识是否误用。前者强调生成过程的结构化，后者强调结果可靠性的核查与修正。

## Q5：为什么采用触发式校验，而不是所有问题都校验？

**回答：** 全量校验会显著增加推理耗时，而并非所有问题都需要复杂核查。简单事实识别题通常可直接回答；涉及文字、Logo、价格、旁白、原因解释和营销策略的问题更容易出现细节误读或过度推断，因此更适合触发校验。触发式策略能够在可靠性和效率之间取得折中。

## Q6：实验中如果视觉感知提升不明显，如何解释？

**回答：** 广告视频问答中的很多问题由语音、字幕和营销语义主导，通用多模态模型在基础视觉识别上已经具备一定能力，因此视觉感知单项提升可能不明显。本文的主要收益不一定体现在“看见更多对象”，而体现在更好地组织跨模态证据、补充广告知识并通过校验减少错误。可以通过营销策略、受众分析、证据一致性和幻觉率等指标体现方法价值。

## Q7：知识库目前只有 30 条，是否足够支撑论文？

**回答：** 30 条知识库是 MVP 阶段，用于验证 RAG 流程和消融趋势。论文中可以说明该知识库覆盖常见广告营销概念、消费者心理、创意策略、多模态证据和合规风险。后续若时间允许，可扩展到 80–150 条，并补充行业类知识。实验重点不是证明知识库规模最大，而是验证广告知识增强对问答质量的贡献。

## Q8：本文方法的局限是什么？

**回答：** 主要有三点。第一，广告营销知识库规模仍有限，难以覆盖所有行业和品牌背景；第二，链式校验会带来额外耗时，需要进一步研究动态触发和轻量验证器；第三，抽象隐喻、情绪氛围和高语境创意仍然难以完全自动理解，未来可引入更细粒度的情绪建模和人工评分机制。

## Q9：本文创新点如何概括？

**回答：** 可以概括为四点：一是提出面向广告视频问答的视听—文字协同响应建模；二是提出基于响应密度的全局—局部双流视觉特征压缩；三是构建广告营销知识增强 RAG 流程，并强调证据感知重排序；四是设计触发式链式校验机制，用于降低事实性幻觉和营销概念误用。

## Q10：后续最应该补的实验是什么？

**回答：** 优先补三类实验：RAG 消融、链式校验消融和效率实验。RAG 消融证明外部广告知识的贡献；链式校验消融证明答案可靠性提升来自校验机制；效率实验证明视觉压缩在降低 Token 和时延方面具有实际价值。这三类实验最直接支撑论文的核心模块。
"""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_docx() -> Path | None:
    try:
        from docx import Document
        from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Inches, Pt, RGBColor
    except Exception:
        return None

    out = DOCX_DIR / "基于视听协同感知与链式校验的广告视频问答方法_续写稿_20260618.docx"
    DOCX_DIR.mkdir(parents=True, exist_ok=True)

    def set_run(run, font="宋体", size=11, bold=False, color="000000"):
        run.font.name = font
        run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
        run._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        run._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        run.font.size = Pt(size)
        run.bold = bold
        run.font.color.rgb = RGBColor.from_string(color)

    def fmt_p(p, before=0, after=6, line=1.3, first=False, align=None):
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        p.paragraph_format.line_spacing = line
        if first:
            p.paragraph_format.first_line_indent = Pt(22)
        if align is not None:
            p.alignment = align

    def para(doc, text="", first=True, bold=False, size=11, align=None):
        p = doc.add_paragraph()
        fmt_p(p, first=first, align=align)
        r = p.add_run(text)
        set_run(r, size=size, bold=bold)
        return p

    def h1(doc, text):
        p = doc.add_paragraph()
        fmt_p(p, before=16, after=10, line=1.2, align=WD_ALIGN_PARAGRAPH.CENTER)
        r = p.add_run(text)
        set_run(r, "黑体", 16, True)

    def h2(doc, text):
        p = doc.add_paragraph()
        fmt_p(p, before=12, after=8, line=1.25)
        r = p.add_run(text)
        set_run(r, "黑体", 14, True)

    def h3(doc, text):
        p = doc.add_paragraph()
        fmt_p(p, before=8, after=6, line=1.25)
        r = p.add_run(text)
        set_run(r, "黑体", 12, True)

    def shade(cell, fill):
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), fill)
        tcPr.append(shd)

    def cell_text(cell, text, bold=False, fill=None):
        cell.text = ""
        p = cell.paragraphs[0]
        fmt_p(p, after=0, line=1.15, first=False, align=WD_ALIGN_PARAGRAPH.CENTER if bold else WD_ALIGN_PARAGRAPH.LEFT)
        r = p.add_run(str(text))
        set_run(r, size=9, bold=bold)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        if fill:
            shade(cell, fill)

    def table(doc, headers, rows):
        t = doc.add_table(rows=1, cols=len(headers))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.style = "Table Grid"
        for i, h in enumerate(headers):
            cell_text(t.rows[0].cells[i], h, True, "F2F4F7")
        for row in rows:
            cs = t.add_row().cells
            for i, v in enumerate(row):
                cell_text(cs[i], v)
        para(doc, "", first=False)

    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Inches(1)
    sec.bottom_margin = Inches(1)
    sec.left_margin = Inches(1)
    sec.right_margin = Inches(1)
    styles = doc.styles
    styles["Normal"].font.name = "宋体"
    styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    styles["Normal"].font.size = Pt(11)

    p = doc.add_paragraph()
    fmt_p(p, before=36, after=20, align=WD_ALIGN_PARAGRAPH.CENTER)
    r = p.add_run(TITLE)
    set_run(r, "黑体", 20, True)
    para(doc, "论文续写稿（第2章扩写、RAG MVP扩展、实验与答辩材料）", first=False, bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, f"生成位置：{ROOT}", first=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, f"生成日期：{DATE}", first=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_page_break()

    h1(doc, "一、续写目标与历史衔接")
    for text in [
        "历史版本已经完成论文初稿、优化稿、图示设计、RAG MVP 和第5章实验计划。本次续写不再写入 efs-mgr 目录，而是在 /Users/bytedance/vqa_thesis_continue 下继续生成材料。",
        "论文主线继续保持为：视听协同特征压缩、广告知识增强 RAG 推理和链式校验优化。续写重点是补齐第2章相关理论、扩展 RAG MVP、设计可执行实验记录模板，并生成答辩 Q&A。",
    ]:
        para(doc, text)

    h1(doc, "二、第2章相关理论扩写摘要")
    for title, body in [
        ("2.1 视频问答与广告视频理解", "广告视频问答不仅需要识别画面对象和事件，还需要理解品牌、卖点、受众、情绪和营销策略等高层语义。与通用视频问答相比，它更依赖跨模态证据协同和领域知识约束。"),
        ("2.2 多模态大语言模型与视频理解", "多模态大语言模型具备开放词汇理解和自然语言推理能力，但在广告视频中仍面临视觉冗余、领域知识不足和生成幻觉等问题，因此需要任务层面的证据压缩、知识增强和答案校验。"),
        ("2.3 视觉 Token 压缩", "视觉 Token 压缩的目标不是简单减少帧数，而是在保留关键 Logo、字幕、产品细节和场景语义的前提下降低计算成本。本文采用问题、ASR 和 OCR 共同引导的全局—局部双流压缩。"),
        ("2.4 RAG 与链式校验", "RAG 为广告视频问答补充营销理论、消费者心理和创意策略知识；链式校验则检查答案是否受到视频证据和检索知识共同支撑。二者共同降低专业概念误用和无依据生成。"),
    ]:
        h2(doc, title)
        para(doc, body)

    h1(doc, "三、RAG MVP 续写")
    para(doc, "本次将历史 RAG 知识库从 10 条扩展到 30 条，覆盖营销理论、消费者心理、广告创意、多模态证据、评价指标和合规风险。检索公式加入 Evidence 项，使召回结果不仅匹配问题，也匹配 ASR、OCR 和视觉标签。")
    table(doc, ["模块", "历史版本", "本次续写"], [
        ["知识库规模", "10 条", "30 条"],
        ["检索特征", "TF cosine + keyword + prior", "新增 evidence-aware rerank"],
        ["Prompt", "观察/知识匹配/分析/答案", "新增校验字段和证据优先约束"],
        ["实验用途", "流程验证", "支持 RAG 消融、知识一致性和无关知识注入率评估"],
    ])

    h1(doc, "四、实验补充计划")
    h2(doc, "4.1 RAG 消融")
    table(doc, ["编号", "方法", "外部知识", "证据重排序", "预期"], [
        ["R0", "Base", "×", "×", "营销策略和受众分析较弱"],
        ["R1", "+RAG", "√", "×", "专业性提升但可能有噪声"],
        ["R2", "+RAG+Threshold", "√", "×", "无关知识减少"],
        ["R3", "+RAG+Evidence", "√", "√", "策略判断更稳健"],
        ["R4", "+RAG+Check", "√", "√", "幻觉率最低"],
    ])
    h2(doc, "4.2 链式校验消融")
    table(doc, ["编号", "方法", "触发", "预期"], [
        ["C0", "无校验", "×", "速度最快但细节幻觉较高"],
        ["C1", "全量校验", "全部问题", "可靠性提升但耗时较高"],
        ["C2", "触发式校验", "高风险问题", "推荐主方法，兼顾效率和可靠性"],
        ["C3", "触发式拒答", "高风险问题", "准确性提升但覆盖率下降"],
    ])

    h1(doc, "五、答辩高频问题摘要")
    for q, a in [
        ("本文核心创新是什么？", "面向广告视频问答提出视听—文字协同响应、全局—局部双流压缩、证据感知 RAG 和触发式链式校验。"),
        ("RAG 是否会引入幻觉？", "外部知识只作为辅助，检索加入证据感知重排序，Prompt 强调视频证据优先，校验阶段检查知识是否被证据支撑。"),
        ("为什么采用触发式校验？", "全量校验成本高，而高风险问题更需要核查；触发式校验能在可靠性和推理效率之间取得折中。"),
    ]:
        h3(doc, q)
        para(doc, a)

    h1(doc, "六、后续待办")
    for item in [
        "补齐 RAG 消融实验数据。",
        "补齐链式校验消融实验数据。",
        "补齐 Token、推理时间和显存等效率指标。",
        "选择 2–3 个成功案例和 1 个失败案例写入论文。",
        "按学校模板统一目录、标题、参考文献和页眉页脚格式。",
    ]:
        para(doc, "• " + item, first=False)

    doc.save(out)
    return out


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    RAG.mkdir(parents=True, exist_ok=True)
    DOCX_DIR.mkdir(parents=True, exist_ok=True)

    write_text(ROOT / "README.md", README)
    write_text(DOCS / "论文续写整合稿.md", THESIS_MD)
    write_text(DOCS / "实验补充计划与记录模板.md", EXPERIMENT_MD)
    write_text(DOCS / "答辩Q&A.md", QA_MD)
    write_json(RAG / "marketing_knowledge_base_extended.json", KB_ITEMS)
    write_text(RAG / "rag_retriever.py", RETRIEVER)

    docx_path = build_docx()
    manifest = {
        "root": str(ROOT),
        "generated_at": DATE,
        "files": [
            str(ROOT / "README.md"),
            str(DOCS / "论文续写整合稿.md"),
            str(DOCS / "实验补充计划与记录模板.md"),
            str(DOCS / "答辩Q&A.md"),
            str(RAG / "marketing_knowledge_base_extended.json"),
            str(RAG / "rag_retriever.py"),
        ] + ([str(docx_path)] if docx_path else []),
        "docx_generated": bool(docx_path),
        "note": "All outputs are under /Users/bytedance/vqa_thesis_continue, not under efs-mgr.",
    }
    write_json(ROOT / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
