---
type: Entry Point
title: VQA Thesis Workspace — Quickstart
description: Entry point for the AdsQA master thesis continuation workspace. Covers thesis scope, experimental status, reproducibility, and source document index.
tags: [adsqa, thesis, vqa, documentation]
---

# Quickstart: AdsQA Master Thesis Workspace

This repository is the working directory for a master's thesis titled **"基于视觉特征压缩与链式反思的广告视频问答方法"** (Visual Feature Compression and Chain-of-Reflection for Advertising Video Question Answering). It contains the thesis continuation work built on prior drafts, RAG MVP, multi-agent orchestration, and an extensive fair-evaluation experimental framework.

## Overview

The thesis addresses Advertising Video Question Answering (AdsQA), proposing an evidence-centric pipeline:

```
Evidence Localization → Evidence-Preserving Visual Compression → Evidence-Driven Knowledge Retrieval → Statement-Level Evidence Verification
```

The core claim is that **selecting the right video evidence matters more than retrieving more knowledge**, and that evidence localization improvement does not **stably** translate to QA accuracy gains — a finding documented through rigorous controlled experiments.

## Repository Contents

| Area | Description | Key Paths |
|---|---|---|
| **Thesis Drafts & Chapters** | Full thesis text, per-chapter drafts, review records | `/docs/完整论文_题目不变_证据流闭环版.md`, `/docs/第3章_视觉特征压缩与证据定位方法.md`, `/docs/第4章_知识增强链式反思推理方法.md`, `/docs/第5章_实验设计与结果分析.md` |
| **Experiment Results** | Central experiment ledger with metrics and reproducibility index | `/docs/AdsQA实验结果总表与复现索引.md` |
| **Innovation Status** | Negative results and fallback plans for both innovation points | `/docs/创新点一阶段性负结果与论文降级方案.md` |
| **Research Log** | Chronological decision record with timestamped entries | `/docs/论文思考记录.md` |
| **Evaluation Framework** | Fair experiment protocol, audit tools, inference scripts | `/evaluation/`, `/.codex_fair_protocol/` |
| **RAG MVP** | Advertising marketing knowledge base and retrieval demo | `/rag_mvp/` |
| **Execution Scripts** | GPU cluster orchestration, cron gates, post-processing | `/evaluation/scripts/`, `/tools/` |
| **Code** | Evaluation scripts for Qwen, MiniCPM, LLaVA models | `/代码/` |
| **Ad Video Analysis System** | Full-stack analysis application (FastAPI + Electron) | `/ad_video_analysis_system/` |

## Key Facts

- **Dataset**: AdsQA — 7859 test samples across 5 task categories (visual perception, emotion analysis, theme extraction, marketing strategy, audience analysis)
- **Base Model**: Qwen3-VL-8B with 32 actual views, 11,664 visual tokens, secondary sampling disabled
- **Best Available QA**: Raw Uniform 32 frames + ASR + Qwen3-VL-8B (Relaxed 68.50% on Confirm-300)
- **Best Evidence Localization**: 16+16 frame-cap + query-conditioned cached OCR (Evidence Recall 29/30, Region Recall 10/10)
- **Main Experimental Finding**: Evidence localization improvement does NOT stably translate to QA accuracy gains — documented across 4 independent Confirm sets totaling 950+ samples
- **Fair Protocol**: Same base model, same token budget, secondary sampling disabled, paired bootstrap with 10,000 resamples, independent confirm sets for pilot result validation

## Documentation Pages

| Page | Description |
|---|---|
| [Thesis Scope & Architecture](thesis-scope.md) | Thesis title, chapter structure, innovation points (original plan vs current status), core technical methods |
| [Datasets & Evaluation](datasets-evaluation.md) | AdsQA dataset details, task categories, sub-sets, evaluation metrics, fair protocol |
| [Experiments & Reproducibility](experiments-reproducibility.md) | Experiment results ledger, reproducibility index, metrics definitions, fair protocol requirements |
| [Innovation Status](innovation-status.md) | Current status of both innovation points, negative results, fallback/downgrade plans, key diagnoses |
| [Source Map](source-map.md) | Concise index to canonical source documents with descriptions and usage notes |
| [Agent Guidance](agent-guidance.md) | Instructions for future agents on working with this repository |

## Data & Code Exclusions

The following are **excluded** from this wiki's scope and should not be treated as experimental evidence:
- `.tmp*`, `tmp/`, `artifacts/`, `outputs/`, `output/`, `runs/`, `remote_staging/`, `remote_patch/`, `remote_work/`, `remote_worktree/`, `source_texts/`
- External JSON data files, PDFs, credentials, `.env` files
- Node modules, Python virtual environments

## Backlog

| Area | Reason Deferred |
|---|---|
| Ad Video Analysis System (`/ad_video_analysis_system/`) | Separate full-stack application; document when integration with thesis evaluation is needed |
| Patent-related materials (`/专利相关/`, `/patent_agents/`) | Not directly part of thesis experimental workflow |
| Software copyright docs | Administrative, not technical |
| AgentSkill-Eval materials | Separate skill-evaluation project; not central to thesis |
