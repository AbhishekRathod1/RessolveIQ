from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import get_db
from app.main import app


@pytest.fixture
def test_session_factory(
    tmp_path, monkeypatch
) -> Generator[sessionmaker[Session], None, None]:
    database_path = tmp_path / "test_resolveiq.db"
    test_engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    test_session_factory = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    def override_get_db() -> Generator[Session, None, None]:
        database = test_session_factory()
        try:
            yield database
        finally:
            database.close()

    monkeypatch.setattr("app.main.engine", test_engine)
    app.dependency_overrides[get_db] = override_get_db
    yield test_session_factory
    app.dependency_overrides.pop(get_db, None)
    test_engine.dispose()


@pytest.fixture
def client(
    test_session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
