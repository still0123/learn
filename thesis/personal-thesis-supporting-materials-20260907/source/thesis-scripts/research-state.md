# Research State: AdsQA evidence-centric video VQA trends

## Current Stage
SYNTHESIZE

## Research Question
How do recent computer vision and multimodal video-understanding trends affect an AdsQA thesis based on token compression, evidence selection, RAG, and chain-of-thought/reflection?

## Key Decisions
- SCOPE: Treat the user request as a literature-grounded positioning check rather than a compute task.
- LITERATURE: Used literature-review subagents plus arXiv connector searches because bundled research skills were unavailable in this environment.
- SYNTHESIZE: The defensible direction is evidence-centric video VQA under fixed visual-token budgets; prompt-only chain-of-thought/reflection should be demoted to output protocol or analysis, not claimed as a main novelty.

## Experiment Log
| Attempt | Method | Result | Status |
|---------|--------|--------|--------|
| 1 | Literature scan across video VQA, VLM reasoning, token-efficient video understanding | Recent work emphasizes temporal grounding, query-aware evidence selection, token compression, visual grounding, and hallucination verification | Complete |

## Critique History
- Pre-COMPUTE: Not applicable; no compute launched.
- Post-COMPUTE: Not applicable; no compute launched.

## What Worked
- Recent papers support framing AdsQA around evidence retrieval/selection, visual-token budgets, ASR/OCR grounding, and negative results showing evidence localization does not automatically improve QA.

## What Didn't Work
- Atlas initialization failed due to unauthenticated OpenScience login; `atlas` CLI is unavailable in this environment.
- Skills `research-lookup`, `literature-review`, and `scientific-critical-thinking` were unavailable through the skill tool, so direct literature agents and arXiv searches were used.

## Open Questions
- Whether to rename the thesis to remove chain-of-thought/reflection from the title, or keep the old title and reinterpret reflection as evidence verification.

## Artifacts
- literature-review.md: missing
- reasoning.md: missing
- methodology.md: missing
- figures/: not applicable
- experiments.tsv: not applicable

---

# Research State Addendum: AgentSkill-Eval skill evaluation optimization

## Current Stage
SYNTHESIZE

## Research Question
What related work and optimization ideas can AgentSkill-Eval borrow for evaluating and improving agent skills?

## Key Decisions
- SCOPE: Treat the request as a literature-grounded positioning and optimization scan, not a compute task.
- LITERATURE: Used Atlas initialization, direct arXiv/OpenAlex/Semantic Scholar searches, and literature-review subagents because bundled research skills were unavailable through the skill loader in this runtime.
- SYNTHESIZE: Closest related lines are LLM-agent benchmarks, tool-use benchmarks, prompt/agent optimization, and emerging SKILL.md/skill-artifact research; AgentSkill-Eval remains differentiated by paired marginal-value evaluation of skills.

## Experiment Log
| Attempt | Method | Result | Status |
|---------|--------|--------|--------|
| 1 | Literature scan across agent benchmarks, tool benchmarks, prompt optimization, skill artifacts | Identified borrowable ideas: process metrics, stable virtual environments, skill contracts/IR, skill retrieval eval, failure-driven optimization, locked evaluation hygiene | Complete |

## Critique History
- Pre-COMPUTE: Not applicable; no compute launched.
- Post-COMPUTE: Not applicable; no compute launched.

## What Worked
- Literature around AgentBench, AgentBoard, WebArena, SWE-bench, ToolLLM/StableToolBench, AppWorld, DSPy, APE, APO, OPRO, TextGrad, Reflexion, Voyager, Skill-as-Pseudocode, SkCC, and Contractual Skills gives direct optimization ideas.

## What Didn't Work
- Skill tool could not load `research-lookup` in this runtime; direct database searches and literature-review subagents were used instead.
- `atlas` CLI is unavailable, but `openscience project init --format=json` successfully linked an Atlas project graph.

## Open Questions
- Which optimization direction to prioritize first: skill contract/IR, discovery/retrieval evaluation, or failure-driven skill mutation with confirmation split.

## Artifacts
- literature-review.md: not created for this quick scan
- reasoning.md: not created for this quick scan
- methodology.md: not created for this quick scan
- figures/: not applicable
- experiments.tsv: not applicable
