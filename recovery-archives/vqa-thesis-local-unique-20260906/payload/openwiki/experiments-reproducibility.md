---
type: Concept
title: Experiments & Reproducibility
description: Central experiment results ledger, reproducibility index, metrics definitions, and fair protocol requirements for all controlled experiments.
tags: [experiments, reproducibility, metrics, fair-protocol, results]
---

# Experiments & Reproducibility

## Central Experiment Ledger

The master experiment ledger is at `/docs/AdsQA实验结果总表与复现索引.md`. This file is the **single authoritative entry point** for all experiment results, parameters, code paths, and reproducibility status. The [论文思考记录](/docs/论文思考记录.md) stores decisions and conclusions; the ledger stores numbers and paths.

### Status Legend

| Status | Meaning |
|---|---|
| **有效本地 baseline** | Model inference and local evaluation reproducible; usable as baseline |
| **待统一重评** | Needs re-evaluation with final unified judge, prompt, or missing-item rules |
| **历史参考** | Historical reference only; do not enter final thesis tables |
| **无效/不完整** | Serious missing data, protocol errors, or irreproducible; not usable as conclusion |

## Key Results Summary

### ReAd-R Baseline (Qwen2.5-7B-VL)

| Setting | N | Strict | Relaxed | Status |
|---|---|---|---|---|
| Full test set | 7829/7859 | 34.60% | 48.10% | Effective local baseline; pending unified re-evaluation |
| Balanced-3000 coverage | 2990/3000 | 35.35% | 49.25% | Effective subset; missing items pending |
| Balanced-3000 missing=0 | 3000 | 35.23% | 49.08% | Conservative report ready; pending re-evaluation |

### Innovation 1 Controlled Comparisons (Qwen3-VL-8B, 32 views, 11,664 tokens)

#### Evidence-300 — Frozen Formal Comparison (July 16, 2026)

| Method | Strict | Relaxed | Paired Win/Tie/Loss | Bootstrap CI |
|---|---|---|---|---|
| Raw Uniform | 63.00% | 75.33% | — | — |
| MMR32 | 62.67% | 75.33% | 42/218/40 (Raw wins) | `[-0.0317, +0.0317]` |

**Conclusion**: Raw and MMR32 are statistically indistinguishable. Evidence localization does not stably translate to QA accuracy gain.

#### Confirm-300 — Raw Uniform Baseline

| Data | Strict | Relaxed |
|---|---|---|
| Confirm-300 Raw Uniform | **50.00%** | **68.50%** |
| Confirm-300B Raw Uniform | 50.33% | **68.50%** |

Raw Uniform achieves 68.50% Relaxed on two independent 300-sets — the most stable QA configuration.

#### Innovation 1 Route Results

| Route | Key Finding |
|---|---|
| **OCR Reliability Calibration** | Region Recall improved (7/10 → 10/10), QA unchanged |
| **Fixed Global/Local Budget** (24+8, 16+16) | Clear temporal/space tradeoff, no QA gain |
| **Focus-Context Temporal Encoding** | Pilot50 positive, Confirm-300B Relaxed pairwise mean negative |
| **Contrastive-Gradient Localization** | Concentration sharpened (0.0125 → 0.1534), Region Recall 7/10 |
| **VideoITG Strong Baseline** | Pilot50: Strict 44% (equal to Raw), Relaxed 60% (vs Raw 61%) |
| **24+8 Conservative Correction** | Evidence Recall 29/30 (below Raw 30/30); stopped before QA |

### Innovation 2 Key Results

| Stage | Finding |
|---|---|
| Counterfactual Sufficiency MVP (Pilot 100) | `s(E+) > s(E-)` direction correct, but 24+8 completion degraded QA (Raw Relaxed 58.0% → 55.0%) |
| v2.3 Claim Support/Conflict (Eval 69 pairs) | Visual pair accuracy 97.10%, AUROC 0.94938 — **evidence dependency established** |
| v2.3 Lightweight Verifier (Eval 69) | Pair accuracy 94.20% (below visual Qwen 97.10%, above text-only 85.51%) |
| RealClaim-300 Development Gate | Qwen visual AUROC 0.5510, v2.3 AUROC 0.5998 — **all pre-registered gates failed** |
| RealClaim-300 v2 (corrected frames) | Visual AUROC 0.5378 vs text-only 0.5457 — still using old semantic labels |
| EvidenceSupport-Pilot60 | Gold-label annotation protocol in progress |

## Reproducibility Index

