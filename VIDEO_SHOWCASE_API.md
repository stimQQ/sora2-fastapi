# 视频展示列表 API 文档

## 概述

为首页添加视频展示列表功能，用于展示存储在阿里云 OSS 的精选视频。支持 CDN 加速。

## 数据库表

### video_showcases 表

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | Integer | 主键，自增 |
| video_url | String(500) | OSS 视频链接 |
| prompt | Text | 视频生成提示词 |
| is_active | Boolean | 是否在首页展示 |
| display_order | Integer | 显示顺序（数字越大越靠前） |
| thumbnail_url | String(500) | 缩略图链接（可选） |
| duration_seconds | Integer | 视频时长（秒） |
| view_count | Integer | 浏览次数 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## API 接口

### 1. 获取视频列表（分页）

**端点**: `GET /api/showcase/videos`

**参数**:
- `page` (可选): 页码，默认 1
- `page_size` (可选): 每页数量，默认 12，最大 100

**响应示例**:
```json
{
  "total": 50,
  "page": 1,
  "page_size": 12,
  "total_pages": 5,
  "videos": [
    {
      "id": 1,
      "video_url": "https://cdn.yourdomain.com/videos/example.mp4",
      "prompt": "一个美丽的日落场景，海浪拍打着沙滩",
      "thumbnail_url": "https://cdn.yourdomain.com/thumbnails/example.jpg",
      "duration_seconds": 30,
      "view_count": 1234,
      "created_at": "2025-10-05T10:00:00Z"
    }
  ]
}
```

### 2. 获取单个视频详情

**端点**: `GET /api/showcase/videos/{video_id}`

**响应示例**:
```json
{
  "id": 1,
  "video_url": "https://cdn.yourdomain.com/videos/example.mp4",
  "prompt": "一个美丽的日落场景，海浪拍打着沙滩",
  "thumbnail_url": "https://cdn.yourdomain.com/thumbnails/example.jpg",
  "duration_seconds": 30,
  "view_count": 1235,
  "created_at": "2025-10-05T10:00:00Z"
}
```

**说明**: 每次调用会自动增加浏览次数

## CDN 配置

### 1. 在 .env 文件中添加 CDN 域名

```bash
# 阿里云 OSS CDN 域名（可选）
ALIYUN_OSS_CDN_DOMAIN=cdn.yourdomain.com
```

### 2. CDN 自动转换

如果配置了 `ALIYUN_OSS_CDN_DOMAIN`，API 会自动将 OSS 链接转换为 CDN 链接：

```
原始 OSS: https://test-video-animate.oss-cn-beijing.aliyuncs.com/videos/example.mp4
转换后 CDN: https://cdn.yourdomain.com/videos/example.mp4
```

### 3. 配置阿里云 CDN

#### 步骤 1: 创建 CDN 加速域名
1. 登录阿里云控制台
2. 进入 CDN 服务
3. 添加域名：`cdn.yourdomain.com`
4. 源站类型：OSS 域名
5. 源站域名：选择你的 OSS Bucket

#### 步骤 2: 配置 CNAME
1. 阿里云会提供一个 CNAME 记录，如：`cdn.yourdomain.com.w.kunlunsl.com`
2. 在你的 DNS 服务商（如 Cloudflare）添加 CNAME 记录：
   ```
   类型: CNAME
   名称: cdn
   目标: cdn.yourdomain.com.w.kunlunsl.com
   ```

#### 步骤 3: 配置 SSL（可选但推荐）
1. 在阿里云 CDN 控制台启用 HTTPS
2. 上传证书或使用阿里云免费证书

#### 步骤 4: 优化配置
1. **缓存规则**：
   - 视频文件 (.mp4, .mov): 缓存 30 天
   - 图片文件 (.jpg, .png): 缓存 7 天

2. **性能优化**：
   - 启用 Gzip 压缩
   - 启用 HTTP/2

3. **访问控制**（可选）：
   - 防盗链配置
   - IP 黑白名单

## 数据库迁移

运行数据库迁移以创建 `video_showcases` 表：

```bash
alembic upgrade head
```

## 添加示例数据

可以通过数据库直接插入示例视频：

```sql
INSERT INTO video_showcases (video_url, prompt, is_active, display_order, thumbnail_url, duration_seconds)
VALUES
  ('https://test-video-animate.oss-cn-beijing.aliyuncs.com/videos/example1.mp4',
   '一个美丽的日落场景，海浪拍打着沙滩',
   true,
   100,
   'https://test-video-animate.oss-cn-beijing.aliyuncs.com/thumbnails/example1.jpg',
   30),
  ('https://test-video-animate.oss-cn-beijing.aliyuncs.com/videos/example2.mp4',
   '城市夜景，霓虹灯闪烁',
   true,
   90,
   'https://test-video-animate.oss-cn-beijing.aliyuncs.com/thumbnails/example2.jpg',
   25);
```

## 前端集成示例

### React/Next.js 示例

```typescript
// API 调用
async function getShowcaseVideos(page = 1, pageSize = 12) {
  const response = await fetch(
    `https://api.yourdomain.com/api/showcase/videos?page=${page}&page_size=${pageSize}`
  );
  return response.json();
}

// 组件使用
function VideoGallery() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getShowcaseVideos().then(data => {
      setVideos(data.videos);
      setLoading(false);
    });
  }, []);

  return (
    <div className="grid grid-cols-3 gap-4">
      {videos.map(video => (
        <div key={video.id} className="video-card">
          <video
            src={video.video_url}
            poster={video.thumbnail_url}
            controls
          />
          <p>{video.prompt}</p>
          <span>{video.view_count} 次浏览</span>
        </div>
      ))}
    </div>
  );
}
```

## 性能优化建议

### 1. CDN 缓存策略
- 视频文件：长期缓存（30天）
- 缩略图：中期缓存（7天）
- API 响应：不缓存或短期缓存（5分钟）

### 2. 分页加载
- 首页默认显示 12 个视频
- 支持下拉加载更多
- 预加载缩略图

### 3. 懒加载
- 使用 Intersection Observer 实现视频懒加载
- 只在视频进入视口时加载

### 4. 视频格式优化
- 使用 H.264 编码（兼容性最好）
- 分辨率：1080p 或 720p
- 码率：适中（2-5 Mbps）

## 监控和分析

### 浏览量统计
- 每次访问视频详情会自动增加 `view_count`
- 可用于热门视频排序

### CDN 流量监控
- 在阿里云 CDN 控制台查看流量使用
- 设置流量告警避免超额

### 成本估算
- 阿里云 CDN：约 0.24 元/GB（中国大陆）
- 假设平均视频 50MB，每月 10000 次播放
- 流量：500GB/月
- 成本：约 120 元/月

## 故障排查

### 视频无法播放
1. 检查 OSS 文件是否存在
2. 检查 OSS Bucket 权限（公共读）
3. 检查 CDN 配置是否正确

### CDN 未生效
1. 检查 CNAME 是否配置正确：`dig cdn.yourdomain.com`
2. 检查是否启用了阿里云 CDN 加速
3. 清除 CDN 缓存重试

### API 返回空列表
1. 检查数据库是否有数据
2. 检查 `is_active` 字段是否为 true
3. 查看后端日志

## 后续优化

1. **管理后台**：添加视频管理界面（上传、编辑、删除）
2. **标签系统**：为视频添加分类标签
3. **搜索功能**：支持按提示词搜索
4. **推荐算法**：根据浏览量、点赞等推荐视频
5. **国际化**：支持多语言提示词

---

**创建时间**: 2025-10-05
**维护者**: Video Animation Platform Team
