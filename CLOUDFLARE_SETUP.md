# Cloudflare CDN 配置指南

## 快速开始

Cloudflare 将为你的 API 提供全球 CDN 加速，完全免费。

## 第一步：添加域名到 Cloudflare

### 1. 注册/登录 Cloudflare
访问 https://dash.cloudflare.com/sign-up

### 2. 添加站点
1. 点击 "添加站点"
2. 输入你的域名（如 `yourdomain.com`）
3. 选择 Free 计划
4. 点击继续

### 3. 更新域名服务器
Cloudflare 会显示两个域名服务器，例如：
```
molly.ns.cloudflare.com
randy.ns.cloudflare.com
```

去你的域名注册商（阿里云万网、GoDaddy 等）修改 DNS 服务器为 Cloudflare 提供的服务器。

等待 DNS 生效（通常 10-30 分钟）。

## 第二步：配置 DNS 记录

在 Cloudflare 控制台 → DNS → 记录，添加：

```
类型: CNAME
名称: api
目标: cname.vercel-dns.com
代理状态: 已代理（橙色云朵图标）
```

如果是根域名：
```
类型: CNAME
名称: @
目标: cname.vercel-dns.com
代理状态: 已代理
```

## 第三步：SSL/TLS 配置

1. 进入 SSL/TLS → 概述
2. 加密模式选择：**完全（严格）**
3. 进入 SSL/TLS → 边缘证书：
   - ✅ 始终使用 HTTPS：开启
   - ✅ 自动 HTTPS 重写：开启
   - TLS 最低版本：1.2

## 第四步：速度优化

### 自动优化
进入 速度 → 优化：
- ✅ Auto Minify（自动压缩）：勾选 JavaScript、CSS、HTML
- ✅ Brotli：开启
- ✅ Early Hints：开启

### HTTP 版本
进入 网络：
- ✅ HTTP/2：开启
- ✅ HTTP/3 (QUIC)：开启

## 第五步：缓存配置

### 缓存规则
进入 缓存 → 缓存规则 → 创建规则：

**规则 1：不缓存 API 响应**
```
规则名称: 绕过 API 缓存
匹配条件: URI 路径以 /api/ 开头
操作: 绕过缓存
```

**规则 2：缓存文档页面**
```
规则名称: 缓存文档
匹配条件: URI 路径匹配 /docs 或 /redoc
操作: 缓存所有内容
边缘 TTL: 1 小时
```

**规则 3：缓存健康检查**
```
规则名称: 缓存健康检查
匹配条件: URI 路径 = /health
操作: 缓存所有内容
边缘 TTL: 5 分钟
```

## 第六步：安全设置（可选）

### WAF（Web 应用防火墙）
进入 安全性 → WAF：
- 启用 Cloudflare 托管规则

### 速率限制
进入 安全性 → WAF → 速率限制规则：

```
规则名称: API 速率限制
匹配条件: URI 路径以 /api/ 开头
请求速率: 100 请求/分钟
操作: 阻止
持续时间: 1 分钟
```

## 第七步：验证配置

### 检查 DNS
```bash
# 检查 DNS 是否生效
dig api.yourdomain.com

# 或使用 nslookup
nslookup api.yourdomain.com
```

### 测试 HTTPS
```bash
# 测试 API
curl https://api.yourdomain.com/health

# 检查 Cloudflare 响应头
curl -I https://api.yourdomain.com/health | grep cf-ray
```

如果看到 `cf-ray` 响应头，说明 Cloudflare 已生效！

### 测试缓存
```bash
# 第一次请求
curl -I https://api.yourdomain.com/health

# 查看 cf-cache-status 响应头
# MISS = 未缓存
# HIT = 命中缓存
# BYPASS = 绕过缓存
```

## 性能优化建议

### 1. 使用 Argo Smart Routing（付费）
- 成本：$5/月 + $0.10/GB
- 提升：平均 30% 性能提升
- 适合：全球用户访问

### 2. 配置 Page Rules（免费 3 条）
进入 规则 → 页面规则：

**强制 HTTPS**
```
URL: http://*api.yourdomain.com/*
设置: 始终使用 HTTPS
```

### 3. 启用 WebSocket
进入 网络：
- ✅ WebSockets：开启

## 中国加速方案

### 方案 1：Cloudflare（海外用户）
Cloudflare 在中国速度一般，主要服务海外用户。

### 方案 2：双 CDN 架构（推荐）
- 国内用户：阿里云 CDN
- 海外用户：Cloudflare CDN

使用智能 DNS 分流：
- 阿里云 DNS 支持按地区解析
- 国内解析到阿里云 CDN
- 海外解析到 Cloudflare

## 监控与分析

### Cloudflare 分析
进入 分析 → 流量：
- 查看请求量、带宽使用
- 查看缓存命中率
- 查看威胁/安全事件

### 告警设置
进入 通知：
- 配置告警（流量激增、DDoS 攻击等）
- 设置邮件/Webhook 通知

## 常见问题

### Q: 为什么要用 Cloudflare？
A: 免费提供全球 CDN、DDoS 防护、SSL 证书。

### Q: 会影响阿里云服务吗？
A: 不会。Cloudflare 只是 CDN 层，后端仍使用阿里云 RDS、OSS、Redis。

### Q: 缓存会导致数据不一致吗？
A: 我们配置了绕过 API 缓存，只缓存静态内容（文档、健康检查），不影响业务数据。

### Q: 中国访问慢怎么办？
A: 考虑使用阿里云 CDN 作为国内加速方案，Cloudflare 服务海外用户。

### Q: 如何清除缓存？
A: Cloudflare 控制台 → 缓存 → 配置 → 清除缓存

## 成本

- **Free 计划**：完全免费，无限流量
- **Pro 计划**：$20/月，额外功能（图片优化、WAF 等）
- **推荐**：先用 Free，流量大了再升级

## 总结

完成以上配置后，你的架构将是：

```
用户
  ↓
Cloudflare CDN（全球加速、SSL、安全防护）
  ↓
Vercel Serverless（FastAPI 应用）
  ↓
阿里云 RDS + Redis + OSS（数据层）
```

所有改动：
- ✅ 零代码修改
- ✅ 继续使用阿里云服务
- ✅ 获得全球 CDN 加速
- ✅ 免费 SSL 证书
- ✅ DDoS 防护

开始享受全球加速吧！🚀
