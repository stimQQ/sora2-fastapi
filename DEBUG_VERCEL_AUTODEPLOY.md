# 调试 Vercel 自动部署问题

## 当前状态
- ✅ Git Repository 已连接（显示 Disconnect）
- ❌ 推送后不自动部署

## 需要检查的配置项

### 1. Production Branch 设置

在 **Settings** → **Git** 页面，检查：

**Production Branch**: 应该是 `main`

如果显示其他分支（如 `master`），需要修改：
1. 点击 Production Branch 右侧的 **Edit**
2. 改为 `main`
3. 点击 **Save**

### 2. Ignored Build Step 设置

在 **Settings** → **Git** 页面，往下滚动找到：

**Ignored Build Step**

确认这里是**空的**或者设置为默认值。

如果有自定义命令（如 `git diff HEAD^ HEAD --quiet`），这会阻止自动部署。

**解决方法**：
- 点击 **Edit**
- 删除所有内容或设置为空
- 点击 **Save**

### 3. Auto Deploy from Git 设置

确认自动部署已启用：

在 **Settings** → **Git** 中，应该看到类似的选项：
- ✅ **Deploy Hooks Enabled**
- ✅ **Auto Deploy from Git**

如果有开关，确保都是**开启状态**。

### 4. 检查 GitHub Webhook

Vercel 通过 GitHub Webhook 接收推送通知。

**在 GitHub 检查**：
1. 访问：https://github.com/stimQQ/sora2-fastapi/settings/hooks
2. 应该看到一个 Vercel 的 webhook（URL 包含 `vercel.com`）
3. 点击进入查看状态：
   - **Recent Deliveries** 应该有记录
   - 检查最近的推送是否触发了 webhook
   - 如果显示 ❌ 错误，查看错误信息

**如果没有 Vercel webhook**：
说明连接有问题，需要重新连接：
1. Vercel Settings → Git → 点击 **Disconnect**
2. 再点击 **Connect Git Repository**
3. 重新选择仓库

### 5. 检查部署日志

在 Vercel **Deployments** 页面：

1. 查看所有部署记录
2. 找最新的几次推送对应的时间
3. 看是否有对应的部署记录

**如果没有**：说明 Webhook 没有触发
**如果有但失败**：查看失败日志

---

## 快速测试流程

### 测试 1：手动触发 Webhook

1. 进入 GitHub webhook 设置：
   https://github.com/stimQQ/sora2-fastapi/settings/hooks

2. 点击 Vercel webhook

3. 滚动到底部，点击 **Redeliver** 按钮（重新发送最近的一个推送事件）

4. 查看 Vercel Deployments 是否开始新部署

### 测试 2：小改动推送

```bash
# 修改一个无关紧要的文件
echo "$(date)" >> .vercel_deploy_test

# 提交
git add .vercel_deploy_test
git commit -m "Test webhook: $(date +%s)"
git push origin main

# 立即去 Vercel Deployments 页面查看
# 应该在 10-30 秒内看到新部署
```

### 测试 3：检查 Vercel 的通知设置

1. Vercel 右上角头像 → **Account Settings**
2. 左侧 → **Notifications**
3. 确认 **Deployment Notifications** 已启用
4. 如果有部署，你会收到邮件

---

## 常见问题排查

### 问题 A: 显示已连接但实际没触发

**原因**：连接配置损坏

**解决**：
1. Disconnect
2. 等待 10 秒
3. 重新 Connect
4. 测试推送

### 问题 B: Webhook 显示错误

**可能的错误**：
- `404 Not Found`：项目被删除或重命名
- `401 Unauthorized`：权限问题
- `500 Server Error`：Vercel 服务问题

**解决**：
- Disconnect 后重新连接
- 或删除项目重新导入

### 问题 C: Production Branch 不匹配

**症状**：推送到 `main` 但 Vercel 监听 `master`

**解决**：
1. Settings → Git → Production Branch
2. 改为 `main`
3. Save

---

## 终极解决方案

如果以上都不行，使用这个**100% 有效**的方法：

### 重新导入项目

1. **导出环境变量**（重要！）：
   - Settings → Environment Variables
   - 复制所有变量到文本文件保存

2. **删除当前项目**：
   - Settings → Advanced → Delete Project
   - 输入项目名确认删除

3. **从 GitHub 重新导入**：
   - Vercel 首页 → Add New → Project
   - Import Git Repository
   - 选择 `stimQQ/sora2-fastapi`
   - Import

4. **重新配置环境变量**：
   - 粘贴之前保存的环境变量

5. **Deploy**

这样建立的连接**绝对可靠**，一定会自动部署。

---

## 检查清单

请按顺序检查以下项目，并告诉我每一项的状态：

- [ ] **Production Branch** = `main` ？
- [ ] **Ignored Build Step** 是否为空？
- [ ] **GitHub Webhook** 是否存在？
- [ ] **Webhook Recent Deliveries** 有记录吗？
- [ ] **最近推送的 commit** 在 Webhook 中有对应记录吗？
- [ ] **测试推送后** Vercel Deployments 有新记录吗？

---

## 我的建议

**最快的解决方法**：

1. 先检查 **Production Branch** 是否是 `main`
2. 检查 **Ignored Build Step** 是否为空
3. 如果都正确，去 GitHub 查看 Webhook 状态
4. 如果 Webhook 有错误，Disconnect 然后重新 Connect
5. 如果还不行，删除项目重新导入（5 分钟搞定）

---

现在请检查上面的几个配置项，告诉我：
1. Production Branch 显示什么？
2. Ignored Build Step 里有内容吗？
3. GitHub Webhook 存在吗？有错误吗？
