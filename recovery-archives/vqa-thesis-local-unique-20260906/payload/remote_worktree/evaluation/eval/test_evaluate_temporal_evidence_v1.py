import unittest

from evaluate_temporal_evidence_v1 import selection_metrics


class TemporalEvidenceMetricsTest(unittest.TestCase):
    def test_hits_interval_and_reports_coverage(self):
        result = selection_metrics(
            [0, 25, 50, 75, 99],
            frame_count=100,
            fps=10.0,
            units=[{"modalities": ["visual"], "intervals_sec": [[4.9, 5.1]]}],
            tolerance=0.0,
            coverage_bins=4,
        )
        self.assertEqual(result["visual_unit_hits"], [True])
        self.assertEqual(result["covered_bins"], 4)
        self.assertEqual(result["unique_frame_count"], 5)

    def test_audio_only_unit_is_not_scored_as_visual(self):
        result = selection_metrics(
            [0, 99],
            frame_count=100,
            fps=10.0,
            units=[{"modalities": ["audio"], "intervals_sec": [[0.0, 9.9]]}],
            tolerance=0.5,
            coverage_bins=2,
        )
        self.assertEqual(result["visual_units"], 0)
        self.assertEqual(result["visual_unit_hits"], [])


if __name__ == "__main__":
    unittest.main()
