from pathlib import Path
import sys
import unittest

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.tools.run_qwen25_gated_avcrop_groupcv_v1 import (  # noqa: E402
    APPENDED_LOCAL_VIEW_COUNT,
    InferenceProtocolError,
    construct_input_views,
    make_random_crop_specs,
    validate_crop_specs,
)


def base_views():
    frames = [Image.new("RGB", (120, 80), color=(index, 0, 0)) for index in range(32)]
    metadata = [
        {"global_rank": index, "source_frame_index": index * 3}
        for index in range(32)
    ]
    return frames, metadata


def hit_manifest():
    specs = [
        {
            "source_global_rank": index,
            "bbox_norm": [0.1, 0.1, 0.7, 0.7],
            "crop_mode": "fixture",
        }
        for index in range(8)
    ]
    return {
        "question_id": "q1",
        "append_crop8": True,
        "local_view_count": 8,
        "submitted_view_count": 40,
        "clip_crop_specs": specs,
        "av_crop_specs": specs,
    }


class Qwen25GatedAVCropInputTest(unittest.TestCase):
    def test_raw_and_gate_miss_keep_global_views_only(self):
        frames, metadata = base_views()
        raw, raw_plan, _ = construct_input_views(
            method="A_Raw32",
            question_id="q1",
            global_frames=frames,
            global_metadata=metadata,
            unified_size=64,
            gate_record=None,
        )
        self.assertEqual(len(raw), 32)
        self.assertEqual(len(raw_plan), 32)
        self.assertTrue(all(item["view_type"] == "global" for item in raw_plan))

        miss, miss_plan, _ = construct_input_views(
            method="E_Gated_AVCrop8",
            question_id="q1",
            global_frames=frames,
            global_metadata=metadata,
            unified_size=64,
            gate_record={
                "question_id": "q1",
                "append_crop8": False,
                "local_view_count": 0,
                "submitted_view_count": 32,
            },
        )
        self.assertEqual(len(miss), 32)
        self.assertEqual(len(miss_plan), 32)

    def test_all_gated_methods_append_exactly_eight_on_same_gate_hit(self):
        frames, metadata = base_views()
        manifest = hit_manifest()
        for method in (
            "C_Gated_RandomCrop8",
            "D_Gated_CLIPCrop8",
            "E_Gated_AVCrop8",
        ):
            views, plan, _ = construct_input_views(
                method=method,
                question_id="q1",
                global_frames=frames,
                global_metadata=metadata,
                unified_size=64,
                gate_record=manifest,
            )
            self.assertEqual(len(views), 40)
            self.assertEqual(len(plan), 40)
            self.assertEqual(
                sum(item["view_type"] == "local" for item in plan),
                APPENDED_LOCAL_VIEW_COUNT,
            )

    def test_random_crop_specs_are_deterministic(self):
        self.assertEqual(make_random_crop_specs("q1", 8), make_random_crop_specs("q1", 8))
        self.assertNotEqual(make_random_crop_specs("q1", 8), make_random_crop_specs("q2", 8))

    def test_crop_specs_reject_bad_boxes_and_wrong_count(self):
        with self.assertRaisesRegex(InferenceProtocolError, "exactly eight"):
            validate_crop_specs([], "av_crop_specs")
        with self.assertRaisesRegex(InferenceProtocolError, "invalid bbox_norm"):
            validate_crop_specs(
                [
                    {
                        "source_global_rank": index,
                        "bbox_norm": [0.9, 0.1, 0.7, 0.7],
                    }
                    for index in range(8)
                ],
                "av_crop_specs",
            )


if __name__ == "__main__":
    unittest.main()
