# VQA local-unique recovery archive (2026-09-06)

This package is a content-addressed backup of the remaining personal VQA
research material from `/Users/bytedance/vqa_thesis_continue`. It was prepared
without modifying the originals.

## Scope and safety boundary

- Includes 677 staged files (22685630 bytes) from local review
  derivatives, personal research scripts, AgentSkill-Eval study revisions,
  software-copyright drafts, and generated OpenWiki pages.
- Does not include raw AdsQA video files, model weights, data sets, Git metadata,
  company-domain artifacts, secret files, or private reference-answer records.
- A static scan found 30 API-key/token *environment
  or placeholder references* and no embedded high-confidence credential.
- `MANIFEST.tsv` records all source candidates, including files omitted because
  their exact Git blob already exists on the verified `adsqa-research-code`
  remote or because an identical local canonical copy is present here.

## Verification instructions

1. Verify every `payload/` file against `SHA256SUMS`.
2. For files marked `ALREADY_REMOTE_ORIGIN_MAIN`, verify the listed Git blob in
   commit `30d5974a0bca7eed0daaf467b976067a02c9bb47` (the remote `origin/main` commit at staging time).
3. Restore the omitted duplicate path by copying the listed canonical payload
   file; the content SHA-256 is identical.

## Archive accounting

| Category | Files |
|---|---:|
| staged payload | 677 |
| already present in origin/main by Git blob | 15 |
| exact duplicate source copies omitted | 10 |
| private-reference files retained locally, not uploaded | 4 |

No original file was moved or deleted while creating this package.
