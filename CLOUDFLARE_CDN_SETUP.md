# Cloudflare CDN 配置指南

**项目**: Video Animation Platform (Wan2.2-Animate)
**CDN 服务商**: Cloudflare
**更新日期**: 2025-10-04

---

## 📋 目录

1. [为什么选择 Cloudflare](#1-为什么选择-cloudflare)
2. [域名准备](#2-域名准备)
3. [Cloudflare 账户设置](#3-cloudflare-账户设置)
4. [DNS 配置](#4-dns-配置)
5. [CDN 加速配置](#5-cdn-加速配置)
6. [后端代码调整](#6-后端代码调整)
7. [前端配置](#7-前端配置)
8. [性能优化](#8-性能优化)
9. [监控与测试](#9-监控与测试)

---

## 1. 为什么选择 Cloudflare

### ✅ 优势

| 特性 | 免费版 | Pro 版 ($20/月) | Business 版 ($200/月) |
|------|--------|----------------|---------------------|
| **全球节点** | 300+ | 300+ | 300+ |
| **流量** | 无限 | 无限 | 无限 |
| **DDoS 防护** | ✅ | ✅ 增强 | ✅ 高级 |
| **SSL/TLS** | ✅ 自动 | ✅ 自动 | ✅ 自动 |
| **页面规则** | 3 条 | 20 条 | 50 条 |
| **智能路由** | ❌ | ✅ Argo | ✅ Argo |
| **中国网络优化** | ❌ | ❌ | ✅ China Network |

### 📊 推荐方案

**初期推荐**: **免费版**
- 全球加速足够用
- 0 成本
- 自动 HTTPS

**用户增长后**: **Pro 版 ($20/月)**
- Argo 智能路由（降低 30% 延迟）
- 更好的缓存策略
- 高级分析

---

## 2. 域名准备

### 方案 A: 使用海外域名（推荐）

**已有域名**: `sparkvideo.cc`

**子域名规划**:
```
api.sparkvideo.cc          → 后端 API（源站，阿里云北京）
cdn-api.sparkvideo.cc      → Cloudflare CDN 加速域名
www.sparkvideo.cc          → 前端（Next.js on Vercel）
admin.sparkvideo.cc        → 后台管理（可选）
```

### 方案 B: 使用国内域名 + ICP 备案

**如果使用 .cn 域名**:
- ⚠️ 需要 ICP 备案
- ⚠️ Cloudflare 在中国大陆可能较慢
- ✅ 建议配合阿里云 CDN 使用

---

## 3. Cloudflare 账户设置

### 步骤 1: 注册 Cloudflare 账户

1. 访问 https://dash.cloudflare.com/sign-up
2. 使用邮箱注册
3. 验证邮箱

### 步骤 2: 添加站点

1. 点击 **Add a Site**
2. 输入域名: `sparkvideo.cc`
3. 选择计划:
   - **Free** (推荐先用免费版)
   - Pro ($20/月) - 需要 Argo 智能路由时升级

### 步骤 3: 更改 DNS 服务器

Cloudflare 会提供两个 DNS 服务器地址，例如：

```
alexa.ns.cloudflare.com
mark.ns.cloudflare.com
```

**在你的域名注册商（如 GoDaddy、阿里云）修改 DNS 服务器**:

```
旧的 DNS: ns1.aliyun.com, ns2.aliyun.com
新的 DNS: alexa.ns.cloudflare.com, mark.ns.cloudflare.com
```

⚠️ **DNS 生效时间**: 通常 5 分钟 - 24 小时

---

## 4. DNS 配置

### 在 Cloudflare DNS 面板添加记录

登录 Cloudflare → 选择域名 → DNS → Records

#### A 记录（指向源站服务器）

```
类型: A
名称: api
IPv4 地址: <你的阿里云服务器公网 IP>
代理状态: ✅ 已代理（Proxied） ← 重要！开启 CDN
TTL: Auto
```

**示例**:
```
A    api           47.95.123.45    Proxied    Auto
```

#### CNAME 记录（CDN 加速域名）

```
类型: CNAME
名称: cdn-api
目标: api.sparkvideo.cc
代理状态: ✅ 已代理（Proxied）
TTL: Auto
```

#### 前端域名（可选）

```
CNAME    www           sparkvideo.vercel.app    Proxied    Auto
```

### 最终 DNS 配置

```
记录类型    名称        值                        代理状态
─────────────────────────────────────────────────────────
A           api         47.95.123.45             Proxied ✅
CNAME       cdn-api     api.sparkvideo.cc        Proxied ✅
CNAME       www         sparkvideo.vercel.app    Proxied ✅
```

---

## 5. CDN 加速配置

### 5.1 SSL/TLS 设置

**路径**: SSL/TLS → Overview

**推荐配置**:
```
加密模式: Full (strict)  ← 推荐
```

**说明**:
- **Off**: 不加密（不推荐）
- **Flexible**: Cloudflare ↔ 用户加密，Cloudflare ↔ 源站不加密
- **Full**: 全程加密（源站可以用自签名证书）
- **Full (strict)**: 全程加密（源站必须用有效证书） ← **推荐**

### 5.2 缓存配置

**路径**: Caching → Configuration

#### 缓存级别
```
Caching Level: Standard
```

#### 浏览器缓存 TTL
```
Browser Cache TTL: 4 hours
```

#### 开发模式（调试时使用）
```
Development Mode: Off  （调试时临时开启）
```

### 5.3 页面规则 (Page Rules)

**路径**: Rules → Page Rules

免费版有 **3 条规则**，需要合理使用。

#### 规则 1: API 请求不缓存

```
URL: api.sparkvideo.cc/api/*

设置:
  - Cache Level: Bypass
  - Disable Performance
```

**说明**: API 动态接口不缓存，保证数据实时性

---

#### 规则 2: 静态资源缓存

```
URL: api.sparkvideo.cc/uploads/*

设置:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 month
  - Browser Cache TTL: 1 week
```

**说明**: 上传的图片视频缓存 1 个月

---

#### 规则 3: Swagger 文档缓存

```
URL: api.sparkvideo.cc/docs

设置:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 2 hours
```

**说明**: API 文档页面缓存 2 小时

---

### 5.4 速度优化

**路径**: Speed → Optimization

#### Auto Minify（自动压缩）
```
✅ JavaScript
✅ CSS
✅ HTML
```

#### Brotli 压缩
```
✅ 开启
```

#### Early Hints
```
✅ 开启（如果是 Pro 版）
```

---

### 5.5 防火墙规则

**路径**: Security → WAF → Custom rules

#### 规则 1: 阻止常见攻击

```
规则名称: Block SQL Injection
表达式: (http.request.uri.query contains "union select") or (http.request.uri.query contains "drop table")
操作: Block
```

#### 规则 2: 速率限制（Pro 版）

```
规则名称: Rate Limit API
表达式: (http.request.uri.path contains "/api/")
操作: Challenge (Managed)
速率: 100 requests / minute
```

---

## 6. 后端代码调整

### 6.1 更新 CORS 配置

编辑 `.env` 文件:

```bash
# 添加 Cloudflare CDN 域名到 CORS 白名单
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://sparkvideo.cc,https://api.sparkvideo.cc,https://cdn-api.sparkvideo.cc
```

### 6.2 信任 Cloudflare IP（获取真实 IP）

Cloudflare 会在请求头中添加 `CF-Connecting-IP`，需要获取用户真实 IP。

创建中间件 `app/middleware/cloudflare.py`:

```python
"""
Cloudflare middleware for getting real client IP.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class CloudflareMiddleware(BaseHTTPMiddleware):
    """
    Extract real client IP from Cloudflare headers.
    """

    async def dispatch(self, request: Request, call_next):
        # Get real IP from Cloudflare headers
        real_ip = (
            request.headers.get("CF-Connecting-IP")
            or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.client.host
        )

        # Store real IP in request state
        request.state.real_ip = real_ip

        # Add Cloudflare info to logs
        cf_ray = request.headers.get("CF-Ray")
        cf_country = request.headers.get("CF-IPCountry")

        if cf_ray:
            logger.debug(f"Cloudflare request: Ray={cf_ray}, IP={real_ip}, Country={cf_country}")

        response = await call_next(request)
        return response
```

### 6.3 注册中间件

编辑 `main.py`:

```python
from app.middleware.cloudflare import CloudflareMiddleware

# 添加 Cloudflare 中间件
app.add_middleware(CloudflareMiddleware)
```

### 6.4 获取用户真实 IP 的工具函数

创建 `app/utils/request.py`:

```python
"""
Request utilities.
"""
from fastapi import Request


def get_client_ip(request: Request) -> str:
    """
    Get real client IP address, considering Cloudflare proxy.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address
    """
    # Try to get from request state (set by CloudflareMiddleware)
    if hasattr(request.state, "real_ip"):
        return request.state.real_ip

    # Fallback to headers
    return (
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.client.host
        if request.client
        else "unknown"
    )


def get_cloudflare_info(request: Request) -> dict:
    """
    Get Cloudflare request information.

    Returns:
        dict: {
            'ray': Cloudflare Ray ID,
            'country': Country code,
            'colo': Datacenter location,
            'ip': Client IP
        }
    """
    return {
        "ray": request.headers.get("CF-Ray"),
        "country": request.headers.get("CF-IPCountry"),
        "colo": request.headers.get("CF-RAY", "").split("-")[-1] if request.headers.get("CF-Ray") else None,
        "ip": get_client_ip(request),
    }
```

### 6.5 更新速率限制中间件

编辑 `app/middleware/rate_limit.py`，使用真实 IP:

```python
from app.utils.request import get_client_ip

# 在速率限制中使用真实 IP
@limiter.limit("100/minute")
async def rate_limited_endpoint(request: Request):
    client_ip = get_client_ip(request)
    # ... 使用 client_ip 进行速率限制
```

---

## 7. 前端配置

### 7.1 Next.js 环境变量

创建/更新 `.env.local`:

```bash
# 使用 Cloudflare CDN 加速
NEXT_PUBLIC_API_BASE_URL=https://cdn-api.sparkvideo.cc/api

# 或者直连源站（调试时使用）
# NEXT_PUBLIC_API_BASE_URL=https://api.sparkvideo.cc/api

# API Key
NEXT_PUBLIC_API_KEY=your-api-key-here
```

### 7.2 动态切换 CDN

创建 `lib/api-config.ts`:

```typescript
// lib/api-config.ts

const USE_CDN = process.env.NEXT_PUBLIC_USE_CDN !== 'false'; // 默认使用 CDN

export const API_CONFIG = {
  // CDN 加速域名（全球用户）
  CDN_URL: 'https://cdn-api.sparkvideo.cc/api',

  // 直连源站（调试或 CDN 故障时）
  DIRECT_URL: 'https://api.sparkvideo.cc/api',

  // 当前使用的 URL
  BASE_URL: USE_CDN
    ? 'https://cdn-api.sparkvideo.cc/api'
    : 'https://api.sparkvideo.cc/api',
};

export const getApiUrl = () => {
  return API_CONFIG.BASE_URL;
};
```

### 7.3 使用示例

```typescript
// pages/api/videos/create.ts
import { getApiUrl } from '@/lib/api-config';

const response = await fetch(`${getApiUrl()}/videos/text-to-video`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(data),
});
```

---

## 8. 性能优化

### 8.1 Argo Smart Routing（Pro 版）

**路径**: Traffic → Argo Smart Routing

**价格**: $5/月 + $0.10/GB

**效果**:
- 降低 30% 延迟
- 智能选择最快路径
- 绕过网络拥堵

**配置**:
```
✅ Enable Argo Smart Routing
```

---

### 8.2 使用 Cloudflare Workers（高级）

创建边缘函数处理简单逻辑：

```javascript
// Cloudflare Worker 示例：缓存 API 响应
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const cache = caches.default
  const url = new URL(request.url)

  // 任务查询接口可以短时间缓存
  if (url.pathname.startsWith('/api/videos/tasks/')) {
    // 尝试从缓存获取
    let response = await cache.match(request)

    if (!response) {
      // 缓存未命中，请求源站
      response = await fetch(request)

      // 缓存 5 秒
      const headers = new Headers(response.headers)
      headers.set('Cache-Control', 'max-age=5')

      response = new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: headers
      })

      event.waitUntil(cache.put(request, response.clone()))
    }

    return response
  }

  // 其他请求直接转发
  return fetch(request)
}
```

---

### 8.3 HTTP/3 (QUIC)

**路径**: Network → HTTP/3 (with QUIC)

```
✅ 开启 HTTP/3
```

**效果**:
- 更快的连接建立
- 更好的移动网络性能

---

### 8.4 早期提示 (Early Hints)

**路径**: Speed → Optimization → Early Hints

```
✅ 开启 Early Hints（Pro 版）
```

**效果**:
- 提前发送资源提示
- 减少页面加载时间

---

## 9. 监控与测试

### 9.1 Cloudflare Analytics

**路径**: Analytics & Logs → Traffic

查看:
- 流量统计
- 请求数量
- 缓存命中率
- 带宽使用
- 威胁阻止数

---

### 9.2 性能测试

#### 测试 CDN 是否生效

```bash
# 查看响应头，应该包含 Cloudflare 标识
curl -I https://cdn-api.sparkvideo.cc/api/auth/me

# 响应头应该包含：
# cf-ray: xxxxx-HKG  （表示经过香港节点）
# cf-cache-status: DYNAMIC / HIT / MISS
# server: cloudflare
```

#### 全球延迟测试

使用工具：
- https://www.dotcom-tools.com/website-speed-test
- https://tools.keycdn.com/speed

**测试域名**:
- `https://cdn-api.sparkvideo.cc/api/auth/me`

---

### 9.3 监控告警

#### Cloudflare 通知

**路径**: Notifications

配置告警：
- 流量异常（DDoS 攻击）
- SSL 证书即将过期
- DNS 记录更改

---

### 9.4 日志查询（Enterprise 版）

**路径**: Analytics & Logs → Logs → Logpush

可以将日志推送到：
- AWS S3
- Google Cloud Storage
- Azure Blob Storage

---

## 10. 故障排查

### 问题 1: 522 错误（连接超时）

**原因**: Cloudflare 无法连接到源站

**解决**:
1. 检查源站服务器是否运行
2. 检查防火墙是否允许 Cloudflare IP
3. 检查 SSL 证书是否有效

**允许 Cloudflare IP**:
```bash
# 下载 Cloudflare IP 列表
curl https://www.cloudflare.com/ips-v4 > cloudflare-ips-v4.txt
curl https://www.cloudflare.com/ips-v6 > cloudflare-ips-v6.txt

# 在阿里云安全组添加这些 IP
```

---

### 问题 2: 缓存问题

**清除缓存**:

**路径**: Caching → Configuration → Purge Cache

选项:
- Purge Everything (清除所有)
- Purge by URL (清除指定 URL)
- Purge by Tag (按标签清除，Pro 版)

---

### 问题 3: CORS 错误

**检查**:
1. `.env` 中 CORS 配置是否包含 CDN 域名
2. Cloudflare Page Rules 是否影响了 CORS 头

**临时解决**: 使用 Cloudflare Workers 添加 CORS 头

---

### 问题 4: 中国大陆访问慢

**原因**: 免费版 Cloudflare 在中国大陆可能较慢

**解决方案**:
1. 升级到 Business 版 + China Network ($200/月)
2. 或配合阿里云 CDN 使用（双 CDN）
3. 或使用智能 DNS 分流（中国用户走阿里云，海外用户走 Cloudflare）

---

## 11. 成本估算

### 免费版（推荐初期）
```
月费用: $0
流量: 无限
带宽: 无限
节点: 300+
限制: 3 条页面规则
```

### Pro 版（用户增长后）
```
月费用: $20
+ Argo Smart Routing: $5 + $0.10/GB
+ 高级缓存策略
+ 更详细的分析
```

### Business 版（大规模）
```
月费用: $200
+ China Network 加速
+ 高级 DDoS 防护
+ 优先级支持
```

---

## 12. 检查清单

部署前检查：

- [ ] Cloudflare 账户已创建
- [ ] DNS 已迁移到 Cloudflare
- [ ] A 记录已添加并开启代理
- [ ] SSL/TLS 模式设置为 Full (strict)
- [ ] 页面规则已配置（API 不缓存，静态资源缓存）
- [ ] 后端 CORS 已更新
- [ ] Cloudflare 中间件已添加
- [ ] 前端 API_BASE_URL 已更新
- [ ] 测试 CDN 是否生效
- [ ] 监控已配置

---

## 13. 快速启动命令

### 1. 添加 Cloudflare 中间件

```bash
# 创建中间件文件
cat > app/middleware/cloudflare.py << 'EOF'
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class CloudflareMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        real_ip = request.headers.get("CF-Connecting-IP") or request.client.host
        request.state.real_ip = real_ip
        response = await call_next(request)
        return response
EOF
```

### 2. 更新环境变量

```bash
# 编辑 .env
echo "CORS_ALLOWED_ORIGINS=http://localhost:3000,https://sparkvideo.cc,https://api.sparkvideo.cc,https://cdn-api.sparkvideo.cc" >> .env
```

### 3. 测试 CDN

```bash
# 测试 CDN 是否生效
curl -I https://cdn-api.sparkvideo.cc/api/auth/me

# 应该看到：
# cf-ray: xxxxx
# server: cloudflare
```

---

## 附录

### A. Cloudflare IP 范围

**IPv4**:
```
173.245.48.0/20
103.21.244.0/22
103.22.200.0/22
103.31.4.0/22
141.101.64.0/18
108.162.192.0/18
190.93.240.0/20
188.114.96.0/20
197.234.240.0/22
198.41.128.0/17
162.158.0.0/15
104.16.0.0/13
104.24.0.0/14
172.64.0.0/13
131.0.72.0/22
```

### B. 有用的链接

- Cloudflare 状态页: https://www.cloudflarestatus.com/
- Cloudflare 文档: https://developers.cloudflare.com/
- Cloudflare 社区: https://community.cloudflare.com/
- Speed Test: https://speed.cloudflare.com/

---

**文档版本**: 1.0
**更新日期**: 2025-10-04
**作者**: Claude AI
