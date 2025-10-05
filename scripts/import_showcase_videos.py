#!/usr/bin/env python3
"""
Script to import Sora showcase videos from JSON file to database.
Only imports videos with valid prompts (excludes '【视频已删除或无效】').
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.base import get_db_write
from app.models.video_showcase import VideoShowcase
from app.core.config import settings


async def import_videos():
    """Import videos from JSON file to database."""

    # Read JSON file
    json_file_path = Path(__file__).parent.parent.parent / "sora_videos_all.json"

    print(f"📖 Reading JSON file: {json_file_path}")

    if not json_file_path.exists():
        print(f"❌ Error: JSON file not found at {json_file_path}")
        return

    with open(json_file_path, 'r', encoding='utf-8') as f:
        videos_data = json.load(f)

    print(f"📊 Total videos in JSON: {len(videos_data)}")

    # Filter valid videos (exclude deleted/invalid ones)
    valid_videos = [
        video for video in videos_data
        if video.get("提示词") and video["提示词"] != "【视频已删除或无效】"
    ]

    print(f"✅ Valid videos to import: {len(valid_videos)}")
    print(f"❌ Skipped invalid videos: {len(videos_data) - len(valid_videos)}")

    if not valid_videos:
        print("⚠️ No valid videos to import!")
        return

    # Get database session
    async for db in get_db_write():
        try:
            # Check how many videos already exist
            result = await db.execute(select(VideoShowcase))
            existing_videos = result.scalars().all()
            print(f"📦 Existing videos in database: {len(existing_videos)}")

            # Prepare videos for insertion
            inserted_count = 0
            skipped_count = 0

            for idx, video_data in enumerate(valid_videos, 1):
                url = video_data.get("URL", "")
                prompt = video_data.get("提示词", "")

                # Extract video ID from URL
                # Format: https://sora.chatgpt.com/p/s_68dc0a9f62688191aca2f63c9a27caad
                video_id = url.split("/")[-1] if url else ""

                # Check if video already exists by URL
                check_query = select(VideoShowcase).where(VideoShowcase.video_url == url)
                existing = await db.execute(check_query)
                if existing.scalar_one_or_none():
                    skipped_count += 1
                    continue

                # Create showcase video record
                # Note: Since we don't have the actual video file URL, we'll use the Sora page URL
                # Frontend will need to handle this appropriately
                showcase_video = VideoShowcase(
                    prompt=prompt,  # Use prompt from JSON
                    video_url=url,  # Sora page URL (not actual video file)
                    thumbnail_url=None,  # No thumbnail available
                    duration_seconds=5,  # Default 5 seconds (Sora default)
                    view_count=0,
                    display_order=1000 - video_data.get('序号', idx),  # Higher number = higher in list
                    is_active=True
                )

                db.add(showcase_video)
                inserted_count += 1

                # Commit in batches of 50 to avoid long transactions
                if inserted_count % 50 == 0:
                    await db.commit()
                    print(f"💾 Committed batch: {inserted_count}/{len(valid_videos)}")

            # Final commit for remaining videos
            await db.commit()

            print("\n" + "=" * 60)
            print(f"✅ Import completed successfully!")
            print(f"   - Inserted: {inserted_count} videos")
            print(f"   - Skipped (already exists): {skipped_count} videos")
            print(f"   - Total valid videos: {len(valid_videos)}")
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ Error during import: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🎬 Sora Showcase Videos Import Script")
    print("=" * 60 + "\n")

    asyncio.run(import_videos())

    print("\n✨ Done!\n")
