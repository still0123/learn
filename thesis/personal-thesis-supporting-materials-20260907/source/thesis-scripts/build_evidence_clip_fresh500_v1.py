#!/usr/bin/env python3
"""Build answer-free continuous evidence-clip candidates for Fresh-500."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

FORBIDDEN = {"answer", "ground_truth", "reference_answer", "judge_score", "label"}

def args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    for name in ("items", "siglip-manifest", "source-root", "video-index-dir", "output-root"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--max-items", type=int, default=-1)
    return p.parse_args()

def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()

def canon(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(x, ensure_ascii=True) + "\n" for x in rows), encoding="utf-8")

def load_by_id(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in jsonl(path):
        qid = str(row.get("question_id", ""))
        if not qid or qid in out: raise RuntimeError(f"duplicate/missing question_id: {qid}")
        out[qid] = row
    return out

def load_indexes(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for shard in sorted(path.glob("index_shard*of4.jsonl")):
        for row in jsonl(shard):
            vid = str(row.get("video_id", ""))
            if not vid or vid in out: raise RuntimeError(f"duplicate/missing video_id: {vid}")
            out[vid] = row
    return out

def window(center: int) -> tuple[int, int]:
    if center <= 1: return 0, 2
    if center >= 30: return 29, 31
    return center - 1, center + 1

def make_row(item: dict[str, Any], source: dict[str, Any], siglip: dict[str, Any], method: str) -> dict[str, Any]:
    candidate64 = [int(x) for x in siglip["candidate64_frame_indices"]]
    if len(candidate64) != 64: raise RuntimeError(f"candidate64 length != 64 for {item['question_id']}")
    a0_frames = {int(x) for x in item["a0_frame_indices"]}
    anchors = source.get("evidence_anchors", [])
    if len(anchors) != 2: raise RuntimeError(f"source anchor count != 2 for {item['question_id']}")
    output = dict(item); new_anchors: list[dict[str, Any]] = []
    for ai, anchor in enumerate(anchors):
        center = int(anchor["source_global_rank"])
        if center < 0 or center >= 64: raise RuntimeError(f"invalid center rank for {item['question_id']}")
        if method != "fixed_clip" and int(anchor["source_frame_index"]) in a0_frames:
            raise RuntimeError(f"clip center reuses A0 frame for {item['question_id']}")
        start, end = window(center)
        new_anchors.append({
            "anchor_index": ai, "source_global_rank": center, "source_frame_index": candidate64[center],
            "bbox_norm": [0.0, 0.0, 1.0, 1.0], "bbox_source": f"{method}:continuous_clip",
            "scale_level": "full", "dominant_slot": anchor.get("dominant_slot", "visual"),
            "slot_scores": anchor.get("slot_scores", {"visual": 0.0, "ocr": 0.0, "asr": 0.0}),
            "sources": sorted(set(anchor.get("sources", []))), "clip_start_rank": start,
            "clip_center_rank": center, "clip_end_rank": end, "clip_start_frame_index": candidate64[start],
            "clip_end_frame_index": candidate64[end], "clip_span_rank_count": end - start + 1,
        })
    output["evidence_anchors"] = new_anchors
    output["innovation1_selection"] = {
        "schema_version": "query_guided_evidence_clip_v1", "method": method,
        "clip_policy": "three_adjacent_candidate64_ranks_start_center_end",
        "center_source": "answer_free_source_manifest", "answer_or_outcome_fields_used": False,
        "judge_scores_read": False,
    }
    return output

def main() -> None:
    a = args(); items_path = Path(a.items).resolve(); siglip_path = Path(a.siglip_manifest).resolve()
    source_root = Path(a.source_root).resolve(); index_dir = Path(a.video_index_dir).resolve(); root = Path(a.output_root).resolve()
    if root.exists() and any(root.iterdir()): raise RuntimeError("output root must be absent or empty")
    items = jsonl(items_path); items = items[:a.max_items] if a.max_items > 0 else items
    siglip = load_by_id(siglip_path); indexes = load_indexes(index_dir)
    source_paths = {"fixed_clip": source_root / "fusion_full.jsonl", "query_clip": source_root / "slot_coverage.jsonl", "random_clip": source_root / "random_residual.jsonl"}
    sources = {k: load_by_id(v) for k, v in source_paths.items()}; outputs = {k: [] for k in source_paths}
    for item in items:
        qid = str(item["question_id"])
        if FORBIDDEN & set(item): raise RuntimeError(f"forbidden field in {qid}")
        if str(item["video_id"]) not in indexes: raise RuntimeError(f"missing video index for {qid}")
        for method, source in sources.items(): outputs[method].append(make_row(item, source[qid], siglip[qid], method))
    root.mkdir(parents=True, exist_ok=True)
    for method, rows in outputs.items():
        write_jsonl(root / f"{method}.jsonl", rows); write_jsonl(root / f"{method}_smoke20.jsonl", rows[:20])
    audit = {"schema_version": "query_guided_evidence_clip_audit_v1", "passed": True, "rows": len(items), "videos": len({str(x["video_id"]) for x in items}), "methods": list(outputs), "views": 12, "visual_tokens": 3992, "spatial_policy": "base8_512_plus_four_temporal_endpoint_views_896", "clip_policy": "three_adjacent_candidate64_ranks_start_center_end", "answer_or_outcome_fields_used": False, "judge_scores_read": False, "inputs": {"items_sha256": sha(items_path), "siglip_sha256": sha(siglip_path)}, "outputs": {k: canon(v) for k, v in outputs.items()}}
    (root / "audit.json").write_text(json.dumps(audit, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=True, indent=2))

if __name__ == "__main__": main()
