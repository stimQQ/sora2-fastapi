# 修复 Vercel 自动部署 - 完整指南

## 🔴 当前问题
推送到 GitHub 后，Vercel 不自动部署

## ✅ 解决方案（按顺序尝试）

---

## 方法 1: 检查并修复 Git 连接（最可能）

### 步骤 1: 进入 Vercel 项目设置
1. 打开 Vercel 控制台
2. 选择你的项目
3. 点击 **Settings** 标签
4. 点击左侧 **Git**

### 步骤 2: 检查配置

你应该看到以下信息：

```
Connected Git Repository
Repository: stimQQ/sora2-fastapi
```

**关键配置项检查：**

#### ✅ Production Branch
应该显示：`main`

**如果显示其他**（如 `master`）：
1. 点击 Production Branch 右侧的铅笔图标（Edit）
2. 改为 `main`
3. 点击 Save

#### ✅ Ignored Build Step
应该是：**空的** 或显示 `(default)`

**如果有内容**：
1. 点击 Edit
2. 删除所有内容
3. Save

### 步骤 3: 重新连接（如果上面都正确但还不行）

1. 点击 **Disconnect** 按钮
2. 确认断开连接
3. 等待 5 秒
4. 点击 **Connect Git Repository**
5. 选择 **GitHub**
6. 选择 `stimQQ/sora2-fastapi`
7. 点击 **Connect**

---

## 方法 2: 检查 GitHub Webhook

### 访问 GitHub Webhook 设置
https://github.com/stimQQ/sora2-fastapi/settings/hooks

### 应该看到：
- 一个 Vercel webhook（URL 包含 `vercel.com`）
- 状态：绿色勾号 ✓

### 如果没有 Vercel webhook：
说明 Vercel 没有正确连接，回到方法 1 重新连接

### 如果 webhook 存在但有红色 X：
1. 点击进入 webhook
2. 查看 **Recent Deliveries**
3. 点击最近的一个查看错误
4. 如果显示 404/401 错误 → Disconnect 并重新连接

### 测试 Webhook：
1. 点击 webhook 进入详情页
2. 滚动到底部
3. 点击 **Redeliver** 按钮（重新发送最近的推送）
4. 立即查看 Vercel Deployments，应该看到新部署

---

## 方法 3: 使用 Vercel CLI 强制部署

如果自动部署一直不工作，使用 CLI 手动部署：

```bash
# 1. 安装 Vercel CLI
npm i -g vercel

# 2. 登录
vercel login

# 3. 进入项目目录
cd /Users/crusialee/Desktop/SparkInc/011-sparkvideo_sora/fastapi-backend（sora2）

# 4. 链接项目
vercel link

# 5. 部署到生产环境
vercel --prod

# 6. 之后每次都可以用这个命令部署
vercel --prod
```

---

## 方法 4: 删除并重新导入项目（终极方案）

这是 **100% 有效** 的方法，但需要重新配置环境变量。

### 准备工作：导出环境变量

1. Vercel 项目 → Settings → Environment Variables
2. 复制所有变量到文本文件保存（或截图）

**必需的环境变量列表**：
```
DATABASE_URL_MASTER
REDIS_URL
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
SECRET_KEY
QWEN_VIDEO_API_KEY
PROXY_API_KEY
SORA_API_KEY
ALIYUN_OSS_ACCESS_KEY
ALIYUN_OSS_SECRET_KEY
ALIYUN_OSS_BUCKET
ALIYUN_OSS_ENDPOINT
ALIYUN_OSS_REGION
JWT_SECRET_KEY
CORS_ALLOWED_ORIGINS
... (所有其他配置)
```

### 删除项目

1. Vercel 项目 → Settings → Advanced
2. 滚动到底部
3. 点击 **Delete Project**
4. 输入项目名称确认删除

### 重新导入

1. Vercel 首页：https://vercel.com/new
2. 点击 **Add New...** → **Project**
3. 选择 **Import Git Repository**
4. 找到 `stimQQ/sora2-fastapi`
5. 点击 **Import**

### 配置项目

**重要**：不要立即部署！

1. 在导入页面，先配置环境变量
2. 点击 **Environment Variables** 展开
3. 粘贴之前保存的所有环境变量
4. 确认无误后，点击 **Deploy**

### 完成！

重新导入后，Git Integration 会自动配置好，以后推送会自动部署。

---

## 快速测试自动部署

完成上述任一方法后，测试：

```bash
# 1. 创建测试文件
echo "Auto deploy test: $(date)" > .vercel_test

# 2. 提交推送
git add .vercel_test
git commit -m "Test auto deploy: $(date +%s)"
git push origin main

# 3. 立即查看 Vercel
# 打开: https://vercel.com/dashboard
# 进入项目 → Deployments
# 应该在 10-30 秒内看到新部署开始
```

---

## 我的建议

### 最快的方法（5 分钟）：

**如果你不怕重新配置环境变量** → 直接用方法 4（删除重新导入）

**如果想保留项目** → 先试方法 1（Disconnect 重新连接）

### 诊断步骤：

1. **先检查** Production Branch 和 Ignored Build Step
2. **再检查** GitHub Webhook 是否存在且正常
3. **如果都正常但不工作** → Disconnect 重新连接
4. **如果还不行** → 删除重新导入

---

## 常见错误原因

| 原因 | 症状 | 解决方法 |
|------|------|----------|
| Production Branch 设置错误 | 推送 main 不部署 | 改为 `main` |
| Ignored Build Step 有内容 | 所有推送都被忽略 | 清空 |
| Webhook 损坏 | 推送后没反应 | 重新连接 |
| 首次用 CLI 部署 | 没建立 Git 连接 | 重新从 GitHub 导入 |

---

## 现在立即做这个：

### 最简单的测试：

1. **打开两个浏览器标签**：
   - 标签 1：Vercel Deployments 页面
   - 标签 2：GitHub Webhook 页面

2. **执行测试推送**：
```bash
git commit --allow-empty -m "Test: $(date +%s)"
git push origin main
```

3. **观察**：
   - 标签 2（GitHub）：30 秒内应该看到 webhook 被触发（Recent Deliveries 有新记录）
   - 标签 1（Vercel）：30 秒内应该看到新部署开始

4. **结果判断**：
   - ✅ 两个都有反应 → 自动部署正常
   - ❌ GitHub 有，Vercel 没有 → Disconnect 重新连接
   - ❌ 两个都没有 → 检查 Production Branch 和 Ignored Build Step

---

现在请：

1. 告诉我 **Production Branch** 显示什么
2. 告诉我 **Ignored Build Step** 里有内容吗
3. 或者直接执行上面的测试推送，告诉我两个标签页的反应

如果你想最快解决，我建议直接 **Disconnect → 重新 Connect**，这通常能解决 90% 的问题！
