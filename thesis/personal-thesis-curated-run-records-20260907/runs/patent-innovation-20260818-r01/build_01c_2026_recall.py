#!/usr/bin/env python3
"""Build the strict-2026 I1-R metadata recall pool.

This is a metadata-only collector. It does not fetch full text and never marks
title or abstract matches as verified.
"""

from __future__ import annotations

import html
import json
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests


RUN_DIR = Path("/Users/bytedance/vqa_thesis_continue/runs/patent-innovation-20260818-r01")
POOL_PATH = RUN_DIR / "01c_2026_recall_pool.jsonl"
SUMMARY_PATH = RUN_DIR / "01c_2026_recall_summary.md"
DATE_START = date(2026, 1, 1)
DATE_END = date(2026, 8, 18)
TARGET = 800
SOFT_CAP = 1200
USER_AGENT = "I1-R-2026-metadata-recall/1.0 (mailto: research@example.com)"


OPENALEX_QUERIES = [
    ("A", "A01_video_qa", "video question answering"),
    ("A", "A02_image_visual_qa", "image visual question answering"),
    ("A", "A03_long_video", "long video understanding"),
    ("A", "A04_temporal_grounding", "temporal video grounding moment retrieval"),
    ("A", "A05_multimodal_qa", "multimodal question answering"),
    ("A", "A06_docvqa", "document visual question answering DocVQA"),
    ("A", "A07_chart_table_qa", "chart table question answering"),
    ("A", "A08_textvqa_ocr", "scene text question answering OCR"),
    ("A", "A09_video_captioning", "video captioning evidence description"),
    ("A", "A10_active_perception", "active visual perception second look"),
    ("A", "A11_visual_agent_tools", "visual agent tool use zoom crop"),
    ("A", "A12_audio_visual_qa", "audio visual question answering"),
    ("A", "A13_egocentric_video", "egocentric video understanding"),
    ("B", "B01_detection_segmentation", "object detection instance segmentation"),
    ("B", "B02_visual_grounding", "visual grounding referring expression region text alignment"),
    ("B", "B03_ocr_layout", "OCR scene text recognition document layout analysis"),
    ("B", "B04_fine_grained", "fine grained recognition small object high resolution"),
    ("B", "B05_saliency_evidence", "saliency attention map evidence region CAM"),
    ("B", "B06_tracking_vos", "object tracking video segmentation temporal consistency"),
    ("B", "B07_scene_graph_entailment", "scene graph visual entailment image fact verification"),
    ("C", "C01_mllm", "multimodal large language model"),
    ("C", "C02_vlm_instruction", "vision language model visual instruction"),
    ("C", "C03_video_language", "video language model long video"),
    ("C", "C04_visual_tokens", "visual token compression multi image"),
    ("C", "C05_alignment_fusion", "image text alignment cross modal fusion"),
    ("C", "C06_audio_visual_alignment", "audio visual alignment cross modal"),
    ("C", "C07_preference_rl", "multimodal preference optimization reinforcement learning"),
    ("C", "C08_grounded_reasoning", "grounded chain of thought visual reasoning tool"),
    ("C", "C09_rag_agent", "multimodal retrieval augmented generation citation attribution agent planning memory"),
    ("D", "D01_hallucination", "multimodal hallucination detection factuality"),
    ("D", "D02_uncertainty_abstention", "uncertainty calibration selective prediction abstention"),
    ("D", "D03_verifier_reranking", "answer verifier generator reranking fallback"),
    ("D", "D04_counterfactual_negatives", "counterfactual evidence hard negative contrastive ranking"),
    ("D", "D05_robust_weak_supervision", "out of distribution robustness weak supervision noisy labels vision"),
    ("D", "D06_visual_budget", "visual token budget frame selection pruning dynamic resolution"),
    ("D", "D07_system_routing_audit", "budget aware inference early exit model routing audit provenance"),
]

ARXIV_QUERIES = [
    ("A", "A01_video_qa", "video question answering"),
    ("A", "A03_long_video", "long video understanding"),
    ("A", "A04_temporal_grounding", "temporal video grounding"),
    ("A", "A06_docvqa", "document visual question answering"),
    ("A", "A10_active_perception", "active visual perception"),
    ("A", "A12_audio_visual_qa", "audio visual question answering"),
    ("B", "B02_visual_grounding", "visual grounding"),
    ("B", "B03_ocr_layout", "scene text recognition"),
    ("B", "B06_tracking_vos", "video object tracking segmentation"),
    ("C", "C01_mllm", "multimodal large language model"),
    ("C", "C03_video_language", "video language model"),
    ("C", "C04_visual_tokens", "visual token compression"),
    ("C", "C08_grounded_reasoning", "visual reasoning tool"),
    ("D", "D01_hallucination", "multimodal hallucination"),
    ("D", "D02_uncertainty_abstention", "selective prediction uncertainty calibration"),
    ("D", "D04_counterfactual_negatives", "counterfactual evidence contrastive learning"),
]

