import os
import atexit
import pytest
import pytest_asyncio
import asyncio
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Start Postgres container for the test session at module load time
# so that its connection URL overrides settings before any other imports occur.
container = PostgresContainer("postgres:16-alpine")
container.start()

# Stop container at python interpreter exit
atexit.register(container.stop)

# Set environment variables for Settings before importing app modules
raw_url = container.get_connection_url()
parts = raw_url.split("://", 1)
os.environ["DATABASE_URL"] = f"postgresql+asyncpg://{parts[1]}"
os.environ["DATABASE_URL_SYNC"] = f"postgresql://{parts[1]}"
os.environ["ENVIRONMENT"] = "test"

# Import models to register with Base.metadata, then import DB & app configuration
import src.core.models  # noqa: F401
from src.core.database import Base, get_db
import src.core.database
from src.main import app


@pytest.fixture(scope="session", autouse=True)
def init_database():
    """Initialize database tables once for the test session using a separate loop."""
    db_url = f"postgresql+asyncpg://{parts[1]}"

    # Run setup synchronously in a dedicated loop
    loop = asyncio.new_event_loop()
    try:

        async def setup():
            engine = create_async_engine(db_url, echo=False)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            await engine.dispose()

        loop.run_until_complete(setup())
    finally:
        loop.close()

    yield

    # Teardown: drop tables
    loop = asyncio.new_event_loop()
    try:

        async def teardown():
            engine = create_async_engine(db_url, echo=False)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()

        loop.run_until_complete(teardown())
    finally:
        loop.close()


@pytest_asyncio.fixture()
async def test_engine():
    """Create a new async engine for each test to avoid event loop conflicts."""
    db_url = f"postgresql+asyncpg://{parts[1]}"
    engine = create_async_engine(db_url, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_conn(test_engine):
    """Yields a connection that is enrolled in a transaction that gets rolled back."""
    async with test_engine.connect() as conn:
        transaction = await conn.begin()
        yield conn
        await transaction.rollback()


@pytest_asyncio.fixture()
async def db_session(db_conn) -> AsyncSession:
    """AsyncSession with transaction rollback after each test."""
    session_factory = async_sessionmaker(
        bind=db_conn, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
def patch_global_engine(test_engine):
    """Patch src.core.database.engine to use the function-scoped test_engine to prevent loop conflicts on shutdown."""
    orig_engine = src.core.database.engine
    src.core.database.engine = test_engine
    yield
    src.core.database.engine = orig_engine


@pytest_asyncio.fixture()
async def client(db_session):
    """
    FastAPI AsyncClient overriding get_db with our rolled-back session.
    Also suppresses the background scheduler from running during lifespan setup.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Suppress the background scheduler during client startup
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("src.ingestion.scheduler.start_ingestion_scheduler", lambda: None)
        mp.setattr("src.ingestion.scheduler.stop_ingestion_scheduler", lambda: None)

        from httpx import AsyncClient, ASGITransport

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c

    app.dependency_overrides.clear()
