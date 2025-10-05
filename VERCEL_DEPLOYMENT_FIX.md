# Vercel 部署修复说明

## 问题描述

### 错误 1: TypeError: issubclass() arg 1 must be a class
```
TypeError: issubclass() arg 1 must be a class
Python process exited with exit status: 1
```

### 错误 2: 自动部署不工作
推送到 GitHub 后 Vercel 不自动触发部署

---

## 解决方案

### 修复 1: 改用 Vercel 推荐的配置方式

参考成功的项目 `sketchmagic-fastapi-backend`，做了以下更改：

#### 1.1 文件重命名
```bash
api/index.py → api/main.py
```

#### 1.2 移除 Mangum 适配器

**之前 (错误的方式)**:
```python
from mangum import Mangum

app = FastAPI(...)

handler = Mangum(app, lifespan="off")
```

**现在 (正确的方式)**:
```python
# 直接导出 FastAPI app，Vercel 可以直接使用 ASGI
app = FastAPI(...)

# 不需要 Mangum - FastAPI 本身就是 ASGI 应用
```

#### 1.3 更新 vercel.json

**之前 (使用 builds + routes)**:
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

**现在 (使用 rewrites + functions)**:
```json
{
  "version": 2,
  "regions": ["sin1"],
  "functions": {
    "api/main.py": {
      "maxDuration": 30
    }
  },
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/api/main.py"
    }
  ],
  "env": {
    "PYTHONUNBUFFERED": "1",
    "LOG_LEVEL": "INFO"
  }
}
```

#### 1.4 移除 requirements.txt 中的 mangum
```diff
- mangum==0.17.0
```

#### 1.5 添加调试输出
```python
print("="*60, flush=True)
print("[VERCEL] Serverless Entry Point Starting", flush=True)
print(f"[VERCEL] Python path: {sys.path[0]}", flush=True)
print(f"[VERCEL] Current directory: {os.getcwd()}", flush=True)
print("="*60, flush=True)
```

#### 1.6 禁用 Redis（serverless 环境）
```python
os.environ.update({
    "VERCEL": "1",
    "DISABLE_REDIS": "1"
})
```

---

## 核心差异对比

### builds vs rewrites

| 配置方式 | 适用场景 | 限制 |
|---------|----------|------|
| `builds` + `routes` | 传统方式，需要构建步骤 | 与 `functions` 冲突 |
| `rewrites` + `functions` | 现代方式，更灵活 | Vercel 推荐 |

### Mangum vs 直接使用 FastAPI

| 方式 | 工作原理 | 问题 |
|------|----------|------|
| Mangum | 将 ASGI 包装为 AWS Lambda handler | 在 Vercel 环境可能导致类型检查错误 |
| 直接使用 FastAPI | Vercel 原生支持 ASGI | 无额外依赖，更稳定 |

---

## 为什么这样修复有效？

1. **Vercel 原生支持 ASGI**:
   - Vercel 的 Python runtime 可以直接识别和运行 ASGI 应用
   - 不需要额外的适配器层（如 Mangum）

2. **rewrites 更现代**:
   - `rewrites` 是 Vercel 推荐的路由配置方式
   - 与 `functions` 配置兼容
   - 避免了 `builds` 和 `functions` 的冲突

3. **移除不必要的依赖**:
   - Mangum 是为 AWS Lambda 设计的
   - Vercel 有自己的 serverless 实现
   - 减少依赖可以减少部署问题

---

## 验证修复

### 本地测试
```bash
# 安装依赖
pip install -r requirements.txt

# 运行开发服务器
uvicorn main:app --reload
```

### Vercel 部署测试

提交并推送后，检查：

1. **部署日志**: https://vercel.com/dashboard → 你的项目 → Deployments
2. **查看日志中的输出**:
   ```
   [VERCEL] Serverless Entry Point Starting
   [VERCEL] ✓ Successfully imported all modules
   [VERCEL] ✓ FastAPI app created and ready
   ```

3. **测试 API**:
   ```bash
   # 健康检查
   curl https://your-domain.vercel.app/health

   # API 文档
   curl https://your-domain.vercel.app/docs
   ```

---

## 自动部署修复

如果推送后还是不自动部署，参考：`VERCEL_AUTO_DEPLOY_DIAGNOSIS.md`

**快速解决方法**:
1. Vercel 项目 → Settings → Git → **Disconnect**
2. 等待 10 秒
3. **Connect Git Repository** → 选择仓库
4. 确认 **Production Branch** = `main`
5. 测试推送

---

## 文件结构

修复后的项目结构：

```
fastapi-backend/
├── api/
│   └── main.py          # Vercel 入口点 (重命名自 index.py)
├── app/
│   ├── api/
│   ├── core/
│   ├── models/
│   └── ...
├── vercel.json          # 使用 rewrites + functions
├── requirements.txt     # 移除 mangum
└── ...
```

---

## 提交记录

```
452a57a - Fix Vercel deployment: use rewrites instead of builds, remove Mangum
```

**主要更改**:
- ✅ 重命名 `api/index.py` → `api/main.py`
- ✅ 移除 Mangum 适配器
- ✅ 更新 `vercel.json` 使用 `rewrites`
- ✅ 从 `requirements.txt` 移除 `mangum`
- ✅ 添加调试输出
- ✅ 设置 `DISABLE_REDIS=1`

---

## 参考项目

成功的配置参考：
- **项目**: `sketchmagic-fastapi-backend`
- **位置**: `/Users/crusialee/Desktop/SparkInc/010-Doodle-to-illustration/sketchmagic-fastapi-backend/`
- **关键文件**:
  - `vercel.json` - 使用 `rewrites` 配置
  - `api/main.py` - 直接导出 FastAPI app

---

## 常见问题

### Q1: 为什么不用 Mangum？
A: Mangum 是为 AWS Lambda 设计的，Vercel 有自己的 serverless 实现，可以直接运行 ASGI 应用。

### Q2: builds 和 rewrites 的区别？
A:
- `builds`: 需要明确的构建步骤，与 `functions` 冲突
- `rewrites`: URL 重写规则，更灵活，Vercel 推荐

### Q3: 为什么要禁用 Redis？
A: Vercel serverless 函数是无状态的，每次请求可能在不同的实例上运行，维护长连接的 Redis 客户端会导致问题。

### Q4: 如何在 Vercel 上使用 Redis？
A:
- 使用 Vercel KV (基于 Redis)
- 或使用外部 Redis 服务 (如 Upstash Redis)
- 配置连接池和超时策略

---

## 下一步

1. ✅ 部署成功后，配置自定义域名 `api.sparkvideo.cc`
2. ✅ 设置环境变量（数据库、OSS、Redis 等）
3. ✅ 配置 Cloudflare CDN 加速
4. ✅ 测试所有 API 端点
5. ✅ 设置监控和告警

---

**最后更新**: 2025-10-05
**修复状态**: ✅ 已修复并推送到 GitHub
