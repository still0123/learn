import json
import tempfile
import unittest
from pathlib import Path

from skill_learning.evolution import EvolutionEngine
from skill_learning.models import RuntimeResult
from skill_learning.runtime import DemoRuntime
from skill_learning.schema import validate_schema
from skill_learning.tasks import ExactMatchJSONLAdapter
from skill_learning.workspace import Workspace


INITIAL_SKILL = """# Normalize Text

## Procedure

Return the input unchanged.
"""


def example_adapter():
    path = Path(__file__).resolve().parents[1] / "examples" / "normalization" / "tasks.jsonl"
    return ExactMatchJSONLAdapter(path)


class NoImproveRuntime(DemoRuntime):
    def run(self, **kwargs):
        if kwargs["role"] != "task-executor":
            return super().run(**kwargs)
        request = json.loads(kwargs["user_prompt"])
        payload = {"answer": request["task"]["input"]}
        validate_schema(payload, kwargs["result_schema"])
        return RuntimeResult(payload=payload)


class MultiCandidateRuntime:
    def __init__(self, *, duplicate: bool = False):
        self.duplicate = duplicate

    def describe(self):
        return {"runtime": "multi-candidate-test", "model": "deterministic"}

    def run(self, **kwargs):
        request = json.loads(kwargs["user_prompt"])
        role = kwargs["role"]
        if role == "task-executor":
            task_id = request["task"]["id"]
            skill = request.get("skill") or ""
            if "RULE B" in skill or ("RULE A" in skill and task_id == "validation-a"):
                return RuntimeResult(payload={"answer": "good"})
            return RuntimeResult(payload={"answer": "bad"})
        if role == "knowledge-maintainer":
            evidence = [trace["id"] for trace in request["traces"] if not trace["passed"]]
            return RuntimeResult(payload={"patterns": [
                {
                    "id": "alpha-rule",
                    "title": "Alpha rule",
                    "observation": "Alpha output is wrong.",
                    "strategy": "Add RULE A.",
                    "evidence_ids": [evidence[0]],
                },
                {
                    "id": "beta-rule",
                    "title": "Beta rule",
                    "observation": "Beta output is wrong.",
                    "strategy": "Add RULE B.",
                    "evidence_ids": [evidence[-1]],
                },
            ]})
        if role == "skill-proposer":
            target = request["target_pattern"]
            rule = "RULE B" if self.duplicate or target["id"] == "beta-rule" else "RULE A"
            return RuntimeResult(payload={
                "skill_name": request["skill_name"],
                "summary": f"Add {rule} for the assigned failure pattern",
                "old_text": "Return the input unchanged.",
                "new_text": f"Return the result using {rule}.",
                "evidence_ids": target["evidence_ids"],
                "pattern_ids": [target["id"]],
            })
        raise ValueError(role)


def multi_candidate_adapter(temp: Path) -> ExactMatchJSONLAdapter:
    path = temp / "multi-candidate-tasks.jsonl"
    rows = [
        {"id": "train-a", "split": "train", "input": "a", "expected": "good"},
        {"id": "train-b", "split": "train", "input": "b", "expected": "good"},
        {"id": "validation-a", "split": "validation", "input": "a", "expected": "good"},
        {"id": "validation-b", "split": "validation", "input": "b", "expected": "good"},
        {"id": "test-a", "split": "test", "input": "a", "expected": "good"},
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return ExactMatchJSONLAdapter(path)


class EvolutionTests(unittest.TestCase):
    def test_demo_accepts_improving_skill(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Workspace(temp)
            workspace.initialize(skill_name="normalize", skill_text=INITIAL_SKILL)
            summary = EvolutionEngine(
                workspace=workspace,
                runtime=DemoRuntime(),
                adapter=example_adapter(),
            ).run(iterations=1)

            self.assertEqual(summary.initial_validation_score, 0.0)
            self.assertEqual(summary.final_validation_score, 1.0)
            self.assertEqual(summary.final_test_score, 1.0)
            self.assertEqual(summary.accepted, 1)
            self.assertEqual(summary.final_version, 1)
            self.assertIn("lowercase, trimmed", workspace.read_skill("normalize"))
            self.assertTrue((Path(temp) / "versions" / "normalize" / "v000" / "SKILL.md").is_file())
            proposer_view = Path(temp) / ".views" / "proposer" / "iteration-000"
            visible_paths = {path.relative_to(proposer_view).as_posix() for path in proposer_view.rglob("*")}
            self.assertIn("traces/train-001.json", visible_paths)
            self.assertFalse(any("validation" in path or "test" in path for path in visible_paths))
            impacts = (Path(temp) / "events" / "skill-impact.jsonl").read_text(encoding="utf-8")
            self.assertIn('"candidate_id": "candidate-01"', impacts)
            self.assertIn('"diff": "--- skills/normalize/SKILL.md', impacts)
            self.assertTrue(
                (Path(temp) / "candidates" / "iteration-000" / "candidate-01" / "normalize" / "SKILL.md").is_file()
            )

    def test_rejected_candidate_does_not_change_active_skill_but_keeps_wiki(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Workspace(temp)
            workspace.initialize(skill_name="normalize", skill_text=INITIAL_SKILL)
            summary = EvolutionEngine(
                workspace=workspace,
                runtime=NoImproveRuntime(),
                adapter=example_adapter(),
            ).run(iterations=1)

            self.assertEqual(summary.rejected, 1)
            self.assertEqual(summary.final_version, 0)
            self.assertEqual(workspace.read_skill("normalize"), INITIAL_SKILL)
            self.assertTrue((Path(temp) / "wiki" / "patterns" / "normalize-case-and-space.md").is_file())
            impact = workspace.read_impact_log()
            self.assertIn("rejected", impact)

    def test_multiple_candidates_promote_only_the_unique_validation_best(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = Workspace(root / "workspace")
            workspace.initialize(skill_name="normalize", skill_text=INITIAL_SKILL)
            summary = EvolutionEngine(
                workspace=workspace,
                runtime=MultiCandidateRuntime(),
                adapter=multi_candidate_adapter(root),
                candidate_count=2,
            ).run(iterations=1, evaluate_test=False)

            self.assertEqual(summary.accepted, 1)
            self.assertEqual(summary.rejected, 1)
            self.assertEqual(summary.skipped, 0)
            self.assertEqual(summary.final_version, 1)
            self.assertIn("RULE B", workspace.read_skill("normalize"))
            impacts = [
                json.loads(line)
                for line in (root / "workspace" / "events" / "skill-impact.jsonl").read_text().splitlines()
            ]
            self.assertEqual([item["decision"] for item in impacts], ["rejected-not-best", "accepted"])
            self.assertEqual([item["candidate_id"] for item in impacts], ["candidate-01", "candidate-02"])

    def test_duplicate_candidates_are_skipped_before_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = Workspace(root / "workspace")
            workspace.initialize(skill_name="normalize", skill_text=INITIAL_SKILL)
            summary = EvolutionEngine(
                workspace=workspace,
                runtime=MultiCandidateRuntime(duplicate=True),
                adapter=multi_candidate_adapter(root),
                candidate_count=2,
            ).run(iterations=1, evaluate_test=False)

            self.assertEqual(summary.accepted, 1)
            self.assertEqual(summary.rejected, 0)
            self.assertEqual(summary.skipped, 1)
            impacts = [
                json.loads(line)
                for line in (root / "workspace" / "events" / "skill-impact.jsonl").read_text().splitlines()
            ]
            self.assertEqual([item["decision"] for item in impacts], ["duplicate", "accepted"])


if __name__ == "__main__":
    unittest.main()
