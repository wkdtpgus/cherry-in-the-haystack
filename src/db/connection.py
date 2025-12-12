"""Database connection management.

Supports both SQLite (local dev/testing) and PostgreSQL (production).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

from src.db.models import Base

# Load environment variables
load_dotenv()


def get_database_url() -> str:
    """Get database URL from environment or use SQLite default."""
    db_url = os.getenv("DATABASE_URL")

    if db_url:
        return db_url

    # Default to SQLite for local development
    sqlite_path = os.path.join(os.getcwd(), "local_dev.db")
    return f"sqlite:///{sqlite_path}"


def create_db_engine(echo: bool = False):
    """Create SQLAlchemy engine.

    Args:
        echo: If True, log all SQL statements

    Returns:
        SQLAlchemy Engine
    """
    url = get_database_url()

    # PostgreSQL-specific settings
    if url.startswith("postgresql"):
        return create_engine(
            url,
            echo=echo,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # Verify connections before using
        )

    # SQLite settings
    return create_engine(
        url,
        echo=echo,
        connect_args={"check_same_thread": False},  # SQLite only
    )


def get_session_maker(engine=None) -> sessionmaker:
    """Get sessionmaker for creating database sessions.

    Args:
        engine: SQLAlchemy engine (creates new one if None)

    Returns:
        Configured sessionmaker
    """
    if engine is None:
        engine = create_db_engine()

    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db(engine=None) -> None:
    """Initialize database (create all tables).

    Args:
        engine: SQLAlchemy engine (creates new one if None)
    """
    if engine is None:
        engine = create_db_engine()

    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """Get a new database session.

    Usage:
        with get_session() as session:
            # do database operations
            session.commit()
    """
    SessionLocal = get_session_maker()
    return SessionLocal()
