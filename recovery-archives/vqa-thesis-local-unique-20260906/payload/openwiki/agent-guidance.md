---
type: Playbook
title: Agent Guidance for Thesis Workspace
description: Structured instructions for future agents working with this AdsQA master thesis repository. Covers entry points, source hierarchy, experimentation rules, and safety checks.
tags: [agent-guidance, workflow, safety]
---

# Agent Guidance

This page provides structured instructions for future AI agents working in this repository. Read this **first** before performing any operation.

## Before You Start

1. **Read the wiki entrypoint**: Start at [quickstart.md](quickstart.md), then follow links to relevant section pages
2. **For experiment questions**: Consult the central ledger at `/docs/AdsQA实验结果总表与复现索引.md` before running new experiments
3. **For innovation status**: Read `/docs/创新点一阶段性负结果与论文降级方案.md` — do NOT assume any innovation claim is valid without checking this document
4. **For decision history**: Read the [论文思考记录](/docs/论文思考记录.md) to understand why methodological decisions were made

## Source Hierarchy

When answering questions or making decisions, use this priority order:

1. **Experiment ledger** (`/docs/AdsQA实验结果总表与复现索引.md`) — for numbers and metrics
2. **Innovation status** (`/docs/创新点一阶段性负结果与论文降级方案.md`) — for claims and conclusions
3. **Chapter drafts** (`/docs/第3章*.md`, `/docs/第4章*.md`, `/docs/第5章*.md`) — for technical method details
4. **Research log** (`/docs/论文思考记录.md`) — for decision rationale and history
5. **Full thesis** (`/docs/完整论文_题目不变_证据流闭环版.md`) — for integrated framing

## Critical Safety Rules

### Do NOT

- **Do not claim QA accuracy improvement** for any evidence selection, cropping, verification, or completion module — this has been repeatedly disproven under fair protocol
- **Do not use Pilot50 results as final conclusions** — these were screening results that did not replicate on independent Confirm sets
- **Do not cite RealClaim-300 v1 results as evidence** — the v1 protocol had a frame-selection error (processor slot indices were mistaken for video frame numbers)
- **Do not mix different base models, token budgets, or judges in the same comparison table** without explicit footnotes
- **Do not report Strict alone** — always report both Strict and Relaxed with paired win/tie/loss and bootstrap CI
- **Do not treat artifacts/ or runs/ directories as canonical** — they contain intermediate results that may use different protocols
- **Do not edit `/AGENTS.md`, `/CLAUDE.md`, or `/docs/agent_orchestration_v2.md`** unless explicitly asked
- **Do not read or expose .env files, credentials, or secrets**

### Must Do

- **Verify experiment protocol** before citing any result: check visual protocol audit, token budget, secondary sampling status, and source frame identity
- **Validate against the fair protocol checklist**: same model, same budget, same judge, independent confirm set, paired bootstrap CI
- **For new experiments**: create a new experiment ID and result directory; never overwrite historical results
- **For ablation comparisons**: ensure source frames are identical between conditions
- **Use SHA-256 dataset manifests** to verify data integrity
- **Report both Strict and Relaxed** with paired win/tie/loss and 10,000× bootstrap CI

## Working with Evaluation Code

The evaluation framework is in `/evaluation/`:
- `evaluation/scripts/` — Shell scripts for batch inference orchestration, audit, and post-processing
- `evaluation/tools/` — Python scripts for analysis, audit, training, and data preparation
- `evaluation/methods/` — Method implementations (spatial cropping, focus-context, etc.)

When modifying or extending evaluation code:
1. Check that the fair protocol invariants are maintained (32 views, 11,664 tokens, no secondary sampling)
2. Run the visual protocol audit after inference
3. Use SHA-256 to verify dataset consistency

## Thesis Writing Guidance

If asked to help with thesis writing:

1. **Current innovation framing** (from the downgrade):
   - Innovation 1: Token-budget-constrained evidence localization + non-monotonicity finding
   - Innovation 2: Claim-evidence support/conflict verification + multimodal counterfactual ablation
   - Do not claim "stable QA accuracy improvement"

2. **Chapter 5 structure**: Follow the template in `/docs/第5章_实验设计与结果分析.md` but replace placeholder values with actual numbers from the experiment ledger

3. **Two-table structure**: Keep Table 1 (fair comparison, same base) and Table 2 (cross-method reference) separate, with clear footnotes

4. **Failure analysis**: Include dedicated subsections documenting failure modes for each innovation point

## File Exclusions

When performing file operations or searches, **exclude**:
- `.tmp*`, `tmp/`, `artifacts/`, `outputs/`, `output/`, `runs/`, `remote_staging/`, `remote_patch/`, `remote_work/`, `remote_worktree/`, `source_texts/`
- External JSON data files (e.g., `external_marketing_kb*.json`, `asr_set.json`, `testset_*.json`)
- PDFs, `.env`, credentials, node_modules, `.venv*`

These contain intermediate results, raw data, or administrative files that are not canonical wiki content.

## Stability & State

- This repository is a **master thesis continuation workspace** — it is actively developed with new experiments
- Key decisions are documented in [论文思考记录](/docs/论文思考记录.md)
- The central experiment ledger is the single source of truth for numbers
- Innovation claims are regularly re-evaluated through controlled experiments
- Before citing any experiment, verify that its protocol audit passed

## Git Awareness

This repository is **not a git repository** (no `.git` directory). All version tracking is done through:
- Date-stamped document files (`_20260719.md` suffixes)
- Chronological research log entries
- Explicit manifest SHA-256 hashes
- Run IDs and artifact directory timestamps

Treat file modification dates and document version numbers as the primary history mechanism.
