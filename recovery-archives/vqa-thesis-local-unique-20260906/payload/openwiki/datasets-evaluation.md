---
type: Concept
title: Datasets & Evaluation
description: AdsQA dataset details, task categories, sub-sets for controlled experimentation, evaluation metrics, and the fair-protocol evaluation framework.
tags: [adsqa, dataset, evaluation, metrics, fair-protocol]
---

# Datasets & Evaluation

## AdsQA Dataset

The thesis uses the **AdsQA** advertising video question answering dataset as its primary evaluation benchmark. AdsQA targets ad video understanding with questions spanning visual recognition, emotion analysis, theme extraction, marketing strategy, and audience targeting.

### Task Categories

| Category | Description | Example Question |
|---|---|---|
| 视觉感知 (Visual Perception) | Identify objects, people, scenes, logos, text | "画面中出现了什么产品？" |
| 情感分析 (Emotion Analysis) | Judge emotional tone, appeal, audience feeling | "广告传达了怎样的情绪？" |
| 主题提取 (Theme Extraction) | Summarize theme, core message, product USP | "该广告主要表达什么主题？" |
| 营销策略 (Marketing Strategy) | Analyze persuasion strategy, creative technique | "这个广告如何制造紧迫感？" |
| 受众分析 (Audience Analysis) | Identify target audience or usage scenario | "该广告主要面向哪类用户？" |

### Dataset Sizes

| Split | Samples | Notes |
|---|---|---|
| Full test set | 7,859 | Ground truth at `/代码/testset_groundtruth.json` |
| Balanced-3000 | 3,000 | 600 per type, seed 42 |
| Balanced-2500 | 2,500 | 500 per type, seed 42 |

### Specialized Sub-Sets (for ablation)

| Sub-set | Purpose |
|---|---|
| 声画对齐子集 (AV-Aligned) | Control for AV asynchrony experiments |
| 语音领先子集 (Audio-Leading) | Test temporal window coverage for pre-visual narration |
| 语音滞后子集 (Audio-Lagging) | Test temporal window coverage for delayed narration |
| 语音无关子集 (Audio-Irrelevant) | Test audio noise suppression |
| OCR/Logo子集 | Text/brand detail questions |
| 营销策略子集 (Marketing Strategy) | Knowledge retrieval effectiveness |
| 高风险幻觉子集 (High-Risk Hallucination) | Reflection verification effectiveness |

## Experiment Sub-Sets

The evaluation framework uses multiple controlled subsets for iterative experimentation:

### Pilot & Confirm Sets

| Set | Size | Purpose | Status |
|---|---|---|---|
| Pilot50 | 50 (10×5 types) | Initial innovation screening, mechanism validation | Historical — not for final conclusions |
| Confirm-300 (A) | 300 | First independent replication of Pilot50 results | Completed |
| Confirm-300B | 300 | Independent replication of focus-context | Completed |
| Confirm-300C | 300 | Independent replication of lightweight temporal selector | Completed |
| Evidence-300 | 300 | Frozen comparison: Raw vs MMR32 with full protocol audit | Completed — final conclusion |
| EvidenceSupport-Pilot60 | 60 | Evidence gold-label annotation protocol verification | In progress |
| RealClaim-300 (v1/v2) | 300 | Real model answer statement-level verification | Completed (v1 invalid, v2 with corrected frames) |

All Confirm sets have **zero overlap** in questions and videos with each other and with Pilot50.

### Fair Protocol for Controlled Experiments

Every controlled experiment must satisfy:

1. **Same base model checkpoint**: Both conditions use the same Qwen3-VL-8B checkpoint
2. **Same answer prompt**: Identical prompt template
3. **Same token budget**: 32 actual representation views, 11,664 visual tokens
4. **Secondary sampling disabled**: `processor` must not re-sample frames
5. **Identical source frames** (for ablation comparisons): 32 source frames per question, identical between conditions
6. **Protocol audit**: Visual protocol audit JSON must pass before results are accepted
7. **Independent judge**: DeepSeek (full-response or Answer-only) with 10,000× paired bootstrap confidence intervals
8. **Report both Strict and Relaxed**: Never report only one metric

### Visual Protocol Audit

Each experiment requires auditing:
- Number of actual submitted/representation views per question (must be 32/32)
- Visual token count (must be 11,664)
- Secondary sampling disabled (must be true)
- Source frame identity (for paired comparisons)
- Errors and missing items (must be 0)

Audit output: `evaluation/runs/<experiment>/formal_visual_protocol_audit_v1.json`

## Evaluation Metrics

### Primary Metrics

| Metric | Definition |
|---|---|
| **Strict** | `count(Answer:1) / N` |
| **Relaxed** | `(count(Answer:1) + 0.5 × count(Answer:0.5)) / N` |
| **Paired Win/Tie/Loss** | Per-question comparison between two methods |
| **Paired Bootstrap CI** | 10,000 resamples, mean score difference with 95% CI |

### Evidence Metrics

| Metric | Definition |
|---|---|
| Evidence Recall | Fraction of ground-truth evidence units captured |
| Evidence Precision | Fraction of captured evidence that is relevant |
| Region Recall | Fraction of spatial regions correctly localized |
| Temporal Recall | Fraction of temporal bins with at least one captured frame |

### Quality Metrics

| Metric | Definition |
|---|---|
| Evidence Consistency | `claims_supported_by_evidence / total_claims` |
| Knowledge Consistency | Correct marketing concept usage rate |
| Hallucination Rate | Fraction of samples with unsupported content |
| Visual Tokens | Actual visual tokens per sample |
| Inference Latency | End-to-end inference time per sample |

## Data Storage

Active data is stored under `/.codex_fair_protocol/data/`:
- `videos/` (~30G) — Original AdsQA videos
- `frames_8/` (~7.9G) — Eight-frame fallback
- `testset_question.json` — Full test questions
- `testset_groundtruth.json` — Full test ground truth
- `balanced*_seed42*` — Balanced subsets with construction manifest
- `pilot50_*` — Fixed 50-question pilot with manifest

Source: `/.codex_fair_protocol/data/README.md`
