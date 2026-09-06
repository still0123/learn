from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from skill_learning.experiment import ExperimentConfig, ExperimentRunner
from skill_learning.inspection import inspect_experiment, render_inspection
from skill_learning.runtime import DemoRuntime


class InspectionTests(unittest.TestCase):
    def test_inspection_surfaces_statistics_and_candidate_decision(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "experiment"
            config = ExperimentConfig(
                experiment_id="inspect-demo",
                dataset_path=root / "examples" / "normalization" / "tasks.jsonl",
                adapter_name="exact",
                skill_name="normalize",
                skill_path=root / "examples" / "normalization" / "skills" / "normalize" / "SKILL.md",
                iterations=1,
                candidates=2,
                repeats=1,
                bootstrap_samples=100,
            )
            ExperimentRunner(
                output_dir=output,
                config=config,
                runtime_factory=DemoRuntime,
            ).run()

            view = inspect_experiment(output)
            self.assertEqual(view["experiment_id"], "inspect-demo")
            self.assertEqual(view["repeats"][0]["final_version"], 1)
            self.assertEqual(view["repeats"][0]["candidates"][0]["candidate_id"], "candidate-01")
            rendered = render_inspection(view)
            self.assertIn("Three-condition Test summary", rendered)
            self.assertIn("Candidate decisions", rendered)
            self.assertIn("candidate-01", rendered)

    def test_inspection_rejects_unknown_repeat(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "summary.json").write_text(
                '{"experiment_id":"empty","manifest":{"runtime":{}},"repeats":[]}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "repeat 1"):
                inspect_experiment(root, repeat=1)


if __name__ == "__main__":
    unittest.main()
