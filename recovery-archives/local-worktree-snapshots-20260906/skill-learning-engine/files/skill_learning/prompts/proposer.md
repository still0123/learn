Diagnose the summarized Train outcomes before proposing one atomic edit to the named Skill. The request
assigns exactly one `target_pattern`; propose a reusable rule for that pattern only, not a combined
rewrite for every visible failure. Return that one pattern ID in `pattern_ids`.
For `evidence_ids`, copy only the exact IDs listed on `target_pattern.evidence_ids`; do not invent,
rename, or summarize trace IDs.
First inspect `wiki/index.md` and `wiki/skill-impact.md`, then read relevant Pattern pages and
the required number of files under `traces/`. Rejected approaches in the impact history must
not be repeated without new evidence. The edit must replace one exact text span, cite supplied
Pattern and trace IDs, and express a reusable procedure rather than task answers. Do not edit
files directly. Call `submit_result` exactly once after completing the required reads.