### Code Paths

| Component | Path |
|---|---|
| Innovation 1 main inference | `evaluation/methods/av_evidence/inference_av_evidence_budget_v1.py` |
| Focus-context encoding | `evaluation/methods/av_evidence/focus_context.py` |
| Visual protocol audit | `evaluation/eval/audit_visual_protocol.py` |
| Focus mechanism audit | `evaluation/eval/audit_focus_context.py` |
| Claim support/conflict inference | `evaluation/tools/inference_claim_support_text_only_v23.py` |
| Lightweight verifier training | `evaluation/tools/train_lightweight_claim_evidence_verifier_v23.py` |
| RealClaim-300 build | `evaluation/tools/build_realclaim300_v1.py` |
| Qwen3-VL evaluation | `/代码/eval_qwen3.py` |

### Artifact Paths

| Experiment | Artifact Path |
|---|---|
| Confirm-300 | `artifacts/innovation1_confirm300_20260711_v1/` |
| 24+8 pilot | `artifacts/innovation1_budget24g8l_pilot50_20260712_v1/` |
| Focus-context pilot | `artifacts/innovation1_focuscontext32_pilot50_20260712_v1/` |
| Confirm-300B | `artifacts/innovation1_confirm300b_focuscontext_20260712_v1/` |
| Gradient localization | `artifacts/innovation1_contrastive_gradient_localization_pilot50_20260712_v1/` |
| Evidence-300 formal | `evaluation/runs/innovation1_evidence300_stage_v1/` |
| Adaptive router | `evaluation/runs/adaptive_temporal_router_evidence300_v1/` |
| Innovation 2 v2.3 | `evaluation/runs/innovation2_claim_support_conflict_v23/` |
| RealClaim-300 v1/v2 | `evaluation/runs/innovation2_realclaim300_v1/` |

### Experiment Data Requirements

To reproduce any controlled experiment, you need:
1. **Audited source frames**: 32/32 views, 11,664 tokens, secondary sampling off
2. **Protocol audit JSON**: Must pass before results are valid
3. **DeepSeek judge prompt**: Use historical Answer-only prompt for backward compatibility
4. **Paired bootstrap**: 10,000 resamples with per-question score difference
5. **SHA-256 dataset manifests**: Verify against recorded hashes

## Fair Protocol Requirements

Every experiment intended for thesis conclusions must satisfy:

1. **Same base model**: Both conditions use identical Qwen3-VL-8B checkpoint
2. **Same answer prompt**: Identical prompt template across conditions
3. **Same token budget**: 32 actual representation views, 11,664 visual tokens
4. **No secondary sampling**: `processor` must not re-sample frames
5. **Source frame control**: For ablation, 32 source frames must be identical between conditions
6. **Independent confirm set**: Pilot results must be validated on zero-overlap confirm sets
7. **Report paired metrics**: Never report only aggregate accuracy; always include win/tie/loss and bootstrap CI
8. **Two-table structure**: Table 1 = same-base fair comparison; Table 2 = cross-method reference (with footnotes for different bases/budgets)

### Two-Table Structure for Thesis (Frozen July 16, 2026)

**Table 1**: Same base model (Qwen3-VL-8B), same budget (11,664 visual tokens), same judge
- Raw Uniform32, CLIP Top-K32, VideoITG-32, MMR32 (self-intermediate), Proposed Method, Oracle (optional)

**Table 2**: Cross-method comparison with explicit footnotes
- AdsQA/Qwen, ReAd-R (Qwen2.5-VL-7B, GRPO), AD-MIR, Proposed Method
- Markers: `†` for local re-evaluation, `*` for original paper values

## Evaluation Scripts & Tools

Batch inference and orchestration scripts are in `/evaluation/scripts/`:
- `run_confirm3000_parallel_gate_v1.sh` — Main gate for 3000-run parallelism
- `watch_evidence300_formal_audit_v1.sh` — Audit pipeline
- `run_realclaim300_frozen_pipeline_v1.sh` — RealClaim pipeline
- `run_qwen25_shared32_isolation_gpu4_v1.sh` — Qwen2.5 isolation experiment

Analysis tools in `/evaluation/tools/` include:
- `analyze_realclaim300_v1.py` — RealClaim diagnostic analysis
- `audit_claim_support_conflict_v23.py` — Claim support audit
- `train_lightweight_claim_evidence_verifier_v23.py` — Verifier training
- `evaluate_development244_frozen_baselines_v1.py` — Development set evaluation
