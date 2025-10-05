#!/usr/bin/env python3
"""
批量上传视频到阿里云 OSS，并插入到 video_showcases 表

使用方法:
    python scripts/upload_videos_to_oss.py --folder /path/to/videos --prompts prompts.txt

    或者交互式上传:
    python scripts/upload_videos_to_oss.py --folder /path/to/videos --interactive
"""

import os
import sys
import argparse
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import mimetypes

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import oss2
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# 加载环境变量
load_dotenv()

# 导入模型
from app.models.video_showcase import VideoShowcase
from app.core.config import settings


class OSSUploader:
    """阿里云 OSS 上传工具"""

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

    def upload_file(self, local_path: str, oss_path: str, progress_callback=None) -> str:
        """
        上传文件到 OSS

        Args:
            local_path: 本地文件路径
            oss_path: OSS 存储路径（不包含 bucket）
            progress_callback: 进度回调函数

        Returns:
            文件的 OSS URL
        """
        # 确保 OSS 路径不以 / 开头
        oss_path = oss_path.lstrip('/')

        # 获取文件 MIME 类型
        mime_type, _ = mimetypes.guess_type(local_path)
        if not mime_type:
            mime_type = 'application/octet-stream'

        # 上传文件
        try:
            # 使用分片上传处理大文件
            file_size = os.path.getsize(local_path)

            if file_size > 100 * 1024 * 1024:  # 大于 100MB 使用分片上传
                oss2.resumable_upload(
                    self.bucket,
                    oss_path,
                    local_path,
                    store=oss2.ResumableStore(root='/tmp'),
                    multipart_threshold=100*1024*1024,
                    part_size=10*1024*1024,
                    num_threads=4,
                    progress_callback=progress_callback
                )
            else:
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
            print(f"✗ 上传失败: {e}")
            raise

    def get_video_info(self, local_path: str) -> Dict:
        """
        获取视频信息（时长、尺寸等）

        需要安装: pip install opencv-python
        """
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
            print("⚠ 提示: 安装 opencv-python 可以自动获取视频时长")
            return {'duration_seconds': None}
        except Exception as e:
            print(f"⚠ 获取视频信息失败: {e}")
            return {'duration_seconds': None}


async def insert_to_database(videos: List[Dict]) -> None:
    """
    批量插入视频记录到数据库

    Args:
        videos: 视频信息列表
    """
    # 创建异步数据库连接
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


def read_prompts_from_file(prompts_file: str) -> List[str]:
    """
    从文件读取提示词列表

    文件格式（每行一个提示词）：
        一个美丽的日落场景
        城市夜景，霓虹灯闪烁
        森林中的小溪流水
    """
    with open(prompts_file, 'r', encoding='utf-8') as f:
        prompts = [line.strip() for line in f if line.strip()]
    return prompts


def get_video_files(folder: str) -> List[str]:
    """获取文件夹中的所有视频文件"""
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm'}
    video_files = []

    for file in Path(folder).iterdir():
        if file.is_file() and file.suffix.lower() in video_extensions:
            video_files.append(str(file))

    return sorted(video_files)


def progress_callback(consumed_bytes, total_bytes):
    """上传进度回调"""
    if total_bytes:
        rate = int(100 * consumed_bytes / total_bytes)
        print(f'\r上传进度: {rate}%', end='', flush=True)


async def main():
    parser = argparse.ArgumentParser(description='批量上传视频到阿里云 OSS')
    parser.add_argument('--folder', required=True, help='视频文件夹路径')
    parser.add_argument('--prompts', help='提示词文件路径（每行一个提示词）')
    parser.add_argument('--interactive', action='store_true', help='交互式输入提示词')
    parser.add_argument('--prefix', default='showcase', help='OSS 存储路径前缀')
    parser.add_argument('--skip-db', action='store_true', help='跳过数据库插入，仅上传')
    parser.add_argument('--output', help='输出链接到文件')

    args = parser.parse_args()

    # 检查文件夹是否存在
    if not os.path.isdir(args.folder):
        print(f"✗ 文件夹不存在: {args.folder}")
        return

    # 获取所有视频文件
    video_files = get_video_files(args.folder)
    if not video_files:
        print(f"✗ 文件夹中没有找到视频文件: {args.folder}")
        return

    print(f"✓ 找到 {len(video_files)} 个视频文件\n")

    # 获取提示词
    prompts = []
    if args.prompts:
        prompts = read_prompts_from_file(args.prompts)
        print(f"✓ 从文件读取了 {len(prompts)} 个提示词\n")
    elif args.interactive:
        print("请为每个视频输入提示词（直接回车使用文件名）:\n")
    else:
        print("⚠ 未指定提示词，将使用文件名作为提示词\n")

    # 初始化 OSS 上传器
    try:
        uploader = OSSUploader()
    except Exception as e:
        print(f"✗ 初始化 OSS 失败: {e}")
        return

    # 批量上传
    uploaded_videos = []
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    for idx, video_file in enumerate(video_files, 1):
        filename = Path(video_file).name
        print(f"\n[{idx}/{len(video_files)}] 处理: {filename}")

        # 获取提示词
        if args.interactive:
            prompt = input(f"  提示词 [{filename}]: ").strip()
            if not prompt:
                prompt = Path(video_file).stem
        elif prompts and idx <= len(prompts):
            prompt = prompts[idx - 1]
        else:
            prompt = Path(video_file).stem

        # 构建 OSS 路径
        oss_path = f"{args.prefix}/{timestamp}/{filename}"

        try:
            # 上传视频
            print(f"  正在上传...", end='', flush=True)
            video_url = uploader.upload_file(video_file, oss_path, progress_callback)
            print(f"\n  ✓ 上传成功: {video_url}")

            # 获取视频信息
            video_info = uploader.get_video_info(video_file)

            uploaded_videos.append({
                'video_url': video_url,
                'prompt': prompt,
                'is_active': True,
                'display_order': len(video_files) - idx,  # 倒序排列
                'duration_seconds': video_info.get('duration_seconds')
            })

        except Exception as e:
            print(f"\n  ✗ 上传失败: {e}")
            continue

    # 显示上传结果
    print(f"\n{'='*60}")
    print(f"上传完成！成功: {len(uploaded_videos)}/{len(video_files)}")
    print(f"{'='*60}\n")

    # 输出链接
    if uploaded_videos:
        print("视频链接列表:")
        for idx, video in enumerate(uploaded_videos, 1):
            print(f"{idx}. {video['video_url']}")
            print(f"   提示词: {video['prompt']}")

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
                print("你可以稍后手动插入或使用 --skip-db 参数")
        else:
            print("\n⚠ 跳过数据库插入（使用了 --skip-db 参数）")


if __name__ == '__main__':
    asyncio.run(main())
