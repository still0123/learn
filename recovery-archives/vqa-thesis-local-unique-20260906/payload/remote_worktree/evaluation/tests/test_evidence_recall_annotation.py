import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "eval" / "build_evidence_recall_annotation_pack.py"
SPEC = importlib.util.spec_from_file_location("evidence_recall", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EvidenceRecallTest(unittest.TestCase):
    def test_temporal_and_region_recall(self):
        rows = [{
            "question_id": "q1",
            "annotation_status": "complete",
            "evidence_observability": "visual",
            "evidence_units": [{
                "id": "u1",
                "modalities": ["visual"],
                "intervals_sec": [[4.0, 6.0]],
                "bbox_norm": [0.2, 0.2, 0.4, 0.4],
                "required": True,
            }],
        }]
        evidence = {
            "hit": {"q1": {
                "selected_frames": [{"timestamp_sec": 5.0}],
                "selected_local_views": [{"timestamp_sec": 5.0, "bbox_norm": [0.1, 0.1, 0.5, 0.5]}],
            }},
            "miss": {"q1": {
                "selected_frames": [{"timestamp_sec": 8.0}],
                "selected_local_views": [{"timestamp_sec": 8.0, "bbox_norm": [0.1, 0.1, 0.5, 0.5]}],
            }},
        }
        metadata = {"q1": {"fps": 25.0}}
        summary, details = MODULE.score_annotations(rows, evidence, metadata, tolerance=0.0)
        self.assertEqual(summary["hit"]["evidence_unit_recall"], 1.0)
        self.assertEqual(summary["hit"]["visual_evidence_recall"], 1.0)
        self.assertEqual(summary["hit"]["region_recall"], 1.0)
        self.assertEqual(summary["miss"]["evidence_unit_recall"], 0.0)
        self.assertEqual(summary["miss"]["visual_evidence_recall"], 0.0)
        self.assertEqual(details[0]["methods"]["miss"]["unit_hits"], [False])

    def test_metadata_only_is_excluded(self):
        rows = [{
            "question_id": "q1",
            "annotation_status": "complete",
            "evidence_observability": "metadata_only",
            "evidence_units": [{"modalities": ["visual"], "intervals_sec": [[0, 1]]}],
        }]
        summary, details = MODULE.score_annotations(rows, {"method": {"q1": {}}}, {"q1": {"fps": 25}}, 0.5)
        self.assertEqual(summary["method"]["eligible"], 0)
        self.assertEqual(details, [])

    def test_embedded_focus_is_not_counted_as_an_extra_input_view(self):
        rows = [{
            "question_id": "q1",
            "annotation_status": "complete",
            "evidence_observability": "visual",
            "evidence_units": [{
                "modalities": ["visual"],
                "intervals_sec": [[4.0, 6.0]],
                "bbox_norm": [0.2, 0.2, 0.4, 0.4],
            }],
        }]
        evidence = {"focus": {"q1": {
            "selected_frames": [{"timestamp_sec": 5.0}],
            "selected_local_views": [{
                "timestamp_sec": 5.0,
                "bbox_norm": [0.1, 0.1, 0.5, 0.5],
                "submission_mode": "embedded_focus_context",
            }],
        }}}
        summary, details = MODULE.score_annotations(rows, evidence, {"q1": {"fps": 25}}, 0.0)
        self.assertEqual(summary["focus"]["region_recall"], 1.0)
        self.assertEqual(summary["focus"]["input_views"], 1)
        self.assertEqual(details[0]["methods"]["focus"]["input_view_count"], 1)


if __name__ == "__main__":
    unittest.main()
