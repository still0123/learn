import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_balanced_pilot_subset.py"


class BalancedPilotBuilderTest(unittest.TestCase):
    def test_nonempty_filter_and_seed_preference(self):
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            videos = tmp / "videos"
            videos.mkdir()
            questions = [
                {"question_id": "blank_t1", "video": "v0", "question_type": ["Type_1"]},
                {"question_id": "valid_t1", "video": "v1", "question_type": ["Type_1"]},
                {"question_id": "source_t2", "video": "v2", "question_type": ["Type_2"]},
                {"question_id": "seed_t2", "video": "v3", "question_type": ["Type_2"]},
            ]
            groundtruth = [
                {**row, "answer": "" if row["question_id"] == "blank_t1" else "answer"}
                for row in questions
            ]
            seed = [questions[0], questions[3]]
            for video_id in ("v0", "v1", "v2", "v3"):
                (videos / f"{video_id}.mp4").touch()
            for name, data in (("questions.json", questions), ("groundtruth.json", groundtruth), ("seed.json", seed)):
                (tmp / name).write_text(json.dumps(data), encoding="utf-8")

            command = [
                sys.executable,
                str(SCRIPT),
                "--question-source", str(tmp / "questions.json"),
                "--groundtruth-source", str(tmp / "groundtruth.json"),
                "--question-out", str(tmp / "out_questions.json"),
                "--groundtruth-out", str(tmp / "out_groundtruth.json"),
                "--manifest-out", str(tmp / "manifest.json"),
                "--video-root", str(videos),
                "--per-type", "1",
                "--require-nonempty-answer",
                "--seed-question-file", str(tmp / "seed.json"),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)

            selected = json.loads((tmp / "out_questions.json").read_text(encoding="utf-8"))
            selected_gt = json.loads((tmp / "out_groundtruth.json").read_text(encoding="utf-8"))
            manifest = json.loads((tmp / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual([row["question_id"] for row in selected], ["valid_t1", "seed_t2"])
            self.assertTrue(all(row["answer"] for row in selected_gt))
            self.assertEqual(manifest["selected_from_seed"], {"Type_2": 1})
            self.assertEqual(manifest["skipped_empty_answers"], {"Type_1": 1})

    def test_exclusion_removes_questions_and_all_rows_from_excluded_videos(self):
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            videos = tmp / "videos"
            videos.mkdir()
            questions = [
                {"question_id": "excluded_q", "video": "v0", "question_type": ["Type_1"]},
                {"question_id": "same_video", "video": "v0", "question_type": ["Type_1"]},
                {"question_id": "selected_q", "video": "v1", "question_type": ["Type_1"]},
            ]
            groundtruth = [{**row, "answer": "answer"} for row in questions]
            excluded = [questions[0]]
            for video_id in ("v0", "v1"):
                (videos / f"{video_id}.mp4").touch()
            for name, data in (
                ("questions.json", questions),
                ("groundtruth.json", groundtruth),
                ("excluded.json", excluded),
            ):
                (tmp / name).write_text(json.dumps(data), encoding="utf-8")

            command = [
                sys.executable,
                str(SCRIPT),
                "--question-source", str(tmp / "questions.json"),
                "--groundtruth-source", str(tmp / "groundtruth.json"),
                "--question-out", str(tmp / "out_questions.json"),
                "--groundtruth-out", str(tmp / "out_groundtruth.json"),
                "--manifest-out", str(tmp / "manifest.json"),
                "--video-root", str(videos),
                "--per-type", "1",
                "--exclude-question-file", str(tmp / "excluded.json"),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)

            selected = json.loads((tmp / "out_questions.json").read_text(encoding="utf-8"))
            manifest = json.loads((tmp / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual([row["question_id"] for row in selected], ["selected_q"])
            self.assertEqual(manifest["excluded_question_count"], 1)
            self.assertEqual(manifest["excluded_video_count"], 1)
            self.assertEqual(manifest["skipped_excluded_questions"], {"Type_1": 1})
            self.assertEqual(manifest["skipped_excluded_videos"], {"Type_1": 1})


if __name__ == "__main__":
    unittest.main()
