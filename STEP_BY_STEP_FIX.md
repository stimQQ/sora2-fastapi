# 🔧 逐步修复 Vercel 自动部署 - 详细图文指南

## 问题：Disconnect/Reconnect 后仍然不自动部署

这说明配置有问题。我们需要逐步检查和修复。

---

## 📍 第一步：找到并设置 Production Branch

### 1.1 访问 Vercel 项目设置

1. 打开浏览器访问：https://vercel.com/dashboard
2. 在项目列表中找到你的项目（名称可能是 `sora2-fastapi` 或其他）
3. **点击项目名称**进入项目详情页

### 1.2 进入 Git 设置

1. 在项目页面顶部，点击 **Settings** 标签
2. 在左侧菜单中，点击 **Git**

### 1.3 找到 Production Branch

在 Git 设置页面，你会看到以下几个部分：

```
┌─────────────────────────────────────────┐
│ Connected Git Repository                │
│ ├─ GitHub                               │
│ └─ stimQQ/sora2-fastapi                 │
│    [Disconnect 按钮]                    │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Production Branch                       │  ← 这个很重要！
│ The Git branch used for Production      │
│ Deployments                             │
│                                         │
│ [当前显示的分支名]  [Edit 按钮]        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Deploy Hooks                            │
│ ...                                     │
└─────────────────────────────────────────┘
```

### 1.4 检查并修改 Production Branch

**查看当前值**：
- 应该显示：`main`
- 如果显示：`master` 或其他 → **需要修改！**

**修改步骤**：
1. 点击 Production Branch 右侧的 **Edit** 按钮（或铅笔图标 ✏️）
2. 在弹出的输入框或下拉菜单中，输入或选择：`main`
3. 点击 **Save** 或 **Update** 按钮
4. 等待确认消息

---

## 📍 第二步：检查 Ignored Build Step

### 2.1 在同一个 Git 设置页面往下滚动

找到这个部分：

```
┌─────────────────────────────────────────┐
│ Ignored Build Step                      │  ← 这个也很重要！
│ Command to determine if a build should  │
│ be skipped                              │
│                                         │
│ [                                  ]    │
│ └─ 这里应该是空的                       │
│    [Edit 按钮]                          │
└─────────────────────────────────────────┘
```

**检查**：
- 应该显示：**空白** 或 `(default)` 或 `git diff HEAD^ HEAD --quiet .`
- 如果有其他内容（特别是会始终返回 true 的命令）→ **需要清空！**

**修改步骤**（如果有内容）：
1. 点击 **Edit** 按钮
2. **删除所有内容**，让输入框变为空白
3. 点击 **Save**

---

## 📍 第三步：检查 GitHub Webhook

### 3.1 访问 GitHub Webhook 设置

1. 打开新标签页，访问：
   ```
   https://github.com/stimQQ/sora2-fastapi/settings/hooks
   ```

2. 你应该看到 Webhooks 列表

### 3.2 查找 Vercel Webhook

在列表中找到 Vercel 的 webhook：

```
Webhooks / Manage webhook

• https://api.vercel.com/v1/integrations/deploy/...  ← Vercel webhook
  ✓ Active (绿色勾号)
  或
  ✗ Failed (红色 X)
```

### 3.3 检查 Webhook 详情

1. **点击 Vercel webhook** 进入详情页
2. 查看 **Recent Deliveries** 部分

**如果有 Recent Deliveries**：
- 点击最近的一个（显示时间戳）
- 查看 **Response** 标签
- 检查状态码：
  - ✅ **200 OK**: 正常
  - ❌ **404 Not Found**: 项目已删除或 URL 失效
  - ❌ **401 Unauthorized**: 权限问题
  - ❌ **500 Server Error**: Vercel 服务问题

**如果没有 Recent Deliveries**：
- 说明 GitHub 根本没有触发 webhook
- 可能是 webhook 配置损坏

---

## 🎯 第四步：根据检查结果采取行动

### 情况 A：Production Branch 是 main，Ignored Build Step 为空，但还是不部署

**问题**：Webhook 可能损坏或没有触发

**解决方案**：手动触发 webhook 测试

1. 在 GitHub Webhook 详情页
2. 滚动到底部
3. 找到最近的一个 Delivery（如果有）
4. 点击右侧的 **Redeliver** 按钮
5. 确认重新发送
6. **立即去 Vercel Deployments 页面查看**
7. 应该看到新的部署开始

**如果 Redeliver 触发了部署**：
- 说明 webhook 工作，但 Git push 没有触发
- 需要检查 webhook 的触发条件

**如果 Redeliver 也不触发部署**：
- 说明 webhook 完全损坏
- 需要重新导入项目

### 情况 B：Production Branch 不是 main

**解决方案**：
1. 改为 `main`
2. 保存
3. 测试推送：
   ```bash
   git commit --allow-empty -m "Test after branch fix: $(date +%s)"
   git push origin main
   ```

### 情况 C：Ignored Build Step 有内容

**解决方案**：
1. 清空内容
2. 保存
3. 测试推送（同上）

### 情况 D：没有 Vercel Webhook

**问题**：Git Integration 根本没有建立

