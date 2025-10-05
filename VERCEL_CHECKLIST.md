# Vercel 部署检查清单

## ✅ 已完成的准备工作

### 1. 文件配置
- [x] `vercel.json` - Vercel 部署配置
- [x] `api/index.py` - Serverless 入口点
- [x] `.vercelignore` - 忽略不必要的文件
- [x] `requirements.txt` - Python 依赖（已包含 mangum）

### 2. 代码调整
- [x] 移除 lifespan 依赖（serverless 不支持）
- [x] 简化数据库连接（每个请求独立连接）
- [x] 配置 Mangum handler

---

## 🚀 部署步骤

### 第一步：在 Vercel 导入项目

1. 访问 https://vercel.com/new
2. 选择 "Import Git Repository"
3. 连接你的 GitHub 账号
4. 选择刚才推送的仓库
5. 点击 "Import"

### 第二步：配置环境变量

在 Vercel 项目设置 → Environment Variables 中添加以下变量：

#### 🔴 必需的环境变量（从 .env 复制）

```bash
# 应用配置
APP_NAME=Video Animation Platform
APP_VERSION=1.0.0
ENVIRONMENT=production
SECRET_KEY=你的secret_key（从 .env 复制）

# API Keys
QWEN_VIDEO_API_KEY=你的qwen_api_key
PROXY_API_KEY=你的proxy_api_key
SORA_API_KEY=你的sora_api_key

# 数据库（阿里云 RDS PostgreSQL）
# ⚠️ 重要：Vercel 需要使用 asyncpg 驱动
DATABASE_URL_MASTER=postgresql+asyncpg://user:password@host:5432/dbname

# Redis（阿里云 Redis）
REDIS_URL=你的阿里云Redis连接字符串
CELERY_BROKER_URL=你的Redis_URL/1
CELERY_RESULT_BACKEND=你的Redis_URL/2

# 存储（阿里云 OSS）
STORAGE_BACKEND=oss
ALIYUN_OSS_ACCESS_KEY=你的OSS_access_key
ALIYUN_OSS_SECRET_KEY=你的OSS_secret_key
ALIYUN_OSS_BUCKET=test-video-animate
ALIYUN_OSS_ENDPOINT=https://oss-cn-beijing.aliyuncs.com
ALIYUN_OSS_REGION=cn-beijing

# CDN（可选，如果配置了 Cloudflare CDN）
ALIYUN_OSS_CDN_DOMAIN=cdn.yourdomain.com

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

# CORS（重要：添加你的前端域名）
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# 短信（阿里云）
ALIYUN_SMS_ACCESS_KEY=你的短信access_key
ALIYUN_SMS_SECRET_KEY=你的短信secret_key
ALIYUN_SMS_SIGN_NAME=你的签名
ALIYUN_SMS_TEMPLATE_CODE=你的模板码
```

#### ⚠️ 数据库 URL 格式注意

确保使用 `postgresql+asyncpg://` 而不是 `postgresql://`：

```bash
# ❌ 错误格式
DATABASE_URL_MASTER=postgresql://user:pass@host:5432/db

# ✅ 正确格式（Vercel + asyncpg）
DATABASE_URL_MASTER=postgresql+asyncpg://user:pass@host:5432/db
```

### 第三步：配置阿里云白名单

由于 Vercel 的 IP 是动态的，需要在阿里云配置白名单：

#### RDS 白名单配置
1. 登录阿里云 RDS 控制台
2. 进入你的实例 → 数据安全性 → 白名单设置
3. 添加白名单组：
   - 名称：`vercel`
   - IP 地址：`0.0.0.0/0`（允许所有 IP）
   - ⚠️ 注意：生产环境建议使用更严格的配置

#### Redis 白名单配置
1. 登录阿里云 Redis 控制台
2. 进入你的实例 → 白名单设置
3. 添加白名单：`0.0.0.0/0`

### 第四步：部署

1. 在 Vercel 点击 "Deploy"
2. 等待构建完成（约 2-5 分钟）
3. 部署成功后会获得一个 URL：`https://your-project.vercel.app`

---

## 🧪 部署后测试

### 1. 测试健康检查

```bash
curl https://your-project.vercel.app/health
```

预期响应：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "platform": "Vercel Serverless"
}
```

### 2. 测试根端点

```bash
curl https://your-project.vercel.app/
```

预期响应：应该返回 API 信息和端点列表

### 3. 测试 API 文档

访问：`https://your-project.vercel.app/docs`

应该能看到 Swagger UI 文档界面

### 4. 测试视频展示接口

```bash
curl https://your-project.vercel.app/api/showcase/videos
```

---

## ⚠️ 常见问题和解决方案

### 问题 1: 部署失败 - ModuleNotFoundError

**原因**：依赖安装失败

**解决**：
1. 检查 `requirements.txt` 格式是否正确
2. 确保 `mangum` 已添加到依赖中
3. 查看 Vercel 部署日志查找具体缺失的包

### 问题 2: 500 错误 - 数据库连接失败

**原因**：数据库白名单或连接字符串问题

**解决**：
1. 检查阿里云 RDS 白名单是否添加了 `0.0.0.0/0`
2. 确认 `DATABASE_URL_MASTER` 使用 `postgresql+asyncpg://` 协议
3. 测试数据库是否可以从外网访问

### 问题 3: Redis 连接超时

**原因**：Redis 白名单限制

**解决**：
1. 检查阿里云 Redis 白名单配置
2. 确认 Redis 是否允许公网访问
3. 检查 `REDIS_URL` 格式是否正确

### 问题 4: CORS 错误

**原因**：CORS 配置不正确

**解决**：
1. 在 Vercel 环境变量中配置 `CORS_ALLOWED_ORIGINS`
2. 添加你的前端域名到允许列表
3. 确保包含协议（https://）

### 问题 5: 函数超时

**原因**：Vercel 免费版有 10 秒超时限制

**解决**：
1. 升级到 Vercel Pro（60 秒超时）
2. 优化长时间运行的任务（使用 Celery worker）

---

## 📊 监控和日志

### 查看日志

1. Vercel 控制台 → Deployments
2. 点击最新部署
3. 查看 "Function Logs"

### 设置告警

1. Vercel 控制台 → Settings → Notifications
2. 配置邮件告警：
   - Deployment failures
   - High error rates
   - Budget alerts

---

## 🔄 持续部署

### 自动部署

每次推送到 GitHub main 分支时，Vercel 会自动部署：

```bash
git add .
git commit -m "Update feature"
git push origin main

# Vercel 会自动检测并部署
```

### 预览部署

Pull Request 会自动创建预览部署，方便测试。

---

## ✅ 部署成功检查清单

部署完成后，确认以下所有项目：

- [ ] `/health` 端点返回 healthy
- [ ] `/docs` 可以访问 Swagger UI
- [ ] `/api/showcase/videos` 可以获取视频列表
- [ ] 数据库连接正常（检查日志）
- [ ] Redis 连接正常（检查日志）
- [ ] OSS 文件可以正常访问
- [ ] CORS 配置正确（前端可以调用 API）
- [ ] 环境变量全部配置完成

---

## 🎯 下一步

### 1. 配置自定义域名

参考 `VERCEL_DEPLOY.md` 中的域名配置部分

### 2. 配置 Cloudflare CDN

参考 `CLOUDFLARE_SETUP.md` 进行 CDN 配置

### 3. 部署 Celery Worker

Celery worker 需要单独部署（推荐 Railway 或阿里云 ECS）

---

**准备好了吗？开始部署吧！🚀**

有问题请查看 Vercel 部署日志或提交 Issue。
