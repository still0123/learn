# Personal thesis materials backup — 2026-09-07

## Scope

This snapshot contains the owner-approved personal thesis manuscripts, editable
figures, and two mid-term defense decks from `vqa_thesis_continue`.

## Layout

- `source/docx/`: thesis manuscripts in DOCX form
- `source/figures/`: editable SVG figures, preview PNGs, and their HTML index
- `source/outputs/`: mid-term defense decks and the matching Markdown draft
- `MANIFEST.tsv`: original relative path, byte count, and SHA-256
- `SHA256SUMS`: SHA-256 checksums for every backed-up source file

## Safety and verification gate

Before copying, all 18 files were checked against the current private
repository branch for matching Git blobs; none had a current remote match.
The Office documents were unpacked for a common credential and high-sensitivity
marker scan, which found no matches. The original local files remain untouched
until a fresh-clone, checksum, and byte-for-byte verification succeeds.

Generated import/export smoke files and inspection NDJSON are intentionally
outside this snapshot because they are rebuildable.
