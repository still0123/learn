# AdsQA 2026 Crop Literature Review

Search date: 2026-08-06

## Scope

- Included: papers first released or formally published in 2026.
- Topic: query-guided cropping, active visual perception, region retrieval,
  high-resolution VQA, and grounded OCR.
- Engineering gate: public paper plus enough public code or weights to support
  an answer-free, fixed-budget, two-anchor experiment.
- Excluded from the primary list: 2025 preprints, even if revised in 2026.

## Main Finding

The 2026 literature points to four concrete weaknesses in a plain
attention-map crop:

1. Raw attention aggregation is noisy; useful grounding is concentrated in a
   subset of heads.
2. A model may locate a correct crop but continue to rely on the global image.
3. One dominant saliency region can hide spatially disjoint supporting
   evidence.
4. Local detail must retain enough instruction-relevant context, not merely
   maximize saliency.

These weaknesses match the AdsQA negative results: DeepEyes and ZoomEye failed
at Screen, while VLM-R3 improved at Screen but did not replicate at
Confirmation.

## Verified 2026 Papers

| Priority | Paper | Mechanism | Public assets | AdsQA assessment |
|---|---|---|---|---|
| 1 | Q-Zoom: Query-Aware Adaptive Perception for Efficient Multimodal Large Language Models, arXiv:2604.06912 | Dynamic gate plus self-distilled region proposal network; re-decodes a query-relevant ROI | Qwen2.5/Qwen3 code, training data, and Qwen3-VL-4B checkpoint are public | Best immediately executable policy; export ROI only and keep Clean Qwen3-VL-8B as final answer model |
| 2 | Entropy-Gradient Grounding: Training-Free Evidence Retrieval in Vision-Language Models, arXiv:2604.08456, ECCV 2026 | Backpropagates next-token entropy to visual embeddings; ranks disjoint regions; iterative zoom with spatial-entropy stopping | LLaVA code public; Qwen code still marked coming soon | Best mechanism match for Evidence Gap, but requires a Qwen3 adapter before formal use |
| 3 | TikArt: Stabilizing Aperture-Guided Fine-Grained Visual Reasoning with Reinforcement Learning, arXiv:2602.14482 | Qwen3-VL-8B Think-Aperture-Observe loop with box Zoom and SAM2 Segment actions | Code and TikArt-8B weights public | Reproducible fallback; Segment view is substantively different from failed bbox-only policies |
| 4 | Focus, Don't Prune: Identifying Instruction-Relevant Regions for Information-Rich Image Understanding, arXiv:2603.22815, CVPR 2026 | Instruction-region alignment followed by independent region refinement | Qwen2-VL/LLaVA code and models public | Strong for text-rich ads, but backbone and token-refinement integration are less direct |
| 5 | Learning to Focus and Precise Cropping, arXiv:2603.27494 | Information-gap RL plus grounding loss to force dependence on crop evidence | Repository exists, but code and releases are still absent | Important diagnosis; not currently reproducible |
| 6 | Head-Aware Visual Cropping, arXiv:2601.22483 | OCR-diagnostic head selection, spatial entropy, and gradient sensitivity | No official code or weights found | Useful design evidence, but not eligible for a formal candidate |
| 7 | Look Where It Matters: High-Resolution Crops Retrieval for Efficient VLMs, arXiv:2603.16932 | AwaRes low-resolution global view plus learned crop retrieval | Paper available | Already tested locally; AwaResFirst10 produced no gain and is closed |
| 8 | UHR-BAT, arXiv:2604.13565 | Query-guided multi-scale importance plus region-wise preserve-and-merge | Repository announced | Token-compression architecture, not a clean two-crop policy |
| 9 | LLaVA-UHD v4, arXiv:2605.08985 | Slice-based encoding with early in-ViT token compression | Code repository announced | Requires changing the final model architecture, violating the frozen answer-model control |
| 10 | GutenOCR, arXiv:2601.14490 | Query-conditioned text-box detection and localized reading | Code and open weights public | Possible OCR-specific auxiliary locator, not a general crop policy |

## Recommended Finite Search Order

Complete the already preregistered HiDe Screen first. If it fails:

### Candidate 1: QZoomROI10

- Frozen policy: public `Q-Zoom-Qwen3VL-4B`.
- Input: each of the same two frozen anchor frames plus the question.
- Output used: SD-RPN top ROI only; Q-Zoom answer and dynamic gate are ignored.
- Candidate views: two 896 x 896 ROI crops.
- Fallback: frozen AVFunnel-mid crop when no valid ROI exists.
- Final answer model: unchanged Clean Qwen3-VL-8B.
- No AdsQA labels, references, or judge scores are read by the policy.
- One official checkpoint and one fixed ROI rule; no threshold sweep.

### Candidate 2: EntropyGradientCompact10

Run only after a Qwen3 interface and semantic Smoke pass:

- Compute next-token entropy gradients from question plus anchor image.
- Extract the official ranked disjoint coherent regions.
- Preserve all official default stopping and ranking rules.
- Pack selected regions into one layout-preserving compact image per anchor;
  do not collapse them into a union bbox.
- Two 896 x 896 compact views, same final Qwen3-VL-8B answer model.
- No threshold or region-count tuning on AdsQA scores.

This combines the paper's uncertainty-guided multi-evidence retrieval with the
already audited compact-layout renderer. It changes the localization signal,
not the answer protocol.

### Candidate 3: TikArtAperture10

- Frozen policy: public TikArt-8B checkpoint.
- Use the last successfully executed aperture per anchor.
- Preserve both official Zoom and Segment actions.
- Render a Segment result as a masked object-centric view, not its enclosing
  rectangle.
- Ignore TikArt's final answer.
- No prompt, iteration, or action-type selection after observing AdsQA scores.

## Closed or Deferred

- AwaRes: closed by local negative Screen.
- DeepEyes: ICLR 2026, but closed by local negative Screen.
- LFPC: deferred until code and a fixed checkpoint exist.
- HAVC: deferred until official code and frozen expert-head indices exist.
- PinPoint: deferred behind Q-Zoom because it needs more backbone-specific
  integration and is trained primarily for document-style inputs.
- UHR-BAT and LLaVA-UHD v4: excluded because they alter token encoding or the
  answer model rather than producing the required two crop views.

## Sources

- https://arxiv.org/abs/2604.06912
- https://github.com/YuHengsss/Q-Zoom
- https://arxiv.org/abs/2604.08456
- https://github.com/merci00001/entropy-gradient-grounding
- https://arxiv.org/abs/2602.14482
- https://github.com/TikArt-Team/TikArt
- https://arxiv.org/abs/2603.22815
- https://github.com/minckwon/PinPoint
- https://arxiv.org/abs/2603.27494
- https://github.com/XuanPu-Z/LFPC
- https://arxiv.org/abs/2601.22483
- https://arxiv.org/abs/2603.16932
- https://arxiv.org/abs/2604.13565
- https://arxiv.org/abs/2605.08985
- https://arxiv.org/abs/2601.14490
