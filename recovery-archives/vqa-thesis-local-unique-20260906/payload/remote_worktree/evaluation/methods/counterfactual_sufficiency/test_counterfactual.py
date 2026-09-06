from PIL import Image

from counterfactual import (
    build_rescue_sequence,
    categorize_question,
    choose_corrected_answer,
    make_visual_counterfactual,
    question_stem,
    select_asr_excerpt,
    should_rescue,
)


def _frames(count=32):
    return [Image.new("RGB", (64, 48), (index, index, index)) for index in range(count)]


def test_question_normalization_and_categories():
    raw = "Voiceover: hello\n\nQuestion:What price is displayed on screen?"
    assert question_stem(raw) == "What price is displayed on screen?"
    assert categorize_question(raw) == "ocr_text"
    assert categorize_question("What does the narrator say?") == "speech_audio"


def test_asr_excerpt_prefers_question_overlap():
    asr = "Dogs run outside. Save fifty percent today. A family eats dinner. Download the app now."
    excerpt = select_asr_excerpt(asr, "What discount is offered?", max_chars=40)
    assert "fifty percent" in excerpt.lower()


def test_counterfactual_preserves_budget_and_size():
    frames = _frames()
    output, trace = make_visual_counterfactual(frames, list(range(32)), destroy_count=4)
    assert len(output) == 32
    assert trace["destroyed_input_indices"] == [28, 29, 30, 31]
    assert all(before.size == after.size for before, after in zip(frames, output))


def test_rescue_is_fixed_budget():
    frames = _frames()

    def cropper(frame, index):
        return frame.crop((8, 8, 56, 40)), {"index": index}

    output, trace = build_rescue_sequence(frames, list(range(32)), cropper, local_count=8)
    assert len(output) == 32
    assert trace["context_count"] == 24
    assert trace["local_count"] == 8
    assert trace["evidence_indices"] == list(range(24, 32))
    assert trace["dropped_indices"] == list(range(8))


def test_rescue_decision_and_conservative_switch():
    rescue, reasons = should_rescue(0.55, 0.20)
    assert rescue and reasons == ["low_positive_support"]
    rescue, reasons = should_rescue(0.80, 0.77)
    assert rescue and reasons == ["counterfactual_insensitive"]
    answer, trace = choose_corrected_answer("a", "b", 0.4, 0.46, switch_margin=0.05)
    assert answer == "b" and trace["switched"]
    answer, trace = choose_corrected_answer("a", "b", 0.4, 0.44, switch_margin=0.05)
    assert answer == "a" and not trace["switched"]
