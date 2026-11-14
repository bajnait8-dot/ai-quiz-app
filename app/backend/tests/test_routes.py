from db import get_evaluation, save_evaluation, save_quiz

from tests.helpers import csrf_token, quiz_payload


def test_dashboard_renders_intro(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Create interactive quizzes" in response.text
    assert 'id="generate-form"' in response.text
    assert "content-security-policy" in response.headers


def test_generate_quiz_returns_quiz_fragment(client, monkeypatch):
    import routers.quiz as quiz_router

    async def fake_generate(topic, intensity, length):
        payload = quiz_payload("generated-quiz")
        payload.update(topic=topic, intensity=intensity, length=length)
        return payload

    monkeypatch.setattr(quiz_router, "generate_quiz", fake_generate)

    token = csrf_token(client)
    response = client.post(
        "/generate-quiz",
        data={
            "csrf_token": token,
            "topic": "Python testing fundamentals",
            "intensity": "easy",
            "length": "5",
        },
    )

    assert response.status_code == 200
    assert response.headers["hx-push-url"] == "/quiz/generated-quiz"
    assert "Check Score" in response.text
    assert "Python testing fundamentals" in response.text


def test_generate_quiz_validation_error_keeps_intro(client):
    token = csrf_token(client)
    response = client.post(
        "/generate-quiz",
        data={
            "csrf_token": token,
            "topic": "abc",
            "intensity": "easy",
            "length": "5",
        },
    )

    assert response.status_code == 200
    assert "at least" in response.text
    assert "Create interactive quizzes" in response.text


def test_generate_quiz_rejects_bad_csrf(client):
    response = client.post(
        "/generate-quiz",
        data={
            "csrf_token": "wrong-token",
            "topic": "Python testing fundamentals",
            "intensity": "easy",
            "length": "5",
        },
    )
    assert response.status_code == 200
    assert "session expired" in response.text


def test_evaluate_quiz_renders_results(client, monkeypatch):
    quiz = quiz_payload("eval-quiz")
    save_quiz(quiz)

    import routers.quiz as quiz_router

    async def fake_evaluate(quiz_data, selected_options):
        return {
            "topic": quiz_data["topic"],
            "score": 50,
            "correct_answers_index": [1],
            "incorrect_answers_index": [2],
            "improvement_tips": "Review fixtures and keep practising.",
            "links": ["https://example.com/pytest"],
            "selected_options": selected_options,
        }

    monkeypatch.setattr(quiz_router, "build_evaluation", fake_evaluate)

    token = csrf_token(client)
    response = client.post(
        "/quiz/eval-quiz/evaluate",
        data={
            "csrf_token": token,
            "question-1": "1",
            "question-2": "2",
        },
    )

    assert response.status_code == 200
    assert "Score: 50%" in response.text
    assert "Correct: 1" in response.text
    assert "Incorrect: 1" in response.text
    assert "Review fixtures" in response.text


def test_evaluate_quiz_requires_all_answers(client):
    save_quiz(quiz_payload("missing-answers"))
    token = csrf_token(client)
    response = client.post(
        "/quiz/missing-answers/evaluate",
        data={"csrf_token": token, "question-1": "1"},
    )

    assert response.status_code == 200
    assert response.headers["hx-retarget"] == "#quiz-error"
    assert "missing: 2" in response.text


def test_share_page_shows_saved_evaluation(client):
    save_quiz(quiz_payload("share-quiz"))
    save_evaluation(
        "share-quiz",
        {
            "topic": "Python testing fundamentals",
            "score": 100,
            "correct_answers_index": [1, 2],
            "incorrect_answers_index": [],
            "improvement_tips": "Perfect score.",
            "links": ["https://example.com/pytest"],
            "selected_options": [1, 1],
        },
    )

    response = client.get("/quiz/share-quiz")
    assert response.status_code == 200
    assert "Score: 100%" in response.text
    assert "Perfect score." in response.text


def test_retry_clears_saved_evaluation(client):
    save_quiz(quiz_payload("retry-quiz"))
    save_evaluation(
        "retry-quiz",
        {
            "topic": "Python testing fundamentals",
            "score": 50,
            "correct_answers_index": [1],
            "incorrect_answers_index": [2],
            "improvement_tips": "Review fixtures.",
            "links": [],
            "selected_options": [1, 2],
        },
    )

    token = csrf_token(client)
    response = client.post("/quiz/retry-quiz/retry", data={"csrf_token": token})

    assert response.status_code == 200
    assert "Check Score" in response.text
    assert "Quiz Results" not in response.text
    assert response.headers["hx-push-url"] == "/quiz/retry-quiz"
    assert get_evaluation("retry-quiz") is None


def test_retry_rejects_bad_csrf(client):
    save_quiz(quiz_payload("retry-csrf"))
    save_evaluation(
        "retry-csrf",
        {
            "topic": "Python testing fundamentals",
            "score": 50,
            "correct_answers_index": [1],
            "incorrect_answers_index": [2],
            "improvement_tips": "Review fixtures.",
            "links": [],
            "selected_options": [1, 2],
        },
    )

    response = client.post(
        "/quiz/retry-csrf/retry", data={"csrf_token": "wrong-token"}
    )

    assert response.status_code == 200
    assert response.headers["hx-retarget"] == "#quiz-error"
    assert "session expired" in response.text
    assert get_evaluation("retry-csrf") is not None


def test_print_page_renders_blank_paper_quiz(client):
    save_quiz(quiz_payload("print-quiz"))
    save_evaluation(
        "print-quiz",
        {
            "topic": "Python testing fundamentals",
            "score": 50,
            "correct_answers_index": [1],
            "incorrect_answers_index": [2],
            "improvement_tips": "Review fixtures.",
            "links": [],
            "selected_options": [1, 2],
        },
    )

    response = client.get("/quiz/print-quiz/print")

    assert response.status_code == 200
    assert "Python testing fundamentals" in response.text
    assert "Which tool runs Python tests?" in response.text
    assert "A)" in response.text
    assert "B)" in response.text
    assert "pytest" in response.text
    assert "Name:" in response.text
    assert "Circle the letter" in response.text
    # The printout is always blank, even when the interactive quiz was solved.
    assert "Score:" not in response.text
    assert "Quiz Results" not in response.text
    assert "pytest is the standard Python test runner." not in response.text
    assert "checked" not in response.text


def test_print_page_unknown_quiz_returns_404(client):
    response = client.get("/quiz/does-not-exist/print")
    assert response.status_code == 404
    assert "Quiz not found" in response.text


def test_unknown_quiz_returns_404_page(client):
    response = client.get("/quiz/does-not-exist")
    assert response.status_code == 404
    assert "Quiz not found" in response.text


def test_health_endpoints(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/health/ready").json()["status"] == "ready"
