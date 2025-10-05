#!/usr/bin/env python3
"""
Script to download Sora videos from chatgpt.com and upload to Aliyun OSS.
Maintains the database ID to ensure prompt-video correspondence.
"""

import asyncio
import sys
import os
from pathlib import Path
import httpx
from io import BytesIO
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from app.db.base import get_db_write
from app.models.video_showcase import VideoShowcase
from app.services.storage.factory import get_storage_provider


async def extract_video_url_from_page(page_url: str) -> str:
    """
    Extract actual video URL from Sora page.
    The page contains a <video> tag with the actual .mp4 URL.
    """
    # Mimic browser headers to avoid 403
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
        try:
            response = await client.get(page_url)
            response.raise_for_status()
            html = response.text

            # Look for video URL in HTML
            # Typical pattern: <video src="https://.../*.mp4" or similar
            import re

            # Try multiple patterns
            patterns = [
                r'<video[^>]+src="([^"]+\.mp4[^"]*)"',
                r'<source[^>]+src="([^"]+\.mp4[^"]*)"',
                r'"videoUrl":"([^"]+\.mp4[^"]*)"',
                r'"url":"([^"]+\.mp4[^"]*)"',
                r'https://[^\s"]+\.mp4[^\s"]*',  # Any .mp4 URL
            ]

            for pattern in patterns:
                match = re.search(pattern, html)
                if match:
                    if pattern.startswith('http'):
                        video_url = match.group(0)
                    else:
                        video_url = match.group(1)
                    # Unescape if needed
                    video_url = video_url.replace('\\/', '/')
                    return video_url

            return None

        except Exception as e:
            print(f"  ❌ Error extracting video URL: {e}")
            return None


async def download_video(video_url: str) -> bytes:
    """Download video file from URL."""
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        try:
            response = await client.get(video_url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"  ❌ Download error: {e}")
            return None


async def upload_to_oss(video_content: bytes, video_id: int) -> str:
    """
    Upload video to Aliyun OSS.
    Use video_id for filename to maintain correspondence with database.
    """
    try:
        storage_provider = get_storage_provider()

        # Create storage key using video ID
        # Format: showcase/videos/001.mp4, 002.mp4, etc.
        storage_key = f"showcase/videos/{video_id:03d}.mp4"

        # Create BytesIO object
        file_obj = BytesIO(video_content)

        # Upload
        oss_url = await storage_provider.upload_file(
            file=file_obj,
            key=storage_key,
            content_type="video/mp4",
            metadata={
                "video_id": str(video_id),
                "source": "sora_chatgpt",
                "uploaded_at": datetime.utcnow().isoformat()
            }
        )

        return oss_url

    except Exception as e:
        print(f"  ❌ Upload error: {e}")
        return None


async def process_videos(start_id: int = None, end_id: int = None, limit: int = None):
    """
    Process videos: download from Sora and upload to OSS.

    Args:
        start_id: Start from this video ID (optional)
        end_id: End at this video ID (optional)
        limit: Process only this many videos (optional)
    """

    async for db in get_db_write():
        try:
            # Build query
            query = select(VideoShowcase).where(
                VideoShowcase.video_url.like('%sora.chatgpt.com%')
            ).order_by(VideoShowcase.id)

            # Apply filters
            if start_id:
                query = query.where(VideoShowcase.id >= start_id)
            if end_id:
                query = query.where(VideoShowcase.id <= end_id)
            if limit:
                query = query.limit(limit)

            result = await db.execute(query)
            videos = result.scalars().all()

            total = len(videos)
            print(f"\n📊 Found {total} videos to process")

            if total == 0:
                print("⚠️ No videos to process!")
                return

            print(f"📝 ID range: {videos[0].id} - {videos[-1].id}")
            print("=" * 70)

            success_count = 0
            failed_count = 0
            skipped_count = 0

            for idx, video in enumerate(videos, 1):
                print(f"\n[{idx}/{total}] Processing Video ID: {video.id}")
                print(f"  Prompt: {video.prompt[:60]}...")
                print(f"  Sora URL: {video.video_url}")

                try:
                    # Step 1: Extract actual video URL from Sora page
                    print(f"  🔍 Extracting video URL from page...")
                    actual_video_url = await extract_video_url_from_page(video.video_url)

                    if not actual_video_url:
                        print(f"  ⚠️ Could not extract video URL, skipping...")
                        skipped_count += 1
                        continue

                    print(f"  ✅ Found video URL: {actual_video_url[:80]}...")

                    # Step 2: Download video
                    print(f"  ⬇️ Downloading video...")
                    video_content = await download_video(actual_video_url)

                    if not video_content:
                        print(f"  ❌ Download failed, skipping...")
                        failed_count += 1
                        continue

                    size_mb = len(video_content) / 1024 / 1024
                    print(f"  ✅ Downloaded: {size_mb:.2f} MB")

                    # Step 3: Upload to OSS
                    print(f"  ⬆️ Uploading to OSS as video {video.id:03d}.mp4...")
                    oss_url = await upload_to_oss(video_content, video.id)

                    if not oss_url:
                        print(f"  ❌ Upload failed, skipping...")
                        failed_count += 1
                        continue

                    print(f"  ✅ Uploaded: {oss_url}")

                    # Step 4: Update database
                    print(f"  💾 Updating database...")
                    update_stmt = (
                        update(VideoShowcase)
                        .where(VideoShowcase.id == video.id)
                        .values(video_url=oss_url)
                    )
                    await db.execute(update_stmt)
                    await db.commit()

                    print(f"  ✅ Database updated!")
                    success_count += 1

                    # Rate limiting - avoid overwhelming servers
                    if idx < total:
                        print(f"  ⏳ Waiting 2 seconds before next video...")
                        await asyncio.sleep(2)

                except Exception as e:
                    print(f"  ❌ Error processing video {video.id}: {e}")
                    failed_count += 1
                    await db.rollback()
                    continue

            # Summary
            print("\n" + "=" * 70)
            print("📊 Processing Summary:")
            print(f"  ✅ Success: {success_count}")
            print(f"  ❌ Failed: {failed_count}")
            print(f"  ⚠️ Skipped: {skipped_count}")
            print(f"  📝 Total: {total}")
            print("=" * 70)

        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Download Sora videos and upload to OSS')
    parser.add_argument('--start-id', type=int, help='Start from this video ID')
    parser.add_argument('--end-id', type=int, help='End at this video ID')
    parser.add_argument('--limit', type=int, help='Process only this many videos')
    parser.add_argument('--test', action='store_true', help='Test mode: process only 1 video')

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("🎬 Sora Videos Download & Upload Script")
    print("=" * 70)

    if args.test:
        print("⚠️ TEST MODE: Processing only 1 video")
        asyncio.run(process_videos(limit=1))
    else:
        asyncio.run(process_videos(
            start_id=args.start_id,
            end_id=args.end_id,
            limit=args.limit
        ))

    print("\n✨ Done!\n")
