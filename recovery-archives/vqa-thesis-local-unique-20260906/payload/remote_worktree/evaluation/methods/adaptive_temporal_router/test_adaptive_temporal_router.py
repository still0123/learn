import copy
import math
import unittest

from evaluation.methods.adaptive_temporal_router.features import build_feature_vector, feature_names
from evaluation.methods.adaptive_temporal_router.metrics import development_gate, selection_metrics


def sample_record(qid="q1", raw=0.0, mmr=1.0):
    values = [index / 63.0 for index in range(64)]
    selected = list(range(0, 64, 2))
    raw_ranks = list(range(1, 64, 2))
    return {
        "question_id": qid, "video_id": qid, "split": "train",
        "primary_type": "Type_1",
        "question": "Which visual element connects the story to the product?",
        "router_inputs": {
            "asr_present": True, "asr_length": 120, "candidate_count": 64,
            "candidate_scores": values, "raw_candidate_ranks": raw_ranks,
            "mmr_selected_candidate_ranks": selected,
            "selector_trace": {
                "question_asr_reliability": 0.6,
                "question_component": values, "asr_component": values[::-1],
                "scene_change_component": [0.2] * 64, "base_score": values,
                "bin_counts": [4] * 8,
                "decision_trace": [{"duplicate_similarity": 0.5, "coverage_deficit": 0.2}] * 24,
            },
        },
        "supervision": {"raw_score": raw, "mmr_score": mmr, "mmr_better": int(mmr > raw)},
    }


class AdaptiveRouterTest(unittest.TestCase):
    def test_feature_vector_is_finite_and_stable(self):
        vector = build_feature_vector(sample_record())
        self.assertEqual(len(vector), len(feature_names()))
        self.assertTrue(all(math.isfinite(value) for value in vector))

    def test_supervision_is_not_a_feature(self):
        left = sample_record(raw=0.0, mmr=1.0)
        right = copy.deepcopy(left)
        right["supervision"] = {"raw_score": 1.0, "mmr_score": 0.0, "ground_truth": "leak"}
        self.assertEqual(build_feature_vector(left), build_feature_vector(right))

    def test_development_gate(self):
        records = [sample_record("q1", 0.0, 1.0), sample_record("q2", 1.0, 1.0)]
        report = selection_metrics(records, [0.9, 0.1], 0.5, bootstrap_samples=100, seed=1)
        gate = development_gate(report)
        self.assertTrue(gate["passed"])
        self.assertEqual(report["switch_precision"], 1.0)


if __name__ == "__main__":
    unittest.main()

