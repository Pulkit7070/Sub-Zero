"""Database connection and session management."""

import ssl
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# Convert postgresql:// to postgresql+asyncpg://
database_url = settings.database_url
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Remove sslmode from URL (handled separately for asyncpg)
if "?sslmode=" in database_url:
    database_url = database_url.split("?sslmode=")[0]
elif "&sslmode=" in database_url:
    database_url = database_url.replace("&sslmode=require", "").replace("&sslmode=prefer", "")

# Create SSL context for Supabase
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

engine = create_async_engine(
    database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={"ssl": ssl_context},
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


async def init_db():
    """Initialize database connection."""
    try:
        # Test connection
        async with engine.begin() as conn:
            pass
        print("Database connection established successfully")
    except Exception as e:
        print(f"Warning: Could not connect to database: {e}")
        print("The server will start but database operations will fail.")
        print("Please update DATABASE_URL in .env with valid credentials.")


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
