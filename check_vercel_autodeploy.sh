#!/bin/bash

# Vercel 自动部署检查脚本
# 用于快速诊断为什么 Git 推送后 Vercel 不自动部署

echo "======================================"
echo "Vercel 自动部署诊断工具"
echo "======================================"
echo ""

# 检查当前分支
echo "1. 检查当前 Git 分支:"
CURRENT_BRANCH=$(git branch --show-current)
echo "   当前分支: $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "   ⚠️  警告: 你不在 main 分支上！"
    echo "   Vercel Production Branch 通常设置为 'main'"
    echo ""
fi

# 检查是否有未推送的提交
echo ""
echo "2. 检查是否有未推送的提交:"
UNPUSHED=$(git log origin/$CURRENT_BRANCH..$CURRENT_BRANCH --oneline 2>/dev/null)
if [ -z "$UNPUSHED" ]; then
    echo "   ✅ 所有提交已推送到远程仓库"
else
    echo "   ⚠️  有未推送的提交:"
    echo "$UNPUSHED" | sed 's/^/      /'
    echo ""
fi

# 显示最近的提交
echo ""
echo "3. 最近的 5 次提交:"
git log --oneline -5 | sed 's/^/   /'
echo ""

# 获取最新提交的信息
LATEST_COMMIT=$(git log -1 --format="%H")
LATEST_COMMIT_SHORT=$(git log -1 --format="%h")
LATEST_COMMIT_MSG=$(git log -1 --format="%s")
LATEST_COMMIT_TIME=$(git log -1 --format="%ci")

echo ""
echo "4. 最新提交详情:"
echo "   Commit: $LATEST_COMMIT_SHORT"
echo "   消息: $LATEST_COMMIT_MSG"
echo "   时间: $LATEST_COMMIT_TIME"
echo ""

# 检查远程仓库
echo ""
echo "5. 远程仓库信息:"
REMOTE_URL=$(git remote get-url origin)
echo "   远程仓库: $REMOTE_URL"
echo ""

# 提取仓库信息 (GitHub)
if [[ $REMOTE_URL == *"github.com"* ]]; then
    REPO_PATH=$(echo $REMOTE_URL | sed -E 's/.*github\.com[:/](.*)\.git/\1/')
    echo "   GitHub 仓库: $REPO_PATH"
    echo ""
    echo "   📝 请检查以下链接:"
    echo "   ├─ Webhook 设置: https://github.com/$REPO_PATH/settings/hooks"
    echo "   └─ 最新提交: https://github.com/$REPO_PATH/commit/$LATEST_COMMIT"
    echo ""
fi

# 诊断建议
echo ""
echo "======================================"
echo "诊断步骤"
echo "======================================"
echo ""
echo "请按顺序检查以下项目:"
echo ""
echo "【Vercel 控制台】"
echo "1. 访问: https://vercel.com/dashboard"
echo "2. 选择你的项目 → Settings → Git"
echo "3. 检查:"
echo "   ├─ Production Branch = 'main' ?"
echo "   ├─ Ignored Build Step 是否为空?"
echo "   └─ 是否显示 'Disconnect' 按钮 (说明已连接)?"
echo ""
echo "【GitHub Webhook】"
echo "1. 访问 Webhook 设置 (上面的链接)"
echo "2. 检查:"
echo "   ├─ 是否有 Vercel webhook (URL 包含 vercel.com)?"
echo "   ├─ 点击进入查看 Recent Deliveries"
echo "   ├─ 最近的推送是否触发了 webhook?"
echo "   └─ Status 是否为 200 (绿色勾号)?"
echo ""
echo "【Vercel Deployments】"
echo "1. 访问: https://vercel.com/dashboard (选择项目 → Deployments)"
echo "2. 检查:"
echo "   ├─ 最新部署对应的 commit 是什么?"
echo "   ├─ 是否是 $LATEST_COMMIT_SHORT?"
echo "   └─ 如果不是，说明自动部署没有触发"
echo ""

# 快速测试
echo ""
echo "======================================"
echo "快速测试自动部署"
echo "======================================"
echo ""
echo "执行以下命令创建测试提交:"
echo ""
echo "  git commit --allow-empty -m \"Test auto deploy: \$(date +%s)\""
echo "  git push origin main"
echo ""
echo "然后立即查看:"
echo "  ├─ Vercel Deployments 页面 (应该在 30 秒内看到新部署)"
echo "  └─ GitHub Webhook Recent Deliveries (应该有新记录)"
echo ""

# 修复建议
echo ""
echo "======================================"
echo "如果自动部署不工作"
echo "======================================"
echo ""
echo "【快速修复】"
echo "1. Vercel → Settings → Git → Disconnect"
echo "2. 等待 10 秒"
echo "3. Connect Git Repository → 选择仓库"
echo "4. 确认 Production Branch = main"
echo "5. 测试推送"
echo ""
echo "【终极方案】"
echo "如果 Disconnect/Reconnect 不行:"
echo "1. 导出环境变量 (Settings → Environment Variables)"
echo "2. 删除 Vercel 项目 (Settings → Advanced → Delete)"
echo "3. 从 GitHub 重新导入项目"
echo "4. 配置环境变量"
echo "5. Deploy"
echo ""
echo "详细步骤请查看: VERCEL_AUTO_DEPLOY_DIAGNOSIS.md"
echo ""
