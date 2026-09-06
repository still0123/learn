---
type: Reference
title: Source Map
description: Concise index to canonical source documents with descriptions, usage notes, and inter-document relationships.
tags: [reference, source-map, index]
---

# Source Map

## Thesis Chapters

| Document | Key Content | When to Use | Relationship |
|---|---|---|---|
| `/docs/完整论文_题目不变_证据流闭环版.md` | Full thesis text: abstract, all 6 chapters, evidence-flow framing | Starting point for understanding the full thesis argument | Aggregates content from Ch.3, Ch.4, Ch.5 drafts |
| `/docs/第3章_视觉特征压缩与证据定位方法.md` | Chapter 3 method: oversampling, response maps, dual-stream input | When writing/verifying Innovation 1 technical description | → [thesis-scope.md](thesis-scope.md) core method |
| `/docs/第4章_知识增强链式反思推理方法.md` | Chapter 4 method: knowledge base, evidence-driven RAG, chain-of-reflection | When writing/verifying Innovation 2 technical description | → [thesis-scope.md](thesis-scope.md) core method |
| `/docs/第5章_实验设计与结果分析.md` | Experimental design, metrics, ablation templates, analysis templates | Template for writing Chapter 5; many tables need real data filled in | → [datasets-evaluation.md](datasets-evaluation.md), [experiments-reproducibility.md](experiments-reproducibility.md) |
| `/docs/论文主体骨架_题目不变_证据流主线版.md` | Earlier thesis skeleton; contains chapter structure decisions | Historical reference for structural decisions before continuation | Predecessor to the full thesis draft |

## Experimental Evidence

| Document | Key Content | When to Use | Relationship |
|---|---|---|---|
| `/docs/AdsQA实验结果总表与复现索引.md` | **Primary experiment ledger**: all results, parameters, code paths, reproducibility index | First stop for any experiment number or result question | → [experiments-reproducibility.md](experiments-reproducibility.md) |
| `/docs/创新点一阶段性负结果与论文降级方案.md` | **Comprehensive negative results**: all Innovation 1 and 2 routes, decision gates, downgrade plan | Understanding the full innovation status and why | → [innovation-status.md](innovation-status.md) |
| `/docs/论文思考记录.md` | **Chronological decision record**: ~25 entries covering 2026-06-18 to 2026-07-16 | Understanding WHY decisions were made | Backs all [innovation-status.md](innovation-status.md) conclusions |

## Dataset & Infrastructure

| Document | Key Content | When to Use |
|---|---|---|
| `/.codex_fair_protocol/data/README.md` | Active data directory: video paths, dataset files, balanced subsets | Understanding data layout and file locations |
| `/manifest.json` | Original continuation package file listing | Historical reference only |

## Evaluation Code & Scripts

| Path | Purpose |
|---|---|
| `/evaluation/scripts/` | Batch inference orchestration, audit pipelines, cron gates |
| `/evaluation/tools/` | Analysis, audit, training, build scripts for all experiments |
| `/tools/` | Experiment execution scripts (Confirm-300, VideoITG, budget ablation) |
| `/代码/eval_qwen3.py` | Qwen3-VL evaluation script |
| `/代码/eval_qwen2vl_fix.py` | Qwen2-VL evaluation |
| `/代码/eval_adqa.py` | Base AdsQA evaluation |

## Project Management & Agent Instructions

| Document | Key Content | When to Use |
|---|---|---|
| `/AGENTS.md` | OpenWiki configuration marker | Do not edit |
| `/CLAUDE.md` | OpenWiki configuration marker | Do not edit |
| `/research-state.md` | Literature positioning and research state log | Historical context for research direction decisions |
| `/README.md` | Top-level README for the continuation workspace | First-time orientation |
| `/docs/闭环多Agent论文写作编排方案.md` | Multi-agent thesis writing orchestration plan | If resuming multi-agent workflow |
| `[Agent Guidance](agent-guidance.md)` | How future agents should work with this repo | **Read this first** before any agent run |

## Supplementary Materials

| Document | Key Content |
|---|---|
| `/docs/第3章_闭环审查修订版.md` | Chapter 3 with closed-loop review applied |
| `/docs/第4章_闭环审查修订版.md` | Chapter 4 with closed-loop review applied |
| `/docs/第5章_闭环审查修订版.md` | Chapter 5 with closed-loop review applied |
| `/docs/第3-4章图示索引与插入说明.md` | Figure placement guide for Chapters 3-4 |
| `/docs/第3-4章方法章节整合说明.md` | Method chapter integration notes |
| `/docs/AdsQA论文详细阅读笔记.md` | AdsQA paper reading notes |
| `/docs/AdsQA本地Baseline评测结果记录.md` | Local baseline results (historical; superseded by experiment ledger) |
| `/docs/RAG升级_Embedding与Hybrid检索说明.md` | RAG retrieval method description |
| `/docs/开题报告可替换段落_题目不变版.md` | Thesis proposal alternative paragraphs |
| `/docs/答辩Q&A.md` | Mock defense Q&A |

## Figures

| Path | Content |
|---|---|
| `/figures/` | Thesis figures |
| `/generate_method_figures.py` | Figure generation script |

## Related Projects

| Path | Description |
|---|---|
| `/ad_video_analysis_system/` | Full-stack ad video analysis application (FastAPI + Electron) |
| `/rag_mvp/` | RAG MVP: 30-entry marketing knowledge base + standalone retriever |
| `/专利相关/` | Patent materials |
| `/软件著作权申请资料/` | Software copyright application |
| `/code_refactor/` | Code refactoring workspace |
| `/local_review/` | Local review materials |
| `/patent_agents/` | Patent agent system |
| `/AgentSkill-Eval_秋招资料/` | Separate skill evaluation materials (not thesis core) |
