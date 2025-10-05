# Vercel 自动部署诊断和修复指南

## 当前状态
- ✅ 代码已推送到 GitHub (`main` 分支)
- ✅ Vercel 显示 Git 已连接 (显示 "Disconnect" 按钮)
- ❌ 推送后不自动触发部署

最新提交: `611a5f6 - Test auto deploy trigger: 1759628162`

---

## 问题诊断步骤

### 第一步：检查 Vercel Production Branch 设置

**必须检查这个！这是最常见的原因**

1. 打开 Vercel 控制台: https://vercel.com/dashboard
2. 选择你的项目
3. 点击 **Settings** 标签
4. 点击左侧 **Git**
5. 查看 **Production Branch**

**应该显示**: `main`

**如果显示其他** (比如 `master`):
- 点击 Production Branch 右侧的编辑按钮
- 改为 `main`
- 点击 Save
- 然后测试推送

---

### 第二步：检查 Ignored Build Step

在同一个 **Settings** → **Git** 页面，往下滚动:

找到 **Ignored Build Step** 配置

**应该是**: 空的 或者 显示 `(default)`

**如果有内容** (比如 `git diff HEAD^ HEAD --quiet`):
- 这会阻止所有部署！
- 点击 Edit
- 删除所有内容
- Save
- 然后测试推送

---

### 第三步：检查 GitHub Webhook

1. 访问: https://github.com/stimQQ/sora2-fastapi/settings/hooks
2. 应该看到一个 Vercel 的 webhook (URL 包含 `vercel.com`)
3. 点击进入查看状态

**检查项**:
- ✅ Webhook 存在
- ✅ Recent Deliveries 有记录
- ✅ 最近的推送有对应的 delivery
- ✅ Status 显示绿色勾号 (200 OK)

**如果没有 Vercel webhook**:
- 说明连接有问题
- 需要 Disconnect 然后重新 Connect

**如果 webhook 有错误** (红色 X):
- 查看错误详情
- 如果是 404/401 错误 → 重新连接
- 如果是 500 错误 → Vercel 服务问题

---

## 修复方案

### 方案 A: Disconnect 并重新连接 (推荐)

**这个方法 90% 能解决问题**

1. Vercel 项目 → Settings → Git
2. 点击 **Disconnect** 按钮
3. 确认断开
4. 等待 10 秒
5. 点击 **Connect Git Repository**
6. 选择 GitHub
7. 选择 `stimQQ/sora2-fastapi`
8. 点击 Connect
9. **确认** Production Branch 设置为 `main`
10. 测试推送

### 方案 B: 手动触发 Webhook (测试用)

1. 进入 GitHub: https://github.com/stimQQ/sora2-fastapi/settings/hooks
2. 点击 Vercel webhook
3. 滚动到底部
4. 点击最近的一个 delivery 右侧的 **Redeliver** 按钮
5. 立即查看 Vercel Deployments 页面
6. 应该看到新部署开始

### 方案 C: 删除项目重新导入 (终极方案)

**100% 有效，但需要重新配置环境变量**

准备工作:
1. 导出所有环境变量 (Settings → Environment Variables)
2. 复制到文本文件保存

删除步骤:
1. Settings → Advanced → Delete Project
2. 输入项目名确认

重新导入:
1. Vercel 首页 → Add New → Project
2. Import Git Repository
3. 选择 `stimQQ/sora2-fastapi`
4. Import
5. 配置环境变量 (粘贴之前保存的)
6. Deploy

---

## 快速测试

完成修复后，立即测试:

```bash
# 创建空提交
git commit --allow-empty -m "Test auto deploy: $(date +%s)"

# 推送
git push origin main

# 立即打开 Vercel Deployments 页面
# 应该在 10-30 秒内看到新部署开始
```

**同时观察**:
- Vercel Deployments 页面 (应该有新部署)
- GitHub Webhook Recent Deliveries (应该有新记录)

---

## 常见错误原因总结

| 原因 | 症状 | 解决方法 |
|------|------|----------|
| Production Branch = `master` | 推送 `main` 不部署 | 改为 `main` |
| Ignored Build Step 有内容 | 所有推送都被忽略 | 清空配置 |
| Webhook 损坏 | 推送后没反应 | Disconnect → Reconnect |
| 首次通过 CLI 部署 | 没建立 Git Integration | 从 GitHub 重新导入项目 |
| Webhook 权限错误 | Webhook 404/401 | 重新授权连接 |

---

## 现在立即做这个

### 最简单的诊断方法:

1. **打开两个浏览器标签**:
   - 标签 1: Vercel → 你的项目 → Deployments
   - 标签 2: https://github.com/stimQQ/sora2-fastapi/settings/hooks

2. **执行测试推送**:
```bash
git commit --allow-empty -m "Test webhook: $(date +%s)"
git push origin main
```

3. **观察反应** (30秒内):
   - 标签 2 (GitHub): Webhook Recent Deliveries 应该有新记录
   - 标签 1 (Vercel): Deployments 应该有新部署开始

4. **判断结果**:
   - ✅ 两个都有反应 → 自动部署正常工作
   - ❌ GitHub 有，Vercel 没有 → Disconnect 重新 Connect
   - ❌ 两个都没有 → 检查 Production Branch 和 Ignored Build Step
   - ❌ GitHub 有但显示错误 → 查看错误信息，可能需要重新授权

---

## 需要你提供的信息

请告诉我:

1. **Production Branch** 显示什么? (应该是 `main`)
2. **Ignored Build Step** 里有内容吗? (应该为空)
3. **GitHub Webhook** 存在吗? 状态如何?
4. **Recent Deliveries** 有最近推送的记录吗?

或者直接执行上面的测试推送，告诉我两个标签页的反应。

---

## 我的推荐

**最快解决方案**:

如果你不想一个个检查，直接这样做:

1. Vercel Settings → Git → **Disconnect**
2. 等待 10 秒
3. **Connect Git Repository** → 选择 `stimQQ/sora2-fastapi`
4. 确认 Production Branch = `main`
5. 测试推送

这个方法通常能解决 90% 的自动部署问题。

如果还不行，就用终极方案：删除项目重新导入（5分钟搞定，100%有效）。
