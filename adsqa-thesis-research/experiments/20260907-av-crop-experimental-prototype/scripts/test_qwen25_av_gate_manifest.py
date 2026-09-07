from pathlib import Path
import sys
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.tools.build_qwen25_av_gate_manifest_v1 import normalized_crop_box  # noqa: E402


class Qwen25AVGateManifestTest(unittest.TestCase):
    def test_normalized_crop_box_uses_fixed_valid_scale(self):
        response = np.zeros((4, 4), dtype=np.float32)
        response[3, 3] = 1.0
        box = normalized_crop_box(response, 0.60)
        self.assertEqual(len(box), 4)
        self.assertGreaterEqual(box[0], 0.0)
        self.assertGreaterEqual(box[1], 0.0)
        self.assertLessEqual(box[2], 1.0)
        self.assertLessEqual(box[3], 1.0)
        self.assertAlmostEqual(box[2] - box[0], 0.60)
        self.assertAlmostEqual(box[3] - box[1], 0.60)

    def test_flat_response_uses_centered_crop(self):
        box = normalized_crop_box(np.zeros((4, 4), dtype=np.float32), 0.60)
        self.assertAlmostEqual(box[0], 0.20)
        self.assertAlmostEqual(box[1], 0.20)
        self.assertAlmostEqual(box[2], 0.80)
        self.assertAlmostEqual(box[3], 0.80)


if __name__ == "__main__":
    unittest.main()
