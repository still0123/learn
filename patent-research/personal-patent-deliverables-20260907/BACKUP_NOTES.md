# Personal patent deliverables backup — 2026-09-07

## Scope

This snapshot contains 389 owner-approved personal patent deliverables copied
from `vqa_thesis_continue/deliverables/patent`. It preserves the original
relative paths under `source/`.

## Verification material

- `MANIFEST.tsv` records the original relative path, byte count, and SHA-256.
- `SHA256SUMS` covers every copied source file.

Before copying, the candidate set was compared with the current private
repository branch: no file had an equivalent Git blob or Git LFS content
match. The source tree was scanned for common credential, identity-document,
and recovery-code markers; Office and ZIP containers were unpacked for the
same scan.

## Deliberate exclusion

One ZIP is outside this GitHub backup because its unpacked contents mention
identity-document fields and include a passport-like identifier pattern. It is
listed in `EXCLUDED_FROM_GITHUB.md` and remains untouched in its original
location pending a secure-storage or discard decision.

No source original is moved until a fresh clone, checksum, and byte-for-byte
comparison has succeeded.
