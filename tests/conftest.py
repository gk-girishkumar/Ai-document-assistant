"""Shared test fixtures for unit and integration testing."""

import asyncio
import os
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.compiler import compiles
from pgvector.sqlalchemy import Vector

# Compile Vector as TEXT for SQLite test database
@compiles(Vector, "sqlite")
def compile_vector_sqlite(type_, compiler, **kw):
    return "TEXT"

from doc_assistant.app.core.database import Base, get_db
from doc_assistant.app.main import app
from doc_assistant.app.models.user import User
from doc_assistant.app.core.security import hash_password, create_access_token

# Test SQLite in-memory database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """Create session-wide event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create clean in-memory SQLite engine for each test function."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncSession:
    """Async session fixture connected to test SQLite database."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session

@pytest_asyncio.fixture(scope="function")
async def client(test_engine, db_session) -> AsyncClient:
    """HTTPX AsyncClient overriding get_db dependency."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> tuple[User, str]:
    """Create test user 1 and return (User, bearer_token)."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="testuser@example.com",
        hashed_password=hash_password("StrongP@ssw0rd!"),
        role="user",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(user.id, {"role": user.role})
    return user, token

@pytest_asyncio.fixture
async def test_user_2(db_session: AsyncSession) -> tuple[User, str]:
    """Create second test user for cross-user isolation verification."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="otheruser@example.com",
        hashed_password=hash_password("OtherP@ssw0rd!"),
        role="user",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(user.id, {"role": user.role})
    return user, token
