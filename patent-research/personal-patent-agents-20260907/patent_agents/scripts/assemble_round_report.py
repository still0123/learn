from __future__ import annotations

import argparse
from pathlib import Path

RECOMMENDED_ORDER = [
    "00_plan.md",
    "01_material_inventory.md",
    "02_claim_feature_map.md",
    "03_office_action_issue_map.md",
    "04_prior_art_comparison_matrix.md",
    "05_code_implementation_map.md",
    "06_innovation_candidates.md",
    "07_examiner_critic_review.md",
    "08_revision_strategy.md",
    "09_search_materials_report.md",
    "10_final_recommendation.md",
    "gates.md",
    "artifacts.md",
]


def assemble(run_dir: Path) -> str:
    lines = [f"# Round Report: {run_dir.name}", ""]
    for name in RECOMMENDED_ORDER:
        path = run_dir / name
        if not path.exists():
            continue
        lines.append(f"---\n\n## File: {name}\n")
        lines.append(path.read_text(encoding="utf-8", errors="ignore").rstrip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble a patent analysis round report")
    parser.add_argument("--run-dir", required=True, help="Run directory under runs/")
    parser.add_argument("--out", default="", help="Optional output path; default is <run-dir>/round_report.md")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    out_path = Path(args.out) if args.out else run_dir / "round_report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(assemble(run_dir), encoding="utf-8")
    print(f"assembled report -> {out_path}")


if __name__ == "__main__":
    main()
