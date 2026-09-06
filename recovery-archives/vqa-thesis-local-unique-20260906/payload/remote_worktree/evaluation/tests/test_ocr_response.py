import json

import numpy as np
import pytest

from evaluation.methods.av_evidence.ocr_response import (
    empirical_null_confidence,
    load_ocr_cache,
    load_question_bank,
    normalize_ocr_relevance,
    rasterize_ocr_response,
    validate_ocr_frame_coverage,
    validate_ocr_question_coverage,
)


def test_rasterize_ocr_response_uses_confidence_and_relevance():
    detections = [
        {"text": "GBP 340", "score": 1.0, "bbox_norm": [0.0, 0.0, 0.5, 0.25]},
        {"text": "meter", "score": 0.8, "bbox_norm": [0.5, 0.5, 1.0, 1.0]},
    ]
    response, trace = rasterize_ocr_response(detections, (4, 4), [1.0, 0.0])
    assert response[0, 0] == pytest.approx(1.0)
    assert response[3, 3] == pytest.approx(0.2)
    assert trace["kept_count"] == 2
    assert trace["source_reliability"] == pytest.approx(0.9)


def test_rasterize_ocr_response_rejects_misaligned_scores():
    with pytest.raises(ValueError):
        rasterize_ocr_response([{"score": 1.0, "bbox_norm": [0, 0, 1, 1]}], (2, 2), [])


def test_rasterize_ocr_response_can_weight_source_reliability_by_relevance():
    detections = [
        {"score": 1.0, "bbox_norm": [0.0, 0.0, 0.5, 0.5]},
        {"score": 0.8, "bbox_norm": [0.5, 0.5, 1.0, 1.0]},
    ]
    _, trace = rasterize_ocr_response(
        detections,
        (4, 4),
        [1.0, 0.0],
        source_reliability_mode="weighted",
    )
    assert trace["source_reliability"] == pytest.approx(0.6)
    assert trace["source_reliability_mode"] == "weighted"


def test_normalize_ocr_relevance_competes_across_all_values():
    relevance = normalize_ocr_relevance([0.2, 0.3, 0.6])
    assert relevance.tolist() == pytest.approx([0.0, 0.25, 1.0])
    assert normalize_ocr_relevance([0.4]).tolist() == [1.0]


def test_empirical_null_confidence_is_zero_below_median_and_one_above_bank():
    confidence, percentiles = empirical_null_confidence(
        [0.2, 0.9],
        [[0.1, 0.3, 0.4, 0.5], [0.1, 0.3, 0.4, 0.5]],
    )
    assert percentiles.tolist() == pytest.approx([0.25, 1.0])
    assert confidence.tolist() == pytest.approx([0.0, 1.0])


def test_empirical_null_confidence_rejects_misaligned_bank():
    with pytest.raises(ValueError, match="align"):
        empirical_null_confidence([0.2, 0.3], [[0.1, 0.2]])


def test_load_question_bank_strips_voiceover_prefix(tmp_path):
    path = tmp_path / "train.json"
    path.write_text(
        json.dumps([{"question": "Voiceover: hello\n\nQuestion:What is shown?"}]),
        encoding="utf-8",
    )
    assert load_question_bank(path) == ["What is shown?"]


def test_load_ocr_cache_indexes_sample_rank(tmp_path):
    path = tmp_path / "ocr.json"
    path.write_text(json.dumps({
        "provenance": {"engine": "test"},
        "items": [{
            "question_id": "q1",
            "frames": [{"sample_rank": 7, "detections": [{"text": "hello", "score": 0.9}]}],
        }],
    }), encoding="utf-8")
    cache, provenance = load_ocr_cache(path)
    assert cache["q1"][7][0]["text"] == "hello"
    assert provenance["engine"] == "test"


def test_load_ocr_cache_rejects_duplicate_sample_rank(tmp_path):
    path = tmp_path / "ocr.json"
    path.write_text(json.dumps({
        "items": [{
            "question_id": "q1",
            "frames": [
                {"sample_rank": 7, "detections": []},
                {"sample_rank": 7, "detections": []},
            ],
        }],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate OCR cache sample_rank"):
        load_ocr_cache(path)


def test_validate_ocr_question_coverage_rejects_missing_question():
    with pytest.raises(ValueError, match="missing 1 question"):
        validate_ocr_question_coverage({"q1": {}}, ["q1", "q2"])


def test_validate_ocr_frame_coverage_distinguishes_empty_detections_from_missing_rank():
    validate_ocr_frame_coverage({7: []}, [{"sample_rank": 7}])
    with pytest.raises(ValueError, match="sample_rank"):
        validate_ocr_frame_coverage({7: []}, [{"sample_rank": 8}])
