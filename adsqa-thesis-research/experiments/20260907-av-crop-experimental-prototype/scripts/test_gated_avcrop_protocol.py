from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.methods.gated_avcrop.gate_protocol import (  # noqa: E402
    APPENDED_LOCAL_VIEW_COUNT,
    GateProtocolError,
    audit_group_record_against_manifest,
    build_gate_manifest_record,
    frozen_group_configs,
    model_content_manifest,
    validate_clean_model_path,
    validate_shared_gate_manifest,
)


AV_HIT = {
    "peak_response": 0.82,
    "response_concentration": 0.31,
    "eligible_crop_candidate_count": 11,
}


class GatedAVCropProtocolTest(unittest.TestCase):
    def _hit_record(self, question_id="q1"):
        return build_gate_manifest_record(
            question_id=question_id,
            video_id=f"v-{question_id}",
            question="Which brand logo is written on the product package?",
            asr_evidence={"transcript": "A product is placed on a table."},
            ocr_candidates=[{"text": "NORTHWIND", "bbox": [1, 2, 3, 4]}],
            av_response_stats=AV_HIT,
        ).as_dict()

    def test_visual_detail_question_with_response_peak_hits_gate(self):
        record = self._hit_record()
        self.assertTrue(record["append_crop8"])
        self.assertEqual(record["local_view_count"], APPENDED_LOCAL_VIEW_COUNT)
        self.assertEqual(record["submitted_view_count"], 40)

    def test_asr_prefixed_adsqa_question_is_classified_from_question_suffix(self):
        record = build_gate_manifest_record(
            question_id="q-prefix",
            video_id="v-prefix",
            question=(
                "Voiceover: The narrator describes the product. "
                "Question: Which brand logo is visible on the package?"
            ),
            asr_evidence={"transcript": "The narrator describes the product."},
            ocr_candidates=[],
            av_response_stats=AV_HIT,
        ).as_dict()
        self.assertTrue(record["append_crop8"])
        self.assertEqual(
            record["gate_decision"]["question_type"]["question_text_source"],
            "suffix_after_last_Question_marker",
        )
        self.assertNotIn(
            "narrator",
            record["gate_decision"]["question_type"]["matched_exclusion_terms"],
        )

    def test_fold_specific_rule_can_be_frozen_before_holdout_application(self):
        record = build_gate_manifest_record(
            question_id="q-fold-rule",
            video_id="v-fold-rule",
            question="Question: Which brand logo is visible on the package?",
            asr_evidence="",
            ocr_candidates=[],
            av_response_stats={
                "peak_response": 0.61,
                "response_concentration": 0.03,
                "eligible_crop_candidate_count": 32,
            },
            gate_rule={
                "version": "question_type_av_peak_gate_fold0_v1",
                "minimum_peak_response": 0.60,
                "minimum_response_concentration": 0.02,
                "threshold_selection": "fold0_train_only_fixed_quantile_v1",
            },
        ).as_dict()
        self.assertTrue(record["append_crop8"])
        self.assertEqual(
            record["gate_decision"]["gate_rule"]["version"],
            "question_type_av_peak_gate_fold0_v1",
        )

    def test_audio_narrative_question_is_excluded_even_with_peak(self):
        record = build_gate_manifest_record(
            question_id="q-audio",
            video_id="v-audio",
            question="What does the narrator say about the brand?",
            asr_evidence={"transcript": "Narrator speech."},
            ocr_candidates=[],
            av_response_stats=AV_HIT,
        ).as_dict()
        self.assertFalse(record["append_crop8"])
        self.assertEqual(record["local_view_count"], 0)
        self.assertEqual(record["submitted_view_count"], 32)
        self.assertIn("narrator", record["gate_decision"]["question_type"]["matched_exclusion_terms"])

    def test_gate_rejects_reference_and_judge_fields(self):
        with self.assertRaisesRegex(GateProtocolError, "forbidden gate input field"):
            build_gate_manifest_record(
                question_id="q-leak",
                video_id="v-leak",
                question="Which logo is visible?",
                asr_evidence={"transcript": "No speech.", "reference_answer": "NORTHWIND"},
                ocr_candidates=[],
                av_response_stats=AV_HIT,
            )
        with self.assertRaisesRegex(GateProtocolError, "forbidden gate input field"):
            build_gate_manifest_record(
                question_id="q-judge",
                video_id="v-judge",
                question="Which logo is visible?",
                asr_evidence={"transcript": "No speech."},
                ocr_candidates=[],
                av_response_stats={**AV_HIT, "judge_score": 1.0},
            )

    def test_asr_and_ocr_confidence_scores_are_permitted_gate_inputs(self):
        record = build_gate_manifest_record(
            question_id="q-confidence",
            video_id="v-confidence",
            question="Which logo is visible?",
            asr_evidence={
                "transcript": "A brand name appears.",
                "segments": [{"start": 0.0, "end": 1.0, "text": "brand", "score": 0.91}],
            },
            ocr_candidates=[{"text": "NORTHWIND", "score": 0.96, "bbox": [1, 2, 3, 4]}],
            av_response_stats=AV_HIT,
        ).as_dict()
        self.assertTrue(record["append_crop8"])

    def test_shared_manifest_requires_unique_questions_and_exact_view_counts(self):
        first = self._hit_record("q1")
        second = self._hit_record("q2")
        audit = validate_shared_gate_manifest([first, second])
        self.assertEqual(audit["record_count"], 2)
        self.assertEqual(audit["gate_hit_count"], 2)
        self.assertEqual(audit["allowed_submitted_view_counts"], [40])

        duplicate = dict(second)
        duplicate["question_id"] = "q1"
        with self.assertRaisesRegex(GateProtocolError, "duplicate question_id"):
            validate_shared_gate_manifest([first, duplicate])

    def test_gated_inference_record_must_match_frozen_manifest(self):
        record = self._hit_record()
        audit_group_record_against_manifest(
            "E_Gated_AVCrop8",
            record,
            {
                "question_id": "q1",
                "local_view_count": 8,
                "submitted_view_count": 40,
                "crop_count": 8,
            },
        )
        with self.assertRaisesRegex(GateProtocolError, "exactly eight crops"):
            audit_group_record_against_manifest(
                "E_Gated_AVCrop8",
                record,
                {
                    "question_id": "q1",
                    "local_view_count": 8,
                    "submitted_view_count": 40,
                    "crop_count": 7,
                },
            )

    def test_five_groups_have_the_required_control_structure(self):
        groups = frozen_group_configs()
        self.assertEqual(set(groups), {
            "A_Raw32",
            "B_Raw40",
            "C_Gated_RandomCrop8",
            "D_Gated_CLIPCrop8",
            "E_Gated_AVCrop8",
        })
        self.assertEqual(groups["A_Raw32"]["submitted_view_count"], 32)
        self.assertEqual(groups["B_Raw40"]["submitted_view_count"], 40)
        for name in ("C_Gated_RandomCrop8", "D_Gated_CLIPCrop8", "E_Gated_AVCrop8"):
            self.assertEqual(groups[name]["local_view_count_when_gate_hit"], 8)
            self.assertEqual(groups[name]["submitted_view_count_when_gate_hit"], 40)
            self.assertTrue(groups[name]["gate_manifest_required"])
            self.assertFalse(groups[name]["rag_enabled"])
            self.assertFalse(groups[name]["reflection_enabled"])

    def test_model_manifest_is_deterministic_and_readr_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.json").write_text("{}", encoding="utf-8")
            (root / "weights.bin").write_bytes(b"weights")
            first = model_content_manifest(root)
            second = model_content_manifest(root)
            self.assertEqual(first, second)
            self.assertEqual(first["file_count"], 2)
            self.assertEqual(len(first["content_manifest_sha256"]), 64)
        with self.assertRaisesRegex(GateProtocolError, "ReAd-R is forbidden"):
            validate_clean_model_path("/models/Qwen2.5-7B-VL-ReAd-R")


if __name__ == "__main__":
    unittest.main()
