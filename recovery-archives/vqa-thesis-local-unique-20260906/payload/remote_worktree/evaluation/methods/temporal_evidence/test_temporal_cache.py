import json
import tempfile
import unittest
from pathlib import Path

from temporal_cache import (
    nested_uniform_candidate_indices,
    SCHEMA_VERSION,
    TemporalCacheError,
    load_temporal_index_cache,
    question_sha256,
    temporal_cache_inventory,
    validate_temporal_record,
)


class TemporalCacheTest(unittest.TestCase):
    def record(self):
        return {
            "schema_version": SCHEMA_VERSION,
            "question_id": "q1",
            "question_sha256": question_sha256("where?"),
            "candidate_count": 4,
            "ranked_candidate_ranks": [3, 1, 0, 2],
            "selected_candidate_ranks": [1, 3],
        }

    def test_load_and_validate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cache.jsonl"
            path.write_text(json.dumps(self.record()) + "\n", encoding="utf-8")
            records = load_temporal_index_cache(path)
            inventory = temporal_cache_inventory(path)
            self.assertEqual(len(inventory), 1)
            self.assertEqual(inventory[0]["size_bytes"], path.stat().st_size)
            self.assertEqual(len(inventory[0]["sha256"]), 64)
            ranks = validate_temporal_record(
                records["q1"],
                question_id="q1",
                question="where?",
                candidate_count=4,
                selected_count=2,
            )
            self.assertEqual(ranks, [1, 3])

    def test_rejects_non_chronological_selection(self):
        record = self.record()
        record["selected_candidate_ranks"] = [3, 1]
        with self.assertRaisesRegex(TemporalCacheError, "not chronological"):
            validate_temporal_record(
                record,
                question_id="q1",
                question="where?",
                candidate_count=4,
                selected_count=2,
            )

    def test_rejects_question_drift(self):
        with self.assertRaisesRegex(TemporalCacheError, "question hash mismatch"):
            validate_temporal_record(
                self.record(),
                question_id="q1",
                question="different",
                candidate_count=4,
                selected_count=2,
            )

    def test_nested_candidates_preserve_exact_raw_uniform_frames(self):
        candidates = nested_uniform_candidate_indices(1414, 64, 32)
        baseline = __import__("numpy").linspace(0, 1413, 32, dtype=int).tolist()
        self.assertEqual(len(candidates), 64)
        self.assertEqual(candidates, sorted(candidates))
        self.assertTrue(set(baseline).issubset(candidates))

    def test_short_video_keeps_baseline_with_required_length(self):
        candidates = nested_uniform_candidate_indices(8, 64, 32)
        baseline = __import__("numpy").linspace(0, 7, 32, dtype=int).tolist()
        self.assertEqual(len(candidates), 64)
        self.assertTrue(set(baseline).issubset(candidates))


if __name__ == "__main__":
    unittest.main()
