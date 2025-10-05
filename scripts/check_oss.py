#!/usr/bin/env python3
"""
检查阿里云 OSS 连接状态和文件列表
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import oss2

# 加载环境变量
load_dotenv()

def main():
    print("=" * 60)
    print("阿里云 OSS 连接检查工具")
    print("=" * 60)
    print()

    # 获取配置
    access_key = os.getenv('ALIYUN_OSS_ACCESS_KEY')
    secret_key = os.getenv('ALIYUN_OSS_SECRET_KEY')
    bucket_name = os.getenv('ALIYUN_OSS_BUCKET')
    endpoint = os.getenv('ALIYUN_OSS_ENDPOINT', 'https://oss-cn-beijing.aliyuncs.com')

    print("1. 配置信息:")
    print(f"   Bucket: {bucket_name}")
    print(f"   Endpoint: {endpoint}")
    print(f"   Access Key: {access_key[:10]}..." if access_key else "   Access Key: 未配置")
    print()

    if not all([access_key, secret_key, bucket_name]):
        print("✗ 错误: OSS 配置不完整，请检查 .env 文件")
        return

    # 移除 endpoint 中的 https://
    endpoint = endpoint.replace('https://', '').replace('http://', '')

    try:
        # 连接 OSS
        auth = oss2.Auth(access_key, secret_key)
        bucket = oss2.Bucket(auth, endpoint, bucket_name)

        print("2. 测试连接:")
        # 测试连接 - 获取 bucket 信息
        bucket_info = bucket.get_bucket_info()
        print(f"   ✓ 连接成功!")
        print(f"   Bucket 名称: {bucket_info.name}")
        print(f"   创建时间: {bucket_info.creation_date}")
        print(f"   存储类型: {bucket_info.storage_class}")
        print(f"   访问权限: {bucket_info.acl.grant}")
        print()

        # 列出文件
        print("3. 文件列表:")
        print()

        # 列出所有文件（最多100个）
        file_count = 0
        total_size = 0

        # 按前缀分组统计
        prefixes = {}

        for obj in oss2.ObjectIterator(bucket, max_keys=100):
            file_count += 1
            total_size += obj.size

            # 提取前缀（文件夹）
            prefix = obj.key.split('/')[0] if '/' in obj.key else 'root'
            if prefix not in prefixes:
                prefixes[prefix] = {'count': 0, 'size': 0}
            prefixes[prefix]['count'] += 1
            prefixes[prefix]['size'] += obj.size

            # 显示前20个文件
            if file_count <= 20:
                size_mb = obj.size / 1024 / 1024
                print(f"   [{file_count}] {obj.key}")
                print(f"       大小: {size_mb:.2f} MB")
                print(f"       修改时间: {obj.last_modified}")
                print()

        if file_count == 0:
            print("   ⚠ Bucket 中没有文件")
            print()
            print("   可能的原因:")
            print("   1. 还没有上传过任何文件")
            print("   2. 文件在其他 Bucket 中")
            print("   3. 访问权限不足")
            print()
        else:
            print(f"   总计: {file_count} 个文件，总大小: {total_size / 1024 / 1024:.2f} MB")
            print()

            if file_count > 20:
                print(f"   (仅显示前 20 个文件，共有 {file_count} 个)")
                print()

            # 显示按文件夹统计
            print("4. 文件夹统计:")
            for prefix, stats in sorted(prefixes.items()):
                print(f"   {prefix}/")
                print(f"     文件数: {stats['count']}")
                print(f"     大小: {stats['size'] / 1024 / 1024:.2f} MB")
            print()

        # 检查 showcase 文件夹
        print("5. 检查 showcase 文件夹:")
        showcase_count = 0
        for obj in oss2.ObjectIterator(bucket, prefix='showcase/', max_keys=10):
            if showcase_count == 0:
                print("   找到以下文件:")
            showcase_count += 1
            print(f"   - {obj.key}")

        if showcase_count == 0:
            print("   ✗ showcase/ 文件夹为空")
            print("   说明: 还没有通过脚本上传过视频")
        else:
            print(f"   ✓ 找到 {showcase_count} 个文件")
        print()

        # 给出建议
        print("6. 下一步:")
        if file_count == 0:
            print("   建议: 使用上传脚本测试上传功能")
            print("   命令: python scripts/download_and_upload.py --csv videos.csv")
        else:
            print("   ✓ OSS 配置正常，可以正常使用")

    except oss2.exceptions.NoSuchBucket:
        print(f"✗ 错误: Bucket '{bucket_name}' 不存在")
        print()
        print("解决方法:")
        print("1. 登录阿里云 OSS 控制台: https://oss.console.aliyun.com")
        print("2. 检查 Bucket 名称是否正确")
        print("3. 确认 Bucket 所在区域是否为: cn-beijing")

    except oss2.exceptions.AccessDenied:
        print("✗ 错误: 访问被拒绝")
        print()
        print("解决方法:")
        print("1. 检查 Access Key 和 Secret Key 是否正确")
        print("2. 确认该 Access Key 有 OSS 访问权限")
        print("3. 检查 Bucket 的访问控制设置")

    except Exception as e:
        print(f"✗ 错误: {e}")
        print()
        print(f"错误类型: {type(e).__name__}")

    print()
    print("=" * 60)

if __name__ == '__main__':
    main()
