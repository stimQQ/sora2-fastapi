#!/bin/bash

# 快速测试 Vercel 部署的 API
# 使用方法: ./quick_test.sh https://your-project.vercel.app

if [ -z "$1" ]; then
    echo "使用方法: ./quick_test.sh <Vercel URL>"
    echo "例如: ./quick_test.sh https://your-project.vercel.app"
    exit 1
fi

API_URL=$1

echo "========================================"
echo "测试 Vercel API: $API_URL"
echo "========================================"
echo ""

echo "1️⃣  测试健康检查 (/health)..."
echo "---"
curl -s "$API_URL/health" | python3 -m json.tool || echo "❌ 失败"
echo ""
echo ""

echo "2️⃣  测试根端点 (/)..."
echo "---"
curl -s "$API_URL/" | python3 -m json.tool || echo "❌ 失败"
echo ""
echo ""

echo "3️⃣  测试视频列表 (/api/showcase/videos)..."
echo "---"
curl -s "$API_URL/api/showcase/videos" | python3 -m json.tool || echo "❌ 失败"
echo ""
echo ""

echo "4️⃣  检查响应头（查看 Cloudflare）..."
echo "---"
curl -I "$API_URL/health" 2>&1 | grep -E "(HTTP|cf-|server)"
echo ""

echo "========================================"
echo "✅ 测试完成！"
echo "========================================"
echo ""
echo "接下来："
echo "1. 在浏览器访问: $API_URL/docs"
echo "2. 测试 Swagger UI 文档"
echo "3. 配置自定义域名和 Cloudflare CDN"