CROSSREF_QUERIES = [
    ("A", "A01_video_qa", "video question answering"),
    ("A", "A06_docvqa", "document visual question answering"),
    ("B", "B02_visual_grounding", "visual grounding"),
    ("C", "C01_mllm", "multimodal large language model"),
    ("D", "D01_hallucination", "multimodal hallucination uncertainty"),
]

DBLP_QUERIES = [
    ("A", "A01_video_qa", "video question answering"),
    ("B", "B02_visual_grounding", "visual grounding"),
    ("C", "C01_mllm", "multimodal language model"),
    ("D", "D01_hallucination", "hallucination detection multimodal"),
]

LAYER_QUOTAS = {"A": 280, "B": 160, "C": 200, "D": 160}
LAYER_SELECTION_ORDER = ["B", "D", "C", "A"]
ALLOWED_TYPES = {
    "article",
    "conference-paper",
    "journal-article",
    "posted-content",
    "preprint",
    "proceedings-article",
    "proceedings",
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "the",
    "to",
    "use",
    "with",
}
ARXIV_RE = re.compile(
    r"(?:arxiv(?:\.org/(?:abs|pdf)/|:|\.))"
    r"(?P<id>(?:\d{4}\.\d{4,5}|[a-z\-]+/\d{7})(?:v\d+)?)",
    re.IGNORECASE,
)


@dataclass
class QueryLog:
    interface: str
    layer: str
    cluster: str
    query: str
    status: str
    records: int
    note: str = ""


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", html.unescape(str(value))).strip()


def normalize_title(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", clean_text(value)).casefold()
    asciiish = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", asciiish)


def normalize_doi(value: Any) -> str:
    doi = clean_text(value).lower()
    doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", doi)
    return doi.rstrip(" .")


def extract_arxiv(*values: Any) -> str:
    for raw in values:
        if isinstance(raw, (list, tuple)):
            found = extract_arxiv(*raw)
            if found:
                return found
            continue
        match = ARXIV_RE.search(clean_text(raw))
        if match:
            return re.sub(r"v\d+$", "", match.group("id"), flags=re.IGNORECASE).lower()
    return ""


def arxiv_year(arxiv_id: str) -> int | None:
    match = re.match(r"(\d{2})(?:\d{2})\.", arxiv_id)
    if not match:
        return None
    two_digit = int(match.group(1))
    return 2000 + two_digit if two_digit < 90 else 1900 + two_digit


def has_pre2026_arxiv(group: list[dict[str, Any]]) -> bool:
    for record in group:
        arxiv_id = record["arxiv_id"]
        if not arxiv_id:
            continue
        year = arxiv_year(arxiv_id)
        # Old-style category/YYNNNNN identifiers are necessarily pre-2007.
        if year is None or year < DATE_START.year:
            return True
    return False


def parse_iso_date(value: Any) -> date | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def date_from_parts(value: Any) -> date | None:
    try:
        parts = value["date-parts"][0]
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return date(year, month, day)
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def request_json(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, Any],
    timeout: int = 45,
) -> tuple[dict[str, Any] | None, str]:
    try:
        response = session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json(), ""
    except (requests.RequestException, ValueError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def request_text(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, Any],
    timeout: int = 60,
) -> tuple[str | None, str]:
    try:
        response = session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.text, ""
    except requests.RequestException as exc:
        return None, f"{type(exc).__name__}: {exc}"


