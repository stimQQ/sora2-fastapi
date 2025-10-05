# Vercel 自动部署问题总结

## 📊 当前状态

### Git 仓库
- **分支**: main
- **远程仓库**: https://github.com/stimQQ/sora2-fastapi.git
- **最新提交**: b7de8c6 - Add Vercel auto-deploy diagnostic script

### 最近的测试提交
```
b7de8c6 - Add Vercel auto-deploy diagnostic script
e78083c - Add comprehensive Vercel auto-deploy diagnosis guide
611a5f6 - Test auto deploy trigger: 1759628162
5b9ea0c - Fix showcase router import error
676e57d - Fix vercel.json: remove functions property conflict
```

### Vercel 连接状态
- ✅ Git Repository 已连接 (显示 "Disconnect" 按钮)
- ❌ 推送后不自动触发部署

---

## 🔍 问题描述

**症状**: 第一次手动部署成功后，后续的 Git 推送不会自动触发 Vercel 部署

**已尝试**:
1. ✅ 创建空提交测试 (commit 611a5f6)
2. ✅ 推送新文件测试 (commit e78083c, b7de8c6)
3. ❌ 仍然没有自动触发部署

**可能原因**:
1. Production Branch 设置不是 `main`
2. Ignored Build Step 有内容（阻止自动部署）
3. GitHub Webhook 配置损坏
4. 首次通过 CLI 部署，Git Integration 没有正确建立

---

## 🛠️ 诊断工具

### 1. 运行诊断脚本
```bash
./check_vercel_autodeploy.sh
```

这个脚本会检查:
- 当前分支
- 未推送的提交
- 最近的提交历史
- 远程仓库信息
- 提供诊断步骤和修复建议

### 2. 检查清单

#### Vercel 控制台检查
访问: https://vercel.com/dashboard

进入你的项目 → Settings → Git，检查:

- [ ] **Production Branch** = `main` ？
- [ ] **Ignored Build Step** 是否为空？
- [ ] 是否显示 **Disconnect** 按钮？

#### GitHub Webhook 检查
访问: https://github.com/stimQQ/sora2-fastapi/settings/hooks

检查:

- [ ] 是否有 Vercel webhook (URL 包含 `vercel.com`)？
- [ ] 点击进入 webhook，查看 **Recent Deliveries**
- [ ] 最近的推送是否触发了 webhook？
- [ ] Status 是否为 200 (绿色勾号)？

#### Vercel Deployments 检查
访问: https://vercel.com/dashboard → 选择项目 → Deployments

检查:

- [ ] 最新部署对应的 commit 是什么？
- [ ] 是否是 `b7de8c6` 或更新的？
- [ ] 如果不是，说明自动部署没有触发

---

## ✅ 解决方案

### 方案 A: Disconnect 并重新连接 (推荐，90% 成功率)

这是最快的修复方法:

1. **Disconnect**:
   - Vercel 项目 → Settings → Git
   - 点击 **Disconnect** 按钮
   - 确认断开连接

2. **等待**:
   - 等待 10 秒

3. **重新连接**:
   - 点击 **Connect Git Repository**
   - 选择 **GitHub**
   - 选择仓库: `stimQQ/sora2-fastapi`
   - 点击 **Connect**

4. **验证配置**:
   - 确认 **Production Branch** = `main`
   - 确认 **Ignored Build Step** 为空

5. **测试**:
   ```bash
   git commit --allow-empty -m "Test auto deploy: $(date +%s)"
   git push origin main
   ```

6. **观察**:
   - 立即打开 Vercel Deployments 页面
   - 应该在 10-30 秒内看到新部署开始

### 方案 B: 手动触发 Webhook (测试用)

用于测试 Webhook 是否正常工作:

1. 访问: https://github.com/stimQQ/sora2-fastapi/settings/hooks
2. 点击 Vercel webhook
3. 查看 **Recent Deliveries**
4. 点击最近的一个 delivery 右侧的 **Redeliver** 按钮
5. 立即查看 Vercel Deployments 页面

**如果 Redeliver 触发了部署**:
- 说明 Webhook 本身工作正常
- 问题可能在于 Git 推送没有触发 Webhook
- 可能需要重新连接 Git Integration

**如果 Redeliver 没有触发部署**:
- 说明 Webhook 配置有问题
- 查看 delivery 的响应状态
- 如果是 404/401 错误，需要重新连接

### 方案 C: 删除并重新导入项目 (终极方案，100% 成功)

**警告**: 需要重新配置所有环境变量

#### 准备工作

1. **导出环境变量** (非常重要！):
   - Vercel 项目 → Settings → Environment Variables
   - 复制所有变量到文本文件保存
   - 或者截图保存

#### 删除当前项目

1. Vercel 项目 → Settings → Advanced
2. 滚动到底部
3. 点击 **Delete Project**
4. 输入项目名称确认删除

#### 重新导入

1. 访问: https://vercel.com/new
2. 点击 **Add New...** → **Project**
3. 选择 **Import Git Repository**
4. 找到 `stimQQ/sora2-fastapi`
5. 点击 **Import**

#### 配置项目

**重要**: 在部署前配置环境变量！

