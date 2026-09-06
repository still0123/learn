import tempfile
from pathlib import Path
import unittest

from evaluation.tools.build_claim_evidence_stage1_splits_v1 import PRIMARY_TYPES, select_splits


class Stage1SplitTest(unittest.TestCase):
    def test_joint_splits_are_balanced_and_video_disjoint(self):
        questions = []
        groundtruth = []
        with tempfile.TemporaryDirectory() as temp_dir:
            video_root = Path(temp_dir)
            for type_index, primary_type in enumerate(PRIMARY_TYPES):
                for row_index in range(6):
                    qid = f"q{type_index}_{row_index}"
                    video = f"v{type_index}_{row_index}"
                    questions.append({
                        "question_id": qid,
                        "video": video,
                        "question": "Question?",
                        "question_type": [primary_type],
                    })
                    groundtruth.append({
                        "question_id": qid,
                        "video": video,
                        "answer": "Answer",
                        "question_type": [primary_type],
                    })
                    (video_root / f"{video}.mp4").touch()
            selected, audit = select_splits(
                questions,
                groundtruth,
                excluded_question_ids={"q0_0"},
                excluded_video_ids=set(),
                video_root=video_root,
                per_type_per_split=2,
                seed=17,
            )
        for split_name in ("dev300", "confirmd300"):
            rows = selected[split_name]
            self.assertEqual(len(rows), 10)
            counts = {primary_type: 0 for primary_type in PRIMARY_TYPES}
            for _, _, _, primary_type in rows:
                counts[primary_type] += 1
            self.assertEqual(set(counts.values()), {2})
        dev_questions = {row[1]["question_id"] for row in selected["dev300"]}
        confirm_questions = {row[1]["question_id"] for row in selected["confirmd300"]}
        dev_videos = {row[1]["video"] for row in selected["dev300"]}
        confirm_videos = {row[1]["video"] for row in selected["confirmd300"]}
        self.assertFalse(dev_questions & confirm_questions)
        self.assertFalse(dev_videos & confirm_videos)
        self.assertNotIn("q0_0", dev_questions | confirm_questions)
        self.assertEqual(audit["selected_video_count"], 20)


if __name__ == "__main__":
    unittest.main()
