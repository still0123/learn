import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from skill_learning.tasks import (
    ConventionalBranchJSONLAdapter,
    ConventionalCommitJSONLAdapter,
    ExactMatchJSONLAdapter,
    JSONValueJSONLAdapter,
    PesterShouldMigrationJSONLAdapter,
)


class TaskAdapterTests(unittest.TestCase):
    def test_requires_all_three_splits(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "tasks.jsonl"
            path.write_text(
                '{"id":"one","split":"train","input":"x","expected":"x"}\n',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                ExactMatchJSONLAdapter(path)

    def test_example_dataset_loads(self):
        path = Path(__file__).resolve().parents[1] / "examples" / "normalization" / "tasks.jsonl"
        adapter = ExactMatchJSONLAdapter(path)
        self.assertEqual(len(adapter.tasks("train")), 3)
        self.assertEqual(len(adapter.tasks("validation")), 2)
        self.assertEqual(len(adapter.tasks("test")), 2)

    def test_json_adapter_accepts_semantic_json_and_answer_wrappers(self):
        path = Path(__file__).resolve().parents[1] / "examples" / "record_ops" / "tasks.jsonl"
        adapter = JSONValueJSONLAdapter(path)
        task = adapter.tasks("train")[0]
        answer = "<answer>\n```json\n" + json.dumps(task.expected) + "\n```\n</answer>"
        score = adapter.score(task, answer)
        self.assertEqual(score.value, 1.0)
        self.assertEqual(score.metrics, {"valid_json": 1.0, "exact_match": 1.0})

    def test_json_adapter_separates_invalid_json_and_wrong_value(self):
        path = Path(__file__).resolve().parents[1] / "examples" / "record_ops" / "tasks.jsonl"
        adapter = JSONValueJSONLAdapter(path)
        task = adapter.tasks("train")[0]
        invalid = adapter.score(task, "not-json")
        wrong = adapter.score(task, "[]")
        self.assertEqual(invalid.metrics["valid_json"], 0.0)
        self.assertEqual(wrong.metrics["valid_json"], 1.0)
        self.assertEqual(wrong.value, 0.0)

    def test_record_ops_split_counts_and_expected_values(self):
        path = Path(__file__).resolve().parents[1] / "examples" / "record_ops" / "tasks.jsonl"
        adapter = JSONValueJSONLAdapter(path)
        self.assertEqual(
            {split: len(adapter.tasks(split)) for split in ("train", "validation", "test")},
            {"train": 10, "validation": 6, "test": 12},
        )
        for split in ("train", "validation", "test"):
            for task in adapter.tasks(split):
                self.assertEqual(adapter.score(task, json.dumps(task.expected)).value, 1.0)

    def test_conventional_commit_dataset_and_original_source_are_fixed(self):
        root = Path(__file__).resolve().parents[1]
        adapter = ConventionalCommitJSONLAdapter(
            root / "examples" / "conventional_commit" / "tasks.jsonl"
        )
        self.assertEqual(
            {split: len(adapter.tasks(split)) for split in ("train", "validation", "test")},
            {"train": 12, "validation": 8, "test": 10},
        )
        pilot = ConventionalCommitJSONLAdapter(
            root / "examples" / "conventional_commit" / "pilot-tasks.jsonl"
        )
        self.assertEqual(
            {split: len(pilot.tasks(split)) for split in ("train", "validation", "test")},
            {"train": 3, "validation": 2, "test": 2},
        )
        learning_pilot = PesterShouldMigrationJSONLAdapter(
            root / "examples" / "pester_should_migration" / "learning-pilot-tasks.jsonl"
        )
        self.assertEqual(
            {
                split: len(learning_pilot.tasks(split))
                for split in ("train", "validation", "test")
            },
            {"train": 3, "validation": 2, "test": 2},
        )
        learning_pilot_v2 = PesterShouldMigrationJSONLAdapter(
            root / "examples" / "pester_should_migration" / "learning-pilot-v2-tasks.jsonl"
        )
        self.assertEqual(
            {
                split: len(learning_pilot_v2.tasks(split))
                for split in ("train", "validation", "test")
            },
            {"train": 4, "validation": 3, "test": 4},
        )
        full_tasks = {
            task.id: task
            for split in ("train", "validation", "test")
            for task in adapter.tasks(split)
        }
        for split in ("train", "validation", "test"):
            for task in pilot.tasks(split):
                self.assertEqual(task, full_tasks[task.id])
        skill = (
            root
            / "examples"
            / "conventional_commit"
            / "skills"
            / "original"
            / "SKILL.md"
        )
        self.assertEqual(
            hashlib.sha256(skill.read_bytes()).hexdigest(),
            "250235f71b8c501a7744ded911281292324bcd1a2d014e34b25041e2d2c8bf73",
        )
        for split in ("train", "validation", "test"):
            for task in adapter.tasks(split):
                expected = task.expected
                scope = f"({expected['scope']})" if expected["scope"] else ""
                header = (
                    f"{expected['type']}{scope}: "
                    + " ".join(expected["description_terms"])
                )
                footer = []
                if expected["breaking_note_terms"]:
                    footer.append(
                        "BREAKING CHANGE: " + " ".join(expected["breaking_note_terms"])
                    )
                if expected["references"]:
                    footer.append("Refs: " + " ".join(expected["references"]))
                answer = header + ("\n\n" + "\n".join(footer) if footer else "")
                self.assertEqual(adapter.score(task, answer).value, 1.0, task.id)

    def test_conventional_branch_pilot_and_source_are_fixed(self):
        root = Path(__file__).resolve().parents[1]
        adapter = ConventionalBranchJSONLAdapter(
            root / "examples" / "conventional_branch" / "pilot-tasks.jsonl"
        )
        self.assertEqual(
            {split: len(adapter.tasks(split)) for split in ("train", "validation", "test")},
            {"train": 3, "validation": 3, "test": 3},
        )
        original = root / "examples" / "conventional_branch" / "skills" / "original" / "SKILL.md"
        ablated = root / "examples" / "conventional_branch" / "skills" / "ablated" / "SKILL.md"
        self.assertEqual(
            hashlib.sha256(original.read_bytes()).hexdigest(),
            "94b962ff93ac639c8b760a29465ca48f51d6af1ad1b4bdd242d52f1260959b07",
        )
        self.assertEqual(
            hashlib.sha256(ablated.read_bytes()).hexdigest(),
            "34f814525a7cef0ef0a84592a2c575f349575cce90ca87986e367dcf776973fe",
        )
        for split in ("train", "validation", "test"):
            for task in adapter.tasks(split):
                self.assertEqual(adapter.score(task, task.expected["branch"]).value, 1.0, task.id)

    def test_conventional_branch_adapter_rejects_invalid_branch_syntax(self):
        root = Path(__file__).resolve().parents[1]
        adapter = ConventionalBranchJSONLAdapter(
            root / "examples" / "conventional_branch" / "pilot-tasks.jsonl"
        )
        task = adapter.tasks("train")[0]
        score = adapter.score(task, "Feature/Issue_482--Add OAuth Login")
        self.assertEqual(score.metrics["valid_branch_syntax"], 0.0)
        self.assertEqual(score.metrics["single_branch_output"], 1.0)
        self.assertLess(score.value, 1.0)

    def test_conventional_commit_adapter_scores_breaking_footer(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "examples"
            / "conventional_commit"
            / "tasks.jsonl"
        )
        adapter = ConventionalCommitJSONLAdapter(path)
        task = next(item for item in adapter.tasks("train") if item.id == "train-cc-009")
        correct = adapter.score(
            task,
            "feat(api): rename user identifier\n\n"
            "BREAKING CHANGE: user_id was renamed to id",
        )
        missing_footer = adapter.score(task, "feat(api): renamed user identifier")
        self.assertEqual(correct.value, 1.0)
        self.assertEqual(correct.metrics["breaking_change"], 1.0)
        self.assertLess(missing_footer.value, correct.value)
        self.assertEqual(missing_footer.metrics["imperative_verb"], 0.0)
        self.assertEqual(missing_footer.metrics["breaking_change"], 0.0)

    def test_conventional_commit_adapter_scores_issue_reference_and_wrappers(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "examples"
            / "conventional_commit"
            / "tasks.jsonl"
        )
        adapter = ConventionalCommitJSONLAdapter(path)
        task = next(item for item in adapter.tasks("train") if item.id == "train-cc-010")
        answer = (
            "<answer>\n```text\n"
            "fix(billing): prevent duplicate invoice charge\n\nCloses #482\n"
            "```\n</answer>"
        )
        score = adapter.score(task, answer)
        self.assertEqual(score.value, 1.0)
        self.assertEqual(score.metrics["references"], 1.0)

    def test_conventional_commit_adapter_rejects_non_header_output(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "examples"
            / "conventional_commit"
            / "tasks.jsonl"
        )
        adapter = ConventionalCommitJSONLAdapter(path)
        task = adapter.tasks("test")[0]
        score = adapter.score(task, "Here is your commit message: feat(export): add CSV export")
        self.assertEqual(score.value, 0.0)
        self.assertEqual(score.metrics["valid_format"], 0.0)

    def test_pester_dataset_pilot_and_upstream_source_are_fixed(self):
        root = Path(__file__).resolve().parents[1]
        adapter = PesterShouldMigrationJSONLAdapter(
            root / "examples" / "pester_should_migration" / "tasks.jsonl"
        )
        self.assertEqual(
            {split: len(adapter.tasks(split)) for split in ("train", "validation", "test")},
            {"train": 12, "validation": 8, "test": 10},
        )
        pilot = PesterShouldMigrationJSONLAdapter(
            root / "examples" / "pester_should_migration" / "pilot-tasks.jsonl"
        )
        self.assertEqual(
            {split: len(pilot.tasks(split)) for split in ("train", "validation", "test")},
            {"train": 3, "validation": 2, "test": 2},
        )
        full_tasks = {
            task.id: task
            for split in ("train", "validation", "test")
            for task in adapter.tasks(split)
        }
        for split in ("train", "validation", "test"):
            for task in pilot.tasks(split):
                self.assertEqual(task, full_tasks[task.id])
        skill = (
            root
            / "examples"
            / "pester_should_migration"
            / "skills"
            / "original"
            / "SKILL.md"
        )
        self.assertEqual(
            hashlib.sha256(skill.read_bytes()).hexdigest(),
            "d80c47ed3cda083f6411da12d0251a136608eada05c846eeba361e3168c9f14f",
        )
        ablated = (
            root
            / "examples"
            / "pester_should_migration"
            / "skills"
            / "ablated"
            / "SKILL.md"
        )
        self.assertEqual(
            hashlib.sha256(ablated.read_bytes()).hexdigest(),
            "39bbb32ee7f12008a57bc7fb3074ce31e4a67e7cafe7b13b57df71de6a1aee15",
        )
        for split in ("train", "validation", "test"):
            for task in adapter.tasks(split):
                expected = task.expected
                answer = "\n".join([*expected["context"], *expected["required"]])
                self.assertEqual(adapter.score(task, answer).value, 1.0, task.id)

    def test_pester_adapter_scores_semantic_migrations_and_wrappers(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "examples"
            / "pester_should_migration"
            / "tasks.jsonl"
        )
        adapter = PesterShouldMigrationJSONLAdapter(path)
        truthy = next(item for item in adapter.tasks("train") if item.id == "train-pester-04")
        correct = adapter.score(
            truthy,
            "<answer>\n```powershell\n$retryCount = 1\n$retryCount | Should-BeTruthy\n```\n</answer>",
        )
        strict_boolean = adapter.score(
            truthy,
            "$retryCount = 1\n$retryCount | Should-BeTrue",
        )
        with_explanation = adapter.score(
            truthy,
            "Here is the migrated code:\n$retryCount = 1\n$retryCount | Should-BeTruthy",
        )
        self.assertEqual(correct.value, 1.0)
        self.assertLess(strict_boolean.value, correct.value)
        self.assertEqual(strict_boolean.metrics["required_rewrites"], 0.0)
        self.assertLess(with_explanation.value, correct.value)
        self.assertEqual(with_explanation.metrics["code_only_output"], 0.0)


if __name__ == "__main__":
    unittest.main()
