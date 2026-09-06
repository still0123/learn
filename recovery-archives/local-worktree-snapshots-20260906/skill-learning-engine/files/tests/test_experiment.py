import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from skill_learning.experiment import ExperimentConfig, ExperimentRunner
from skill_learning.runtime import DemoRuntime


class ExperimentTests(unittest.TestCase):
    def test_repeated_demo_writes_three_condition_report(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "experiment"
            config = ExperimentConfig(
                experiment_id="demo-v2",
                dataset_path=root / "examples" / "normalization" / "tasks.jsonl",
                adapter_name="exact",
                skill_name="normalize",
                skill_path=root / "examples" / "normalization" / "skills" / "normalize" / "SKILL.md",
                iterations=1,
                repeats=2,
                bootstrap_samples=100,
                bootstrap_seed=9,
            )
            summary = ExperimentRunner(
                output_dir=output,
                config=config,
                runtime_factory=DemoRuntime,
            ).run()

            self.assertEqual(summary["conditions"]["no_skill"]["mean_score"], 0.0)
            self.assertEqual(summary["conditions"]["seed_skill"]["mean_score"], 0.0)
            self.assertEqual(summary["conditions"]["evolved_skill"]["mean_score"], 1.0)
            comparison = summary["paired_statistics"]["evolved_vs_seed_skill"]
            self.assertEqual(comparison["observed_delta"], 1.0)
            self.assertFalse(comparison["sufficient_pairs"])
            self.assertFalse(comparison["significant_improvement"])
            self.assertTrue((output / "manifest.json").is_file())
            self.assertTrue((output / "inputs" / "tasks.jsonl").is_file())
            self.assertIn(
                "确定性 Demo Runtime",
                (output / "report.md").read_text(encoding="utf-8"),
            )
            events = output / "repeat-001" / "workspace" / "events" / "evaluations.jsonl"
            phases = [json.loads(line)["phase"] for line in events.read_text().splitlines()]
            validation_candidate = next(
                phase for phase in phases if phase.startswith("validation-candidate-")
            )
            self.assertLess(phases.index(validation_candidate), phases.index("test-no-skill"))
            self.assertEqual(
                phases[-3:],
                ["test-no-skill", "test-seed-skill", "test-evolved-skill"],
            )
            snapshot = output / "inputs" / "prompts"
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                set(manifest["inputs"]["prompt_sha256"]),
                {"executor.md", "maintainer.md", "proposer.md"},
            )
            self.assertTrue(all((snapshot / name).is_file() for name in manifest["inputs"]["prompt_sha256"]))

    def test_existing_output_is_not_overwritten(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "existing"
            output.mkdir()
            config = ExperimentConfig(
                experiment_id="existing",
                dataset_path=root / "examples" / "normalization" / "tasks.jsonl",
                adapter_name="exact",
                skill_name="normalize",
                skill_path=root / "examples" / "normalization" / "skills" / "normalize" / "SKILL.md",
                repeats=1,
                bootstrap_samples=100,
            )
            with self.assertRaises(FileExistsError):
                ExperimentRunner(
                    output_dir=output,
                    config=config,
                    runtime_factory=DemoRuntime,
                ).run()

    def test_skill_source_metadata_is_snapshotted_and_hash_checked(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            skill_dir = temp_root / "seed"
            skill_dir.mkdir()
            skill_text = (
                root / "examples" / "normalization" / "skills" / "normalize" / "SKILL.md"
            ).read_text(encoding="utf-8")
            skill_path = skill_dir / "SKILL.md"
            skill_path.write_text(skill_text, encoding="utf-8")
            variant_sha256 = hashlib.sha256(skill_text.encode("utf-8")).hexdigest()
            source = {
                "schema_version": 1,
                "source_type": "test-fixture",
                "repository": "https://example.invalid/skill",
                "commit": "a" * 40,
                "path": "SKILL.md",
                "license": "MIT",
                "upstream_sha256": variant_sha256,
                "variant_sha256": variant_sha256,
                "variant": "original",
                "modifications": [],
            }
            (skill_dir / "SOURCE.json").write_text(
                json.dumps(source),
                encoding="utf-8",
            )
            output = temp_root / "experiment"
            config = ExperimentConfig(
                experiment_id="source-snapshot",
                dataset_path=root / "examples" / "normalization" / "tasks.jsonl",
                adapter_name="exact",
                skill_name="normalize",
                skill_path=skill_path,
                iterations=1,
                repeats=1,
                bootstrap_samples=100,
            )
            summary = ExperimentRunner(
                output_dir=output,
                config=config,
                runtime_factory=DemoRuntime,
            ).run()
            self.assertEqual(summary["manifest"]["skill_source"], source)
            self.assertTrue((output / "inputs" / "skill-source.json").is_file())

            source["variant_sha256"] = "0" * 64
            bad_dir = temp_root / "bad-seed"
            bad_dir.mkdir()
            bad_skill = bad_dir / "SKILL.md"
            bad_skill.write_text(skill_text, encoding="utf-8")
            (bad_dir / "SOURCE.json").write_text(json.dumps(source), encoding="utf-8")
            bad_config = ExperimentConfig(
                experiment_id="source-mismatch",
                dataset_path=root / "examples" / "normalization" / "tasks.jsonl",
                adapter_name="exact",
                skill_name="normalize",
                skill_path=bad_skill,
                iterations=1,
                repeats=1,
                bootstrap_samples=100,
            )
            with self.assertRaisesRegex(ValueError, "variant_sha256"):
                ExperimentRunner(
                    output_dir=temp_root / "bad-experiment",
                    config=bad_config,
                    runtime_factory=DemoRuntime,
                ).run()

    def test_runtime_configuration_cannot_drift_between_repeats(self):
        root = Path(__file__).resolve().parents[1]
        created = 0

        class DriftingRuntime(DemoRuntime):
            def __init__(self, model):
                self.model = model

            def describe(self):
                return {"runtime": "demo", "model": self.model}

        def factory():
            nonlocal created
            created += 1
            return DriftingRuntime(f"demo-{created}")

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "drift"
            config = ExperimentConfig(
                experiment_id="drift",
                dataset_path=root / "examples" / "normalization" / "tasks.jsonl",
                adapter_name="exact",
                skill_name="normalize",
                skill_path=root / "examples" / "normalization" / "skills" / "normalize" / "SKILL.md",
                iterations=1,
                repeats=2,
                bootstrap_samples=100,
            )
            with self.assertRaisesRegex(ValueError, "runtime configuration changed"):
                ExperimentRunner(
                    output_dir=output,
                    config=config,
                    runtime_factory=factory,
                ).run()
            self.assertTrue((output / "repeat-002" / "failure.json").is_file())


if __name__ == "__main__":
    unittest.main()
