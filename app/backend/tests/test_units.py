from services.evaluation import sanitize_links, score_quiz
from services.validation import ValidationError, parse_answers, validate_generate_form


def test_validate_generate_form_accepts_valid_input():
    topic, intensity, length = validate_generate_form(
        "  Python generators  ", "HARD", "7"
    )
    assert topic == "Python generators"
    assert intensity == "hard"
    assert length == 7


def test_validate_generate_form_rejects_short_topic():
    try:
        validate_generate_form("abc", "easy", "5")
    except ValidationError as exc:
        assert "at least" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValidationError")


def test_validate_generate_form_rejects_out_of_range_length():
    for value in ("4", "16", "nope"):
        try:
            validate_generate_form("Python generators", "easy", value)
        except ValidationError:
            continue
        raise AssertionError(f"expected ValidationError for {value}")


def test_parse_answers_requires_every_question():
    from starlette.datastructures import FormData

    form = FormData({"question-1": "2", "question-2": ""})
    try:
        parse_answers(form, 2)
    except ValidationError as exc:
        assert "missing: 2" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValidationError")


def test_parse_answers_rejects_out_of_range_option():
    from starlette.datastructures import FormData

    form = FormData({"question-1": "5"})
    try:
        parse_answers(form, 1)
    except ValidationError:
        return
    raise AssertionError("expected ValidationError")


def test_score_quiz_counts_correct_and_incorrect():
    quiz = {
        "topic": "Testing",
        "questions": [
            {"question": "q1", "options": ["a", "b", "c", "d"], "correct_answer": 1},
            {"question": "q2", "options": ["a", "b", "c", "d"], "correct_answer": 2},
            {"question": "q3", "options": ["a", "b", "c", "d"], "correct_answer": 3},
        ],
    }
    result = score_quiz(quiz, [1, 4, 3])
    assert result["score"] == 67
    assert result["correct_answers_index"] == [1, 3]
    assert result["incorrect_answers_index"] == [2]


def test_sanitize_links_drops_unsafe_schemes():
    links = sanitize_links(
        [
            "https://example.com/docs",
            "javascript:alert(1)",
            "ftp://example.com/file",
            "http://example.com",
            "https://example.com/docs",
        ]
    )
    assert links == ["https://example.com/docs", "http://example.com"]
