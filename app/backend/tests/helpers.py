import re

from fastapi.testclient import TestClient


def csrf_token(client: TestClient) -> str:
    response = client.get("/")
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match, "CSRF token not found on the dashboard"
    return match.group(1)


def quiz_payload(quiz_id: str = "quiz-1", answer: int = 1) -> dict:
    return {
        "quiz_id": quiz_id,
        "topic": "Python testing fundamentals",
        "intensity": "easy",
        "length": 2,
        "questions": [
            {
                "question": "Which tool runs Python tests?",
                "options": ["pytest", "npm", "cargo", "make"],
                "correct_answer": answer,
                "short_explanation": "pytest is the standard Python test runner.",
            },
            {
                "question": "What is a fixture?",
                "options": ["A setup helper", "A CSS rule", "A database", "A syntax error"],
                "correct_answer": 1,
                "short_explanation": "Fixtures prepare state for tests.",
            },
        ],
        "related_topics": [
            "Pytest Fundamentals",
            "Test Fixtures Explained",
            "Mocking In Python",
        ],
    }