**解决方案**：删除项目重新导入（见第五步）

---

## 🚨 第五步：终极方案 - 删除并重新导入项目

如果以上都不行，这是 **100% 有效** 的方法。

### 5.1 准备工作（非常重要！）

**导出环境变量**：

1. Vercel 项目 → Settings → Environment Variables
2. **逐个复制所有环境变量**到文本文件，格式如下：

```bash
# 保存为 vercel-env-backup.txt

DATABASE_URL_MASTER=postgresql+asyncpg://...
DATABASE_URL_SLAVES=postgresql+asyncpg://...
REDIS_URL=redis://...
CELERY_BROKER_URL=redis://...
CELERY_RESULT_BACKEND=redis://...
ALIYUN_OSS_ACCESS_KEY=...
ALIYUN_OSS_SECRET_KEY=...
ALIYUN_OSS_BUCKET=...
ALIYUN_OSS_ENDPOINT=...
ALIYUN_OSS_REGION=...
SECRET_KEY=...
JWT_SECRET_KEY=...
QWEN_VIDEO_API_KEY=...
PROXY_API_KEY=...
SORA_API_KEY=...
SORA_API_URL=...
CORS_ALLOWED_ORIGINS=...
FRONTEND_URL=...

# 等等... 复制所有的环境变量！
```

**或者直接截图保存所有环境变量页面**

### 5.2 删除当前项目

1. Vercel 项目 → Settings → Advanced
2. 滚动到页面最底部
3. 找到 **Delete Project** 部分（红色区域）
4. 点击 **Delete** 按钮
5. 在弹出的对话框中：
   - 输入项目名称确认（例如 `sora2-fastapi`）
   - 点击 **Delete** 确认删除

### 5.3 从 GitHub 重新导入项目

1. 访问 Vercel 首页：https://vercel.com/new

2. 点击 **Add New...** 按钮（右上角）

3. 选择 **Project**

4. 在 "Import Git Repository" 部分：
   - 点击 **GitHub** 标签
   - 找到 **stimQQ/sora2-fastapi**
   - 点击 **Import** 按钮

5. 在配置页面：

   **项目名称**：保持默认或自定义

   **Framework Preset**：选择 `Other`

   **Root Directory**：保持默认 `./`

   **Build Command**：留空（我们不需要）

   **Output Directory**：留空

   **Install Command**：留空

6. **重要：配置环境变量**

   - 点击展开 **Environment Variables**
   - 点击 **Add** 按钮
   - 逐个添加之前保存的环境变量：
     ```
     Name: DATABASE_URL_MASTER
     Value: postgresql+asyncpg://...

     Name: REDIS_URL
     Value: redis://...

     ... （依次添加所有变量）
     ```

7. 确认所有环境变量都已添加后，点击 **Deploy** 按钮

### 5.4 等待首次部署完成

1. Vercel 会开始构建和部署
2. 等待 2-5 分钟
3. 看到 "Congratulations!" 页面表示成功

### 5.5 验证自动部署

重新导入后，立即测试：

```bash
git commit --allow-empty -m "Test auto deploy after reimport: $(date +%s)"
git push origin main
```

**立即查看 Vercel Deployments 页面**：
- 应该在 10-30 秒内看到新的部署开始
- 这次肯定会自动部署！

---

## 📊 检查清单

完成修复后，确认以下项目：

- [ ] Production Branch = `main`
- [ ] Ignored Build Step 为空
- [ ] GitHub 有 Vercel webhook
- [ ] Webhook Recent Deliveries 有记录
- [ ] 测试推送后 Vercel 自动开始部署
- [ ] 部署成功（状态 Ready）
- [ ] API 可以访问（https://your-domain.vercel.app/health）

---

## 🔍 现在请告诉我

请按照上述步骤检查后，告诉我：

### 检查结果：

1. **Production Branch 当前显示**：_____________（填写）

2. **Ignored Build Step 内容**：_____________（填写 "空白" 或具体内容）

3. **GitHub Webhook 状态**：
   - [ ] 存在
   - [ ] 不存在
   - 如果存在，最近的 delivery 状态码：_____________

4. **手动触发 Redeliver 后**：
   - [ ] Vercel 开始部署了
   - [ ] Vercel 没反应

5. **你选择的解决方案**：
   - [ ] 修改 Production Branch 为 main
   - [ ] 清空 Ignored Build Step
   - [ ] 准备删除重新导入项目

---

## ⚡ 快速决策树

```
开始
  │
  ├─ Production Branch 不是 main？
  │   └─ 改为 main → 测试推送 → 成功？结束 : 继续
  │
  ├─ Ignored Build Step 有内容？
  │   └─ 清空 → 测试推送 → 成功？结束 : 继续
  │
  ├─ 没有 GitHub Webhook？
  │   └─ 删除重新导入项目 → 结束
  │
  ├─ Webhook 状态不是 200？
  │   └─ 删除重新导入项目 → 结束
  │
  └─ 以上都正常但还是不部署？
      └─ 删除重新导入项目 → 结束（100%成功）
```

---

**告诉我检查结果，我会根据情况指导下一步！**
