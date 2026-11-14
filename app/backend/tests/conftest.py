import os
import tempfile

# Configure the app before it is imported anywhere else.
_TMP_DIR = tempfile.mkdtemp(prefix="ai-quiz-tests-")
os.environ["DATABASE_PATH"] = os.path.join(_TMP_DIR, "test.db")
os.environ["GROQ_API_KEY"] = "test-key"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["ENVIRONMENT"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from db import init_db  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture()
def client():
    init_db()
    with TestClient(app) as test_client:
        yield test_client
