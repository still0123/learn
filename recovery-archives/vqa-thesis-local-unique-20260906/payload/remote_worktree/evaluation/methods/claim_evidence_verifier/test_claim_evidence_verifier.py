import unittest

from evaluation.methods.claim_evidence_verifier.dataset import pair_record_from_trace
from evaluation.methods.claim_evidence_verifier.features import (
    build_feature_vector,
    extract_answer_claim,
    feature_names,
)
from evaluation.methods.claim_evidence_verifier.metrics import (
    binary_metrics,
    select_conservative_threshold,
)


def example_record():
    return {
        "question_id": "q1",
        "video_id": "v1",
        "source_method": "raw_uniform",
        "category": "price_promo",
        "question": "What price is shown?",
        "asr_excerpt": "The offer is only $10 today.",
        "initial_answer": "1. [Observation]: A price appears.\n3. [Answer]: It costs $20.",
        "rescue_answer": "3. [Answer]: It costs $10.",
        "support": {
            "initial_on_positive": -1.0,
            "initial_on_counterfactual": -2.0,
            "initial_on_rescue": -3.0,
            "rescue_on_rescue": -1.0,
        },
        "relevance_scores": [0.1, 0.2, 0.8, 0.9],
        "counterfactual": {"destroyed_input_indices": [2, 3], "view_count_before": 4},
        "rescue": {"reasons": ["counterfactual_insensitive"]},
        "supervision": {
            "ground_truth": "$10",
            "initial_score": 0.0,
            "rescue_score": 1.0,
            "rescue_better": 1,
        },
    }


class FeatureTest(unittest.TestCase):
    def test_final_answer_extraction(self):
        self.assertEqual(extract_answer_claim(example_record()["initial_answer"]), "It costs $20.")

    def test_feature_vector_is_stable_and_aligned(self):
        vector = build_feature_vector(example_record())
        self.assertEqual(len(vector), len(feature_names()))
        self.assertEqual(vector, build_feature_vector(example_record()))

    def test_supervision_cannot_change_features(self):
        record = example_record()
        before = build_feature_vector(record)
        record["supervision"] = {
            "ground_truth": "SECRET SHOULD NEVER ENTER FEATURES",
            "initial_score": 1.0,
            "rescue_score": 0.0,
            "rescue_better": 0,
        }
        self.assertEqual(before, build_feature_vector(record))

    def test_pair_record_requires_real_rescue_candidate(self):
        trace = {
            "question_id": "q1",
            "video_id": "v1",
            "question": "Question?",
            "initial_answer": "Initial",
            "rescue": {"triggered": False},
        }
        with self.assertRaises(ValueError):
            pair_record_from_trace(trace, "raw_uniform")


class MetricTest(unittest.TestCase):
    def test_binary_metrics(self):
        metrics = binary_metrics([1, 1, 0, 0], [0.95, 0.9, 0.2, 0.1])
        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertEqual(metrics["auroc"], 1.0)

    def test_conservative_threshold_rejects_harmful_switch(self):
        records = []
        probabilities = [0.95, 0.90, 0.20, 0.10]
        values = [(0.0, 1.0), (0.5, 1.0), (1.0, 0.0), (1.0, 1.0)]
        for index, (initial, rescue) in enumerate(values):
            records.append({
                "question_id": str(index),
                "category": "visual_detail",
                "supervision": {
                    "initial_score": initial,
                    "rescue_score": rescue,
                    "rescue_better": int(rescue > initial),
                },
            })
        selection = select_conservative_threshold(records, probabilities)
        self.assertEqual(selection["threshold"], 0.9)
        self.assertEqual(selection["beneficial_switches"], 2)
        self.assertEqual(selection["harmful_switches"], 0)


if __name__ == "__main__":
    unittest.main()
