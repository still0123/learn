#!/usr/bin/env python3
"""Exa semantic paper recall. Reads EXA_API_KEY from the process environment."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import requests


RUN_DIR = Path(__file__).resolve().parent
OUT = RUN_DIR / "01f_exa_semantic_pool.jsonl"
SUMMARY = RUN_DIR / "01f_exa_semantic_summary.md"
API_URL = "https://api.exa.ai/search"
COST_CAP = 2.0
QUERIES = [
    ("A01", "2026 video or image question answering methods that improve answer accuracy through evidence localization, temporal reasoning, or structured visual understanding; exclude generic benchmark surveys"),
    ("A02", "2026 long video understanding and temporal grounding methods using event structure, iterative observation, active evidence seeking, or query-conditioned memory"),
    ("A03", "2026 document image understanding DocVQA chart question answering and scene text reasoning methods with region grounding or evidence attribution"),
    ("A04", "2026 visual agents that zoom crop inspect or call tools to gather additional image or video evidence before answering"),
    ("B01", "2026 computer vision methods for short-lived scene text logo price or small object detection across video frames with temporal association"),
    ("B02", "2026 fine-grained product attribute recognition high-resolution image understanding and entity attribute binding across views or frames"),
    ("B03", "2026 visual grounding referring segmentation or evidence region extraction that preserves object identity across video frames"),
    ("B04", "2026 video event graph scene graph causal graph or role action outcome representation for narrative understanding"),
    ("B05", "2026 audio visual temporal alignment methods handling nonzero lag asynchronous narration and multiple alignment hypotheses"),
    ("C01", "2026 multimodal large language model or video language model methods for grounded reasoning with explicit evidence citations and verifiable intermediate states"),
    ("C02", "2026 multimodal agent planning memory state machine or multi-agent collaboration for image and video understanding with auditable tool traces"),
    ("C03", "2026 multimodal retrieval augmented generation methods that bind retrieved evidence regions timestamps or provenance to generated claims"),
    ("C04", "2026 multimodal preference optimization reinforcement learning or process supervision using evidence correctness grounding or factuality rewards"),
    ("D01", "2026 multimodal hallucination detection and claim-level fact verification using image or video evidence, atomic claims, contradiction search, or calibrated support scores"),
    ("D02", "2026 uncertainty calibration selective prediction abstention conformal risk control or risk coverage for vision language models and visual question answering"),
    ("D03", "2026 counterfactual visual evidence hard negative contrastive ranking or causal intervention training for multimodal factuality and evidence dependence"),
    ("D04", "2026 verifier generator candidate answer ranking conservative replacement fallback or edit-level answer correction based on visual evidence"),
    ("D05", "2026 visual token compression dynamic resolution frame selection early exit routing or budget-aware multimodal inference that preserves decisive evidence"),
]


def norm_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def main() -> int:
    key = os.environ.get("EXA_API_KEY")
    if not key:
        print("EXA_API_KEY is not set", file=sys.stderr)
        return 2

    seen: dict[str, dict] = {}
    query_stats: list[dict] = []
    total_cost = 0.0
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    })

    for cluster, query in QUERIES:
        if total_cost >= COST_CAP:
            break
        payload = {
            "query": query,
            "type": "auto",
            "category": "publication",
            "numResults": 100,
            "startPublishedDate": "2025-01-01T00:00:00.000Z",
            "endPublishedDate": "2026-08-18T23:59:59.999Z",
            "contents": {"highlights": True},
        }
        body = None
        last_error = ""
        for attempt in range(3):
            try:
                response = session.post(API_URL, json=payload, timeout=90)
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = f"HTTP_{response.status_code}"
                    if attempt < 2:
                        import time
                        time.sleep(2 ** attempt)
                        continue
                response.raise_for_status()
                body = response.json()
                break
            except (requests.RequestException, ValueError) as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                last_error = f"HTTP_{status}" if status else type(exc).__name__
                if attempt < 2 and (status == 429 or (status and status >= 500)):
                    import time
                    time.sleep(2 ** attempt)
                    continue
                break
        if body is None:
            query_stats.append({"cluster": cluster, "status": "ERROR", "error": last_error})
            continue

        cost = float(body.get("costDollars", {}).get("total") or 0)
        total_cost += cost
        results = body.get("results") or []
        query_stats.append({"cluster": cluster, "status": "OK", "results": len(results), "cost_usd": cost})

        for item in results:
            title = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            if not title or not url:
                continue
            key_name = norm_title(title) or url
            record = seen.setdefault(key_name, {
                "title": title,
                "url": url,
                "published_date_estimate": item.get("publishedDate"),
                "author": item.get("author"),
                "query_clusters": [],
                "highlights": [],
                "source": "exa",
                "status": "exa_semantic_only",
                "metadata_only": True,
                "full_text_verified": False,
            })
            if cluster not in record["query_clusters"]:
                record["query_clusters"].append(cluster)
            for highlight in item.get("highlights") or []:
                if highlight not in record["highlights"]:
                    record["highlights"].append(highlight)

    with OUT.open("w", encoding="utf-8") as stream:
        for record in sorted(seen.values(), key=lambda value: value["title"].lower()):
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    ok_queries = sum(item["status"] == "OK" for item in query_stats)
    errors = sum(item["status"] == "ERROR" for item in query_stats)
    SUMMARY.write_text(
        "\n".join([
            "# Exa语义补召回汇总",
            "",
            f"- 查询成功：{ok_queries}",
            f"- 查询失败：{errors}",
            f"- 去重结果：{len(seen)}",
            f"- 累计费用（USD）：{total_cost:.6f}",
            f"- 费用硬上限（USD）：{COST_CAP:.2f}",
            "- 状态：仅语义召回，未完成论文族、2026资格或官方正文核验。",
            "",
            "## 查询明细",
            "",
            "```json",
            json.dumps(query_stats, ensure_ascii=False, indent=2),
            "```",
            "",
        ]),
        encoding="utf-8",
    )
    assert OUT.exists() and SUMMARY.exists()
    print(json.dumps({"queries": ok_queries, "errors": errors, "records": len(seen), "cost_usd": total_cost}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
