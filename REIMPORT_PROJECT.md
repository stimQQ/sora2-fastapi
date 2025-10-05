# 🔄 重新导入 Vercel 项目 - 完整指南

## 为什么要重新导入？

**当前状态**：
- ✅ Production Branch = `main` (正确)
- ✅ Ignored Build Step = `Automatic` (正确)
- ✅ Domain 已配置 = `api.sparkvideo.cc`
- ❌ 断开重连后还是不自动部署

**结论**：配置正确，但 Git Integration 底层连接损坏，需要完全重建。

---

## 📋 重新导入步骤

### 第一步：导出环境变量（5分钟）

#### 方法 1：手动复制（推荐）

1. Vercel 项目 → Settings → Environment Variables
2. 打开文本编辑器，创建文件 `vercel-env-backup.txt`
3. 逐个复制环境变量，格式如下：

```bash
# Database
DATABASE_URL_MASTER=你的值
DATABASE_URL_SLAVES=你的值

# Redis
REDIS_URL=你的值
CELERY_BROKER_URL=你的值
CELERY_RESULT_BACKEND=你的值

# Aliyun OSS
ALIYUN_OSS_ACCESS_KEY=你的值
ALIYUN_OSS_SECRET_KEY=你的值
ALIYUN_OSS_BUCKET=你的值
ALIYUN_OSS_ENDPOINT=你的值
ALIYUN_OSS_REGION=你的值

# Security
SECRET_KEY=你的值
JWT_SECRET_KEY=你的值

# API Keys
QWEN_VIDEO_API_KEY=你的值
PROXY_API_KEY=你的值
SORA_API_KEY=你的值
SORA_API_URL=你的值

# CORS
CORS_ALLOWED_ORIGINS=你的值

# Frontend
FRONTEND_URL=你的值

# 其他所有环境变量...
```

#### 方法 2：截图保存

1. 滚动环境变量页面
2. 对每个环境变量截图
3. 保存所有截图

#### 必需的环境变量清单

确保导出以下所有变量：

- [ ] `DATABASE_URL_MASTER`
- [ ] `DATABASE_URL_SLAVES`
- [ ] `REDIS_URL`
- [ ] `CELERY_BROKER_URL`
- [ ] `CELERY_RESULT_BACKEND`
- [ ] `ALIYUN_OSS_ACCESS_KEY`
- [ ] `ALIYUN_OSS_SECRET_KEY`
- [ ] `ALIYUN_OSS_BUCKET`
- [ ] `ALIYUN_OSS_ENDPOINT`
- [ ] `ALIYUN_OSS_REGION`
- [ ] `SECRET_KEY`
- [ ] `JWT_SECRET_KEY`
- [ ] `QWEN_VIDEO_API_KEY`
- [ ] `PROXY_API_KEY`
- [ ] `SORA_API_KEY`
- [ ] `SORA_API_URL`
- [ ] `SORA_CALLBACK_URL`
- [ ] `CORS_ALLOWED_ORIGINS`
- [ ] `FRONTEND_URL`
- [ ] 其他项目特定的变量...

---

### 第二步：删除当前项目（1分钟）

1. Vercel 项目 → **Settings**
2. 点击左侧 → **Advanced**
3. 滚动到页面最底部
4. 找到 **Delete Project** 部分（红色背景）
5. 点击 **Delete** 按钮
6. 在弹出的确认对话框中：
   - 输入项目名称确认
   - 点击 **Delete** 按钮确认删除

**重要提示**：
- 删除项目不会删除 GitHub 代码
- 删除项目不会删除数据库数据
- 删除项目只是删除 Vercel 的部署配置

---

### 第三步：从 GitHub 重新导入（3分钟）

#### 3.1 开始导入

1. 访问 Vercel 首页：https://vercel.com/new

2. 或者点击右上角 **Add New...** → **Project**

3. 在 "Import Git Repository" 页面：
   - 点击 **GitHub** 标签（如果不在的话）
   - 在搜索框输入：`sora2-fastapi`
   - 找到 **stimQQ/sora2-fastapi**
   - 点击 **Import** 按钮

#### 3.2 配置项目

在项目配置页面：

**Project Name**：
```
sora2-fastapi
（或保持默认）
```

**Framework Preset**：
```
Other
（保持默认）
```

**Root Directory**：
```
./
（保持默认）
```

**Build and Output Settings**：
- Build Command: 留空
- Output Directory: 留空
- Install Command: 留空

**这些都不需要配置，因为我们用的是 serverless functions**

---

### 第四步：配置环境变量（5分钟）

**重要**：必须在部署前配置环境变量！

#### 4.1 展开环境变量部分

在项目配置页面，找到 **Environment Variables** 部分，点击展开。

#### 4.2 添加环境变量

**方法 1：逐个添加**

1. 点击第一个输入框，输入变量名（如 `DATABASE_URL_MASTER`）
2. 在第二个输入框，输入变量值
3. 在 "Environment" 下拉菜单，选择：
   - **Production** (必选)
   - Preview (可选)
   - Development (可选)
4. 点击 **Add** 按钮
5. 重复以上步骤，添加所有环境变量

**方法 2：批量导入（推荐）**

