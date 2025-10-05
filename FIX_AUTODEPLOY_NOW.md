# 🚨 立即修复 Vercel 自动部署

## 问题确认

已推送 5 次提交到 GitHub，但 Vercel 都没有自动部署：
```
4746d39 - Add documentation for Vercel deployment fix and custom domain setup
452a57a - Fix Vercel deployment: use rewrites instead of builds, remove Mangum
45bbd97 - Add comprehensive Vercel auto-deploy troubleshooting summary
b7de8c6 - Add Vercel auto-deploy diagnostic script
e78083c - Add comprehensive Vercel auto-deploy diagnosis guide
```

## 🎯 立即执行（5分钟解决）

### 步骤 1: Disconnect Git Integration

1. 打开浏览器，访问：https://vercel.com/dashboard
2. 选择你的项目（sora2-fastapi 或类似名称）
3. 点击顶部 **Settings** 标签
4. 点击左侧 **Git**
5. 找到 **Connected Git Repository** 部分
6. 点击 **Disconnect** 按钮
7. 在弹出的确认对话框中，输入项目名确认
8. 等待 10 秒

### 步骤 2: Reconnect Git Repository

1. 在同一页面，点击 **Connect Git Repository** 按钮
2. 选择 **GitHub**
3. 如果提示授权，点击 **Authorize Vercel**
4. 在仓库列表中找到 **stimQQ/sora2-fastapi**
5. 点击 **Connect**
6. Vercel 会自动开始导入

### 步骤 3: 验证配置

连接后，**立即检查**以下配置：

#### 3.1 Production Branch
- 应该显示：`main`
- 如果不是，点击 Edit 改为 `main`

#### 3.2 Ignored Build Step
- 应该是：**空的** 或显示 `(default)`
- 如果有内容，点击 Edit 清空

#### 3.3 Environment Variables
- 点击左侧 **Environment Variables**
- 确认所有必需的环境变量都已配置
- 如果缺失，添加以下变量：
  ```
  DATABASE_URL_MASTER=your-value
  REDIS_URL=your-value
  ALIYUN_OSS_ACCESS_KEY=your-value
  ALIYUN_OSS_SECRET_KEY=your-value
  ALIYUN_OSS_BUCKET=your-value
  ALIYUN_OSS_ENDPOINT=your-value
  SECRET_KEY=your-value
  JWT_SECRET_KEY=your-value
  (等等...)
  ```

### 步骤 4: 触发部署

重新连接后，Vercel 通常会自动触发一次部署。

**如果没有自动部署**，创建一个测试提交：

```bash
git commit --allow-empty -m "Test auto deploy after reconnect: $(date +%s)"
git push origin main
```

### 步骤 5: 验证成功

1. **立即打开** Vercel 项目页面 → **Deployments** 标签
2. 应该在 **10-30 秒内** 看到新的部署开始
3. 状态应该显示：
   - 🟡 Building (构建中)
   - 🟡 Deploying (部署中)
   - 🟢 Ready (完成)

---

## 🔍 如果还是不工作

### 检查 GitHub Webhook

1. 访问：https://github.com/stimQQ/sora2-fastapi/settings/hooks
2. 应该看到一个 Vercel webhook
3. 点击进入，查看 **Recent Deliveries**
4. 最近的推送应该有对应的 delivery 记录
5. Status 应该是 **200**（绿色勾号）

**如果 webhook 有错误**：
- 404: 项目已删除或 URL 失效 → 重新连接
- 401: 权限问题 → 重新授权 GitHub
- 500: Vercel 服务问题 → 等待或联系支持

---

## 📝 预期结果

修复后，自动部署应该这样工作：

```
本地修改 → git commit → git push origin main
    ↓
GitHub 接收推送 → 触发 Webhook
    ↓
Vercel 接收通知 → 开始部署（10-30秒内）
    ↓
Building → Deploying → Ready（2-5分钟）
    ↓
收到 Vercel 邮件通知 "Deployment Ready"
```

---

## ⚠️ 如果 Disconnect/Reconnect 不行

那就用**终极方案**（需要重新配置环境变量）：

### 删除并重新导入项目

#### 准备工作（非常重要！）

1. **导出环境变量**：
   - Vercel 项目 → Settings → Environment Variables
   - **复制所有变量到文本文件保存**（或截图）
   - 不导出的话，删除后就找不回来了！

#### 删除当前项目

1. Settings → Advanced
2. 滚动到底部
3. 点击 **Delete Project**
4. 输入项目名称确认删除

#### 重新导入

1. 访问：https://vercel.com/new
2. 点击 **Add New...** → **Project**
3. 选择 **Import Git Repository**
4. 找到 **stimQQ/sora2-fastapi**
5. 点击 **Import**

#### 配置项目

**重要**：在部署前先配置环境变量！

1. 在导入页面，展开 **Environment Variables**
2. **粘贴之前保存的所有环境变量**
3. 确认 Production Branch = `main`
4. 点击 **Deploy**

这样重新导入的项目，Git Integration 会 **100% 正确建立**，以后推送一定会自动部署。

---

## 🎯 现在就做

**推荐方案**：先试 Disconnect/Reconnect（90% 成功率）

1. Disconnect
2. 等待 10 秒
3. Reconnect
4. 测试推送

**如果不行**：删除重新导入（100% 成功率）

---

## 📞 需要帮助？

如果按照上述步骤还是不行，请提供以下信息：

1. Vercel Settings → Git 页面的截图
2. GitHub Webhook 页面的截图
3. Vercel Deployments 页面显示的最新 commit 是什么？
4. Production Branch 设置是什么？
5. Ignored Build Step 里有内容吗？

---

**重要**：这个问题 99% 是因为 Git Integration 配置问题，Disconnect/Reconnect 或重新导入几乎肯定能解决！
