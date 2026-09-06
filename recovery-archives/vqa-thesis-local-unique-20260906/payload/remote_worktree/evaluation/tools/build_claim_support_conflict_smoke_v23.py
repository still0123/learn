#!/usr/bin/env python3
"""Build and independently audit a 30-item claim support/conflict label smoke."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any
from urllib import error, request


GENERATOR_VERSION = "adsqa_claim_triplet_generator_v23"
AUDITOR_VERSION = "adsqa_claim_triplet_auditor_v23"
GENERATOR_PROMPT = """You create hard claim-verification examples for advertisement video evidence.

Question: {question}
Verified evidence fact: {fact}

Return one JSON object with exactly these string fields:
- contradicted_claim: a fluent answer claim that stays on the same question and changes exactly one decisive factual atom, so it directly conflicts with the verified fact.
- changed_atom: briefly state the single factual atom changed.
- insufficient_claim: a fluent answer claim that stays on the same question but adds one plausible specific detail not established or contradicted by the verified fact.

Do not mention evidence, annotations, ground truth, verification, or this instruction. Do not merely negate the whole sentence. Keep each claim under 70 words. Output JSON only."""
AUDITOR_PROMPT = """You audit a claim-verification triplet using only the verified fact below.

Question: {question}
Verified fact: {fact}
Supported claim: {supported}
Candidate contradicted claim: {contradicted}
Claimed changed atom: {changed_atom}
Candidate insufficient claim: {insufficient}

Return one JSON object with exactly these fields:
- supported_matches_fact: boolean
- contradiction_same_question: boolean
- contradiction_changes_exactly_one_atom: boolean
- contradiction_directly_conflicts: boolean
- insufficient_same_question: boolean
- insufficient_not_established: boolean
- insufficient_not_directly_conflicted: boolean
- no_meta_language: boolean
- contradiction_reason: short string
- insufficient_reason: short string

Be strict. If the insufficient claim can be inferred from the verified fact, mark insufficient_not_established false. Output JSON only."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def stable_rank(seed: int, qid: str) -> str:
    return hashlib.sha256(f"{seed}:{qid}".encode("utf-8")).hexdigest()


def extract_json(text: str) -> dict[str, Any]:
    value = str(text or "").strip()
    value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.IGNORECASE)
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", value, re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("model response is not a JSON object")
    return parsed


