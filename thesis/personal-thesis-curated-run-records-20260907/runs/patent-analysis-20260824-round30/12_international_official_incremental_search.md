# 国际官方库增量检索记录（V4.6 独权窄主链）

检索日期：2026-08-24。拟申请日前提按当前项目日期处理；本文只给技术检索结论，不给授权保证或法律意见。

## 1. 目标特征

本轮只核查 V4.6 的 F3--F9：候选答案不读取/不接收初答的隔离生成；在同一扩展证据集 E+ 上配对复评；原子声明映射；增量视频证据的时空模态见证；依赖闭包；闭包级原子提交或回退；受限重组和不得复活失效声明。

## 2. 官方库可访问性与查询式

检索入口：WIPO PATENTSCOPE、EPO Register / Espacenet 可公开入口。实际执行的概念组为：

* `video question answering` + `evidence` / `verification`；
* `visual question answering` + `verification`；
* `candidate answer` + `same evidence`；
* `atomic claim` / `claim-level` + `evidence` + `answer`；
* `evidence` + `rollback` + artificial intelligence；
* `blind` / `isolated candidate generation` + evidence。

PATENTSCOPE 的已知记录页可返回题名、申请人和摘要；其交互式检索页在本环境触发“Processing / CAPTCHA”，而 EPO 直接登记页/文献 PDF 入口被访问安全策略拦截。因此，本轮不能把“未命中”表述为 WIPO/EPO 全库零结果；它只是可访问官方记录与辅助检索的增量核验。

## 3. 可核验的官方国际记录

| 文献 | 公布日 | 官方来源 | 与 F3--F9 的关系 |
|---|---:|---|---|
| WO2025091218A1, *Grounded visual question-answering method based on dynamic dual-level visual information fusion* | 2025-05-08 | [WIPO PATENTSCOPE](https://patentscope.wipo.int/search/ko/detail.jsf?docId=WO2025091218) | 视频/视觉问答相邻文献；公开问题引导定位、多尺度区域/像素特征融合、文本答案和 grounding mask 同时输出。未见 A0 盲化的 A2、同 E+ 双答案复评、声明迁移许可、见证闭包或提交/回退。对 F3--F9：未直接公开。 |

该文献是**场景近邻**，不宜被漏掉；但它是单模型 grounded VQA，不是“初答—独立候选—同证据核验—事务更新”路线。

## 4. 国际同族线索（需在官方库复核）

辅助检索定位到 `EP4610849A1` / `US20250278422A1`，题名为 *Information retrieval from LLM in industrial applications with reduced hallucination*，并指向中国同族 `CN120561217A`。辅助页显示 EP 公布日为 2025-09-03、US 公布日为 2025-09-04，优先权日为 2024-02-29。其公开主线是：生成答案后，基于问题和/或答案建立验证计划，执行验证动作并用置信度评价答案。

由于本轮未能从 EPO 官方全文页直接取证，此行只作为**待官方确认的国际同族线索**，不得写成“EPO 全文已核对”。即便按辅助全文所示内容，它也只接近“答案后验证计划”（F1/F2 的上位概念），未显示 F3--F9 的窄组合。

官方复核入口（申请/公布号已固定）：

* [EPO Register：EP24160586.4](https://register.epo.org/application?number=EP24160586)
* [EPO Publication Server：EP4610849A1](https://data.epo.org/publication-server/rest/v1.2/patents/EP4610849NWA1/document.pdf)

## 5. 本轮结论与边界

1. 可访问的 WIPO 官方记录新增了一篇 VQA 场景近邻 `WO2025091218A1`；它不会单篇覆盖 V4.6 的 F3--F9。
2. 未发现可据官方全文直接认定为覆盖“隔离候选生成 + 同 E+ 配对复评 + 逐项见证 + 依赖闭包原子提交/回退”的国际单篇文献。
3. 这不是“国际官方数据库穷尽检索完成”的结论。PATENTSCOPE/EPO 的交互访问限制意味着，正式递交前仍应由可登录的代理数据库或代理人以固定申请日前的全文、同族、引证和分类号再跑一次，并保留检索式和结果页。
4. 对独权撰写的影响：继续将 F3--F9 作为不可拆开的数据控制链；不要把普通“grounded VQA”、证据定位、答案后验证或原子写入单独称为创新点。
