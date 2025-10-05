#!/usr/bin/env python3
"""
Script to download Sora videos using browser cookies.
Run this script and paste your cookies when prompted.
"""

import asyncio
import sys
from pathlib import Path
import httpx
from io import BytesIO
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from app.db.base import get_db_write
from app.models.video_showcase import VideoShowcase
from app.services.storage.factory import get_storage_provider


# Global cookie storage
COOKIES = {}


def parse_cookie_string(cookie_string: str) -> dict:
    """Parse cookie string into dictionary."""
    cookies = {}
    for item in cookie_string.split(';'):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            cookies[key.strip()] = value.strip()
    return cookies


async def extract_video_url_from_page(page_url: str, cookies: dict) -> str:
    """Extract video URL from Sora page using cookies."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Referer': 'https://sora.chatgpt.com/',
        'Origin': 'https://sora.chatgpt.com',
    }

    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers=headers,
        cookies=cookies
    ) as client:
        try:
            response = await client.get(page_url)
            response.raise_for_status()
            html = response.text

            # Debug: save HTML to file for inspection
            # with open(f'/tmp/sora_page_{int(time.time())}.html', 'w') as f:
            #     f.write(html)

            import re

            # Multiple patterns to try
            patterns = [
                # OpenAI video URLs with signatures (most specific)
                r'https://videos\.openai\.com/[^\s"<>]+\.mp4[^\s"<>]*',
                # Direct video tag
                r'<video[^>]+src="([^"]+\.mp4[^"]*)"',
                r'<source[^>]+src="([^"]+\.mp4[^"]*)"',
                # JSON data
                r'"videoUrl"\s*:\s*"([^"]+\.mp4[^"]*)"',
                r'"video_url"\s*:\s*"([^"]+\.mp4[^"]*)"',
                r'"url"\s*:\s*"([^"]+\.mp4[^"]*)"',
                r'"src"\s*:\s*"([^"]+\.mp4[^"]*)"',
                # Any mp4 URL in the page
                r'https://[^\s"<>]+\.mp4[^\s"<>]*',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    # Return first match
                    video_url = matches[0]
                    # Clean up
                    video_url = video_url.replace('\\/', '/').replace('\\', '')
                    if video_url.startswith('http'):
                        return video_url

            print(f"  ⚠️ No video URL patterns matched. Page length: {len(html)} chars")
            return None

        except Exception as e:
            print(f"  ❌ Error: {e}")
            return None


async def download_video(video_url: str, cookies: dict = None) -> bytes:
    """Download video file."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://sora.chatgpt.com/',
    }

    async with httpx.AsyncClient(
        timeout=120.0,
        follow_redirects=True,
        headers=headers,
        cookies=cookies or {}
    ) as client:
        try:
            print(f"  ⬇️ Downloading from: {video_url[:80]}...")
            response = await client.get(video_url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"  ❌ Download error: {e}")
            return None


async def upload_to_oss(video_content: bytes, video_id: int) -> str:
    """Upload video to OSS."""
    try:
        storage_provider = get_storage_provider()
        storage_key = f"showcase/videos/{video_id:03d}.mp4"
        file_obj = BytesIO(video_content)

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


async def process_videos(cookies: dict, start_id: int = None, end_id: int = None, limit: int = None):
    """Process videos with authentication cookies."""

    async for db in get_db_write():
        try:
            query = select(VideoShowcase).where(
                VideoShowcase.video_url.like('%sora.chatgpt.com%')
            ).order_by(VideoShowcase.id)

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
                    # Extract video URL
                    print(f"  🔍 Extracting video URL...")
                    actual_video_url = await extract_video_url_from_page(video.video_url, cookies)

                    if not actual_video_url:
                        print(f"  ⚠️ Could not extract video URL, skipping...")
                        skipped_count += 1
                        continue

                    print(f"  ✅ Found: {actual_video_url[:80]}...")

                    # Download
                    print(f"  ⬇️ Downloading...")
                    video_content = await download_video(actual_video_url, cookies)

                    if not video_content:
                        print(f"  ❌ Download failed, skipping...")
                        failed_count += 1
                        continue

                    size_mb = len(video_content) / 1024 / 1024
                    print(f"  ✅ Downloaded: {size_mb:.2f} MB")

                    # Upload to OSS
                    print(f"  ⬆️ Uploading to OSS as {video.id:03d}.mp4...")
                    oss_url = await upload_to_oss(video_content, video.id)

                    if not oss_url:
                        print(f"  ❌ Upload failed, skipping...")
                        failed_count += 1
                        continue

                    print(f"  ✅ Uploaded: {oss_url}")

                    # Update database
                    print(f"  💾 Updating database...")
                    update_stmt = (
                        update(VideoShowcase)
                        .where(VideoShowcase.id == video.id)
                        .values(video_url=oss_url)
                    )
                    await db.execute(update_stmt)
                    await db.commit()

                    print(f"  ✅ Complete!")
                    success_count += 1

                    # Rate limiting
                    if idx < total:
                        print(f"  ⏳ Waiting 3 seconds...")
                        await asyncio.sleep(3)

                except Exception as e:
                    print(f"  ❌ Error: {e}")
                    failed_count += 1
                    await db.rollback()
                    continue

            # Summary
            print("\n" + "=" * 70)
            print("📊 Summary:")
            print(f"  ✅ Success: {success_count}")
            print(f"  ❌ Failed: {failed_count}")
            print(f"  ⚠️ Skipped: {skipped_count}")
            print(f"  📝 Total: {total}")
            print("=" * 70)

        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            await db.rollback()
            raise


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Download Sora videos with cookies')
    parser.add_argument('--start-id', type=int, help='Start from this ID')
    parser.add_argument('--end-id', type=int, help='End at this ID')
    parser.add_argument('--limit', type=int, help='Process only N videos')
    parser.add_argument('--test', action='store_true', help='Test mode (1 video)')
    parser.add_argument('--cookie-file', type=str, help='Path to file containing cookies')

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("🎬 Sora Videos Download Script (with Cookies)")
    print("=" * 70)

    # Get cookies
    cookies = {}

    if args.cookie_file and Path(args.cookie_file).exists():
        print(f"\n📖 Reading cookies from: {args.cookie_file}")
        with open(args.cookie_file, 'r') as f:
            cookie_string = f.read().strip()
            cookies = parse_cookie_string(cookie_string)
    else:
        print("\n🍪 Please paste your cookies from browser:")
        print("   (Open DevTools → Application → Cookies → copy all)")
        print("   Paste the Cookie header value and press Enter twice:\n")

        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)

        cookie_string = ' '.join(lines)
        cookies = parse_cookie_string(cookie_string)

    if not cookies:
        print("❌ No cookies provided! Exiting...")
        return

    print(f"\n✅ Loaded {len(cookies)} cookies")
    print(f"   Keys: {', '.join(list(cookies.keys())[:5])}...")

    # Run processing
    if args.test:
        print("\n⚠️ TEST MODE: Processing 1 video")
        asyncio.run(process_videos(cookies, limit=1))
    else:
        asyncio.run(process_videos(
            cookies,
            start_id=args.start_id,
            end_id=args.end_id,
            limit=args.limit
        ))

    print("\n✨ Done!\n")


if __name__ == "__main__":
    main()
