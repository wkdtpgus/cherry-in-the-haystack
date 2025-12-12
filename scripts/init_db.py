"""Initialize database schema.

Creates all tables defined in SQLAlchemy models.
Use this script for local SQLite setup or initial PostgreSQL schema creation.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.connection import create_db_engine, get_database_url, init_db


def main():
    """Initialize database tables."""
    print("🔧 Initializing database...")

    db_url = get_database_url()
    print(f"📍 Database URL: {db_url}")

    engine = create_db_engine(echo=True)

    print("\n📦 Creating tables...")
    init_db(engine)

    print("\n✅ Database initialized successfully!")
    print("\nCreated tables:")
    print("  - books")
    print("  - paragraph_chunks")
    print("  - idea_groups")
    print("  - key_ideas")
    print("  - processing_progress")


if __name__ == "__main__":
    main()
