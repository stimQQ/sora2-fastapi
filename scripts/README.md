# 批量上传视频到 OSS 脚本使用指南

## 功能说明

本目录包含两个主要脚本：

### 1. `download_and_upload.py` - 从 URL 下载并上传（推荐）
自动从视频下载链接下载视频，上传到阿里云 OSS，并保存到数据库。

**适用场景**：
- 视频托管在其他服务器，需要批量迁移到 OSS
- 从第三方平台下载视频并归档
- 批量抓取网络视频

### 2. `upload_videos_to_oss.py` - 从本地文件夹上传
批量上传本地视频文件到阿里云 OSS，并自动插入到数据库。

**适用场景**：
- 已有本地视频文件
- 从移动硬盘、U盘等导入视频

## 安装依赖

```bash
# 基础依赖
pip install oss2 python-dotenv sqlalchemy asyncpg httpx tqdm

# 可选：获取视频时长信息
pip install opencv-python
```

## 使用方法

---

## 脚本 1: `download_and_upload.py` - 从 URL 下载并上传

### 方式 1：使用 CSV 文件（最推荐）

创建一个 CSV 文件（如 `videos.csv`）：

```csv
url,prompt,display_order
https://example.com/video1.mp4,一个美丽的日落场景,100
https://example.com/video2.mp4,城市夜景，霓虹灯闪烁,90
https://example.com/video3.mp4,森林中的小溪流水,80
```

然后运行：

```bash
python scripts/download_and_upload.py --csv videos.csv
```

### 方式 2：使用 URL 文件 + 提示词文件

准备两个文件：

**video_urls.txt**:
```
https://example.com/video1.mp4
https://example.com/video2.mp4
https://example.com/video3.mp4
```

**prompts.txt**:
```
一个美丽的日落场景
城市夜景，霓虹灯闪烁
森林中的小溪流水
```

然后运行：

```bash
python scripts/download_and_upload.py \
  --urls video_urls.txt \
  --prompts prompts.txt
```

### 方式 3：交互式输入提示词

```bash
python scripts/download_and_upload.py \
  --urls video_urls.txt \
  --interactive
```

脚本会提示你为每个视频输入提示词。

### 方式 4：使用文件名作为提示词

```bash
python scripts/download_and_upload.py --urls video_urls.txt
```

脚本会自动使用文件名作为提示词。

---

## 脚本 2: `upload_videos_to_oss.py` - 从本地文件夹上传

### 方式 1：使用提示词文件（推荐）

准备一个提示词文件（如 `prompts.txt`），每行一个提示词：

```
一个美丽的日落场景
城市夜景，霓虹灯闪烁
森林中的小溪流水
```

然后运行：

```bash
python scripts/upload_videos_to_oss.py \
  --folder /path/to/videos \
  --prompts scripts/prompts_example.txt
```

### 方式 2：交互式输入提示词

```bash
python scripts/upload_videos_to_oss.py \
  --folder /path/to/videos \
  --interactive
```

### 方式 3：使用文件名作为提示词

```bash
python scripts/upload_videos_to_oss.py \
  --folder /path/to/videos
```

## 参数说明

| 参数 | 说明 | 必需 | 默认值 |
|------|------|------|--------|
| `--folder` | 视频文件夹路径 | 是 | - |
| `--prompts` | 提示词文件路径 | 否 | - |
| `--interactive` | 交互式输入提示词 | 否 | false |
| `--prefix` | OSS 存储路径前缀 | 否 | showcase |
| `--skip-db` | 跳过数据库插入 | 否 | false |
| `--output` | 输出链接到文件 | 否 | - |

## 使用示例

### 示例 1：完整上传流程

```bash
# 1. 准备视频文件夹
mkdir ~/videos_to_upload
# 将视频文件放入文件夹

# 2. 准备提示词文件
cat > ~/prompts.txt << EOF
一个美丽的日落场景，海浪轻轻拍打着沙滩
城市夜景，霓虹灯光闪烁，车流穿梭
森林中的小溪，清澈的水流在石头间流淌
EOF

# 3. 运行上传脚本
python scripts/upload_videos_to_oss.py \
  --folder ~/videos_to_upload \
  --prompts ~/prompts.txt \
  --output urls.txt
```

### 示例 2：仅上传不插入数据库

```bash
python scripts/upload_videos_to_oss.py \
  --folder /path/to/videos \
  --prompts prompts.txt \
  --skip-db \
  --output video_urls.txt
```

稍后可以手动将链接插入数据库。

### 示例 3：自定义存储路径

```bash
python scripts/upload_videos_to_oss.py \
  --folder /path/to/videos \
  --prompts prompts.txt \
  --prefix "homepage/featured"
```

视频会上传到 `homepage/featured/20251005_120000/` 路径下。

## 环境变量配置

确保 `.env` 文件中配置了以下变量：

```bash
# 阿里云 OSS
ALIYUN_OSS_ACCESS_KEY=your_access_key
ALIYUN_OSS_SECRET_KEY=your_secret_key
ALIYUN_OSS_BUCKET=your_bucket_name
ALIYUN_OSS_ENDPOINT=https://oss-cn-beijing.aliyuncs.com

# 数据库
DATABASE_URL_MASTER=postgresql://user:pass@host:5432/dbname
```

## 支持的视频格式

- MP4 (.mp4)
- MOV (.mov)
- AVI (.avi)
- MKV (.mkv)
- FLV (.flv)
- WMV (.wmv)
- WebM (.webm)

