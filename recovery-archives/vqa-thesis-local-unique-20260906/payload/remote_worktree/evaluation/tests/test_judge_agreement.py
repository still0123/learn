from __future__ import annotations

import pytest

from evaluation.eval.analyze_judge_agreement import calibration_gate


def payload(*, exact: float, mad: float, left_delta: float, right_delta: float):
    return {
        "pooled": {
            "exact_rate": exact,
            "weighted_mean_absolute_difference": mad,
        },
        "pairwise_method_ranking": {
            "mean_delta_left": left_delta,
            "mean_delta_right": right_delta,
        },
    }


def test_calibration_gate_accepts_threshold_boundary_and_matching_direction():
    gate = calibration_gate(
        payload(exact=0.80, mad=0.10, left_delta=-0.02, right_delta=-0.01),
        0.80,
        0.10,
        True,
    )

    assert gate is not None
    assert gate["passed"] is True
    assert all(gate["checks"].values())


@pytest.mark.parametrize(
    ("exact", "mad", "right_delta", "failed_check"),
    [
        (0.79, 0.10, -0.01, "pooled_exact_rate"),
        (0.80, 0.11, -0.01, "pooled_mean_absolute_difference"),
        (0.80, 0.10, 0.01, "pair_mean_sign_match"),
    ],
)
def test_calibration_gate_rejects_each_failure(exact, mad, right_delta, failed_check):
    gate = calibration_gate(
        payload(exact=exact, mad=mad, left_delta=-0.02, right_delta=right_delta),
        0.80,
        0.10,
        True,
    )

    assert gate is not None
    assert gate["passed"] is False
    assert gate["checks"][failed_check] is False


def test_calibration_gate_requires_pairwise_payload_for_direction_check():
    with pytest.raises(ValueError, match="requires --pair"):
        calibration_gate(
            {"pooled": {"exact_rate": 1.0, "weighted_mean_absolute_difference": 0.0}},
            0.80,
            0.10,
            True,
        )
