import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sys
from unittest.mock import MagicMock
import os
from pathlib import Path

# Override imports if needed or set env vars before importing app
# But for RECORDINGS_DIR, it's a constant. We can patch it.

from app.db.base import Base, get_db
from app.main import app

# 1. In-Memory Database Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db():
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    # Override the dependency
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    # Reset overrides
    app.dependency_overrides.clear()


@pytest.fixture(scope="function", autouse=True)
def mock_recordings_dir(tmp_path):
    """
    Automatically patch RECORDINGS_DIR in usages to use a temporary directory.
    """
    # Create the temp dir
    (tmp_path / "recordings_data").mkdir(exist_ok=True)
    temp_dir = tmp_path / "recordings_data"

    # We need to patch it in:
    # 1. app.services.recorder
    # 2. app.api.endpoints

    from unittest.mock import patch

    p1 = patch("app.services.recorder.RECORDINGS_DIR", temp_dir)
    p2 = patch("app.api.endpoints.RECORDINGS_DIR", temp_dir)

    p1.start()
    p2.start()

    yield temp_dir

    p1.stop()
    p2.stop()
