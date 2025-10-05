# API 接口测试指南

部署到 Vercel 后，使用以下方法测试接口是否正常。

## 1. 获取你的 Vercel URL

部署成功后，Vercel 会提供一个 URL，格式如下：
```
https://your-project-name.vercel.app
```

或者你配置的自定义域名：
```
https://api.yourdomain.com
```

## 2. 基础健康检查

### 测试 1: 根端点
```bash
curl https://your-project.vercel.app/
```

**预期响应**：
```json
{
  "service": "Video Animation Platform",
  "version": "1.0.0",
  "environment": "production",
  "platform": "Vercel Serverless",
  "region": "Unknown",
  "documentation": {
    "swagger": "/docs",
    "redoc": "/redoc"
  },
  "endpoints": {
    "base": "/api",
    "auth": "/api/auth",
    "tasks": "/api/tasks",
    "videos": "/api/videos",
    "payments": "/api/payments",
    "users": "/api/users",
    "showcase": "/api/showcase"
  }
}
```

### 测试 2: 健康检查端点
```bash
curl https://your-project.vercel.app/health
```

**预期响应**：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "platform": "Vercel Serverless"
}
```

### 测试 3: API 文档
在浏览器访问：
```
https://your-project.vercel.app/docs
```

应该能看到 Swagger UI 交互式文档界面。

## 3. 测试视频展示接口

### 获取视频列表（无需认证）
```bash
curl https://your-project.vercel.app/api/showcase/videos
```

**预期响应**：
```json
{
  "total": 0,
  "page": 1,
  "page_size": 12,
  "total_pages": 0,
  "videos": []
}
```

如果数据库中有数据，会返回视频列表。

### 带分页参数
```bash
curl "https://your-project.vercel.app/api/showcase/videos?page=1&page_size=5"
```

## 4. 测试数据库连接

如果视频展示接口返回成功（即使是空数组），说明：
- ✅ 数据库连接正常
- ✅ 阿里云 RDS 白名单配置正确
- ✅ SQLAlchemy 查询正常

如果返回 500 错误：
- ❌ 检查数据库连接字符串
- ❌ 检查 RDS 白名单配置
- ❌ 查看 Vercel 函数日志

## 5. 使用 httpie 测试（推荐）

安装 httpie：
```bash
brew install httpie  # macOS
# 或
pip install httpie
```

测试命令：
```bash
# 更美观的输出
http https://your-project.vercel.app/health

# 测试视频接口
http https://your-project.vercel.app/api/showcase/videos

# 带参数
http https://your-project.vercel.app/api/showcase/videos page==1 page_size==5
```

## 6. 使用 Postman 测试

### 导入到 Postman

创建一个新的 Collection，添加以下请求：

#### Request 1: Health Check
```
GET https://your-project.vercel.app/health
```

#### Request 2: Get Videos
```
GET https://your-project.vercel.app/api/showcase/videos?page=1&page_size=12
```

#### Request 3: API Docs
```
GET https://your-project.vercel.app/docs
```

## 7. 浏览器直接测试

在浏览器地址栏输入以下 URL：

### 健康检查
```
https://your-project.vercel.app/health
```

### 视频列表
```
https://your-project.vercel.app/api/showcase/videos
```

### API 文档
```
https://your-project.vercel.app/docs
```

## 8. JavaScript Fetch 测试

在浏览器控制台运行：

```javascript
// 测试健康检查
fetch('https://your-project.vercel.app/health')
  .then(r => r.json())
  .then(data => console.log(data))

// 测试视频列表
fetch('https://your-project.vercel.app/api/showcase/videos')
  .then(r => r.json())
  .then(data => console.log(data))
```

## 9. 测试 CORS

如果你的前端需要调用 API，测试 CORS 配置：

```javascript
fetch('https://your-project.vercel.app/api/showcase/videos', {
  method: 'GET',
  headers: {
    'Origin': 'https://yourdomain.com'  // 你的前端域名
  }
})
.then(r => r.json())
.then(data => console.log('CORS OK:', data))
.catch(err => console.error('CORS Error:', err))
```

## 10. 完整测试脚本

创建 `test_vercel.sh`：

```bash
#!/bin/bash

API_URL="https://your-project.vercel.app"

echo "======================================"
echo "Vercel API 测试"
echo "======================================"
echo ""

echo "1. 测试根端点..."
curl -s "$API_URL/" | jq .
echo ""

echo "2. 测试健康检查..."
curl -s "$API_URL/health" | jq .
echo ""

echo "3. 测试视频列表..."
curl -s "$API_URL/api/showcase/videos" | jq .
echo ""

echo "4. 测试 API 文档..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/docs")
if [ $STATUS -eq 200 ]; then
    echo "✓ API 文档可访问 (HTTP $STATUS)"
else
    echo "✗ API 文档访问失败 (HTTP $STATUS)"
fi
echo ""

echo "======================================"
echo "测试完成！"
echo "======================================"
```

使用：
```bash
chmod +x test_vercel.sh
./test_vercel.sh
```

## 11. 检查响应头

查看 Cloudflare 是否生效：

```bash
curl -I https://your-project.vercel.app/health
```

应该看到类似这样的响应头：
```
HTTP/2 200
content-type: application/json
cf-ray: xxxxx-HKG
cf-cache-status: DYNAMIC
server: cloudflare
```

如果看到 `cf-ray` 和 `server: cloudflare`，说明 Cloudflare CDN 已生效。

## 12. 性能测试

测试响应时间：

```bash
curl -w "\nTime: %{time_total}s\n" -o /dev/null -s https://your-project.vercel.app/health
```

## 常见错误和解决方案

### 错误 1: 500 Internal Server Error

**原因**: 数据库连接失败

**检查**:
1. Vercel 环境变量是否配置正确
2. 阿里云 RDS 白名单是否包含 `0.0.0.0/0`
3. 查看 Vercel 函数日志

### 错误 2: 502 Bad Gateway

**原因**: 函数超时或崩溃

**检查**:
1. 查看 Vercel 函数日志
2. 检查是否有导入错误
3. 确认所有依赖都在 requirements.txt 中

### 错误 3: 404 Not Found

**原因**: 路由配置错误

**检查**:
1. 确认 `vercel.json` 配置正确
2. 确认 API 路由路径正确

### 错误 4: CORS Error

**原因**: CORS 配置不正确

**解决**:
1. 在 Vercel 环境变量中设置 `CORS_ALLOWED_ORIGINS`
2. 包含你的前端域名

## 13. 查看日志

### Vercel 控制台
1. 进入 Vercel 项目
2. Deployments → 选择最新部署
3. Functions → View Logs

### 实时日志
```bash
# 安装 Vercel CLI
npm i -g vercel

# 登录
vercel login

# 查看实时日志
vercel logs
```

## 14. 下一步

如果所有测试通过：
- ✅ 配置自定义域名
- ✅ 设置 Cloudflare CDN
- ✅ 部署 Celery Worker（如果需要后台任务）
- ✅ 添加监控和告警

---

**测试完成后，你的 API 就可以正式使用了！** 🎉