def openalex_location_urls(work: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for location in work.get("locations") or []:
        urls.extend([location.get("landing_page_url"), location.get("pdf_url")])
    ids = work.get("ids") or {}
    urls.extend(ids.values())
    urls.extend([work.get("doi"), work.get("id")])
    return [clean_text(item) for item in urls if item]


def make_raw(
    *,
    source: str,
    title: str,
    authors: list[str],
    public_date: date | None,
    venue: str,
    doi: str,
    arxiv_id: str,
    official_url: str,
    layer: str,
    cluster: str,
    query: str,
    rank: int,
    total_returned: int,
    record_type: str,
    source_id: str = "",
    date_basis: str = "",
    relevance_score: float = 0.0,
) -> dict[str, Any]:
    return {
        "source": source,
        "title": clean_text(title),
        "title_norm": normalize_title(title),
        "authors": [clean_text(author) for author in authors if clean_text(author)],
        "date": public_date,
        "venue": clean_text(venue),
        "doi": normalize_doi(doi),
        "arxiv_id": arxiv_id.lower(),
        "official_url": clean_text(official_url),
        "layer": layer,
        "cluster": cluster,
        "query": query,
        "rank": rank,
        "total_returned": max(total_returned, 1),
        "type": clean_text(record_type),
        "source_id": clean_text(source_id),
        "date_basis": clean_text(date_basis),
        "relevance_score": float(relevance_score or 0.0),
    }


def collect_openalex(
    session: requests.Session,
    raw: list[dict[str, Any]],
    logs: list[QueryLog],
) -> None:
    endpoint = "https://api.openalex.org/works"
    select = (
        "id,display_name,publication_date,doi,ids,authorships,"
        "primary_location,locations,type,relevance_score"
    )
    for layer, cluster, query in OPENALEX_QUERIES:
        filter_value = (
            f"title_and_abstract.search:{query},"
            f"from_publication_date:{DATE_START.isoformat()},"
            f"to_publication_date:{DATE_END.isoformat()}"
        )
        payload, error = request_json(
            session,
            endpoint,
            params={
                "filter": filter_value,
                "per-page": 100,
                "select": select,
                "mailto": "research@example.com",
            },
        )
        if payload is None:
            logs.append(QueryLog("OpenAlex", layer, cluster, query, "FAILED", 0, error))
            continue
        works = payload.get("results") or []
        logs.append(QueryLog("OpenAlex", layer, cluster, query, "OK", len(works)))
        for rank, work in enumerate(works, start=1):
            title = clean_text(work.get("display_name"))
            work_type = clean_text(work.get("type"))
            if not title or work_type not in ALLOWED_TYPES:
                continue
            primary = work.get("primary_location") or {}
            source = primary.get("source") or {}
            urls = openalex_location_urls(work)
            arxiv_id = extract_arxiv(urls)
            doi = normalize_doi(work.get("doi"))
            if not arxiv_id:
                arxiv_id = extract_arxiv(doi)
            if doi:
                official_url = f"https://doi.org/{doi}"
            elif arxiv_id:
                official_url = f"https://arxiv.org/abs/{arxiv_id}"
            else:
                official_url = clean_text(primary.get("landing_page_url") or work.get("id"))
            raw.append(
                make_raw(
                    source="OpenAlex",
                    title=title,
                    authors=[
                        item.get("author", {}).get("display_name", "")
                        for item in (work.get("authorships") or [])
                    ],
                    public_date=parse_iso_date(work.get("publication_date")),
                    venue=source.get("display_name") or primary.get("raw_source_name") or "",
                    doi=doi,
                    arxiv_id=arxiv_id,
                    official_url=official_url,
                    layer=layer,
                    cluster=cluster,
                    query=query,
                    rank=rank,
                    total_returned=len(works),
                    record_type=work_type,
                    source_id=work.get("id") or "",
                    date_basis="OpenAlex publication_date",
                    relevance_score=work.get("relevance_score") or 0.0,
                )
            )
        time.sleep(0.15)


def atom_text(entry: ET.Element, path: str, namespaces: dict[str, str]) -> str:
    node = entry.find(path, namespaces)
    return clean_text(node.text if node is not None else "")


def collect_arxiv(
    session: requests.Session,
    raw: list[dict[str, Any]],
    logs: list[QueryLog],
) -> None:
    endpoint = "https://export.arxiv.org/api/query"
    namespaces = {
        "atom": "http://www.w3.org/2005/Atom",
        "open": "http://a9.com/-/spec/opensearch/1.1/",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    for layer, cluster, query in ARXIV_QUERIES:
        search_query = (
            f'all:"{query}" AND submittedDate:[202501010000 TO 202608182359]'
        )
        text, error = request_text(
            session,
            endpoint,
            params={
                "search_query": search_query,
                "start": 0,
                "max_results": 200,
                "sortBy": "relevance",
                "sortOrder": "descending",
            },
        )
        if text is None:
            logs.append(QueryLog("arXiv", layer, cluster, query, "FAILED", 0, error))
            time.sleep(3.1)
            continue
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            logs.append(
                QueryLog("arXiv", layer, cluster, query, "FAILED", 0, f"ParseError: {exc}")
            )
            time.sleep(3.1)
            continue
        entries = root.findall("atom:entry", namespaces)
        logs.append(QueryLog("arXiv", layer, cluster, query, "OK", len(entries)))
        for rank, entry in enumerate(entries, start=1):
            entry_id = atom_text(entry, "atom:id", namespaces)
            arxiv_id = extract_arxiv(entry_id)
            title = atom_text(entry, "atom:title", namespaces)
            published = parse_iso_date(atom_text(entry, "atom:published", namespaces))
            comment = atom_text(entry, "arxiv:comment", namespaces)
            raw.append(
                make_raw(
                    source="arXiv",
                    title=title,
                    authors=[
                        atom_text(author, "atom:name", namespaces)
                        for author in entry.findall("atom:author", namespaces)
                    ],
                    public_date=published,
                    venue=f"arXiv{f' ({comment})' if comment else ''}",
                    doi="",
                    arxiv_id=arxiv_id,
                    official_url=f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else entry_id,
                    layer=layer,
                    cluster=cluster,
                    query=query,
                    rank=rank,
                    total_returned=len(entries),
                    record_type="preprint",
                    source_id=entry_id,
                    date_basis="arXiv initial submission (published)",
                )
            )
        time.sleep(3.1)


def crossref_dates(item: dict[str, Any]) -> list[tuple[date, str]]:
    candidates: list[tuple[date, str]] = []
    for field in ("published-online", "published-print", "published", "issued"):
        parsed = date_from_parts(item.get(field))
        if parsed:
            candidates.append((parsed, f"Crossref {field}"))
    created = parse_iso_date((item.get("created") or {}).get("date-time"))
    if created:
        candidates.append((created, "Crossref DOI metadata created"))
    return candidates


def collect_crossref(
    session: requests.Session,
    raw: list[dict[str, Any]],
    logs: list[QueryLog],
) -> None:
    endpoint = "https://api.crossref.org/works"
    select = (
        "DOI,title,author,published-online,published-print,published,"
        "issued,created,URL,container-title,type"
    )
    for layer, cluster, query in CROSSREF_QUERIES:
        payload, error = request_json(
            session,
            endpoint,
            params={
                "query.title": query,
                "filter": (
                    f"from-online-pub-date:{DATE_START.isoformat()},"
                    f"until-online-pub-date:{DATE_END.isoformat()}"
                ),
                "rows": 60,
                "select": select,
                "mailto": "research@example.com",
            },
        )
        if payload is None:
            logs.append(QueryLog("Crossref", layer, cluster, query, "FAILED", 0, error))
            continue
        items = ((payload.get("message") or {}).get("items") or [])
        logs.append(QueryLog("Crossref", layer, cluster, query, "OK", len(items)))
        for rank, item in enumerate(items, start=1):
            title_values = item.get("title") or []
            title = clean_text(title_values[0] if title_values else "")
            item_type = clean_text(item.get("type"))
            if not title or item_type not in ALLOWED_TYPES:
                continue
            dated = sorted(crossref_dates(item), key=lambda pair: pair[0])
            public_date, date_basis = dated[0] if dated else (None, "")
            doi = normalize_doi(item.get("DOI"))
            containers = item.get("container-title") or []
            raw.append(
                make_raw(
                    source="Crossref",
                    title=title,
                    authors=[
                        clean_text(
                            " ".join(
                                part
                                for part in (author.get("given"), author.get("family"))
                                if part
                            )
                        )
                        for author in (item.get("author") or [])
                    ],
                    public_date=public_date,
                    venue=containers[0] if containers else "",
                    doi=doi,
                    arxiv_id=extract_arxiv(doi, item.get("URL")),
                    official_url=(
                        f"https://doi.org/{doi}" if doi else clean_text(item.get("URL"))
                    ),
                    layer=layer,
                    cluster=cluster,
                    query=query,
                    rank=rank,
                    total_returned=len(items),
                    record_type=item_type,
                    source_id=doi,
                    date_basis=date_basis,
                )
            )
        time.sleep(0.5)


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def collect_dblp(
    session: requests.Session,
    raw: list[dict[str, Any]],
    logs: list[QueryLog],
) -> None:
    endpoint = "https://dblp.org/search/publ/api"
    for layer, cluster, query in DBLP_QUERIES:
        payload, error = request_json(
            session,
            endpoint,
            params={"q": f"{query} year:2026:", "h": 100, "format": "json"},
        )
        if payload is None:
            logs.append(QueryLog("DBLP", layer, cluster, query, "FAILED", 0, error))
            continue
        result = payload.get("result") or {}
        hits = as_list((result.get("hits") or {}).get("hit"))
        logs.append(QueryLog("DBLP", layer, cluster, query, "OK", len(hits)))
        for rank, hit in enumerate(hits, start=1):
            info = hit.get("info") or {}
            authors_container = info.get("authors") or {}
            authors = []
            for author in as_list(authors_container.get("author")):
                authors.append(author.get("text", "") if isinstance(author, dict) else author)
            doi = normalize_doi(info.get("doi"))
            raw.append(
                make_raw(
                    source="DBLP",
                    title=clean_text(info.get("title")).rstrip("."),
                    authors=authors,
                    public_date=None,
                    venue=info.get("venue") or "",
                    doi=doi,
                    arxiv_id=extract_arxiv(doi, info.get("ee")),
                    official_url=(
                        f"https://doi.org/{doi}"
                        if doi
                        else clean_text(info.get("ee") or info.get("url"))
                    ),
                    layer=layer,
                    cluster=cluster,
                    query=query,
                    rank=rank,
                    total_returned=len(hits),
                    record_type=info.get("type") or "publication",
                    source_id=info.get("url") or info.get("key") or "",
                    date_basis="DBLP year only; exact date unresolved",
                )
            )
        time.sleep(1.0)


def deduplicate(raw: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    uf = UnionFind(len(raw))
    key_owner: dict[tuple[str, str], int] = {}
    for index, record in enumerate(raw):
        keys = []
        if record["doi"]:
            keys.append(("doi", record["doi"]))
        if record["arxiv_id"]:
            keys.append(("arxiv", record["arxiv_id"]))
        if len(record["title_norm"]) >= 12:
            keys.append(("title", record["title_norm"]))
        for key in keys:
            if key in key_owner:
                uf.union(index, key_owner[key])
            else:
                key_owner[key] = index
    groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for index, record in enumerate(raw):
        groups[uf.find(index)].append(record)
    return list(groups.values())


def is_non_arxiv_doi(doi: str) -> bool:
    return bool(doi) and "10.48550/arxiv." not in doi


def record_quality(record: dict[str, Any]) -> tuple[int, int, int, int]:
    return (
        1 if is_non_arxiv_doi(record["doi"]) else 0,
        1 if record["venue"] and not record["venue"].lower().startswith("arxiv") else 0,
        len(record["authors"]),
        1 if record["official_url"] else 0,
    )


def hit_score(record: dict[str, Any]) -> float:
    source_weight = {"arXiv": 1.10, "OpenAlex": 1.00, "Crossref": 0.82, "DBLP": 0.72}
    rank_component = 1.0 - min(record["rank"] - 1, record["total_returned"]) / max(
        record["total_returned"], 1
    )
    query_words = [
        word
        for word in re.findall(r"[a-z0-9]+", record["query"].casefold())
        if word not in STOPWORDS and len(word) > 2
    ]
    title_words = set(re.findall(r"[a-z0-9]+", clean_text(record["title"]).casefold()))
    title_ratio = (
        sum(1 for word in query_words if word in title_words) / len(query_words)
        if query_words
        else 0.0
    )
    relevance = min(record["relevance_score"] / 100.0, 1.5)
    return source_weight.get(record["source"], 0.5) + rank_component + 2.0 * title_ratio + relevance


def best_hit_for_layer(group: list[dict[str, Any]], layer: str) -> dict[str, Any] | None:
    hits = [record for record in group if record["layer"] == layer]
    return max(hits, key=hit_score) if hits else None


def family_identifier(group: list[dict[str, Any]]) -> str:
    dois = sorted({record["doi"] for record in group if record["doi"]})
    arxiv_ids = sorted({record["arxiv_id"] for record in group if record["arxiv_id"]})
    titles = sorted({record["title_norm"] for record in group if record["title_norm"]})
    if dois:
        return f"doi:{dois[0]}"
    if arxiv_ids:
        return f"arxiv:{arxiv_ids[0]}"
    return f"title:{titles[0] if titles else id(group)}"


def make_family(group: list[dict[str, Any]]) -> dict[str, Any]:
    dated = [record for record in group if record["date"] is not None]
    earliest_record = min(dated, key=lambda record: record["date"]) if dated else None
    best = max(group, key=record_quality)
    title_record = max(group, key=lambda record: (len(record["title"]), record_quality(record)))
    non_arxiv_dois = sorted(
        {record["doi"] for record in group if is_non_arxiv_doi(record["doi"])}
    )
    arxiv_ids = sorted({record["arxiv_id"] for record in group if record["arxiv_id"]})
    all_dois = sorted({record["doi"] for record in group if record["doi"]})
    arxiv_id = arxiv_ids[0] if arxiv_ids else ""
    doi = non_arxiv_dois[0] if non_arxiv_dois else (all_dois[0] if all_dois else "")
    if non_arxiv_dois:
        official_url = f"https://doi.org/{non_arxiv_dois[0]}"
    elif arxiv_id:
        official_url = f"https://arxiv.org/abs/{arxiv_id}"
    else:
        official_url = best["official_url"]
    venue_records = [
        record
        for record in group
        if record["venue"] and not record["venue"].lower().startswith("arxiv")
    ]
    venue = max(venue_records, key=record_quality)["venue"] if venue_records else best["venue"]
    sources = sorted({record["source"] for record in group})
    earliest_date = earliest_record["date"] if earliest_record else None
    if earliest_record and earliest_record["source"] == "arXiv":
        date_confidence = "high"
    elif len({record["source"] for record in dated}) >= 2:
        date_confidence = "medium-high"
    elif doi:
        date_confidence = "medium"
    else:
        date_confidence = "medium"
    layer_hits: dict[str, float] = {}
    for layer in "ABCD":
        hit = best_hit_for_layer(group, layer)
        if hit:
            layer_hits[layer] = hit_score(hit)
    return {
        "family_id": family_identifier(group),
        "group": group,
        "title": title_record["title"],
        "authors": best["authors"],
        "earliest_date": earliest_date,
        "earliest_record": earliest_record,
        "venue": venue or "Unknown / metadata source only",
        "doi": doi,
        "arxiv_id": arxiv_id,
        "official_url": official_url,
        "sources": sources,
        "date_confidence": date_confidence,
        "layer_hits": layer_hits,
        "has_pre2026_arxiv": has_pre2026_arxiv(group),
    }


def select_stratified(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    used: set[str] = set()
    for layer in LAYER_SELECTION_ORDER:
        candidates = [family for family in families if layer in family["layer_hits"]]
        candidates.sort(
            key=lambda family: (
                family["layer_hits"][layer],
                len(family["sources"]),
                family["earliest_date"],
                family["title"],
            ),
            reverse=True,
        )
        for family in candidates:
            if family["family_id"] in used:
                continue
            family["selected_layer"] = layer
            selected.append(family)
            used.add(family["family_id"])
            if sum(1 for item in selected if item["selected_layer"] == layer) >= LAYER_QUOTAS[layer]:
                break
    if len(selected) < TARGET:
        remaining = [family for family in families if family["family_id"] not in used]
        remaining.sort(
            key=lambda family: (
                max(family["layer_hits"].values(), default=0.0),
                len(family["sources"]),
                family["earliest_date"],
            ),
            reverse=True,
        )
        for family in remaining[: TARGET - len(selected)]:
            deficits = {
                layer: LAYER_QUOTAS[layer]
                - sum(1 for item in selected if item["selected_layer"] == layer)
                for layer in "ABCD"
            }
            available = [
                layer
                for layer in "ABCD"
                if layer in family["layer_hits"] and deficits[layer] > 0
            ]
            if available:
                chosen = max(available, key=lambda layer: (deficits[layer], family["layer_hits"][layer]))
            else:
                chosen = max(family["layer_hits"], key=family["layer_hits"].get)
            family["selected_layer"] = chosen
            selected.append(family)
            used.add(family["family_id"])
    return selected[:SOFT_CAP]


def output_record(family: dict[str, Any]) -> dict[str, Any]:
    layer = family["selected_layer"]
    hit = best_hit_for_layer(family["group"], layer)
    assert hit is not None
    all_hits = sorted(
        {
            f"{record['source']}:{record['cluster']}"
            for record in family["group"]
            if record["date"] is None or record["date"] <= DATE_END
        }
    )
    if family["doi"] and is_non_arxiv_doi(family["doi"]):
        identifier = family["doi"]
    elif family["arxiv_id"]:
        identifier = f"arXiv:{family['arxiv_id']}"
    else:
        identifier = family["doi"] or family["family_id"]
    earliest_record = family["earliest_record"]
    return {
        "title": family["title"],
        "authors": family["authors"],
        "earliest_public_date": family["earliest_date"].isoformat(),
        "venue": family["venue"],
        "doi_or_arxiv": identifier,
        "official_url": family["official_url"],
        "search_layer": layer,
        "query_cluster": hit["cluster"],
        "date_confidence": family["date_confidence"],
        "date_basis": earliest_record["date_basis"] if earliest_record else "",
        "doi": family["doi"] or None,
        "arxiv_id": family["arxiv_id"] or None,
        "source_interfaces": family["sources"],
        "all_query_hits": all_hits,
        "metadata_only": True,
        "full_text_verified": False,
    }


def render_query_list(items: list[tuple[str, str, str]]) -> str:
    by_layer: dict[str, list[str]] = defaultdict(list)
    for layer, cluster, query in items:
        by_layer[layer].append(f"`{cluster}`={query}")
    return "\n".join(
        f"- {layer}层：" + "；".join(by_layer[layer])
        for layer in "ABCD"
        if by_layer[layer]
    )


def render_summary(
    *,
    raw: list[dict[str, Any]],
    logs: list[QueryLog],
    groups: list[list[dict[str, Any]]],
    families: list[dict[str, Any]],
    eligible: list[dict[str, Any]],
    selected: list[dict[str, Any]],
) -> str:
    layer_counts = Counter(item["selected_layer"] for item in selected)
    confidence_counts = Counter(item["date_confidence"] for item in selected)
    source_counts = Counter()
    for item in selected:
        source_counts.update(item["sources"])
    expected_clusters = {
        cluster
        for queries in (
            OPENALEX_QUERIES,
            ARXIV_QUERIES,
            CROSSREF_QUERIES,
            DBLP_QUERIES,
        )
        for _, cluster, _ in queries
    }
    selected_hit_clusters = {
        record["cluster"]
        for item in selected
        for record in item["group"]
    }
    missing_clusters = sorted(expected_clusters - selected_hit_clusters)
    logs_by_interface: dict[str, list[QueryLog]] = defaultdict(list)
    for log in logs:
        logs_by_interface[log.interface].append(log)
    dated_raw = [record for record in raw if record["date"] is not None]
    raw_pre2026 = sum(1 for record in dated_raw if record["date"] < DATE_START)
    raw_after_cutoff = sum(1 for record in dated_raw if record["date"] > DATE_END)
    raw_date_unresolved = sum(1 for record in raw if record["date"] is None)
    non2026_families = [
        family
        for family in families
        if family["earliest_date"] is not None and family["earliest_date"] < DATE_START
    ]
    explicit_2025_plus_2026 = 0
    for family in non2026_families:
        has_old_arxiv = any(
            record["source"] == "arXiv"
            and record["date"] is not None
            and record["date"] < DATE_START
            for record in family["group"]
        )
        has_2026 = any(
            record["date"] is not None and DATE_START <= record["date"] <= DATE_END
            for record in family["group"]
        )
        if has_old_arxiv and has_2026:
            explicit_2025_plus_2026 += 1
    valid_raw_records = sum(
        1
        for family in eligible
        for record in family["group"]
        if record["date"] is not None and DATE_START <= record["date"] <= DATE_END
    )
    duplicates_merged = max(valid_raw_records - len(eligible), 0)
    query_failures = [log for log in logs if log.status != "OK"]
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    lines = [
        "# I1-R 2026论文元数据宽召回汇总",
        "",
        f"- 生成时间：`{now}`",
        f"- 严格日期窗口：`{DATE_START.isoformat()}` 至 `{DATE_END.isoformat()}`（按已知最早公开元数据）",
        f"- 去重后输出：**{len(selected)}** 条；目标 `{TARGET}`，软上限 `{SOFT_CAP}`",
        "- 阶段边界：仅元数据宽召回；所有记录均为 `metadata_only=true`、`full_text_verified=false`。",
        "- 去重键：标准化 DOI、arXiv ID、标题 NFKD/小写/去标点归一键联合并查集。",
        "",
        "## 分层数量",
        "",
        "| 层 | 目标 | 实际 |",
        "|---|---:|---:|",
    ]
    for layer in "ABCD":
        lines.append(f"| {layer} | {LAYER_QUOTAS[layer]} | {layer_counts[layer]} |")
    lines.extend(
        [
            "",
            "日期置信度：" + "，".join(
                f"`{key}`={value}" for key, value in sorted(confidence_counts.items())
            ),
            "",
            "入池记录涉及接口：" + "，".join(
                f"`{key}`={value}" for key, value in sorted(source_counts.items())
            ),
            "",
            "## 查询与接口",
            "",
            "合同总请求预算为 72：本次正式批量请求 61 次，开始前接口/字段探测 11 次，共 72 次。正式请求统计如下：",
            "",
            "| 接口 | 请求数 | 成功 | 失败 | 返回元数据条数（含重复/排除项） | 用途 |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    interface_purposes = {
        "OpenAlex": "主召回；限定 title/abstract search 与公开日期窗口",
        "arXiv": "2025-2026 初次提交反查；识别 2025 预印本+2026版本",
        "Crossref": "DOI、作者、venue 与线上/登记日期补充",
        "DBLP": "计算机领域题名/DOI补漏；唯一 year-only 记录不直接入池",
    }
    for interface in ("OpenAlex", "arXiv", "Crossref", "DBLP"):
        interface_logs = logs_by_interface.get(interface, [])
        ok = sum(1 for log in interface_logs if log.status == "OK")
        failed = len(interface_logs) - ok
        returned = sum(log.records for log in interface_logs)
        lines.append(
            f"| {interface} | {len(interface_logs)} | {ok} | {failed} | {returned} | "
            f"{interface_purposes[interface]} |"
        )
    lines.extend(
        [
            "",
            "### OpenAlex 36个查询簇",
            "",
            render_query_list(OPENALEX_QUERIES),
            "",
            "### arXiv 16个历史反查簇",
            "",
            render_query_list(ARXIV_QUERIES),
            "",
            "### Crossref 5个补充簇",
            "",
            render_query_list(CROSSREF_QUERIES),
            "",
            "### DBLP 4个补漏簇",
            "",
            render_query_list(DBLP_QUERIES),
            "",
            "## 排除与去重",
            "",
            f"- 拉取原始元数据：`{len(raw)}` 条。",
            f"- 原始记录中最早日期早于 2026：`{raw_pre2026}` 条；晚于截止日：`{raw_after_cutoff}` 条。",
            f"- 精确日期不可解析：`{raw_date_unresolved}` 条（主要为 DBLP year-only）；若无其他接口给出精确日期则不入池。",
            f"- 去重后最早日期早于 2026 的文献族：`{len(non2026_families)}` 个。",
            f"- 明确识别并排除“2025 arXiv预印本 + 2026会议/期刊元数据”文献族：`{explicit_2025_plus_2026}` 个。",
            f"- 严格日期合格的去重文献族：`{len(eligible)}` 个。",
            f"- 合格原始记录折叠为文献族时合并的重复记录：`{duplicates_merged}` 条。",
            f"- 目标配额后未输出但仍合格的候选：`{max(len(eligible) - len(selected), 0)}` 个。",
            "",
            "## 日期判定规则",
            "",
            "1. arXiv 使用 Atom `published`（初次提交日期）作为最早公开日期，置信度为 `high`。",
            "2. 同标题/DOI/arXiv 文献族取所有接口已知日期的最小值；只要命中 2025 arXiv，即使有 2026 venue 版本也整族排除。",
            "3. Crossref 同时比较 online/print/issued/DOI metadata created，取最早值；OpenAlex 使用 `publication_date`。",
            "4. 只有 DBLP 年份、无精确日期且未被其他接口补齐的记录不入池。",
            "5. DOI-only 记录无法证明不存在未关联的旧预印本，因此保留 `medium` 或 `medium-high`，不提升为全文核验。",
            "",
            "## 覆盖不足",
            "",
            f"- A/B/C/D 四层均有覆盖，但 D 层仅 `{layer_counts['D']}` 条，较建议配额 `{LAYER_QUOTAS['D']}` 少 `{max(LAYER_QUOTAS['D'] - layer_counts['D'], 0)}` 条；D 层 DBLP 补漏请求又触发 429，因 72 次预算已耗尽未重试。",
            "- 最终池中无直接查询命中的细分簇："
            + ("、".join(f"`{cluster}`" for cluster in missing_clusters) if missing_clusters else "无")
            + "。这些簇应视为覆盖不足。",
            "- arXiv 历史反查限于 16 个相关查询簇、每簇前 200 条；题名大幅改动或未被查询命中的 2025 预印本仍可能漏关联。",
            "- OpenAlex/Crossref 的版本合并、venue 和发布日期存在索引延迟；`medium` 日期记录后续必须回到 arXiv版本史、出版社/会议页核验。",
            "- DBLP 缺少日级公开日期，唯一 year-only 命中已保守排除，可能造成正式会议论文漏召回。",
            "- 本轮未逐篇读取摘要或正文，标题/摘要检索命中不代表机制相关，更不代表 `verified`。",
            "- 受 800 条目标配额限制，合格池按 A/B/C/D 比例和查询排名截断；长尾机制仍需后续补召回。",
        ]
    )
    if query_failures:
        lines.extend(["", "## 请求失败", ""])
        for log in query_failures:
            lines.append(
                f"- `{log.interface}/{log.cluster}`：{log.note or log.status}"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    raw: list[dict[str, Any]] = []
    logs: list[QueryLog] = []

    collect_openalex(session, raw, logs)
    collect_arxiv(session, raw, logs)
    collect_crossref(session, raw, logs)
    collect_dblp(session, raw, logs)

    raw = [
        record
        for record in raw
        if record["title"]
        and len(record["title_norm"]) >= 12
        and (record["authors"] or record["source"] == "DBLP")
    ]
    groups = deduplicate(raw)
    families = [make_family(group) for group in groups]
    eligible = [
        family
        for family in families
        if family["earliest_date"] is not None
        and DATE_START <= family["earliest_date"] <= DATE_END
        and not family["has_pre2026_arxiv"]
        and family["layer_hits"]
    ]
    selected = select_stratified(eligible)
    selected.sort(
        key=lambda family: (
            "ABCD".index(family["selected_layer"]),
            -family["earliest_date"].toordinal(),
            family["title"].casefold(),
        )
    )

    pool_tmp = POOL_PATH.with_suffix(".jsonl.tmp")
    summary_tmp = SUMMARY_PATH.with_suffix(".md.tmp")
    with pool_tmp.open("w", encoding="utf-8") as handle:
        for family in selected:
            handle.write(json.dumps(output_record(family), ensure_ascii=False) + "\n")
    summary_tmp.write_text(
        render_summary(
            raw=raw,
            logs=logs,
            groups=groups,
            families=families,
            eligible=eligible,
            selected=selected,
        ),
        encoding="utf-8",
    )
    pool_tmp.replace(POOL_PATH)
    summary_tmp.replace(SUMMARY_PATH)

    print(
        json.dumps(
            {
                "raw_records": len(raw),
                "dedup_groups": len(groups),
                "eligible_families": len(eligible),
                "selected": len(selected),
                "layers": Counter(item["selected_layer"] for item in selected),
                "query_failures": [
                    f"{log.interface}:{log.cluster}" for log in logs if log.status != "OK"
                ],
                "pool": str(POOL_PATH),
                "summary": str(SUMMARY_PATH),
            },
            ensure_ascii=False,
            default=dict,
        )
    )


if __name__ == "__main__":
    main()