1. 点击 **Paste .env** 标签（如果有的话）
2. 将你保存的环境变量文件内容粘贴进去：
   ```
   DATABASE_URL_MASTER=...
   DATABASE_URL_SLAVES=...
   REDIS_URL=...
   （所有变量）
   ```
3. 点击 **Add** 或 **Import**

#### 4.3 验证环境变量

确保所有必需的变量都已添加：
- 数据库连接
- Redis 连接
- OSS 配置
- API 密钥
- CORS 配置

---

### 第五步：部署（2-5分钟）

1. 确认所有环境变量已添加
2. 点击页面底部的 **Deploy** 按钮
3. Vercel 开始构建和部署

**部署过程**：
```
Initializing... (初始化)
  ↓
Building... (构建中)
  ↓
Deploying... (部署中)
  ↓
Ready! (完成)
```

等待 2-5 分钟，看到 "Congratulations!" 页面表示成功。

---

### 第六步：重新配置自定义域名（2分钟）

域名不会自动迁移，需要重新添加。

1. 部署成功后，进入项目
2. 点击 **Settings** → **Domains**
3. 在 "Add Domain" 输入框输入：`api.sparkvideo.cc`
4. 点击 **Add** 按钮
5. Vercel 会自动检测 DNS 配置
6. 等待 SSL 证书签发（1-5分钟）

**DNS 已经配置过**，所以这次会很快。

---

### 第七步：验证自动部署（1分钟）

重新导入后，Git Integration 会自动建立，现在测试：

```bash
# 创建测试提交
git commit --allow-empty -m "Test auto deploy after reimport: $(date +%s)"

# 推送
git push origin main
```

**立即查看 Vercel Deployments 页面**：
- 应该在 **10-30 秒内** 看到新的部署开始
- 状态：Building → Deploying → Ready

**如果看到新部署开始** → ✅ 自动部署修复成功！

---

## 🎯 成功标志

重新导入成功后，应该看到：

### Vercel 项目设置

- ✅ Production Branch = `main`
- ✅ Connected Git Repository = GitHub: stimQQ/sora2-fastapi
- ✅ Ignored Build Step = Automatic
- ✅ 所有环境变量已配置

### GitHub Webhook

- ✅ 存在 Vercel webhook
- ✅ Recent Deliveries 有记录
- ✅ 状态码 = 200 OK

### 自动部署测试

- ✅ 推送后 10-30 秒内自动开始部署
- ✅ 部署成功（Ready 状态）
- ✅ API 可访问（https://api.sparkvideo.cc/health）

---

## 📝 重新导入后的检查清单

- [ ] 项目已从 GitHub 重新导入
- [ ] 所有环境变量已配置
- [ ] Production Branch = `main`
- [ ] 首次部署成功
- [ ] 自定义域名 `api.sparkvideo.cc` 已重新添加
- [ ] SSL 证书已签发
- [ ] 测试推送自动触发部署
- [ ] API 健康检查正常：`https://api.sparkvideo.cc/health`
- [ ] API 文档可访问：`https://api.sparkvideo.cc/docs`

---

## 🚀 预期时间线

| 步骤 | 时间 | 说明 |
|------|------|------|
| 导出环境变量 | 5 分钟 | 手动复制或截图 |
| 删除项目 | 1 分钟 | 确认删除 |
| 重新导入 | 3 分钟 | 从 GitHub 导入 |
| 配置环境变量 | 5 分钟 | 粘贴所有变量 |
| 首次部署 | 2-5 分钟 | 等待完成 |
| 重新配置域名 | 2 分钟 | 添加并验证 |
| 测试自动部署 | 1 分钟 | 推送测试 |
| **总计** | **15-20 分钟** | **100% 解决问题** |

---

## ⚠️ 常见问题

### Q1: 删除项目会丢失数据吗？

**A**: 不会！
- ❌ 不会丢失：GitHub 代码、数据库数据、OSS 文件
- ✅ 需要重新配置：环境变量、自定义域名
- ℹ️ 会丢失：部署历史（但不影响生产环境）

### Q2: 环境变量忘记导出怎么办？

**A**: 如果已经删除项目，环境变量就找不回来了。但是：
- 数据库连接可以从 Aliyun RDS 控制台查看
- OSS 配置可以从 Aliyun OSS 控制台查看
- API 密钥需要重新生成或从其他地方找

### Q3: 重新导入后域名需要重新配置 DNS 吗？

**A**: 不需要！
- DNS CNAME 记录已经配置好，不需要改
- 只需要在 Vercel 重新添加域名
- Vercel 会自动检测 DNS 并签发证书

### Q4: 重新导入后自动部署还是不工作怎么办？

**A**: 几乎不可能！重新导入会完全重建 Git Integration。
- 如果真的不工作，联系 Vercel 支持
- 或检查 GitHub App 权限

---

## 📞 需要帮助？

如果重新导入过程中遇到问题：

1. **环境变量配置问题**：参考 `.env.example` 文件
2. **部署失败**：查看部署日志找到错误原因
3. **域名问题**：参考 `CUSTOM_DOMAIN_SETUP.md`
4. **其他问题**：提供错误截图

---

**准备好了就开始吧！导出环境变量 → 删除项目 → 重新导入 → 完成！** 🚀
