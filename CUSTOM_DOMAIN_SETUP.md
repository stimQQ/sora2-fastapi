# 自定义域名配置指南 - api.sparkvideo.cc

## 目标
将 Vercel 部署的 FastAPI 后端绑定到自定义域名 `api.sparkvideo.cc`

---

## 前提条件

- ✅ Vercel 项目已成功部署
- ✅ 拥有域名 `sparkvideo.cc` 的管理权限
- ✅ 可以访问 DNS 管理后台

---

## 步骤 1: 在 Vercel 添加自定义域名

### 1.1 进入 Vercel 项目设置

1. 访问: https://vercel.com/dashboard
2. 选择你的项目
3. 点击顶部 **Settings** 标签
4. 点击左侧 **Domains**

### 1.2 添加域名

1. 在 "Add Domain" 输入框中输入: `api.sparkvideo.cc`
2. 点击 **Add** 按钮

### 1.3 获取 DNS 配置信息

Vercel 会显示需要添加的 DNS 记录，通常是以下之一：

**选项 A: CNAME 记录** (推荐)
```
Type: CNAME
Name: api
Value: cname.vercel-dns.com
```

**选项 B: A 记录**
```
Type: A
Name: api
Value: 76.76.21.21
```

**选项 C: ALIAS 记录** (某些 DNS 提供商支持)
```
Type: ALIAS
Name: api
Value: alias.vercel-dns.com
```

---

## 步骤 2: 配置 DNS 记录

### 如果使用 Cloudflare

1. 登录 Cloudflare: https://dash.cloudflare.com
2. 选择域名 `sparkvideo.cc`
3. 点击 **DNS** → **Records**
4. 点击 **Add record**

**添加 CNAME 记录**:
```
Type: CNAME
Name: api
Target: cname.vercel-dns.com
Proxy status: DNS only (灰色云朵) 或 Proxied (橙色云朵，推荐)
TTL: Auto
```

5. 点击 **Save**

### 如果使用阿里云 DNS

1. 登录阿里云: https://dns.console.aliyun.com
2. 找到域名 `sparkvideo.cc`
3. 点击 **解析设置**
4. 点击 **添加记录**

**添加 CNAME 记录**:
```
记录类型: CNAME
主机记录: api
解析线路: 默认
记录值: cname.vercel-dns.com
TTL: 10分钟
```

5. 点击 **确定**

### 如果使用腾讯云 DNSPod

1. 登录 DNSPod: https://console.dnspod.cn
2. 找到域名 `sparkvideo.cc`
3. 点击 **添加记录**

**添加 CNAME 记录**:
```
主机记录: api
记录类型: CNAME
线路类型: 默认
记录值: cname.vercel-dns.com
TTL: 600
```

4. 点击 **保存**

---

## 步骤 3: 等待 DNS 传播

DNS 记录传播需要时间：
- **最快**: 5-10 分钟
- **通常**: 30 分钟 - 2 小时
- **最慢**: 24-48 小时

### 检查 DNS 传播状态

#### 方法 1: 使用 dig 命令 (macOS/Linux)
```bash
dig api.sparkvideo.cc

# 应该看到 CNAME 记录指向 cname.vercel-dns.com
```

#### 方法 2: 使用 nslookup 命令 (Windows/macOS/Linux)
```bash
nslookup api.sparkvideo.cc

# 应该返回 Vercel 的 IP 地址
```

#### 方法 3: 在线工具
访问: https://dnschecker.org

输入域名: `api.sparkvideo.cc`

查看全球各地的 DNS 解析结果

---

## 步骤 4: 在 Vercel 验证域名

### 自动验证

通常 Vercel 会自动检测 DNS 配置并验证域名，这个过程需要：
- DNS 记录已生效
- SSL 证书已签发

### 手动检查

1. 返回 Vercel 项目 → Settings → Domains
2. 查看 `api.sparkvideo.cc` 的状态

**状态说明**:
- 🟡 **Pending**: DNS 记录未生效或正在验证
- 🟢 **Valid**: 域名已成功配置并可用
- 🔴 **Invalid**: DNS 配置错误

### 如果显示错误

点击域名右侧的 "⚠️" 图标查看详细错误信息，常见问题：

**错误 1: DNS 记录不正确**
- 检查 CNAME 记录值是否正确
- 确认 TTL 已过期（等待更长时间）

**错误 2: DNS 记录冲突**
- 删除旧的 A 记录或其他冲突记录
- 确保只有一条 `api` 的记录

**错误 3: 证书签发失败**
- 等待自动重试
- 或点击 "Refresh" 按钮手动触发

---

## 步骤 5: SSL/TLS 证书配置

### Vercel 自动签发证书

Vercel 会自动为自定义域名签发 Let's Encrypt SSL 证书：
- ✅ 免费
- ✅ 自动续期
- ✅ 支持通配符证书

### 等待证书签发

1. 在 Vercel Domains 页面查看证书状态
2. 通常需要 1-5 分钟
3. 证书签发后，域名状态变为 🟢 Valid

### 验证 SSL 证书

```bash
# 测试 HTTPS 访问
curl https://api.sparkvideo.cc/health

# 查看证书信息
openssl s_client -connect api.sparkvideo.cc:443 -servername api.sparkvideo.cc
```

---

## 步骤 6: 更新应用配置

### 6.1 更新 CORS 配置

在 Vercel 环境变量中添加新域名：

1. Vercel 项目 → Settings → Environment Variables
2. 找到 `CORS_ALLOWED_ORIGINS`
3. 添加 `https://api.sparkvideo.cc`

