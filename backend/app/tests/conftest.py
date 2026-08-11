import os
import uuid

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_NAME = "troubleshoot_test"

_default_sync = os.environ.get(
    "DATABASE_URL_SYNC", "postgresql+psycopg://app:app@localhost:5432/troubleshoot"
)
_default_async = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5432/troubleshoot"
)
ADMIN_URL_SYNC = f"{_default_sync.rsplit('/', 1)[0]}/postgres"
TEST_URL_SYNC = f"{_default_sync.rsplit('/', 1)[0]}/{TEST_DB_NAME}"
TEST_URL_ASYNC = f"{_default_async.rsplit('/', 1)[0]}/{TEST_DB_NAME}"

# Point the whole app at the test database before app.config (and anything
# that imports it, e.g. app.db.engine's module-level engine used by the API
# routes under test in test_auth.py) is ever imported, so API requests in
# tests hit troubleshoot_test rather than the dev database.
os.environ["DATABASE_URL_SYNC"] = TEST_URL_SYNC
os.environ["DATABASE_URL"] = TEST_URL_ASYNC

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()
get_settings()

from app.core.security import hash_password  # noqa: E402
from app.db.enums import UserRole  # noqa: E402
from app.db.models import User  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _test_database():
    """Create a throwaway test database and run the real Alembic migration
    against it, so tests exercise the exact schema (enums, triggers, the
    ticket-number function) rather than a SQLAlchemy create_all() shortcut.
    """
    admin_engine = create_engine(ADMIN_URL_SYNC, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_URL_SYNC)
    command.upgrade(alembic_cfg, "head")

    yield

    admin_engine = create_engine(ADMIN_URL_SYNC, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)'))
    admin_engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_URL_ASYNC)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_headers(client, db_session):
    """A fresh admin user + a logged-in Authorization header, for tests that
    exercise admin-gated endpoints (routes_admin, and the write paths of
    routes_assets/routes_qr).
    """
    email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
    password = "s3cret-pass"
    user = User(
        email=email,
        full_name="Test Admin",
        role=UserRole.admin,
        password_hash=hash_password(password),
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post("/auth/login", json={"email": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
