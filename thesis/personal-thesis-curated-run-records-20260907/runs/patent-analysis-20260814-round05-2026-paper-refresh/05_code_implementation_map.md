# Implementation Map

| Mechanism | Existing basis | Missing work | Difficulty |
|---|---|---|---|
| Initial evidence and A0/A2 fallback | Existing experiment pipeline | Normalize interfaces | Low |
| Stable `claim_id` and `QSlot` | Claim split scripts | Stable serialization and answer positions | Medium |
| Frozen `W` | None | Dependency graph and closure | Medium |
| Resolution-gain selector | Existing acquisition actions | Labels, ranker and STOP calibration | Medium-high |
| Action descriptor to command | Existing video/OCR/ASR calls | Typed descriptors and adapters | Medium |
| Command-result audit | Metadata fields partly exist | Range/modality/cost/provenance checks | Medium |
| `P subset W` patch | Prompt-level minimal edit | Structured patch and deterministic assembler | Medium |
| `D/M/K` | Support scoring experiments | Fixed candidate/control evaluator | Medium-high |
| Atomic commit/restore | Basic fallback | Multi-claim transaction and audit log | Medium |

## Minimum Prototype Order

1. Stable claims and `W`.
2. Typed patch and deterministic assembler.
3. Command audit and provenance.
4. `D/M/K`.
5. Resolution-gain action labels and selector.
