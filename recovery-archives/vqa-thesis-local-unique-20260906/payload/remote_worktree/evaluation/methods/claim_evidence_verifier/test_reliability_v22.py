import copy
import unittest

from evaluation.methods.claim_evidence_verifier.reliability_v22 import (
    build_feature_vector, classification_metrics, feature_names,
)


class ReliabilityV22Test(unittest.TestCase):
    def rows(self):
        input_row = {
            "question": "What price is shown?", "claim": "The price is ten dollars.",
            "asr_excerpt": "Only ten dollars today.", "ocr_present": True, "primary_type": "Type_1",
            "router_inputs": {
                "candidate_scores": [0.1, 0.3, 0.8, 0.4], "raw_candidate_ranks": [0, 2],
                "mmr_selected_candidate_ranks": [1, 2],
                "selector_trace": {"question_component": [0.2, 0.8], "asr_component": [0.1, 0.7], "question_asr_reliability": 0.6},
            },
            "secret": {"ground_truth": "ten dollars"},
        }
        support = {"scores": {"full": {"supported": 0.8, "refuted": 0.1, "insufficient": 0.1}}}
        return input_row, support

    def test_feature_schema_and_leakage_safety(self):
        row, support = self.rows()
        before = build_feature_vector(row, support)
        changed = copy.deepcopy(row)
        changed["secret"] = {"ground_truth": "changed", "judge_score": 0}
        self.assertEqual(len(before), len(feature_names()))
        self.assertEqual(before, build_feature_vector(changed, support))

    def test_metrics_rank_correct_items_first(self):
        metrics = classification_metrics([1, 1, 0, 0], [0.9, 0.8, 0.2, 0.1], 0.5)
        self.assertEqual(metrics["auroc"], 1.0)
        self.assertEqual(metrics["risk_coverage"]["risks"]["0.4"], 0.0)


if __name__ == "__main__":
    unittest.main()
