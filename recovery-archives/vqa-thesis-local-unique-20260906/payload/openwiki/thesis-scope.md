---
type: Concept
title: Thesis Scope & Architecture
description: Coverage of the master thesis topic, chapter structure, innovation points (original plan vs current experimental status), and core technical methods.
tags: [thesis, architecture, innovation, chapters]
---

# Thesis Scope & Architecture

## Thesis Title

**基于视觉特征压缩与链式反思的广告视频问答方法**  
(Visual Feature Compression and Chain-of-Reflection for Advertising Video Question Answering)

## Core Thesis Pipeline

The thesis is organized around a four-stage evidence flow:

```
证据定位 (Evidence Localization)
    → 证据保留型视觉输入重构 (Evidence-Preserving Visual Input Reconstruction)
    → 证据驱动知识推理 (Evidence-Driven Knowledge Reasoning)
    → 答案-证据一致性验证 (Answer-Evidence Consistency Verification)
```

This replaces the earlier framing of "heatmap + chain-of-thought" which was deemed too generic to serve as a defendable innovation (see [论文思考记录 001](/docs/论文思考记录.md)).

## Chapter Structure

| Chapter | Title | Focus |
|---|---|---|
| Ch.1 | 绪论 | Background, research questions (RQ1–RQ4), contributions |
| Ch.2 | 相关理论与技术基础 | MLLMs, video VQA, RAG, CoT (draft expansion pending) |
| Ch.3 | 基于视觉特征压缩的广告视频证据定位方法 | Evidence-preserving visual compression: keyframe selection, spatial-temporal response maps (Q/ASR/OCR-driven), density-anchored local crops, global-local dual-stream input |
| Ch.4 | 知识增强链式反思推理方法 | Evidence-driven ad knowledge retrieval, structured reasoning protocol, statement decomposition, evidence back-trace reflection |
| Ch.5 | 实验设计与结果分析 | Fair-protocol experiments, main results, ablation studies, efficiency/robustness analysis |
| Ch.6 | 总结与展望 | Summary, limitations, future directions |

## Innovation Points: Plan vs Current Experimental Status

### Original Innovation Plan (Pre-June 2026)

1. **Innovation 1**: Adaptive spatial-temporal visual feature compression with heatmap-driven cropping → improves overall QA accuracy
2. **Innovation 2**: Knowledge-enhanced chain-of-reflection reasoning with RAG → reduces hallucination and improves answer reliability

### Current Experimental Status (as of July 16, 2026)

Both innovations have undergone extensive fair-protocol evaluation. Key findings:

**Innovation 1** — Downgraded from "accuracy improvement" to "budget-constrained evidence localization with failure analysis":
- All spatial cropping variants fail to stably beat Raw Uniform on independent Confirm-300 sets
- MMR32 (multi-modal routing) also ties with Raw Uniform (Strict 63.00% vs 62.67%, CI `[-0.0317, +0.0317]`)
- Key technical contributions preserved: question/ASR/OCR-conditioned response maps, strict token budget allocation, systematic evidence of non-monotonicity between localization quality and QA accuracy
- Recommended framing: **"A token-budget-constrained audio-visual evidence localization framework for AdsQA, revealing the non-monotonic relationship between evidence localization improvement and generative QA accuracy"**

**Innovation 2** — Downgraded from "accuracy improvement" to "claim-evidence support/conflict verification and counterfactual ablation audit":
- Counterfactual sufficiency MVP (pilot 100) showed correct directional `s(E+) > s(E-)` but 24+8 completion did not improve QA (Raw Relaxed 58.0% → 55.0%)
- v2.3 claim-support/conflict verification achieved strong evidence dependency (visual pair accuracy 97.10%, AUROC 0.94938 on Eval 69)
- RealClaim-300 development gate failed (Qwen visual AUROC 0.5510, v2.3 AUROC 0.5998)
- Recommended framing: **"Claim-evidence support/conflict verification with counterfactual modality ablation for reliability analysis"** — explicitly NOT claiming QA accuracy improvement

Full details: [Innovation Status](innovation-status.md)

## Core Technical Methods

### Chapter 3 — Evidence Localization & Compression

1. **High-frequency oversampling + semantic keyframe selection**: Reduce short-duration clue misses
2. **Audio-visual-text spatiotemporal response maps**: Question-conditioned, ASR-conditioned, OCR/Logo-conditioned response computation
3. **Response-density anchored local cropping**: Multi-scale anchor boxes centered on response density maxima
4. **Global-local dual-stream visual input**: Preserve both scene context and fine-grained local evidence
5. **Temporal sliding window**: Mitigate audio-video asynchrony

Source: `/docs/第3章_视觉特征压缩与证据定位方法.md`

### Chapter 4 — Knowledge-Enhanced Chain-of-Reflection

1. **Structured advertising marketing knowledge base**: 5 categories (marketing theory, consumer psychology, ad creativity, multimodal evidence, compliance/reliability)
2. **Evidence-driven knowledge retrieval**: Visual tags, ASR, OCR, and local evidence jointly condition retrieval
3. **Structured reasoning protocol**: Observation → Knowledge Matching → Analysis → Answer
4. **Statement decomposition & evidence back-trace verification**: Decompose initial answer into atomic claims, trace each to video frames, local crops, ASR, OCR, and knowledge entries
5. **Trigger strategy with early stopping**: Control additional inference cost

Source: `/docs/第4章_知识增强链式反思推理方法.md`

### Evaluation Framework

- **Fair Protocol**: Same base model (Qwen3-VL-8B), same token budget (11,664 visual tokens), secondary sampling disabled, independent confirm sets
- **Metrics**: Strict/Relaxed accuracy, paired win/tie/loss, 10,000× paired bootstrap CI
- **Audit-first methodology**: Every experiment requires visual protocol audit before results are considered valid

See: [Experiments & Reproducibility](experiments-reproducibility.md)

## Key Source Documents

| Document | Path | Purpose |
|---|---|---|
| Full thesis draft | `/docs/完整论文_题目不变_证据流闭环版.md` | Complete thesis text with evidence-flow framing |
| Chapter 3 draft | `/docs/第3章_视觉特征压缩与证据定位方法.md` | Evidence localization and compression method |
| Chapter 4 draft | `/docs/第4章_知识增强链式反思推理方法.md` | Knowledge-enhanced reflection method |
| Chapter 5 draft | `/docs/第5章_实验设计与结果分析.md` | Experiment design and analysis plan |
| Innovation 1 results | `/docs/创新点一阶段性负结果与论文降级方案.md` | Comprehensive negative results with fallback plan |
| Experiment ledger | `/docs/AdsQA实验结果总表与复现索引.md` | Central experiment results and reproducibility index |
| Research log | `/docs/论文思考记录.md` | Chronological decision record |
| Thesis main skeleton | `/docs/论文主体骨架_题目不变_证据流主线版.md` | Earlier thesis skeleton before continuation |
