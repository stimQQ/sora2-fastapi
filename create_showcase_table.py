#!/usr/bin/env python3
"""Create video_showcases table manually."""

import asyncio
import asyncpg
import os

async def create_table():
    # Get DATABASE_URL from environment
    db_url = os.getenv("DATABASE_URL", "")

    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return

    # Convert SQLAlchemy URL to asyncpg URL
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    print(f"Connecting to database...")
    conn = await asyncpg.connect(db_url)

    try:
        print("Creating video_showcases table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS video_showcases (
                id SERIAL PRIMARY KEY,
                video_url VARCHAR(500) NOT NULL,
                prompt TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT true,
                display_order INTEGER NOT NULL DEFAULT 0,
                thumbnail_url VARCHAR(500),
                duration_seconds INTEGER,
                view_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """)

        print("Creating indexes...")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_video_showcases_id ON video_showcases(id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_video_showcases_is_active ON video_showcases(is_active)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_video_showcases_display_order ON video_showcases(display_order)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_video_showcases_created_at ON video_showcases(created_at)")

        print("✅ video_showcases table created successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    asyncio.run(create_table())
