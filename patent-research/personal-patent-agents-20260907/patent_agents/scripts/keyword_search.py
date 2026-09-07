from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

ROOT = Path("/Users/bytedance/vqa_thesis_continue")
MANIFEST = ROOT / "patent_agents" / "config" / "material_manifest.yaml"


def load_manifest_paths(manifest_path: Path) -> list[Path]:
    paths: list[Path] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("path:"):
            value = stripped.split(":", 1)[1].strip().strip('"')
            paths.append(Path(value))
    return paths


def grep_text(path: Path, pattern: re.Pattern[str], before: int, after: int) -> Iterable[dict]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for idx, line in enumerate(lines):
        if pattern.search(line):
            start = max(0, idx - before)
            end = min(len(lines), idx + after + 1)
            yield {
                "path": str(path),
                "line": idx + 1,
                "match": line,
                "context": lines[start:end],
            }


def render_markdown(results: dict[str, list[dict]]) -> str:
    lines = ["# 关键词检索报告", ""]
    for query, matches in results.items():
        lines.append(f"## Query: {query}")
        if not matches:
            lines.append("- 无匹配")
            lines.append("")
            continue
        for item in matches:
            lines.append(f"- `{item['path']}:{item['line']}`")
            lines.append("")
            lines.append("```text")
            for ctx in item["context"]:
                lines.append(ctx)
            lines.append("```")
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Search patent materials with keywords/regex")
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--query", action="append", required=True, help="Literal regex query; repeatable")
    parser.add_argument("--before", type=int, default=1)
    parser.add_argument("--after", type=int, default=2)
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown")
    parser.add_argument("--out", default="", help="Optional output path")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    paths = [p for p in load_manifest_paths(manifest_path) if p.exists() and p.is_file()]
    results: dict[str, list[dict]] = {}
    for query in args.query:
        pattern = re.compile(query, re.IGNORECASE)
        matches: list[dict] = []
        for path in paths:
            if path.suffix.lower() not in {".txt", ".md", ".py"}:
                continue
            matches.extend(grep_text(path, pattern, args.before, args.after))
        results[query] = matches

    payload = json.dumps(results, ensure_ascii=False, indent=2) if args.json else render_markdown(results)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
