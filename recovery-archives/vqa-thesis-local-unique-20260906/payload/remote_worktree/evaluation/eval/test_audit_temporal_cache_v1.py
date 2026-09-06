import unittest
from unittest.mock import patch

from audit_temporal_cache_v1 import expected_source_indices, uniform_ranks


class TemporalAuditSamplingTest(unittest.TestCase):
    def test_uniform_ranks_match_numpy_floor_sampling(self):
        self.assertEqual(uniform_ranks(64, 32), [int(value) for value in __import__("numpy").linspace(0, 63, 32)])

    @patch("decord.VideoReader")
    def test_source_indices_match_builder_linspace(self, reader):
        reader.return_value.__len__.return_value = 1414
        result = expected_source_indices("unused.mp4", 64, 32)
        raw = [int(value) for value in __import__("numpy").linspace(0, 1413, 32)]
        self.assertEqual(len(result), 64)
        self.assertTrue(set(raw).issubset(result))


if __name__ == "__main__":
    unittest.main()
