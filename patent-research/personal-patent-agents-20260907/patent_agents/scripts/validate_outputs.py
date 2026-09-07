from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_FILES = [
    "00_plan.md",
    "06_innovation_candidates.md",
    "07_examiner_critic_review.md",
    "10_final_recommendation.md",
    "gates.md",
]

REQUIRED_HEADINGS = {
    "10_final_recommendation.md": [
        "## 执行结论",
        "## 最佳创新点排序",
        "## 推荐权利要求策略",
    ],
    "gates.md": [
        "## Gate 1",
        "## Gate 2",
        "## Gate 3",
    ],
}

BANNED_PLACEHOLDERS = ["TBD", "TODO", "<短名称>", "<问题短名>", "<特征短名>"]


def validate(run_dir: Path) -> dict:
    report = {
        "run_dir": str(run_dir),
        "missing_files": [],
        "missing_headings": {},
        "placeholder_hits": {},
        "ok": True,
    }

    for name in REQUIRED_FILES:
        path = run_dir / name
        if not path.exists():
            report["missing_files"].append(name)
            report["ok"] = False
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for heading in REQUIRED_HEADINGS.get(name, []):
            if heading not in text:
                report["missing_headings"].setdefault(name, []).append(heading)
                report["ok"] = False
        hits = [token for token in BANNED_PLACEHOLDERS if token in text]
        if hits:
            report["placeholder_hits"][name] = hits
            report["ok"] = False

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate patent analysis run outputs")
    parser.add_argument("run_dir", help="Path to run directory")
    args = parser.parse_args()

    report = validate(Path(args.run_dir))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
