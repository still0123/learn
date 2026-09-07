from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.tools.build_train_groupcv_and_fresh_confirm_audit_v1 import (  # noqa: E402
    AuditError,
    audit_fresh_confirm_capacity,
    build_groupcv_folds,
)


def make_train_rows(video_count=10):
    rows = []
    for video_index in range(video_count):
        video = f"{video_index:032x}"
        for question_index in range(5):
            rows.append(
                {
                    "question_id": video_index * 5 + question_index + 1,
                    "video": video,
                    "question": f"question {video_index}-{question_index}",
                    "answer": f"answer {video_index}-{question_index}",
                }
            )
    return rows


class TrainGroupCVAuditTest(unittest.TestCase):
    def test_groupcv_keeps_every_video_and_question_on_one_validation_fold(self):
        rows = make_train_rows()
        folds, oof_questions, oof_groundtruth = build_groupcv_folds(rows, fold_count=5, seed=42)
        self.assertEqual([fold["validation_video_count"] for fold in folds], [2] * 5)
        self.assertEqual([fold["validation_question_count"] for fold in folds], [10] * 5)
        self.assertEqual(len(oof_questions), 50)
        self.assertEqual(len(oof_groundtruth), 50)
        self.assertEqual(
            {item["question_id"] for item in oof_questions},
            {str(row["question_id"]) for row in rows},
        )
        for fold in folds:
            self.assertFalse(set(fold["train_video_ids"]) & set(fold["validation_video_ids"]))

    def test_groupcv_rejects_duplicate_question_ids(self):
        rows = make_train_rows()
        rows[-1] = {**rows[-1], "question_id": rows[0]["question_id"]}
        with self.assertRaisesRegex(AuditError, "question IDs must be unique"):
            build_groupcv_folds(rows, fold_count=5, seed=42)

    def test_fresh_confirm_capacity_uses_question_only_rows_and_exclusions(self):
        test_rows = [
            {
                "question_id": f"q-{index}",
                "video": f"{index:032x}",
                "question": f"question {index}",
                "question_type": ["Type_1"],
            }
            for index in range(4)
        ]
        inventory = audit_fresh_confirm_capacity(
            test_rows,
            {"pilot": {f"{0:032x}"}, "evidence": {f"{1:032x}"}},
        )
        self.assertFalse(inventory["test_groundtruth_read"])
        self.assertEqual(inventory["candidate_unique_video_count"], 2)
        self.assertEqual(inventory["candidate_question_count"], 2)
        self.assertNotIn(f"{0:032x}", inventory["candidate_video_ids"])
        self.assertEqual(inventory["candidate_overlap_by_exclusion_category"], {
            "evidence": 0,
            "pilot": 0,
        })


if __name__ == "__main__":
    unittest.main()
