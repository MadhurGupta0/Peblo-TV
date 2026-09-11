import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.enums import PublishStatus, UserRole
from app.models.season import Season
from app.models.show import Show
from app.models.user import User

EDITOR_PASSWORD = "editor-pass-123"
ADMIN_PASSWORD = "admin-pass-123"


@pytest.fixture(scope="session")
def engine():
    settings = get_settings()
    eng = create_engine(settings.database_url, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture(scope="session")
def SessionFactory(engine):
    return sessionmaker(bind=engine, future=True)


@pytest.fixture
def db_session(engine, SessionFactory):
    session = SessionFactory()
    yield session
    session.close()
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture(autouse=True)
def _reset_catalog_cache():
    # catalog_cache is a module-level singleton (by design — it's the real in-memory cache
    # GET /catalog reads from). Without resetting it, a publish in one test would leak into
    # the next test expecting a fresh/empty catalogue.
    from app.services.catalog_cache import catalog_cache

    catalog_cache.set(None)
    yield
    catalog_cache.set(None)


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def editor_user(db_session):
    user = User(email="editor@test.local", hashed_password=hash_password(EDITOR_PASSWORD), role=UserRole.editor)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session):
    user = User(email="admin@test.local", hashed_password=hash_password(ADMIN_PASSWORD), role=UserRole.admin)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def show(db_session):
    s = Show(slug="test-show", title="Test Show", section="series", categories=["stories"], status=PublishStatus.draft)
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


@pytest.fixture
def season(db_session, show):
    s = Season(show_id=show.id, season_number=1, title=None)
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


def auth_header(client: TestClient, email: str, password: str) -> dict:
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
