import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient, ASGITransport
from datetime import date
from uuid import uuid4

from src.infrastructure.database import Base, get_db
from src.api.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_index_page(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "Clarity" in response.text

@pytest.mark.asyncio
async def test_registration(client, db_session):
    response = await client.post(
        "/auth/register",
        data={"name": "Test User", "email": "test@example.com", "password": "testpass123"}
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_protected_route_redirect(client):
    response = await client.get("/dashboard")
    assert response.status_code == 200

@pytest_asyncio.fixture
async def authenticated_client(client, db_session):
    from src.domain.models import User, UserProfile
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"])
    
    user = User(
        id=uuid4(),
        email="auth@example.com",
        hashed_password=pwd_context.hash("password"),
        full_name="Auth User",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    
    profile = UserProfile(user_id=user.id, profile_mode="financial-os")
    db_session.add(profile)
    await db_session.commit()
    
    response = await client.post(
        "/auth/login",
        data={"email": "auth@example.com", "password": "password"}
    )
    
    return client

@pytest.mark.asyncio
async def test_create_account(authenticated_client, db_session):
    response = await authenticated_client.post(
        "/accounts/new",
        data={"name": "Test Checking", "account_type": "checking", "institution": "Test Bank"}
    )
    assert response.status_code == 200
    assert "/accounts" in response.headers.get("location", "")

@pytest.mark.asyncio
async def test_list_accounts_empty(authenticated_client):
    response = await authenticated_client.get("/accounts")
    assert response.status_code == 200
    assert "No accounts" in response.text