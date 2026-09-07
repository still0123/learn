# Office-Action Risk Map

## Expected Combination Attack

1. Use AVP, Video-MTR, Video-o3, Chain-of-Glimpse or EviSelect for active video evidence acquisition and stopping.
2. Use VideoSEAL or Kestrel for separating search from answer verification.
3. Use CRAFT or TRACE for atomic claims, evidence citations and critic verification.
4. Use CREDiT or VAD for evidence-present/evidence-removed attribution.
5. Use RLER for evidence-weighted candidate preference.
6. Treat `W/P` and rollback as conventional software transaction control.

## Weak Points in V0.3

- `G_pred` could be interpreted as confirming the old claim value, creating confirmation bias.
- Planning metadata was not expressly excluded from supporting evidence in all claim paths.
- A selected command could fail or return a mismatched result without an explicit admission gate.
- The independent claim remained long and exposed many individually known components.

## V0.4 Response

- `G_pred` now targets `QSlot` resolvability or evidence-gap reduction, including refuting the old value.
- Action descriptors, utility scores and commands are expressly non-evidentiary.
- Only successful, command-consistent, budget-compliant and raw-video-traceable results enter `D/M/K`.
- The core combination remains `QSlot resolution utility -> audited evidence -> W/P -> D/M/K -> atomic commit/restore`.
