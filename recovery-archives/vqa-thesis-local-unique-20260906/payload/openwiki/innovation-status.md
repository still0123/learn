---
type: Concept
title: Innovation Status
description: Current experimental status of both innovation points, confirmed negative results, fallback/downgrade plans, diagnoses, and remaining open questions.
tags: [innovation, negative-result, fallback, experiment-status]
---

# Innovation Status

> **Context**: Both innovation points have undergone rigorous fair-protocol evaluation across multiple independent control sets. Neither point has been found to **stably improve QA accuracy**, leading to formal downgrade decisions (July 16, 2026). The technical contributions are preserved at appropriate framing levels.

## Innovation Point 1: Evidence Localization & Visual Compression

### Original Claim

Adaptive spatial-temporal visual feature compression with heatmap-driven cropping **stably improves overall AdsQA QA accuracy**.

### Current Status: Formal Downgrade

The central conclusion, supported by 4 independent Confirm sets (A/B/C, Evidence-300) totaling 950+ non-overlapping samples:

> **Spatial cropping does NOT stably improve QA accuracy over Raw Uniform under fair-protocol conditions.**

This conclusion is not due to protocol artifacts — it has survived:
- Same model checkpoint (Qwen3-VL-8B)
- Same token budget (32 views, 11,664 tokens, secondary sampling disabled)
- Same source frames (for paired comparisons)
- Independent validation on zero-overlap confirm sets
- DeepSeek judge with 10,000× paired bootstrap CIs
- Full protocol audit (visual protocol, question_id alignment, GPU OOM repairs)

### Preserved Technical Contributions

| Contribution | Evidence | Status |
|---|---|---|
| Question/ASR/OCR-conditioned response maps | Spatial-temporal response computation | Verified |
| Strict token budget allocation | 32-view, 11,664-token protocol | Engineering contribution |
| Temporal/spatial evidence tradeoff | 32+0 → 24+8 → 16+16 ablation | Analyzed |
| Evidence localization improvement ≠ QA gain | The core empirical finding | **Confirmed across 4 independent sets** |
| Visual protocol audit methodology | SHA-256 manifests, paired audits | Reproducible framework |

### Recommended Framing

> **A token-budget-constrained audio-visual evidence localization framework for AdsQA, revealing the non-monotonic relationship between evidence localization improvement and generative QA accuracy.**

This allows the thesis to publish:
- The technical framework (response maps, budget allocation, dual-stream input)
- The rigorous evaluation protocol (audit-first, fair comparison, independent confirm)
- The important scientific finding (localization ≠ QA)

### Key Diagnosis: Root Cause

AdsQA questions frequently ask about audience, emotion, narrative strategy, metaphor, and brand mission. These answers depend on cross-temporal narrative, ASR, and whole-ad semantics — **not on a single cropable spatial object**. The CLIP spatial response has average concentration ~0.01, and 82/84 Confirm-300B change samples had no explicit textual intent, supporting this diagnosis.

## Innovation Point 2: Knowledge-Enhanced Chain-of-Reflection

### Original Claim

Knowledge-enhanced chain-of-reflection reasoning with evidence-driven RAG **reduces hallucination and improves answer reliability**.

### Current Status: Formal Downgrade

Multiple gates failed across stages:
- **Counterfactual Sufficiency MVP** (Pilot 100): `s(E+) > s(E-)` direction correct, but 24+8 completion degraded QA
- **v2.3 Claim Support/Conflict**: Evidence dependency established (visual pair accuracy 97.10%) but lightweight verifier did not beat visual Qwen
- **RealClaim-300 Development Gate**: All pre-registered gates failed (Qwen visual AUROC 0.5510, v2.3 AUROC 0.5998)
- **RealClaim-300 v2** (corrected frames): Visual AUROC 0.5378 vs text-only 0.5457

Note: RealClaim-300 **v1** had a protocol error (processor slot indices mistaken for video frame numbers); the thesis must not cite v1 negative conclusions. Fix underway in v2.

### Preserved Technical Contributions

| Contribution | Evidence | Status |
|---|---|---|
| Claim-evidence support/conflict verification | Eval 69: visual pair accuracy 97.10%, AUROC 0.94938 | **Verified as evidence-dependent** |
| Visual modality ablation | Protected visual intervention hit 13/15 with CI support | **Verified for visual modality** |
| Counterfactual sensitivity | `s(E+) > s(E-)` direction correct on 97/100 (Raw) and 98/100 (MMR) | Directional effect confirmed |
| Statement-level evidence dependency analysis | v2.3 framework and RealClaim diagnostics | Technical contribution |

### Recommended Framing

> **Claim-evidence support/conflict verification with counterfactual modality ablation for reliability analysis.**

The thesis may claim:
- Evidence dependency is measurable and visually grounded
- Statement-level verification is learnable (with caveats)
- Visual counterfactual intervention can identify necessary evidence

The thesis must **not** claim:
- QA accuracy improvement from any verification module
- Successful answer switching, refusal, or evidence completion
- Unified cross-modal verification

## Decision Gates Summary

| Gate | Date | Result | Implication |
|---|---|---|---|
| Innovation 1 — Spatial cropping negative | July 12, 2026 | Confirmed across A/B/C/Evidence-300 | Downgrade to evidence localization framework |
| Innovation 1 — MMR32 neutral | July 16, 2026 | Evidence-300: CI `[-0.0317, +0.0317]`, mean diff = 0 | No accuracy innovation claim |
| Innovation 1 — Adaptive router | July 16, 2026 | Calibration + Dev gates failed | Stop; use for failure analysis only |
| Innovation 2 — Counterfactual MVP | July 13, 2026 | QA degradation | Stop expansion |
| Innovation 2 — v2.3 evidence dependency | July 16, 2026 | Eval 69: pair accuracy 97.10% | **Passed** — but not QA improvement |
| Innovation 2 — RealClaim-300 Dev gate | July 16, 2026 | All pre-registered gates failed | Downgrade; use for analysis only |
| Innovation 2 — v2 corrected frames | July 16, 2026 | Protocol passed; results pending gold labels | Awaiting annotation protocol |

## Thesis Writing Constraints

Based on current experimental evidence:

1. **Can claim**: Evidence localization framework, strict token budget, fair protocol, evidence dependency analysis, the non-monotonicity finding
2. **Cannot claim**: Stable QA accuracy improvement from any cropping, selection, verification, or completion module
3. **Must include failure analysis**: Each innovation chapter should include a dedicated subsection documenting the failure modes and diagnoses
4. **Two-table structure**: Clearly separate fair-protocol comparisons from cross-method references

## Open Questions

| Question | Status |
|---|---|
| RealClaim-300 v2 gold-label annotation | Pilot60 protocol in progress |
| Can cross-modal evidence dependency support better claim verification? | Yes (verified) but not yet QA-improving |
| Is there a different evidence selector that beats Raw Uniform? | VideoITG, MMR32 all tested — none stable |
| Should the thesis title change? | Under discussion; remove "chain-of-reflection" from title or reinterpret as evidence verification |

## Source Documents

| Document | Path |
|---|---|
| Formal negative results (Innovation 1) | `/docs/创新点一阶段性负结果与论文降级方案.md` |
| Experiment ledger | `/docs/AdsQA实验结果总表与复现索引.md` |
| Research log | `/docs/论文思考记录.md` |
| Chapter 5 design | `/docs/第5章_实验设计与结果分析.md` |