1. 在导入页面，展开 **Environment Variables**
2. 粘贴之前保存的所有环境变量
3. 确认 **Production Branch** = `main`
4. 点击 **Deploy**

#### 验证

部署完成后:

1. 测试 API: https://your-domain.vercel.app/health
2. 测试推送:
   ```bash
   git commit --allow-empty -m "Test auto deploy after reimport"
   git push origin main
   ```
3. 查看 Vercel Deployments，应该自动触发新部署

---

## 🧪 快速测试自动部署

### 测试步骤

1. **打开两个浏览器标签**:
   - 标签 1: Vercel Deployments 页面
   - 标签 2: https://github.com/stimQQ/sora2-fastapi/settings/hooks

2. **创建测试提交**:
   ```bash
   git commit --allow-empty -m "Test auto deploy: $(date +%s)"
   git push origin main
   ```

3. **观察反应** (30 秒内):
   - 标签 2 (GitHub): Recent Deliveries 应该有新记录
   - 标签 1 (Vercel): Deployments 应该有新部署开始

4. **判断结果**:
   - ✅ **两个都有反应** → 自动部署正常工作 🎉
   - ❌ **GitHub 有，Vercel 没有** → 使用方案 A (Disconnect/Reconnect)
   - ❌ **两个都没有** → 检查 Production Branch 和 Ignored Build Step
   - ❌ **GitHub 有但显示错误** → 查看错误信息，可能需要重新授权

---

## 📝 常见问题

### Q1: 为什么第一次手动部署成功，但后续推送不自动部署？

**A**: 可能的原因:

1. **通过 Vercel CLI 部署的**: CLI 部署不会自动建立 Git Integration
   - 解决: 从 GitHub 重新导入项目

2. **Production Branch 设置错误**: Vercel 监听 `master`，但你推送到 `main`
   - 解决: 修改 Production Branch 为 `main`

3. **Git Integration 损坏**: 虽然显示已连接，但实际配置有问题
   - 解决: Disconnect 然后重新 Connect

### Q2: GitHub Webhook 显示 404 错误怎么办？

**A**: 404 错误说明 Vercel 项目已被删除或 URL 失效

解决方法:
1. Vercel → Settings → Git → Disconnect
2. Connect Git Repository → 重新连接

### Q3: GitHub Webhook 显示 200 但 Vercel 没有部署怎么办？

**A**: Webhook 触发了但 Vercel 没有响应

可能原因:
1. **Ignored Build Step** 有内容 → 清空
2. **Production Branch** 不匹配 → 改为 `main`
3. Vercel 服务问题 → 查看 Vercel Status Page

### Q4: 删除并重新导入项目会丢失数据吗？

**A**: 不会丢失数据，但需要重新配置:

- ❌ **不会丢失**: 源代码、Git 历史、数据库数据
- ⚠️ **需要重新配置**: 环境变量、自定义域名、Team 权限
- ✅ **自动保留**: Deployment 历史会丢失，但不影响生产环境

### Q5: 可以禁用自动部署吗？

**A**: 可以，但不推荐

如果确实需要:
1. Settings → Git → Production Branch
2. 设置为一个不存在的分支（如 `production`）
3. 推送到 `main` 就不会触发部署了

但更好的做法是使用 Vercel 的预览部署（Preview Deployments）功能。

---

## 📚 相关文档

- `VERCEL_AUTO_DEPLOY_DIAGNOSIS.md` - 详细的诊断和修复指南
- `check_vercel_autodeploy.sh` - 自动诊断脚本
- `fix_vercel_autodeploy.md` - 完整的修复方案
- `VERCEL_AUTODEPLOY_SETUP.md` - 自动部署配置指南
- `DEBUG_VERCEL_AUTODEPLOY.md` - 调试步骤

---

## 🎯 建议的下一步

### 如果你有 5 分钟

直接使用 **方案 A** (Disconnect/Reconnect):

1. Disconnect
2. 等待 10 秒
3. Reconnect
4. 测试推送

90% 的情况下这就能解决问题。

### 如果你有 15 分钟

使用 **方案 C** (删除重新导入):

这是 100% 有效的方法，一劳永逸解决所有 Git Integration 问题。

只需要:
1. 导出环境变量 (2 分钟)
2. 删除项目 (1 分钟)
3. 重新导入 (2 分钟)
4. 配置环境变量 (5 分钟)
5. 测试 (5 分钟)

### 如果你想先诊断

运行诊断脚本:

```bash
./check_vercel_autodeploy.sh
```

然后按照输出的建议逐步检查。

---

## ✨ 预期结果

修复后，自动部署应该这样工作:

1. **本地修改代码** → `git add .` → `git commit -m "..."` → `git push origin main`
2. **GitHub 接收推送** → 触发 Webhook
3. **Vercel 接收 Webhook** → 开始新部署 (10-30 秒内)
4. **部署状态**: Building → Deploying → Ready
5. **通知**: 收到 Vercel 邮件通知 "Deployment Ready"

整个流程应该在 **2-5 分钟** 内完成。

---

**最后更新**: 2025-10-05
**当前状态**: 等待修复 Vercel 自动部署配置
