"""
Pytest configuration and shared fixtures for backend tests.
Uses an in-memory SQLite database for test isolation.
"""
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.subscription import Subscription
from app.models.user import User
from app.utils.enums import SubscriptionPlan, UserRole

# In-memory SQLite for tests — isolated per test session
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh database session for each test, rolled back after."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with overridden database dependency."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def regular_user(db_session: AsyncSession) -> User:
    """Create a regular test user with trial subscription."""
    from datetime import datetime, timedelta, timezone

    user = User(
        email="testuser@example.com",
        hashed_password=hash_password("testpassword123"),
        name="Test User",
        role=UserRole.USER,
        is_active=True,
        email_confirmed=True,
    )
    db_session.add(user)
    await db_session.flush()

    subscription = Subscription(
        user_id=user.id,
        plan=SubscriptionPlan.TRIAL,
        is_active=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(subscription)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin test user with Pro subscription."""
    user = User(
        email="admin@example.com",
        hashed_password=hash_password("adminpassword123"),
        name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        email_confirmed=True,
    )
    db_session.add(user)
    await db_session.flush()

    subscription = Subscription(
        user_id=user.id,
        plan=SubscriptionPlan.PRO,
        is_active=True,
        expires_at=None,
    )
    db_session.add(subscription)
    await db_session.flush()
    return user


async def get_auth_headers(client: AsyncClient, email: str, password: str) -> dict:
    """Helper to login and return Authorization headers."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
