import unittest

import numpy as np

from lightweight_selector import (
    SelectorWeights,
    select_conservative_raw_evidence,
    select_temporal_evidence,
)


class LightweightSelectorTest(unittest.TestCase):
    def test_fixed_budget_chronology_and_coverage(self):
        embeddings = np.eye(8, dtype=np.float64)
        question = np.array([0, 0, 0, 0, 1, 1, 1, 1], dtype=np.float64)
        asr = question.copy()
        selected, trace = select_temporal_evidence(
            embeddings,
            question,
            asr,
            top_k=4,
            coverage_bins=4,
        )
        self.assertEqual(selected, sorted(selected))
        self.assertEqual(len(selected), 4)
        self.assertEqual(trace["bin_counts"], [1, 1, 1, 1])

    def test_asr_reliability_ablation_removes_component(self):
        embeddings = np.eye(4, dtype=np.float64)
        _, trace = select_temporal_evidence(
            embeddings,
            np.zeros(4),
            np.arange(4),
            top_k=2,
            coverage_bins=1,
            question_asr_reliability=0.0,
        )
        self.assertEqual(trace["asr_component"], [0.0, 0.0, 0.0, 0.0])

    def test_duplicate_penalty_changes_fill_choice(self):
        embeddings = np.array([
            [1.0, 0.0],
            [0.999, 0.001],
            [0.0, 1.0],
            [0.1, 0.9],
        ])
        question = np.array([1.0, 0.99, 0.4, 0.3])
        asr = np.zeros(4)
        without_penalty, _ = select_temporal_evidence(
            embeddings,
            question,
            asr,
            top_k=2,
            coverage_bins=1,
            weights=SelectorWeights(duplicate_penalty=0.0),
        )
        with_penalty, _ = select_temporal_evidence(
            embeddings,
            question,
            asr,
            top_k=2,
            coverage_bins=1,
            weights=SelectorWeights(duplicate_penalty=1.0),
        )
        self.assertIn(1, without_penalty)
        self.assertNotIn(1, with_penalty)

    def test_conservative_policy_keeps_24_raw_and_adds_8_non_raw(self):
        embeddings = np.eye(64, dtype=np.float64)
        question = np.linspace(0.0, 1.0, 64)
        asr = np.zeros(64)
        raw_ranks = [2 * index for index in range(32)]
        selected, trace = select_conservative_raw_evidence(
            embeddings,
            question,
            asr,
            raw_candidate_ranks=raw_ranks,
        )
        self.assertEqual(selected, sorted(selected))
        self.assertEqual(len(selected), 32)
        self.assertEqual(len(set(selected) & set(raw_ranks)), 24)
        self.assertEqual(len(set(selected) - set(raw_ranks)), 8)
        self.assertEqual(trace["replacement_count"], 8)
        self.assertEqual(trace["bin_counts"], [4] * 8)

    def test_conservative_policy_rejects_malformed_raw_grid(self):
        with self.assertRaises(ValueError):
            select_conservative_raw_evidence(
                np.eye(64),
                np.zeros(64),
                np.zeros(64),
                raw_candidate_ranks=list(range(31)),
            )


if __name__ == "__main__":
    unittest.main()
