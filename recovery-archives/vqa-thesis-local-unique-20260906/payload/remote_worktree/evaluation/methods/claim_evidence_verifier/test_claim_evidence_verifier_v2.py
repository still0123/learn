import copy
import unittest

from evaluation.methods.claim_evidence_verifier.features_v2 import (
    build_feature_vector,
    extract_answer_claim,
    feature_names,
)
from evaluation.methods.claim_evidence_verifier.metrics_v2 import intervention_metrics
from evaluation.methods.claim_evidence_verifier.protocol_v2 import (
    audit_intervention,
    plan_asr_target_control,
    plan_visual_target_control,
)
from evaluation.methods.claim_evidence_verifier.protocol_v21 import (
    plan_asr_target_control_v21,
    plan_visual_target_control_v21,
    raw32_relevance_from_nested_cache,
)


class ProtocolV2Test(unittest.TestCase):
    def setUp(self):
        self.units = [{
            "id": "offer", "modalities": ["visual", "audio"],
            "intervals_sec": [[4.0, 6.0]], "required": True,
        }]

    def test_visual_target_control_has_equal_cost(self):
        plan = plan_visual_target_control([0, 2, 4, 5, 6, 8, 10], self.units, max_target_count=2)
        self.assertTrue(plan["valid"])
        self.assertEqual(plan["target_cost"], plan["control_cost"])
        self.assertFalse(audit_intervention(plan))

    def test_asr_alias_and_duration_match(self):
        segments = [
            {"start": 0.0, "end": 1.0}, {"start": 4.2, "end": 5.2},
            {"start": 8.0, "end": 9.1},
        ]
        plan = plan_asr_target_control(segments, self.units)
        self.assertTrue(plan["valid"])
        self.assertFalse(audit_intervention(plan))

    def test_v21_rejects_distributed_visual_evidence(self):
        units = [{"modalities": ["visual"], "intervals_sec": [[0, 80]], "required": True}]
        plan = plan_visual_target_control_v21(
            list(range(0, 100, 3))[:32], [index / 32 for index in range(32)], units, 100.0
        )
        self.assertFalse(plan["valid"])
        self.assertEqual(plan["reason"], "distributed_visual_evidence_no_safe_control")

    def test_v21_uses_low_relevance_cross_bin_controls(self):
        timestamps = [index * 3.0 for index in range(32)]
        relevance = [0.9 if 30 <= value <= 42 else 0.01 + index / 1000 for index, value in enumerate(timestamps)]
        units = [{"modalities": ["visual"], "intervals_sec": [[30, 42]], "required": True}]
        plan = plan_visual_target_control_v21(timestamps, relevance, units, 96.0)
        self.assertTrue(plan["valid"])
        self.assertGreaterEqual(len(plan["control_temporal_bins"]), 2)
        self.assertLess(max(plan["control_relevance"]), min(plan["target_relevance"]))

    def test_v21_asr_requires_duration_matched_low_relevance_control(self):
        segments = [
            {"start": 0.0, "end": 2.0, "text": "unrelated music"},
            {"start": 4.0, "end": 6.0, "text": "price ten dollars"},
            {"start": 8.0, "end": 10.1, "text": "visit today"},
        ]
        units = [{"modalities": ["audio"], "intervals_sec": [[4.0, 6.0]], "required": True}]
        plan = plan_asr_target_control_v21(segments, units, "what price ten dollars")
        self.assertTrue(plan["valid"])
        self.assertEqual(plan["control_indices"], [0])

    def test_v21_maps_nested_raw_scores_exactly(self):
        cache = {"candidate_frame_indices": [0, 5, 10], "candidate_scores": [0.1, 0.5, 0.9]}
        self.assertEqual(raw32_relevance_from_nested_cache([0, 10], cache), [0.1, 0.9])


class FeatureV2Test(unittest.TestCase):
    def record(self):
        return {
            "question_id": "q1", "question": "What price is shown?", "claim": "The price is $10.",
            "asr_excerpt": "Only ten dollars today.",
            "scores": {
                "full": {"supported": 0.9, "refuted": 0.05, "insufficient": 0.05},
                "target_removed": {"supported": 0.2, "refuted": 0.1, "insufficient": 0.7},
                "control_removed": {"supported": 0.85, "refuted": 0.05, "insufficient": 0.1},
            },
            "metadata": {"modality": "visual", "target_cost": 2, "control_cost": 2},
            "oracle": {"evidence_units": ["SECRET"]},
            "supervision": {"ground_truth": "SECRET", "judge_score": 1.0},
        }

    def test_features_are_aligned_and_leakage_safe(self):
        record = self.record()
        before = build_feature_vector(record)
        changed = copy.deepcopy(record)
        changed["oracle"] = {"evidence_units": ["CHANGED"]}
        changed["supervision"] = {"ground_truth": "CHANGED", "judge_score": 0.0}
        self.assertEqual(len(before), len(feature_names()))
        self.assertEqual(before, build_feature_vector(changed))

    def test_extracts_final_answer_claim(self):
        answer = "1. [Observation]: Text appears.\n3. [Answer]: The price is $10."
        self.assertEqual(extract_answer_claim(answer), "The price is $10.")

    def test_intervention_metric(self):
        result = intervention_metrics([self.record()])
        self.assertEqual(result["strict_pair_accuracy"], 1.0)
        self.assertGreater(result["mean_necessity_contrast"], 0.0)


if __name__ == "__main__":
    unittest.main()
