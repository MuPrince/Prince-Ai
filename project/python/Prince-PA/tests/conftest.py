import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.entities import Base


def _make_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False, class_=Session
    )
    settings.data_dir = tmp_path / "data"
    return session_factory


@pytest.fixture()
def db_session(tmp_path) -> Session:
    session_factory = _make_session(tmp_path)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(tmp_path):
    session_factory = _make_session(tmp_path)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
