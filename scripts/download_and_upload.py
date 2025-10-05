#!/usr/bin/env python3
"""
从 URL 下载视频，上传到阿里云 OSS，并保存到数据库

使用方法:
    python scripts/download_and_upload.py --urls video_urls.txt --prompts prompts.txt
    python scripts/download_and_upload.py --urls video_urls.txt --interactive
    python scripts/download_and_upload.py --csv videos.csv

支持格式:
    1. URL 文件 + 提示词文件（两个文件，行数对应）
    2. URL 文件 + 交互式输入
    3. CSV 文件（包含 URL 和提示词）
"""

import os
import sys
import argparse
import asyncio
import csv
import hashlib
import mimetypes
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urlparse, unquote
import tempfile
import shutil

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
import oss2
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

# 加载环境变量
load_dotenv()

# 导入模型
from app.models.video_showcase import VideoShowcase


class VideoDownloader:
    """视频下载器"""

    def __init__(self, temp_dir: str = None):
        """
        初始化下载器

        Args:
            temp_dir: 临时文件存储目录，默认使用系统临时目录
        """
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix='video_download_')
        self.client = httpx.AsyncClient(timeout=300.0, follow_redirects=True)
        print(f"✓ 临时目录: {self.temp_dir}")

    async def download_video(self, url: str, filename: str = None) -> str:
        """
        从 URL 下载视频到临时目录

        Args:
            url: 视频 URL
            filename: 保存的文件名（可选，默认从 URL 提取）

        Returns:
            下载的本地文件路径
        """
        # 生成文件名
        if not filename:
            # 从 URL 提取文件名
            parsed_url = urlparse(url)
            filename = unquote(os.path.basename(parsed_url.path))

            # 如果没有扩展名，尝试从 Content-Type 获取
            if not os.path.splitext(filename)[1]:
                filename = f"{hashlib.md5(url.encode()).hexdigest()[:8]}.mp4"

        local_path = os.path.join(self.temp_dir, filename)

        # 检查文件是否已存在
        if os.path.exists(local_path):
            print(f"  ✓ 文件已存在，跳过下载")
            return local_path

        try:
            # 先获取文件大小
            head_response = await self.client.head(url)
            total_size = int(head_response.headers.get('content-length', 0))

            # 下载文件
            print(f"  下载中... (大小: {total_size / 1024 / 1024:.2f} MB)")

            with open(local_path, 'wb') as f:
                async with self.client.stream('GET', url) as response:
                    response.raise_for_status()

                    # 进度条
                    downloaded = 0
                    with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"  {filename}") as pbar:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            pbar.update(len(chunk))

            print(f"  ✓ 下载完成: {local_path}")
            return local_path

        except Exception as e:
            print(f"  ✗ 下载失败: {e}")
            if os.path.exists(local_path):
                os.remove(local_path)
            raise

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()

    def cleanup(self):
        """清理临时文件"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"✓ 已清理临时文件: {self.temp_dir}")


class OSSUploader:
    """阿里云 OSS 上传器"""

    def __init__(self):
        """初始化 OSS 客户端"""
        access_key = os.getenv('ALIYUN_OSS_ACCESS_KEY')
        secret_key = os.getenv('ALIYUN_OSS_SECRET_KEY')
        bucket_name = os.getenv('ALIYUN_OSS_BUCKET')
        endpoint = os.getenv('ALIYUN_OSS_ENDPOINT', 'https://oss-cn-beijing.aliyuncs.com')

        if not all([access_key, secret_key, bucket_name]):
            raise ValueError("请在 .env 文件中配置 OSS 相关环境变量")

        # 移除 endpoint 中的 https://
        endpoint = endpoint.replace('https://', '').replace('http://', '')

        self.auth = oss2.Auth(access_key, secret_key)
        self.bucket = oss2.Bucket(self.auth, endpoint, bucket_name)
        self.bucket_name = bucket_name
        self.endpoint = endpoint

        print(f"✓ OSS 连接成功: {bucket_name}")

    def upload_file(self, local_path: str, oss_path: str) -> str:
        """
        上传文件到 OSS

        Args:
            local_path: 本地文件路径
            oss_path: OSS 存储路径

        Returns:
            文件的 OSS URL
        """
        # 确保 OSS 路径不以 / 开头
        oss_path = oss_path.lstrip('/')

        # 获取文件 MIME 类型
        mime_type, _ = mimetypes.guess_type(local_path)
        if not mime_type:
            mime_type = 'video/mp4'

        try:
            file_size = os.path.getsize(local_path)

            # 大文件使用分片上传
            if file_size > 100 * 1024 * 1024:  # 大于 100MB
                print(f"  使用分片上传 ({file_size / 1024 / 1024:.2f} MB)...")
                oss2.resumable_upload(
                    self.bucket,
                    oss_path,
                    local_path,
                    store=oss2.ResumableStore(root='/tmp'),
                    multipart_threshold=100*1024*1024,
                    part_size=10*1024*1024,
                    num_threads=4
                )
            else:
                print(f"  上传中 ({file_size / 1024 / 1024:.2f} MB)...")
                with open(local_path, 'rb') as f:
                    self.bucket.put_object(
                        oss_path,
                        f,
                        headers={'Content-Type': mime_type}
                    )

            # 返回完整 URL
            url = f"https://{self.bucket_name}.{self.endpoint}/{oss_path}"
            return url

        except Exception as e:
            print(f"  ✗ 上传失败: {e}")
            raise

    def get_video_info(self, local_path: str) -> Dict:
        """获取视频信息（时长等）"""
        try:
            import cv2
            video = cv2.VideoCapture(local_path)
            fps = video.get(cv2.CAP_PROP_FPS)
            frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)
            duration = int(frame_count / fps) if fps > 0 else 0
            width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            video.release()

            return {
                'duration_seconds': duration,
                'width': width,
                'height': height,
                'fps': fps
            }
        except ImportError:
            return {'duration_seconds': None}
        except Exception as e:
            print(f"  ⚠ 获取视频信息失败: {e}")
            return {'duration_seconds': None}


async def insert_to_database(videos: List[Dict]) -> None:
    """批量插入视频记录到数据库"""
    database_url = os.getenv('DATABASE_URL_MASTER')
    if not database_url:
        raise ValueError("请在 .env 文件中配置 DATABASE_URL_MASTER")

    # 转换为异步 URL
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')

    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        for video in videos:
            showcase = VideoShowcase(
                video_url=video['video_url'],
                prompt=video['prompt'],
                is_active=video.get('is_active', True),
                display_order=video.get('display_order', 0),
                thumbnail_url=video.get('thumbnail_url'),
                duration_seconds=video.get('duration_seconds'),
                view_count=0
            )
            session.add(showcase)

        await session.commit()
        print(f"✓ 已插入 {len(videos)} 条记录到数据库")

    await engine.dispose()


def read_urls_from_file(urls_file: str) -> List[str]:
    """从文件读取 URL 列表"""
    with open(urls_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return urls


def read_prompts_from_file(prompts_file: str) -> List[str]:
    """从文件读取提示词列表"""
    with open(prompts_file, 'r', encoding='utf-8') as f:
        prompts = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return prompts


def read_from_csv(csv_file: str) -> List[Dict]:
    """
    从 CSV 文件读取 URL 和提示词

    CSV 格式:
        url,prompt,display_order
        https://example.com/video1.mp4,美丽的日落,100
        https://example.com/video2.mp4,城市夜景,90
    """
    videos = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'url' in row and 'prompt' in row:
                videos.append({
                    'url': row['url'].strip(),
                    'prompt': row['prompt'].strip(),
                    'display_order': int(row.get('display_order', 0))
                })
    return videos


async def main():
    parser = argparse.ArgumentParser(description='从 URL 下载视频，上传到 OSS 并保存到数据库')
    parser.add_argument('--urls', help='URL 列表文件路径')
    parser.add_argument('--prompts', help='提示词列表文件路径')
    parser.add_argument('--csv', help='CSV 文件路径（包含 url 和 prompt 列）')
    parser.add_argument('--interactive', action='store_true', help='交互式输入提示词')
    parser.add_argument('--prefix', default='showcase', help='OSS 存储路径前缀')
    parser.add_argument('--skip-db', action='store_true', help='跳过数据库插入')
    parser.add_argument('--output', help='输出链接到文件')
    parser.add_argument('--keep-temp', action='store_true', help='保留临时文件（不清理）')

    args = parser.parse_args()

    # 检查参数
    if not args.csv and not args.urls:
        print("✗ 请指定 --urls 或 --csv 参数")
        parser.print_help()
        return

    # 读取视频列表
    videos_to_process = []

    if args.csv:
        # 从 CSV 读取
        print(f"从 CSV 文件读取: {args.csv}")
        videos_to_process = read_from_csv(args.csv)
        print(f"✓ 读取了 {len(videos_to_process)} 条记录\n")

    else:
        # 从 URL 文件读取
        urls = read_urls_from_file(args.urls)
        print(f"✓ 读取了 {len(urls)} 个 URL\n")

        # 读取提示词
        prompts = []
        if args.prompts:
            prompts = read_prompts_from_file(args.prompts)
            print(f"✓ 读取了 {len(prompts)} 个提示词\n")
        elif args.interactive:
            print("请为每个视频输入提示词:\n")
        else:
            print("⚠ 未指定提示词，将使用文件名作为提示词\n")

        # 组合 URL 和提示词
        for idx, url in enumerate(urls):
            if args.interactive:
                prompt = input(f"[{idx + 1}/{len(urls)}] {url}\n提示词: ").strip()
                if not prompt:
                    filename = os.path.basename(urlparse(url).path)
                    prompt = os.path.splitext(filename)[0]
            elif prompts and idx < len(prompts):
                prompt = prompts[idx]
            else:
                filename = os.path.basename(urlparse(url).path)
                prompt = os.path.splitext(filename)[0]

            videos_to_process.append({
                'url': url,
                'prompt': prompt,
                'display_order': len(urls) - idx
            })

    # 初始化下载器和上传器
    downloader = VideoDownloader()
    try:
        uploader = OSSUploader()
    except Exception as e:
        print(f"✗ 初始化 OSS 失败: {e}")
        return

    # 批量处理
    uploaded_videos = []
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    print(f"\n{'='*60}")
    print(f"开始处理 {len(videos_to_process)} 个视频")
    print(f"{'='*60}\n")

    for idx, video_data in enumerate(videos_to_process, 1):
        url = video_data['url']
        prompt = video_data['prompt']

        print(f"[{idx}/{len(videos_to_process)}] 处理: {prompt}")
        print(f"  URL: {url}")

        try:
            # 1. 下载视频
            local_path = await downloader.download_video(url)

            # 2. 构建 OSS 路径
            filename = os.path.basename(local_path)
            oss_path = f"{args.prefix}/{timestamp}/{filename}"

            # 3. 上传到 OSS
            video_url = uploader.upload_file(local_path, oss_path)
            print(f"  ✓ OSS URL: {video_url}")

            # 4. 获取视频信息
            video_info = uploader.get_video_info(local_path)

            # 5. 添加到结果列表
            uploaded_videos.append({
                'video_url': video_url,
                'prompt': prompt,
                'is_active': True,
                'display_order': video_data.get('display_order', 0),
                'duration_seconds': video_info.get('duration_seconds')
            })

            print(f"  ✓ 完成\n")

        except Exception as e:
            print(f"  ✗ 处理失败: {e}\n")
            continue

    # 关闭下载器
    await downloader.close()

    # 清理临时文件
    if not args.keep_temp:
        downloader.cleanup()
    else:
        print(f"⚠ 保留临时文件: {downloader.temp_dir}")

    # 显示结果
    print(f"\n{'='*60}")
    print(f"处理完成！成功: {len(uploaded_videos)}/{len(videos_to_process)}")
    print(f"{'='*60}\n")

    if uploaded_videos:
        print("OSS 链接列表:")
        for idx, video in enumerate(uploaded_videos, 1):
            print(f"{idx}. {video['video_url']}")
            print(f"   提示词: {video['prompt']}")
            if video.get('duration_seconds'):
                print(f"   时长: {video['duration_seconds']} 秒")

        # 保存到文件
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                for video in uploaded_videos:
                    f.write(f"{video['video_url']}\t{video['prompt']}\n")
            print(f"\n✓ 链接已保存到: {args.output}")

        # 插入数据库
        if not args.skip_db:
            print(f"\n正在插入数据库...")
            try:
                await insert_to_database(uploaded_videos)
            except Exception as e:
                print(f"✗ 数据库插入失败: {e}")
                print("视频已上传到 OSS，但未插入数据库")
        else:
            print("\n⚠ 跳过数据库插入（使用了 --skip-db 参数）")


if __name__ == '__main__':
    asyncio.run(main())
