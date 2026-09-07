from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.tools.freeze_groupcv_gate_manifest_v1 import (  # noqa: E402
    GateFreezeError,
    build_fold_rule,
    percentile,
)


def raw_feature(question_id, visual_detail, peak, concentration):
    return {
        "question_id": question_id,
        "gate_decision": {
            "question_type": {"is_visual_detail_question": visual_detail},
            "permitted_evidence_summary": {
                "peak_response": peak,
                "response_concentration": concentration,
            },
        },
    }


class FreezeGroupCVGateManifestTest(unittest.TestCase):
    def test_percentile_is_interpolated_and_bounded(self):
        self.assertEqual(percentile([1.0, 2.0, 3.0], 0.5), 2.0)
        self.assertEqual(percentile([1.0, 3.0], 0.25), 1.5)
        with self.assertRaises(GateFreezeError):
            percentile([], 0.5)

    def test_fold_rule_uses_only_train_question_features(self):
        features = {
            "train-a": raw_feature("train-a", True, 0.50, 0.01),
            "train-b": raw_feature("train-b", True, 0.70, 0.03),
            "validation": raw_feature("validation", True, 0.99, 0.99),
        }
        rule, diagnostics = build_fold_rule(
            fold_id=0,
            train_question_ids=["train-a", "train-b"],
            raw_by_question=features,
        )
        self.assertLess(rule["minimum_peak_response"], 0.99)
        self.assertEqual(rule["minimum_response_concentration"], 0.0)
        self.assertEqual(diagnostics["fit_visual_detail_question_count"], 2)
        self.assertEqual(rule["threshold_selection"], "outer_fold_train_only_median_peak_v2")


if __name__ == "__main__":
    unittest.main()
