# Vercel 自动部署配置指南

## 问题诊断

如果推送到 GitHub 后 Vercel 没有自动部署，可能是以下原因：

## ✅ 解决方案

### 1. 检查 Vercel 项目是否连接到 GitHub

进入 Vercel 控制台：

1. 打开你的项目
2. 点击 **Settings** 标签
3. 点击左侧 **Git**
4. 检查 **Connected Git Repository**

**如果显示 "No Git Repository"：**

#### 方法 A：重新连接（推荐）
1. 点击 **Connect Git Repository**
2. 选择 **GitHub**
3. 授权 Vercel 访问你的 GitHub
4. 选择仓库：`stimQQ/sora2-fastapi`
5. 点击 **Connect**

#### 方法 B：重新导入项目
1. 在 Vercel 首页点击 **Add New...** → **Project**
2. 选择 **Import Git Repository**
3. 找到 `stimQQ/sora2-fastapi`
4. 点击 **Import**
5. 配置环境变量（复制之前的配置）
6. 部署

### 2. 检查生产分支设置

在 **Settings** → **Git** 中：

1. 找到 **Production Branch**
2. 确认设置为：`main`
3. 如果不是，点击编辑改为 `main`

### 3. 启用自动部署

在 **Settings** → **Git** 中：

1. 确认 **Auto Deploy** 已启用（开关打开）
2. 确认监听的分支是 `main`

### 4. 检查 GitHub App 权限

1. 访问 https://github.com/settings/installations
2. 找到 **Vercel**
3. 点击 **Configure**
4. 确认 `stimQQ/sora2-fastapi` 在允许列表中
5. 如果不在，添加它

### 5. 手动触发部署（临时解决）

如果以上都设置正确但还是不自动部署：

#### 选项 1：Vercel 控制台
1. 进入项目
2. 点击 **Deployments**
3. 点击右上角 **Deploy** 或 **Redeploy**
4. 确保选择最新的 commit

#### 选项 2：使用 Vercel CLI
```bash
# 安装
npm i -g vercel

# 登录
vercel login

# 进入项目目录
cd /path/to/your/project

# 部署到生产环境
vercel --prod
```

#### 选项 3：空提交触发
```bash
# 创建空提交
git commit --allow-empty -m "Trigger Vercel deployment"

# 推送
git push origin main
```

---

## 🔍 验证自动部署已启用

### 测试方法：

1. 修改一个文件（例如添加注释）：
```bash
echo "# Test auto deploy" >> README.md
git add README.md
git commit -m "Test auto deploy"
git push origin main
```

2. 立即去 Vercel 控制台查看 **Deployments** 标签

3. 应该在几秒钟内看到新的部署开始（状态：Building）

---

## 📊 当前提交历史

已推送的 commits（按时间倒序）：

```
a1b1227 - Trigger Vercel deployment - force rebuild (最新)
bed5a4c - Trigger Vercel redeploy with latest code
ca9d85d - Fix Vercel serverless errors (关键修复)
d263a33 - first commit
```

**重要**：确保 Vercel 部署的是 `a1b1227` 或更新的 commit！

---

## ⚠️ 常见问题

### Q: 推送后多久会开始部署？
A: 通常在 5-30 秒内开始

### Q: 如何知道部署是否成功？
A:
1. Vercel 会发送邮件通知
2. 在 Deployments 页面看到绿色的 "Ready" 状态
3. 访问 URL 能正常访问

### Q: 部署失败了怎么办？
A:
1. 查看部署日志（点击失败的部署 → View Function Logs）
2. 检查错误信息
3. 修复后重新推送

### Q: 可以禁用自动部署吗？
A: 可以在 Settings → Git 中关闭，但不推荐

---

## ✅ 最终检查清单

部署前确认：

- [ ] Vercel 项目已连接到 GitHub 仓库
- [ ] Production Branch 设置为 `main`
- [ ] Auto Deploy 已启用
- [ ] GitHub App 有仓库访问权限
- [ ] 已配置所有必需的环境变量
- [ ] 已推送最新的修复代码

---

## 🎯 下一步

完成自动部署配置后：

1. **测试推送触发部署**：修改文件 → commit → push
2. **验证部署成功**：检查 Vercel Deployments 页面
3. **测试 API 接口**：使用 `./quick_test.sh`
4. **配置自定义域名**：参考 `VERCEL_DEPLOY.md`
5. **设置 Cloudflare CDN**：参考 `CLOUDFLARE_SETUP.md`

---

**提示**：如果自动部署还是不工作，考虑删除 Vercel 项目重新导入，这通常能解决连接问题。
