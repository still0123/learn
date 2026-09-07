# 2026 Paper Comparison Matrix

| Paper | Status | Known mechanism | Overlap | Remaining distinction |
|---|---|---|---|---|
| Active Video Perception | CVPR 2026 Findings | Plan-observe-reflect, targeted video interaction, sufficiency stop | Action selection and stop | Claim-slot resolution target plus restricted patch transaction |
| VideoSEAL | ICML 2026 regular | Planner-inspector decoupling and pixel evidence gate | Search/answer authority separation | `W/P` program write set and `D/M` atomic patch gate |
| Chain-of-Glimpse | ICML 2026 regular | Search-guided object-region trajectories | Spatial acquisition | Executable command, audited evidence and claim-level commit |
| Video-MTR | ICML 2026, arXiv camera-ready | Multi-turn segment selection and bi-level reward | Selector training | Not used as independent-claim novelty |
| IV-Bench | ICLR 2026 Poster | Image-grounded video benchmark; more frames may not improve temporal reasoning | Motivates selective acquisition | No direct restricted update transaction |
| ArrowGEV | ACL 2026 Findings | Forward/backward temporal-direction learning | Time-sensitive evidence | Kept outside the core claim |
| MUSEG | ACL 2026 Long | Timestamp-aware multi-segment grounding | Multi-window evidence | Kept as optional implementation |
| EMCompress | ACL 2026 Findings | Answer invariance under compression | Non-target invariance | V0.4 uses deterministic program copy and write set |
| RLER | CVPR 2026 per arXiv | Evidence-weighted candidate election | Candidate preference | V0.4 updates only `P subset W` after `D/M` |
| MoHoBench | AAAI 2026 | Unanswerable visual questions and refusal alignment | Unresolved/negative output | Verified absence requires predefined video coverage checks |
| CRAFT | ACL 2026 Workshop | Atomic claims, critic repair and citation merging | Claim verification | Frozen write set and atomic restore |
| TRACE | ACL 2026 Workshop | OCR/object timeline, evidence-first claim generation | Structured evidence | Utility-controlled reacquisition and commit gate |
| EviSelect | 2026 arXiv | Attention-driven dynamic temporal/spatial visual selection | Gain-cost selector | V0.4 does not claim selector architecture; ties result to `W/D/M` |
| Video-o3 | 2026 arXiv | Seek/jump/zoom/end tool trajectory | Action space and adaptive stop | Action names not relied upon |
| E-VQA | 2026 arXiv | Answer plus dense spatio-temporal evidence | Evidence-backed QA | Evidence controls a restricted patch transaction |
| CREDiT | 2026 arXiv | Counterfactual causal evidence disentanglement | `D`-like attribution | `D` is only one gate in `D/M/W/P` |
| Kestrel | 2026 arXiv | Grounding agent, evidence verification, self-refinement | Verify then revise | No whole-answer rewrite; program-level write set |
| VAD | 2026 arXiv | Evidence-present/removed visual attribution | Fixed-context evidence difference | Coupled to slot update advantage and version transaction |

The paper URLs and detailed notes are recorded in the research report referenced by `01_material_inventory.md`.
