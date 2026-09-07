# External Marketing KB v1.1 Audit

## Files
- Input: `external_marketing_kb_v1_80.json`
- Output: `external_marketing_kb_v1_1_80.json`

## What changed
- Reworked weak / indirect items: `EXT031`, `EXT064`, `EXT074`, `EXT080`
- Rebalanced categories by recategorizing: `EXT018`, `EXT025`, `EXT071`, `EXT077`
- Preserved item count: **80**
- Preserved leakage constraint: **external public sources only**

## Category counts (v1.1)
- `target_audience`: 9
- `emotional_mechanism`: 7
- `cta_signal`: 6
- `sensory_appeal`: 6
- `ad_format`: 5
- `copy_signal`: 5
- `storytelling_device`: 5
- `brand_awareness`: 4
- `campaign_objective`: 4
- `consideration`: 4
- `metaphor`: 4
- `visual_rhetoric`: 4
- `brand_role`: 3
- `comparison`: 3
- `humor`: 3
- `social_proof`: 3
- `value_proposition`: 3
- `conversion`: 2

## Funnel counts
- `awareness`: 26
- `consideration`: 23
- `conversion`: 7
- `general`: 21
- `loyalty`: 3

## Top source concentrations
- 15 × YouTube Help — Tips for creating effective video ads
- 13 × Google Ads Help — About the ABCDs of effective video ads
- 9 × McGraw Hill — Advertising and Promotion (Belch) public textbook page
- 8 × Google Ads Help — Tips for optimizing your Video campaign
- 6 × Nielsen — Advertising emotions increase sales
- 5 × WARC — The power of storytelling in building brand value
- 5 × Kantar — Creative consumer connections: how to reach your consumers
- 5 × Kantar — The art of proof: how creative quality drives profit

## Review notes
- v1.0 did not show strong near-duplicate rule bodies, but it did have source concentration around Google/YouTube guidance.
- The biggest balance issue was category overuse of `target_audience` and `emotional_mechanism`.
- v1.1 reduces the weakest platform-specific inference and turns one indirect metric item into a more concrete format rule.
- This is still a curated heuristic KB, not a claim-by-claim research bibliography. The next useful step is retrieval-time evaluation against held-out question templates.
