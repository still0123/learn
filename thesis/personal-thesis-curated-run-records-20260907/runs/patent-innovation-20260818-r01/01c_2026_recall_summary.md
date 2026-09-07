# I1-R 2026论文元数据宽召回汇总

- 生成时间：`2026-08-18T00:54:48+08:00`
- 严格日期窗口：`2026-01-01` 至 `2026-08-18`（按已知最早公开元数据）
- 去重后输出：**778** 条；目标 `800`，软上限 `1200`。最终 arXiv ID 年份审计排除 22 条旧预印本，严格日期优先，未为凑数突破查询预算。
- 阶段边界：仅元数据宽召回；所有记录均为 `metadata_only=true`、`full_text_verified=false`。
- 去重键：标准化 DOI、arXiv ID、标题 NFKD/小写/去标点归一键联合并查集。

## 分层数量

| 层 | 目标 | 实际 |
|---|---:|---:|
| A | 280 | 272 |
| B | 160 | 158 |
| C | 200 | 240 |
| D | 160 | 108 |

日期置信度：`high`=180，`medium`=479，`medium-high`=119

入池记录涉及接口：`Crossref`=126，`DBLP`=95，`OpenAlex`=506，`arXiv`=269

## 查询与接口

合同总请求预算为 72：本次正式批量请求 61 次，开始前接口/字段探测 11 次，共 72 次。正式请求统计如下：

| 接口 | 请求数 | 成功 | 失败 | 返回元数据条数（含重复/排除项） | 用途 |
|---|---:|---:|---:|---:|---|
| OpenAlex | 36 | 36 | 0 | 1770 | 主召回；限定 title/abstract search 与公开日期窗口 |
| arXiv | 16 | 16 | 0 | 1132 | 2025-2026 初次提交反查；识别 2025 预印本+2026版本 |
| Crossref | 5 | 5 | 0 | 300 | DOI、作者、venue 与线上/登记日期补充 |
| DBLP | 4 | 3 | 1 | 281 | 计算机领域题名/DOI补漏；唯一 year-only 记录不直接入池 |

### OpenAlex 36个查询簇

- A层：`A01_video_qa`=video question answering；`A02_image_visual_qa`=image visual question answering；`A03_long_video`=long video understanding；`A04_temporal_grounding`=temporal video grounding moment retrieval；`A05_multimodal_qa`=multimodal question answering；`A06_docvqa`=document visual question answering DocVQA；`A07_chart_table_qa`=chart table question answering；`A08_textvqa_ocr`=scene text question answering OCR；`A09_video_captioning`=video captioning evidence description；`A10_active_perception`=active visual perception second look；`A11_visual_agent_tools`=visual agent tool use zoom crop；`A12_audio_visual_qa`=audio visual question answering；`A13_egocentric_video`=egocentric video understanding
- B层：`B01_detection_segmentation`=object detection instance segmentation；`B02_visual_grounding`=visual grounding referring expression region text alignment；`B03_ocr_layout`=OCR scene text recognition document layout analysis；`B04_fine_grained`=fine grained recognition small object high resolution；`B05_saliency_evidence`=saliency attention map evidence region CAM；`B06_tracking_vos`=object tracking video segmentation temporal consistency；`B07_scene_graph_entailment`=scene graph visual entailment image fact verification
- C层：`C01_mllm`=multimodal large language model；`C02_vlm_instruction`=vision language model visual instruction；`C03_video_language`=video language model long video；`C04_visual_tokens`=visual token compression multi image；`C05_alignment_fusion`=image text alignment cross modal fusion；`C06_audio_visual_alignment`=audio visual alignment cross modal；`C07_preference_rl`=multimodal preference optimization reinforcement learning；`C08_grounded_reasoning`=grounded chain of thought visual reasoning tool；`C09_rag_agent`=multimodal retrieval augmented generation citation attribution agent planning memory
- D层：`D01_hallucination`=multimodal hallucination detection factuality；`D02_uncertainty_abstention`=uncertainty calibration selective prediction abstention；`D03_verifier_reranking`=answer verifier generator reranking fallback；`D04_counterfactual_negatives`=counterfactual evidence hard negative contrastive ranking；`D05_robust_weak_supervision`=out of distribution robustness weak supervision noisy labels vision；`D06_visual_budget`=visual token budget frame selection pruning dynamic resolution；`D07_system_routing_audit`=budget aware inference early exit model routing audit provenance

### arXiv 16个历史反查簇

