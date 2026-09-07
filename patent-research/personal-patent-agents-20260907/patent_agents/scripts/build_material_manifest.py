from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

ROOT = Path("/Users/bytedance/vqa_thesis_continue")
OUT = ROOT / "patent_agents" / "config" / "material_manifest.yaml"

PRIORITY = {
    "source_texts": "high",
    "docs": "medium",
    "code": "medium",
    "patent_files": "high",
}


def yaml_quote(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def iter_materials() -> Iterable[dict]:
    source_dir = ROOT / "source_texts"
    docs_dir = ROOT / "docs"
    patent_dir = ROOT / "专利相关"

    for path in sorted(source_dir.glob("*.txt")):
        yield {
            "id": path.stem,
            "path": str(path),
            "type": "source_text",
            "priority": PRIORITY["source_texts"],
            "notes": "machine-readable extracted source",
        }

    for path in sorted(docs_dir.glob("*.md")):
        yield {
            "id": path.stem,
            "path": str(path),
            "type": "doc",
            "priority": PRIORITY["docs"],
            "notes": "project documentation/reference",
        }

    for path in sorted(patent_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in {".pdf", ".doc", ".docx", ".txt", ".zip"}:
            yield {
                "id": path.stem,
                "path": str(path),
                "type": f"patent_asset:{path.suffix.lower().lstrip('.')}",
                "priority": PRIORITY["patent_files"],
                "notes": "patent/prosecution/local prior-art asset",
            }

    code_paths = [
        ROOT / "code_refactor" / "evidence" / "evidence_package.py",
        ROOT / "code_refactor" / "rag" / "retriever.py",
        ROOT / "code_refactor" / "reasoning" / "prompt_builder.py",
        ROOT / "code_refactor" / "reflection" / "claim_checker.py",
        ROOT / "rag_mvp" / "rag_retriever.py",
    ]
    for path in code_paths:
        if path.exists():
            yield {
                "id": path.stem,
                "path": str(path),
                "type": "code_evidence",
                "priority": PRIORITY["code"],
                "notes": "implementation evidence",
            }


def dump_yaml(materials: list[dict]) -> str:
    lines = ["materials:"]
    for item in materials:
        lines.extend(
            [
                f"  - id: {item['id']}",
                f"    path: {yaml_quote(item['path'])}",
                f"    type: {item['type']}",
                f"    priority: {item['priority']}",
                f"    notes: {yaml_quote(item['notes'])}",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build patent material manifest")
    parser.add_argument("--out", default=str(OUT), help="Output YAML path")
    args = parser.parse_args()

    out_path = Path(args.out)
    materials = list(iter_materials())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(dump_yaml(materials), encoding="utf-8")
    print(f"wrote {len(materials)} materials -> {out_path}")


if __name__ == "__main__":
    main()
