"""Pytest configuration: async fixtures for DB, app, auth.

Run tests with:
    docker exec crm_backend pytest tests/ -v
"""
import os
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

# Use a SEPARATE test DB to not pollute production data
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://crm:crm@postgres:5432/crm_test_db",
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database and run migrations once per test session."""
    # Create test DB if missing (connect to default db first)
    from sqlalchemy import create_engine
    sync_url = TEST_DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2") \
                                  .replace("/crm_test_db", "/postgres")
    try:
        sync_engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")
        with sync_engine.connect() as conn:
            conn.execute(text("DROP DATABASE IF EXISTS crm_test_db"))
            conn.execute(text("CREATE DATABASE crm_test_db"))
        sync_engine.dispose()
    except Exception as e:
        print(f"Test DB setup warning: {e}")

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Apply all migrations
    from app.db.session import Base
    from app.models import *  # register models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Seed default company
        await conn.execute(text("""
            INSERT INTO companies (id, name, slug, tariff, max_users, max_debtors, is_active, created_at, updated_at)
            VALUES (1, 'Test Company A', 'test-a', 'enterprise', 100, 100000, true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """))
        await conn.execute(text("""
            INSERT INTO companies (id, name, slug, tariff, max_users, max_debtors, is_active, created_at, updated_at)
            VALUES (2, 'Test Company B', 'test-b', 'pro', 10, 10000, true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """))
        await conn.execute(text("SELECT setval('companies_id_seq', (SELECT MAX(id) FROM companies))"))

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    """Fresh DB session per test, rolled back at end."""
    AsyncSessionLocal = async_sessionmaker(
        test_engine, expire_on_commit=False, autoflush=False
    )
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(test_engine):
    """HTTP client targeting our FastAPI app, with test DB injected"""
    # Override DB dependency
    from main import app
    from app.db.session import get_db
    AsyncSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with AsyncSessionLocal() as s:
            yield s
            await s.commit()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_a_token(db_session):
    """Create admin user in company A and return JWT token"""
    import bcrypt
    from sqlalchemy import select
    from app.models import User
    from app.core.security import create_access_token

    h = bcrypt.hashpw(b"Test1234!", bcrypt.gensalt(4)).decode()
    existing = (await db_session.execute(
        select(User).where(User.email == "admin-a@test.local")
    )).scalar_one_or_none()
    if not existing:
        user = User(
            email="admin-a@test.local", full_name="Admin A",
            hashed_password=h, role="ADMIN", is_active=True, company_id=1,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
    else:
        user = existing
    return create_access_token({"sub": str(user.id), "type": "access"}), user.id


@pytest_asyncio.fixture
async def admin_b_token(db_session):
    """Create admin user in company B and return JWT token"""
    import bcrypt
    from sqlalchemy import select
    from app.models import User
    from app.core.security import create_access_token

    h = bcrypt.hashpw(b"Test1234!", bcrypt.gensalt(4)).decode()
    existing = (await db_session.execute(
        select(User).where(User.email == "admin-b@test.local")
    )).scalar_one_or_none()
    if not existing:
        user = User(
            email="admin-b@test.local", full_name="Admin B",
            hashed_password=h, role="ADMIN", is_active=True, company_id=2,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
    else:
        user = existing
    return create_access_token({"sub": str(user.id), "type": "access"}), user.id