**示例**:
```
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://sparkvideo.cc,https://api.sparkvideo.cc
```

### 6.2 更新回调 URL

更新所有需要回调 URL 的配置：

**Sora API 回调**:
```
SORA_CALLBACK_URL=https://api.sparkvideo.cc/api/videos/sora/callback
```

**OAuth 回调**:
```
WECHAT_REDIRECT_URI=https://api.sparkvideo.cc/api/auth/wechat/callback
GOOGLE_REDIRECT_URI=https://api.sparkvideo.cc/api/auth/google/callback
```

**支付回调**:
```
WECHAT_PAY_NOTIFY_URL=https://api.sparkvideo.cc/api/payments/wechat/webhook
STRIPE_WEBHOOK_URL=https://api.sparkvideo.cc/api/payments/stripe/webhook
```

### 6.3 更新前端 API 地址

如果前端使用的是 Vercel 自动域名，需要更新为自定义域名：

**前端 .env 文件**:
```
NEXT_PUBLIC_API_URL=https://api.sparkvideo.cc
```

---

## 步骤 7: 测试自定义域名

### 基础测试

```bash
# 1. 健康检查
curl https://api.sparkvideo.cc/health

# 期望输出:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "environment": "production",
#   "platform": "Vercel Serverless"
# }

# 2. API 文档
curl https://api.sparkvideo.cc/docs

# 3. 根路径
curl https://api.sparkvideo.cc/

# 4. API 端点
curl https://api.sparkvideo.cc/api/showcase/videos
```

### 性能测试

```bash
# 测试响应时间
curl -w "\n\nTotal time: %{time_total}s\n" https://api.sparkvideo.cc/health

# 测试 SSL 握手时间
curl -w "\n\nConnect: %{time_connect}s\nSSL: %{time_appconnect}s\n" https://api.sparkvideo.cc/health
```

### 全面测试

使用测试脚本:
```bash
./quick_test.sh api.sparkvideo.cc
```

---

## 步骤 8: Cloudflare CDN 加速（可选）

如果你的域名使用 Cloudflare，可以启用 CDN 加速：

### 8.1 启用 Proxy（橙色云朵）

1. Cloudflare → DNS → Records
2. 找到 `api` 记录
3. 点击云朵图标，从灰色变为橙色
4. 保存

### 8.2 配置缓存规则

1. Cloudflare → 规则 → Page Rules
2. 创建新规则：

**规则 1: 静态资源缓存**
```
URL: api.sparkvideo.cc/static/*
设置:
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 month
  - Browser Cache TTL: 1 day
```

**规则 2: API 响应不缓存**
```
URL: api.sparkvideo.cc/api/*
设置:
  - Cache Level: Bypass
```

### 8.3 配置 SSL/TLS 模式

1. Cloudflare → SSL/TLS → 概述
2. 选择加密模式: **Full (strict)**

这确保 Cloudflare 和 Vercel 之间使用 HTTPS。

---

## 常见问题

### Q1: DNS 记录已添加，但 Vercel 显示 "Invalid"
**解决方法**:
1. 等待 10-30 分钟让 DNS 传播
2. 清除本地 DNS 缓存: `sudo dscacheutil -flushcache` (macOS)
3. 使用 https://dnschecker.org 验证 DNS 是否全球生效

### Q2: 证书签发失败
**解决方法**:
1. 确保 DNS 记录正确指向 Vercel
2. 删除任何 CAA 记录限制（如果有）
3. 等待 5-10 分钟后 Vercel 自动重试
4. 或手动点击 "Refresh" 触发重新签发

### Q3: 域名可以访问，但显示 404
**解决方法**:
1. 检查 Vercel 部署状态是否成功
2. 确认 `vercel.json` 配置正确
3. 测试默认域名是否正常（如 `xxx.vercel.app`）

### Q4: 使用 Cloudflare Proxy 后 SSL 错误
**解决方法**:
1. Cloudflare SSL/TLS 模式设置为 **Full (strict)**
2. 确保 Vercel 证书已签发
3. 等待 5 分钟让 Cloudflare 缓存更新

### Q5: 可以访问但很慢
**解决方法**:
1. 检查 Vercel 部署区域（建议 Singapore）
2. 启用 Cloudflare CDN（橙色云朵）
3. 优化 API 响应大小和数据库查询

---

## 验证清单

完成配置后，请检查：

- [ ] `https://api.sparkvideo.cc/health` 返回 200 OK
- [ ] `https://api.sparkvideo.cc/docs` 可以访问 API 文档
- [ ] SSL 证书有效（浏览器显示锁图标）
- [ ] 前端可以正常调用 API
- [ ] OAuth 回调 URL 已更新
- [ ] 支付回调 URL 已更新
- [ ] CORS 配置包含新域名

---

## 下一步

域名配置完成后：

1. ✅ 更新第三方服务的回调 URL：
   - WeChat OAuth
   - Google OAuth
   - WeChat Pay
   - Stripe

2. ✅ 配置监控和告警：
   - Uptime monitoring
   - Error tracking (Sentry)
   - Performance monitoring

3. ✅ 设置备份域名：
   - 保留 `xxx.vercel.app` 作为备用
   - 配置域名故障转移

4. ✅ 文档更新：
   - API 文档更新为新域名
   - README 更新

---

**配置完成！** 🎉

你的 FastAPI 后端现在可以通过 `https://api.sparkvideo.cc` 访问了。