- A层：`A01_video_qa`=video question answering；`A03_long_video`=long video understanding；`A04_temporal_grounding`=temporal video grounding；`A06_docvqa`=document visual question answering；`A10_active_perception`=active visual perception；`A12_audio_visual_qa`=audio visual question answering
- B层：`B02_visual_grounding`=visual grounding；`B03_ocr_layout`=scene text recognition；`B06_tracking_vos`=video object tracking segmentation
- C层：`C01_mllm`=multimodal large language model；`C03_video_language`=video language model；`C04_visual_tokens`=visual token compression；`C08_grounded_reasoning`=visual reasoning tool
- D层：`D01_hallucination`=multimodal hallucination；`D02_uncertainty_abstention`=selective prediction uncertainty calibration；`D04_counterfactual_negatives`=counterfactual evidence contrastive learning

### Crossref 5个补充簇

- A层：`A01_video_qa`=video question answering；`A06_docvqa`=document visual question answering
- B层：`B02_visual_grounding`=visual grounding
- C层：`C01_mllm`=multimodal large language model
- D层：`D01_hallucination`=multimodal hallucination uncertainty

### DBLP 4个补漏簇

- A层：`A01_video_qa`=video question answering
- B层：`B02_visual_grounding`=visual grounding
- C层：`C01_mllm`=multimodal language model
- D层：`D01_hallucination`=hallucination detection multimodal

## 排除与去重

- 拉取原始元数据：`3215` 条。
- 原始记录中最早日期早于 2026：`662` 条；晚于截止日：`0` 条。
- 精确日期不可解析：`281` 条（主要为 DBLP year-only）；若无其他接口给出精确日期则不入池。
- 题名历史反查阶段识别的最早日期早于 2026 文献族：`629` 个。
- 题名历史反查明确识别“2025 arXiv预印本 + 2026会议/期刊元数据”文献族：`38` 个。
- 初筛后另以 arXiv ID 年份审计 800 条目标池，追加排除旧预印本文献族 `22` 个：2023 年 `2` 个、2024 年 `8` 个、2025 年 `12` 个。
- 日期元数据初筛合格的去重文献族：`1584` 个；arXiv ID 终审后目标池保留 `778` 个。未输出长尾池未保存原始响应，故不把 `1584-22` 声称为完整严格合格数。
- 合格原始记录折叠为文献族时合并的重复记录：`634` 条。
- 初筛目标配额后未输出的长尾候选：`784` 个；其中是否含未关联旧 arXiv 版本需后续复核。

## 日期判定规则

1. arXiv 使用 Atom `published`（初次提交日期）作为最早公开日期，置信度为 `high`。
2. 同标题/DOI/arXiv 文献族取所有接口已知日期的最小值；只要命中 2025 arXiv，即使有 2026 venue 版本也整族排除。
3. 即使历史题名查询未命中，只要关联 arXiv ID 前缀早于 `26xx`，也按旧预印本硬排除。
4. Crossref 同时比较 online/print/issued/DOI metadata created，取最早值；OpenAlex 使用 `publication_date`。
5. 只有 DBLP 年份、无精确日期且未被其他接口补齐的记录不入池。
6. DOI-only 记录无法证明不存在未关联的旧预印本，因此保留 `medium` 或 `medium-high`，不提升为全文核验。

## 覆盖不足

- A/B/C/D 四层均有覆盖，但 D 层仅 `108` 条，较建议配额 `160` 少 `52` 条；D 层 DBLP 补漏请求又触发 429，因 72 次预算已耗尽未重试。
- 严格 arXiv ID 终审后总量为 `778`，距 800 目标少 `22` 条；未追加请求填充，以免突破查询上限。
- 终审后复查并行 I1 本地产物，发现 `7` 个严格 2026 且非重复候选，但卡片未保存必填的作者元数据；其余候选为重复或最早公开早于 2026，故未用空值或推断作者补池。
- 最终池中无直接查询命中的细分簇为 `B07_scene_graph_entailment`、`C09_rag_agent`、`D03_verifier_reranking`、`D04_counterfactual_negatives`、`D05_robust_weak_supervision`、`D07_system_routing_audit`；这些查询已执行，但返回项未同时通过日期终审、去重与配额截断，相关细分领域覆盖不足。
- arXiv 历史反查限于 16 个相关查询簇、每簇前 200 条；题名大幅改动或未被查询命中的 2025 预印本仍可能漏关联。
- OpenAlex/Crossref 的版本合并、venue 和发布日期存在索引延迟；`medium` 日期记录后续必须回到 arXiv版本史、出版社/会议页核验。
- DBLP 缺少日级公开日期，唯一 year-only 命中已保守排除，可能造成正式会议论文漏召回。
- 本轮未逐篇读取摘要或正文，标题/摘要检索命中不代表机制相关，更不代表 `verified`。
- 受 800 条目标配额限制，合格池按 A/B/C/D 比例和查询排名截断；长尾机制仍需后续补召回。

## 请求失败

- `DBLP/D01_hallucination`：HTTPError: 429 Client Error: Too Many Requests for url: https://dblp.org/search/publ/api?q=hallucination+detection+multimodal+year%3A2026%3A&h=100&format=json
