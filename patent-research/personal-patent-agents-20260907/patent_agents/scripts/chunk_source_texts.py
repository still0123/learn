from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path("/Users/bytedance/vqa_thesis_continue")
SOURCE_DIR = ROOT / "source_texts"
OUT = ROOT / "patent_agents" / "index" / "source_chunks.jsonl"


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")
    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += step
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk source_texts into stable JSONL records")
    parser.add_argument("--source-dir", default=str(SOURCE_DIR))
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=150)
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with out_path.open("w", encoding="utf-8") as f:
        for path in sorted(source_dir.glob("*.txt")):
            text = path.read_text(encoding="utf-8")
            for idx, chunk in enumerate(chunk_text(text, args.chunk_size, args.overlap)):
                record = {
                    "chunk_id": f"{path.stem}::chunk_{idx:04d}",
                    "source_path": str(path),
                    "source_name": path.name,
                    "chunk_index": idx,
                    "text": chunk,
                    "char_count": len(chunk),
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                total += 1

    print(f"wrote {total} chunks -> {out_path}")


if __name__ == "__main__":
    main()
