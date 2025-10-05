# Vercel 快速部署指南

## 架构说明

```
用户请求 → Cloudflare CDN → Vercel Serverless → 阿里云 RDS + OSS + Redis
```

- **前端**: Vercel Serverless Functions
- **数据库**: 阿里云 RDS PostgreSQL (保持不变)
- **缓存**: 阿里云 Redis (保持不变)
- **存储**: 阿里云 OSS (保持不变)
- **CDN**: Cloudflare 全球加速

## 部署步骤

### 1. 推送代码到 GitHub

```bash
git add .
git commit -m "Add Vercel deployment config"
git push origin main
```

### 2. 在 Vercel 导入项目

1. 访问 https://vercel.com/new
2. 导入你的 GitHub 仓库
3. 点击 Deploy（会失败，因为还没配置环境变量）

### 3. 配置环境变量

在 Vercel 项目设置 → Environment Variables 中添加以下变量：

#### 必需变量（从你的 .env 复制）

```bash
# 应用配置
APP_NAME=Video Animation Platform
APP_VERSION=1.0.0
ENVIRONMENT=production
SECRET_KEY=你的secret_key

# API Keys
QWEN_VIDEO_API_KEY=你的qwen_api_key
PROXY_API_KEY=你的proxy_api_key
SORA_API_KEY=你的sora_api_key

# 数据库（阿里云 RDS PostgreSQL）
DATABASE_URL_MASTER=你的阿里云RDS连接字符串

# Redis（阿里云 Redis）
REDIS_URL=你的阿里云Redis连接字符串
CELERY_BROKER_URL=你的Redis_URL/1
CELERY_RESULT_BACKEND=你的Redis_URL/2

# 存储（阿里云 OSS）
STORAGE_BACKEND=oss
ALIYUN_OSS_ACCESS_KEY=你的OSS_access_key
ALIYUN_OSS_SECRET_KEY=你的OSS_secret_key
ALIYUN_OSS_BUCKET=你的bucket名称
ALIYUN_OSS_ENDPOINT=https://oss-cn-beijing.aliyuncs.com
ALIYUN_OSS_REGION=cn-beijing

# JWT
JWT_SECRET_KEY=你的jwt_secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080

# 认证
WECHAT_APP_ID=你的微信app_id
WECHAT_APP_SECRET=你的微信secret
GOOGLE_CLIENT_ID=你的google_client_id
GOOGLE_CLIENT_SECRET=你的google_secret

# 支付
STRIPE_SECRET_KEY=你的stripe_key
WECHAT_PAY_MERCHANT_ID=你的商户号

# CORS
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# 短信（阿里云）
ALIYUN_SMS_ACCESS_KEY=你的短信access_key
ALIYUN_SMS_SECRET_KEY=你的短信secret_key
ALIYUN_SMS_SIGN_NAME=你的签名
ALIYUN_SMS_TEMPLATE_CODE=你的模板码
```

### 4. 重新部署

配置完环境变量后，点击 "Redeploy" 重新部署。

### 5. 测试部署

```bash
# 测试健康检查
curl https://your-project.vercel.app/health

# 测试 API
curl https://your-project.vercel.app/api/tasks
```

## Celery Worker 部署

Vercel 不支持长时间运行的进程，需要单独部署 Celery Worker。

### 选项 1: 阿里云 ECS

在阿里云 ECS 上运行：

```bash
# 拉取代码
git clone your-repo
cd fastapi-backend

# 安装依赖
pip install -r requirements.txt

# 配置 .env（复制生产环境变量）

# 运行 Celery Worker
celery -A celery_app.worker worker --loglevel=info
```

### 选项 2: Docker

```bash
docker build -t video-worker .
docker run -d --env-file .env.production video-worker celery -A celery_app.worker worker --loglevel=info
```

## 配置自定义域名

### 在 Vercel 添加域名

1. 项目设置 → Domains
2. 添加域名：`api.yourdomain.com`
3. Vercel 会给你 CNAME 记录

### 配置 Cloudflare（详见 CLOUDFLARE_SETUP.md）

1. 登录 Cloudflare
2. 添加 CNAME 记录：
   ```
   Type: CNAME
   Name: api
   Target: cname.vercel-dns.com
   Proxy: 启用（橙色云朵）
   ```
3. SSL/TLS 设置为 "Full (strict)"

## 数据库迁移

在本地运行迁移（连接到阿里云 RDS）：

```bash
# 设置生产数据库 URL
export DATABASE_URL_MASTER="你的阿里云RDS连接字符串"

# 运行迁移
alembic upgrade head
```

## 监控

### Vercel 日志
项目 → Deployments → 选择部署 → View Function Logs

### 阿里云监控
- RDS 监控：阿里云控制台 → RDS → 监控
- Redis 监控：阿里云控制台 → Redis → 监控
- OSS 监控：阿里云控制台 → OSS → 监控

## 故障排查

### 数据库连接失败
- 检查阿里云 RDS 白名单，添加 `0.0.0.0/0`（允许所有 IP）
- 或者添加 Vercel IP 范围

### Redis 连接超时
- 检查阿里云 Redis 白名单配置
- 确认 Redis URL 格式正确

### OSS 上传失败
- 检查 OSS Bucket 权限
- 确认 Access Key 和 Secret 正确

## 成本估算

- **Vercel**: 免费（Hobby）或 $20/月（Pro）
- **阿里云 RDS**: 按现有配置
- **阿里云 Redis**: 按现有配置
- **阿里云 OSS**: 按使用量计费
- **Cloudflare**: 免费

总增加成本：约 $0-20/月（仅 Vercel）

## 注意事项

1. ✅ **保持现有代码不变** - 只添加了 `api/index.py` 和 `vercel.json`
2. ✅ **继续使用阿里云服务** - RDS、Redis、OSS 全部不变
3. ✅ **Celery Worker 单独部署** - 需要在 ECS 或其他服务器运行
4. ✅ **Cloudflare 提供 CDN** - 全球加速，免费
5. ⚠️ **配置白名单** - 确保阿里云服务允许 Vercel 访问

## 下一步

1. 部署成功后，配置 Cloudflare CDN（见 `CLOUDFLARE_SETUP.md`）
2. 配置域名和 SSL 证书
3. 监控性能和错误
4. 优化缓存策略