## 输出结果

### 控制台输出示例

```
✓ OSS 连接成功: test-video-animate
✓ 找到 3 个视频文件

[1/3] 处理: sunset.mp4
  正在上传...
上传进度: 100%
  ✓ 上传成功: https://test-video-animate.oss-cn-beijing.aliyuncs.com/showcase/20251005_120000/sunset.mp4

[2/3] 处理: city_night.mp4
  正在上传...
上传进度: 100%
  ✓ 上传成功: https://test-video-animate.oss-cn-beijing.aliyuncs.com/showcase/20251005_120000/city_night.mp4

[3/3] 处理: forest_stream.mp4
  正在上传...
上传进度: 100%
  ✓ 上传成功: https://test-video-animate.oss-cn-beijing.aliyuncs.com/showcase/20251005_120000/forest_stream.mp4

============================================================
上传完成！成功: 3/3
============================================================

视频链接列表:
1. https://test-video-animate.oss-cn-beijing.aliyuncs.com/showcase/20251005_120000/sunset.mp4
   提示词: 一个美丽的日落场景，海浪轻轻拍打着沙滩
2. https://test-video-animate.oss-cn-beijing.aliyuncs.com/showcase/20251005_120000/city_night.mp4
   提示词: 城市夜景，霓虹灯光闪烁，车流穿梭
3. https://test-video-animate.oss-cn-beijing.aliyuncs.com/showcase/20251005_120000/forest_stream.mp4
   提示词: 森林中的小溪，清澈的水流在石头间流淌

✓ 链接已保存到: urls.txt

正在插入数据库...
✓ 已插入 3 条记录到数据库
```

### 输出文件格式（使用 --output）

```
https://bucket.oss-cn-beijing.aliyuncs.com/showcase/20251005_120000/video1.mp4    一个美丽的日落场景
https://bucket.oss-cn-beijing.aliyuncs.com/showcase/20251005_120000/video2.mp4    城市夜景，霓虹灯闪烁
https://bucket.oss-cn-beijing.aliyuncs.com/showcase/20251005_120000/video3.mp4    森林中的小溪流水
```

## 高级功能

### 1. 大文件自动分片上传

脚本会自动检测文件大小：
- 小于 100MB：直接上传
- 大于 100MB：自动使用分片上传，支持断点续传

### 2. 自动获取视频信息

如果安装了 `opencv-python`，脚本会自动获取：
- 视频时长
- 分辨率
- 帧率

这些信息会存储在数据库中。

### 3. 智能排序

上传的视频会按倒序设置 `display_order`：
- 最新上传的视频 `display_order` 最高
- 在首页展示时会优先显示

## 故障排查

### 问题 1：OSS 连接失败

**错误**: `✗ 初始化 OSS 失败: InvalidAccessKeyId`

**解决**:
1. 检查 `.env` 中的 `ALIYUN_OSS_ACCESS_KEY` 和 `ALIYUN_OSS_SECRET_KEY`
2. 确认 AccessKey 是否有效且有 OSS 权限

### 问题 2：上传失败

**错误**: `✗ 上传失败: NoSuchBucket`

**解决**:
1. 检查 `ALIYUN_OSS_BUCKET` 是否正确
2. 确认 Bucket 是否存在且在正确的区域

### 问题 3：数据库插入失败

**错误**: `✗ 数据库插入失败: connection refused`

**解决**:
1. 检查 `DATABASE_URL_MASTER` 是否正确
2. 确认数据库是否可访问
3. 使用 `--skip-db` 跳过数据库插入，稍后手动插入

### 问题 4：无法获取视频时长

**警告**: `⚠ 提示: 安装 opencv-python 可以自动获取视频时长`

**解决**:
```bash
pip install opencv-python
```

## 批量操作技巧

### 技巧 1：批量重命名文件

```bash
# 使用 rename 工具批量重命名
cd /path/to/videos
rename 's/\.MOV$/.mp4/i' *.MOV
```

### 技巧 2：从视频文件生成提示词模板

```bash
# 自动生成提示词文件（使用文件名）
cd /path/to/videos
ls *.mp4 | sed 's/\.mp4$//' > prompts.txt
# 然后手动编辑 prompts.txt
```

### 技巧 3：验证上传结果

```bash
# 上传后检查数据库
psql $DATABASE_URL_MASTER -c "SELECT id, prompt, video_url FROM video_showcases ORDER BY id DESC LIMIT 10;"
```

## 安全建议

1. **不要提交 .env 文件到 Git**
2. **定期轮换 OSS AccessKey**
3. **设置 OSS Bucket 防盗链**
4. **使用 RAM 子账号限制权限**

## 性能优化

1. **网络优化**：
   - 在与 OSS 相同区域的服务器运行脚本
   - 使用内网 Endpoint（如 `oss-cn-beijing-internal.aliyuncs.com`）

2. **并发上传**：
   - 如需批量上传大量视频，可修改脚本支持并发

3. **压缩视频**：
   - 上传前使用 FFmpeg 压缩视频可节省带宽和存储

## 相关文档

- [阿里云 OSS Python SDK](https://help.aliyun.com/document_detail/32026.html)
- [Video Showcase API 文档](../VIDEO_SHOWCASE_API.md)
- [阿里云 CDN 配置](../CLOUDFLARE_SETUP.md)

## 联系支持

如有问题，请提交 Issue 或联系开发团队。
