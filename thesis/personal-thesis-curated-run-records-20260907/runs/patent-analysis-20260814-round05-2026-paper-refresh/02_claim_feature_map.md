# Claim Feature Map

| Claim step | Technical object | Input | Output | Current support |
|---|---|---|---|---|
| S1 | Answer version and claims | Video, question, initial evidence | `V0`, `ClaimRecord`, `QSlot` | Claim splitting partial; stable IDs new |
| S2 | Frozen write set | Support state, dependency graph | `W` | New |
| S3 | Acquisition candidates | `QSlot`, evidence gap | `ActionDescriptor[]` | New |
| S4 | Resolution utility | Evidence state, gap, action descriptors | `G_pred`, `U_pred`, selected action | New |
| S5 | Executable acquisition and audit | Selected descriptor | command, audited evidence | Command conversion and audit new |
| S6 | Restricted patch | Full evidence, `W` | `P subset W` | Prompt-only partial; program patch new |
| S7 | Evidence dependence and update advantage | Fixed candidate, controls, full evidence | `D`, `M` | New |
| S8 | Commit gates | `D/M/K`, QSlot, `W/P` | pass/fail | New |
| S9 | Versioned update | Valid patch or failure | atomic commit or restore `V0` | Basic fallback exists; atomic claim transaction new |

## Critical Coupling

`S4` controls only acquisition. `S5` excludes planning metadata from factual evidence. `S7-S9` alone control answer modification. This separation must remain explicit.
