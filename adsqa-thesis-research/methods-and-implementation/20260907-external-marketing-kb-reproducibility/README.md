# External marketing knowledge-base reproducibility inputs

This small personal thesis-research snapshot preserves the two local versions
of the external marketing knowledge base and the audit script used to inspect
their schema, provenance fields, and near-duplicate entries.

## Included

- `source/audit_external_kb.py`: deterministic local audit utility.
- `source/external_marketing_kb_v1_80.json`: version 1 snapshot.
- `source/external_marketing_kb_v1_1_80.json`: version 1.1 snapshot.

The JSON snapshots differ byte-for-byte, so both are retained. A targeted
static scan found no private-key block, GitHub token, common API-key pattern,
or the reviewed company-marker strings. This is a preservation snapshot, not
a claim about the provenance or license of every external source referenced by
the knowledge-base records.

## Verify

```sh
shasum -a 256 -c SHA256SUMS
```