def api_call(prompt: str, model: str, base_url: str, api_key: str, attempts: int = 4) -> tuple[dict[str, Any], dict[str, Any]]:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps({
        "model": model, "temperature": 0.0, "max_tokens": 500,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    last_error = None
    for attempt in range(attempts):
        try:
            req = request.Request(endpoint, data=payload, method="POST", headers={
                "Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
            })
            with request.urlopen(req, timeout=120) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return extract_json(content), {
                "response_model": body.get("model"), "usage": body.get("usage"),
                "content_sha256": sha256_text(content),
            }
        except (error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"API call failed after {attempts} attempts: {last_error}")


def validate_generated(value: dict[str, Any], supported: str) -> list[str]:
    errors = []
    required = ("contradicted_claim", "changed_atom", "insufficient_claim")
    for key in required:
        if not isinstance(value.get(key), str) or not value[key].strip():
            errors.append(f"missing_{key}")
    if errors:
        return errors
    if value["contradicted_claim"].strip().casefold() == supported.strip().casefold():
        errors.append("contradiction_identical_to_supported")
    if value["insufficient_claim"].strip().casefold() == supported.strip().casefold():
        errors.append("insufficient_identical_to_supported")
    if len(value["contradicted_claim"].split()) > 70 or len(value["insufficient_claim"].split()) > 70:
        errors.append("claim_too_long")
    forbidden = re.compile(r"ground truth|annotation|verified fact|the evidence|this instruction", re.IGNORECASE)
    if forbidden.search(value["contradicted_claim"]) or forbidden.search(value["insufficient_claim"]):
        errors.append("meta_language")
    return errors


def audit_passes(value: dict[str, Any]) -> tuple[bool, list[str]]:
    required_true = (
        "supported_matches_fact", "contradiction_same_question",
        "contradiction_changes_exactly_one_atom", "contradiction_directly_conflicts",
        "insufficient_same_question", "insufficient_not_established",
        "insufficient_not_directly_conflicted", "no_meta_language",
    )
    failures = [key for key in required_true if value.get(key) is not True]
    return not failures, failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--router-dataset", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--per-type", type=int, default=6)
    parser.add_argument("--seed", type=int, default=2026071603)
    parser.add_argument("--max-workers", type=int, default=6)
    parser.add_argument("--all-eligible", action="store_true")
    parser.add_argument("--include-split", action="append", default=[])
    args = parser.parse_args()
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    annotations = {str(row["question_id"]): row for row in load_json(args.annotations)}
    router = load_jsonl(args.router_dataset)
    pools: dict[str, list[dict[str, Any]]] = {f"Type_{index}": [] for index in range(1, 6)}
    included_splits = set(args.include_split or ["train"])
    for row in router:
        qid = str(row["question_id"])
        annotation = annotations[qid]
        if row.get("split") not in included_splits:
            continue
        if annotation.get("review_confidence") != "high":
            continue
        if annotation.get("evidence_observability") not in {"visual", "visual_audio", "audio"}:
            continue
        fact = str(annotation.get("decisive_fact", "")).strip()
        if not fact:
            continue
        pools[str(row["primary_type"])].append({
            "question_id": qid, "video_id": str(row["video_id"]),
            "split": str(row["split"]), "primary_type": str(row["primary_type"]), "question": str(row["question"]),
            "supported_claim": fact,
        })
    selected, videos = [], set()
    if args.all_eligible:
        selected = sorted(
            [row for values in pools.values() for row in values],
            key=lambda row: (row["split"], stable_rank(args.seed, row["question_id"])),
        )
        videos = {row["video_id"] for row in selected}
    else:
        for _ in range(args.per_type):
            for primary_type in [f"Type_{index}" for index in range(1, 6)]:
                ranked = sorted(pools[primary_type], key=lambda row: stable_rank(args.seed, row["question_id"]))
                candidate = next((row for row in ranked if row["video_id"] not in videos and row not in selected), None)
                if candidate is None:
                    raise RuntimeError(f"insufficient unique high-confidence rows for {primary_type}")
                selected.append(candidate)
                videos.add(candidate["video_id"])

    def process(row: dict[str, Any]) -> dict[str, Any]:
        generator_prompt = GENERATOR_PROMPT.format(question=row["question"], fact=row["supported_claim"])
        generated, generator_meta = api_call(generator_prompt, model, base_url, api_key)
        deterministic_errors = validate_generated(generated, row["supported_claim"])
        auditor_prompt = AUDITOR_PROMPT.format(
            question=row["question"], fact=row["supported_claim"], supported=row["supported_claim"],
            contradicted=generated.get("contradicted_claim", ""), changed_atom=generated.get("changed_atom", ""),
            insufficient=generated.get("insufficient_claim", ""),
        )
        audited, auditor_meta = api_call(auditor_prompt, model, base_url, api_key)
        audit_ok, audit_failures = audit_passes(audited)
        return {
            **row, "generator_version": GENERATOR_VERSION, "generated": generated,
            "deterministic_errors": deterministic_errors, "auditor_version": AUDITOR_VERSION,
            "audit": audited, "audit_failures": audit_failures,
            "passed": not deterministic_errors and audit_ok,
            "provenance": {"generator": generator_meta, "auditor": auditor_meta},
        }

    results, failures = [], []
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = {executor.submit(process, row): row for row in selected}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                failures.append({"question_id": futures[future]["question_id"], "error": str(exc)})
    order = {row["question_id"]: index for index, row in enumerate(selected)}
    results.sort(key=lambda row: order[row["question_id"]])
    passed = [row for row in results if row["passed"]]
    pass_rate = len(passed) / len(selected)
    contradiction_fields = (
        "supported_matches_fact", "contradiction_same_question",
        "contradiction_changes_exactly_one_atom", "contradiction_directly_conflicts", "no_meta_language",
    )
    contradiction_passed = [
        row for row in results
        if not row.get("deterministic_errors")
        and all((row.get("audit") or {}).get(field) is True for field in contradiction_fields)
    ]
    contradiction_pass_rate = len(contradiction_passed) / len(selected)
    audit = {
        "schema": "adsqa_claim_support_conflict_smoke_audit_v23",
        "selected": len(selected), "completed": len(results), "api_failures": failures,
        "passed": len(passed), "pass_rate": pass_rate,
        "contradiction_passed": len(contradiction_passed),
        "contradiction_pass_rate": contradiction_pass_rate,
        "split_counts": dict(__import__("collections").Counter(row["split"] for row in selected)),
        "primary_type_counts": {key: sum(row["primary_type"] == key for row in selected) for key in pools},
        "unique_videos": len(videos), "generator_prompt_sha256": sha256_text(GENERATOR_PROMPT),
        "auditor_prompt_sha256": sha256_text(AUDITOR_PROMPT),
        "model_requested": model,
        "label_quality_gate": contradiction_pass_rate >= 0.90 and not failures,
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    result_path = args.output_root / "triplets_audited.jsonl"
    write_jsonl(result_path, results)
    write_json(args.output_root / "audit.json", audit)
    write_json(args.output_root / "manifest.json", {
        "schema": "adsqa_claim_support_conflict_smoke_manifest_v23",
        "results": {"path": str(result_path), "sha256": sha256_file(result_path)},
        "audit": audit, "api_key_archived": False,
    })
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
