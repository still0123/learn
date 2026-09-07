from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path("/Users/bytedance/vqa_thesis_continue")
RUNS_DIR = ROOT / "runs"
TEMPLATE_DIR = Path("/Users/bytedance/.agents/skills/patent-innovation-analysis/templates")

DEFAULT_FILES = {
    "00_plan.md": "# P0 本轮计划\n\n## 本轮目标\n\n- \n\n## 本轮材料范围\n\n- \n\n## 计划输出\n\n- 01_material_inventory.md\n- 02_claim_feature_map.md\n- 03_office_action_issue_map.md\n- 04_prior_art_comparison_matrix.md\n- 05_code_implementation_map.md\n- 06_innovation_candidates.md\n- 07_examiner_critic_review.md\n- 08_revision_strategy.md\n- 09_search_materials_report.md\n- 10_final_recommendation.md\n- gates.md\n\n## 本轮注意事项\n\n- 不编造数据\n- 所有结论必须给出本地来源路径\n- gate 未通过时只能输出候选/修订建议\n",
    "01_material_inventory.md": "# P1 材料清单\n\n## 本地材料\n\n| ID | 路径 | 类型 | 用途 | 可靠性 | 备注 |\n|---|---|---|---|---|---|\n",
    "02_claim_feature_map.md": "# P2 权利要求-技术特征映射\n",
    "03_office_action_issue_map.md": "# P3 审查意见问题图谱\n",
    "04_prior_art_comparison_matrix.md": "# P4 对比文件矩阵\n",
    "05_code_implementation_map.md": "# P8 代码实现难度评审\n",
    "08_revision_strategy.md": "# P7 修改与答复策略\n",
    "09_search_materials_report.md": "# 关键词检索报告\n\n- 待生成\n",
    "gates.md": "# Gate 检查\n\n## Gate 1 材料覆盖\n- 结论：待补\n\n## Gate 2 原始公开支持\n- 结论：待补\n\n## Gate 3 现有技术差异\n- 结论：待补\n",
    "artifacts.md": "# Artifacts\n\n- 待补\n",
}


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize a patent analysis run directory")
    parser.add_argument("--run-id", default=f"patent-analysis-{date.today().strftime('%Y%m%d')}-round01")
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    for name, content in DEFAULT_FILES.items():
        write_if_missing(run_dir / name, content)

    template_map = {
        "06_innovation_candidates.md": TEMPLATE_DIR / "innovation_candidate.md",
        "07_examiner_critic_review.md": TEMPLATE_DIR / "examiner_critic.md",
        "10_final_recommendation.md": TEMPLATE_DIR / "final_recommendation.md",
    }
    for name, src in template_map.items():
        if src.exists() and not (run_dir / name).exists():
            (run_dir / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    sources_path = run_dir / "sources_used.json"
    if not sources_path.exists():
        sources_path.write_text(
            json.dumps({"run_id": args.run_id, "sources": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(run_dir)


if __name__ == "__main__":
    main()
