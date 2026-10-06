import os
import tempfile

# Importlardan OLDIN: testlar alohida SQLite bazada ishlaydi
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
# Mavjud testlar login talab qilmaydi; test_auth.py buni o'zi yoqadi
os.environ["AUTH_DISABLED"] = "1"
os.environ["SECRET_KEY"] = "test-secret-key-test-secret-key-123456"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestClient(app)
