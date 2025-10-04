#!/bin/bash

# API 测试脚本
BASE_URL="http://localhost:8000"

echo "=========================================="
echo "🧪 Video Animation Platform API 测试"
echo "=========================================="
echo ""

# 1. 测试根路径
echo "1️⃣  测试根路径 GET /"
curl -s $BASE_URL/ | python -m json.tool
echo -e "\n"

# 2. 测试健康检查
echo "2️⃣  测试健康检查 GET /health"
curl -s $BASE_URL/health | python -m json.tool
echo -e "\n"

# 3. 查看 API 文档
echo "3️⃣  API 文档地址:"
echo "   Swagger UI: $BASE_URL/docs"
echo "   ReDoc: $BASE_URL/redoc"
echo -e "\n"

# 4. 测试用户注册（需要实现）
echo "4️⃣  测试用户注册 POST /api/auth/register"
echo "   (示例 - 需要替换实际参数)"
cat << 'EOF'
curl -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123!",
    "username": "testuser"
  }'
EOF
echo -e "\n"

# 5. 测试登录（需要实现）
echo "5️⃣  测试用户登录 POST /api/auth/login"
cat << 'EOF'
curl -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123!"
  }'
EOF
echo -e "\n"

# 6. 测试获取当前用户信息（需要 token）
echo "6️⃣  测试获取用户信息 GET /api/auth/me"
cat << 'EOF'
TOKEN="your_jwt_token_here"
curl -X GET "$BASE_URL/api/auth/me" \
  -H "Authorization: Bearer $TOKEN"
EOF
echo -e "\n"

# 7. 测试创建视频任务（需要 token）
echo "7️⃣  测试创建视频任务 POST /api/videos/animate-move"
cat << 'EOF'
TOKEN="your_jwt_token_here"
curl -X POST "$BASE_URL/api/videos/animate-move" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg",
    "video_url": "https://example.com/video.mp4",
    "mode": "wan-std"
  }'
EOF
echo -e "\n"

# 8. 测试查询任务状态（需要 token）
echo "8️⃣  测试查询任务 GET /api/tasks/{task_id}"
cat << 'EOF'
TOKEN="your_jwt_token_here"
TASK_ID="your_task_id_here"
curl -X GET "$BASE_URL/api/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN"
EOF
echo -e "\n"

echo "=========================================="
echo "✅ 测试脚本完成"
echo "=========================================="
echo ""
echo "💡 提示："
echo "   1. 在浏览器打开 http://localhost:8000/docs 可以交互式测试"
echo "   2. 需要先注册/登录获取 JWT token 才能测试需要认证的接口"
echo "   3. 替换上面示例中的 TOKEN 和参数后可以直接运行"
echo ""
