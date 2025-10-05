# SparkVideo Sora 2 API 完整接口文档

> **基础 URL:** `https://api-sora2.sparkvideo.cc`
> **版本:** v1.0
> **更新日期:** 2025-01-15

---

## 目录

1. [认证接口 (Authentication)](#1-认证接口-authentication)
2. [用户接口 (Users)](#2-用户接口-users)
3. [视频生成接口 (Videos)](#3-视频生成接口-videos)
4. [任务管理接口 (Tasks)](#4-任务管理接口-tasks)
5. [支付接口 (Payments)](#5-支付接口-payments)
6. [视频展示接口 (Showcase)](#6-视频展示接口-showcase)

---

## 通用说明

### 认证方式

所有需要认证的接口使用 JWT Bearer Token：

```
Authorization: Bearer {access_token}
```

### 内部 API 密钥

视频生成接口需要额外的 API 密钥：

```
X-API-Key: ba45112b599d79fba659be778e3478b576f9825f1c57b80ad16cb918ec886a66
```

### 通用错误码

| 状态码 | 说明 |
|-------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未认证或 Token 无效 |
| 402 | 积分不足 |
| 403 | 无权限 |
| 404 | 资源不found |
| 422 | 参数验证失败 |
| 429 | 请求频率超限 |
| 500 | 服务器内部错误 |
| 503 | 服务暂时不可用 |

---

## 1. 认证接口 (Authentication)

### 1.1 Google OAuth 登录

**接口说明:** 使用 Google OAuth 授权码登录或注册

**接口地址:** `POST /api/auth/google/login`

**请求头:**
```
Content-Type: application/json
```

**请求参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| code | string | 是 | Google OAuth 授权码 |
| redirect_uri | string | 否 | OAuth 回调 URI |

**请求示例:**
```json
{
  "code": "4/0AY0e-g7xxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "https://sparkvideo.cc/auth/callback"
}
```

**返回参数:**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| access_token | string | JWT 访问令牌 |
| refresh_token | string | 刷新令牌 |
| token_type | string | Token 类型，固定为 "bearer" |
| expires_in | integer | Token 过期时间（秒） |

**返回示例:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 604800
}
```

---

### 1.2 刷新 Token

**接口说明:** 使用刷新令牌获取新的访问令牌

**接口地址:** `POST /api/auth/refresh`

**请求头:**
```
Content-Type: application/json
```

**请求参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| refresh_token | string | 是 | 刷新令牌 |

**请求示例:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**返回示例:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 604800
}
```

---

### 1.3 获取当前用户信息

**接口说明:** 获取当前已认证用户的信息

**接口地址:** `GET /api/auth/me`

**请求头:**
```
Authorization: Bearer {access_token}
```

**返回示例:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "john_doe",
  "credits": 100,
  "region": "CN"
}
```

---

### 1.4 登出

**接口说明:** 登出当前用户（使令牌失效）

**接口地址:** `POST /api/auth/logout`

**请求头:**
```
Authorization: Bearer {access_token}
```

**返回示例:**
```json
{
  "message": "Successfully logged out"
}
```

---



---

## 2. 用户接口 (Users)

### 2.1 获取用户资料

**接口说明:** 获取当前用户的详细资料

**接口地址:** `GET /api/users/profile`

**请求头:**
```
Authorization: Bearer {access_token}
```

**返回示例:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "john_doe",
  "avatar_url": "https://example.com/avatar.jpg",
  "region": "CN",
  "language": "zh-CN",
  "credits": 100,
  "created_at": "2025-01-01T00:00:00Z",
  "last_login_at": "2025-01-15T10:00:00Z"
}
```

---

### 2.2 更新用户资料

**接口说明:** 更新当前用户的资料

**接口地址:** `PUT /api/users/profile`

**请求头:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**请求参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| username | string | 否 | 用户名（3-50 字符） |
| avatar_url | string | 否 | 头像 URL |
| language | string | 否 | 首选语言：zh-CN（简体中文）, zh-TW（繁体中文）, en（英语）, ja（日语）, ko（韩语） |

**请求示例:**
```json
{
  "username": "new_username",
  "avatar_url": "https://example.com/new-avatar.jpg",
  "language": "en"
}
```

**返回示例:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "new_username",
  "avatar_url": "https://example.com/new-avatar.jpg",
  "region": "CN",
  "language": "en",
  "credits": 100,
  "created_at": "2025-01-01T00:00:00Z",
  "last_login_at": "2025-01-15T10:00:00Z"
}
```

---

### 2.3 获取积分余额

**接口说明:** 获取当前用户的积分余额和统计

**接口地址:** `GET /api/users/credits`

**请求头:**
```
Authorization: Bearer {access_token}
```

**返回示例:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "credits": 100,
  "total_earned": 500,
  "total_spent": 400
}
```

---

### 2.4 删除账户

**接口说明:** 请求删除用户账户（软删除）

**接口地址:** `DELETE /api/users/account`

**请求头:**
```
Authorization: Bearer {access_token}
```

**返回示例:**
```json
{
  "message": "Account deletion requested. Your account will be deleted within 30 days."
}
```

---

## 3. 视频生成接口 (Videos)

### 3.1 文生视频 (Text-to-Video)

**接口说明:** 使用 Sora 2 模型从文本生成视频

**接口地址:** `POST /api/videos/text-to-video`

**请求头:**
```
Authorization: Bearer {access_token}
X-API-Key: ba45112b599d79fba659be778e3478b576f9825f1c57b80ad16cb918ec886a66
Content-Type: application/json
```

**请求参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| prompt | string | 是 | 文本描述（最多 5000 字符） |
| aspect_ratio | string | 否 | 宽高比："landscape" 或 "portrait"，默认 "landscape" |
| quality | string | 否 | 质量："standard" 或 "hd"，默认 "standard" |
| webhook_url | string | 否 | 任务完成回调 URL |

**请求示例:**
```json
{
  "prompt": "A beautiful sunset over the ocean, waves gently crashing on the beach",
  "aspect_ratio": "landscape",
  "quality": "standard",
  "webhook_url": "https://your-domain.com/webhook"
}
```

**返回参数:**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 是否成功 |
| task_id | string | 任务 ID（用于查询状态） |
| message | string | 提示消息 |
| credits_estimated | integer | 预计消耗积分 |
| estimated_time | integer | 预计生成时间（秒） |

**返回示例:**
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Text-to-video task created successfully. Credits deducted.",
  "credits_estimated": 20,
  "estimated_time": 180
}
```

**积分消耗:**
- 标准质量: 20 积分/视频
- HD 质量: 30 积分/视频

**注意事项:**
- 积分在任务创建时**立即扣除**
- 任务失败时**自动退款**

---

### 3.2 图生视频 (Image-to-Video)

**接口说明:** 使用 Sora 2 模型从图片生成视频

**接口地址:** `POST /api/videos/image-to-video`

**请求头:**
```
Authorization: Bearer {access_token}
X-API-Key: ba45112b599d79fba659be778e3478b576f9825f1c57b80ad16cb918ec886a66
Content-Type: application/json
```

**请求参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| prompt | string | 是 | 动作描述（最多 5000 字符） |
| image_urls | array | 是 | 图片 URL 数组（必须公开可访问） |
| aspect_ratio | string | 否 | 宽高比："landscape" 或 "portrait"，默认 "landscape" |
| quality | string | 否 | 质量："standard" 或 "hd"，默认 "standard" |
| webhook_url | string | 否 | 任务完成回调 URL |

**请求示例:**
```json
{
  "prompt": "A claymation conductor passionately leads a claymation orchestra",
  "image_urls": [
    "https://file.aiquickdraw.com/custom-page/akr/section-images/17594315607644506ltpf.jpg"
  ],
  "aspect_ratio": "landscape",
  "quality": "standard",
  "webhook_url": "https://your-domain.com/webhook"
}
```

**返回示例:**
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Image-to-video task created successfully. Credits deducted.",
  "credits_estimated": 25,
  "estimated_time": 180
}
```

**积分消耗:**
- 标准质量: 25 积分/视频
- HD 质量: 35 积分/视频

**支持的图片格式:**
- JPEG
- PNG
- WebP
- 最大文件大小: 10MB

---

### 3.3 文件上传

**接口说明:** 上传图片或视频文件到存储服务

**接口地址:** `POST /api/videos/upload`

**请求头:**
```
Authorization: Bearer {access_token}
X-API-Key: ba45112b599d79fba659be778e3478b576f9825f1c57b80ad16cb918ec886a66
Content-Type: multipart/form-data
```

**请求参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file | file | 是 | 文件对象 |
| file_type | string | 否 | 文件类型："image" 或 "video"，默认 "image" |

**cURL 示例:**
```bash
curl -X POST "https://api-sora2.sparkvideo.cc/api/videos/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-API-Key: ba45112b599d79fba659be778e3478b576f9825f1c57b80ad16cb918ec886a66" \
  -F "file=@/path/to/image.jpg" \
  -F "file_type=image"
```

**返回示例:**
```json
{
  "success": true,
  "file_url": "https://sparkvideo-oss.oss-ap-southeast-1.aliyuncs.com/uploads/image/user-id/2025/01/15/abc123_image.jpg",
  "storage_key": "uploads/image/user-id/2025/01/15/abc123_image.jpg",
  "file_size": 245678,
  "content_type": "image/jpeg",
  "file_type": "image",
  "message": "Image uploaded successfully"
}
```

**支持的图片格式:**
- .jpg, .jpeg, .png, .webp

**支持的视频格式:**
- .mp4, .mov, .avi, .webm

**最大文件大小:** 100MB

---

### 3.4 Sora Webhook 回调

**接口说明:** Sora API 任务完成回调端点（由 Sora 调用）

**接口地址:** `POST /api/videos/sora/callback`

**请求头:**
```
Content-Type: application/json
```

**请求参数（由 Sora 发送）:**

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "281e5b0*********************f39b9",
    "model": "sora-2-text-to-video",
    "state": "success",
    "param": "{\"model\":\"sora-2-text-to-video\",\"input\":{...}}",
    "resultJson": "{\"resultUrls\":[\"https://file.aiquickdraw.com/video.mp4\"]}",
    "failCode": null,
    "failMsg": null,
    "costTime": 120000,
    "completeTime": 1757584284490,
    "createTime": 1757584164490
  }
}
```

**返回示例:**
```json
{
  "success": true,
  "message": "Task completed successfully",
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**注意:** 此端点无需认证，由 Sora API 自动调用

---

## 4. 任务管理接口 (Tasks)

### 4.1 查询任务详情

**接口说明:** 根据任务 ID 查询任务状态和结果

**接口地址:** `GET /api/tasks/{task_id}`

**请求头:**
```
Authorization: Bearer {access_token}
X-API-Key: ba45112b599d79fba659be778e3478b576f9825f1c57b80ad16cb918ec886a66
```

**路径参数:**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| task_id | string | 任务 ID |

**返回参数:**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| task_id | string | 任务 ID |
| user_id | string | 用户 ID |
| task_type | string | 任务类型 |
| status | string | 状态：pending, processing, completed, failed |
| progress | float | 进度 (0-100) |
| result_url | string | 结果视频 URL（成功时） |
| error_message | string | 错误消息（失败时） |
| created_at | string | 创建时间 (ISO 8601) |
| updated_at | string | 更新时间 (ISO 8601) |
| completed_at | string | 完成时间 (ISO 8601) |

**返回示例（进行中）:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-uuid",
  "task_type": "text-to-video",
  "status": "processing",
  "progress": 45.5,
  "result_url": null,
  "error_message": null,
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:01:30Z",
  "completed_at": null
}
```

**返回示例（成功）:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-uuid",
  "task_type": "text-to-video",
  "status": "completed",
  "progress": 100.0,
  "result_url": "https://file.aiquickdraw.com/custom-page/akr/section-images/1759432328669pkhobl0t.mp4",
  "error_message": null,
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:03:00Z",
  "completed_at": "2025-01-15T10:03:00Z"
}
```

---

### 4.2 获取用户任务列表

**接口说明:** 获取当前用户的所有任务，支持分页和筛选

**接口地址:** `GET /api/tasks/user/tasks`

**请求头:**
```
Authorization: Bearer {access_token}
```

**查询参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页数量，默认 10，最大 100 |
| status | string | 否 | 按状态筛选 |

**请求示例:**
```
GET /api/tasks/user/tasks?page=1&page_size=10&status=completed
```

**返回示例:**
```json
{
  "tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "user-uuid",
      "task_type": "text-to-video",
      "status": "completed",
      "progress": 100.0,
      "result_url": "https://file.aiquickdraw.com/video.mp4",
      "error_message": null,
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-15T10:03:00Z",
      "completed_at": "2025-01-15T10:03:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 10
}
```

---

### 4.3 取消任务

**接口说明:** 取消进行中的任务

**接口地址:** `DELETE /api/tasks/{task_id}`

**请求头:**
```
Authorization: Bearer {access_token}
```

**路径参数:**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| task_id | string | 任务 ID |

**返回示例:**
```json
{
  "message": "Task cancelled successfully"
}
```

**注意:** 只能取消状态为 pending 或 processing 的任务

---

### 4.4 重试任务

**接口说明:** 重试失败的任务

**接口地址:** `POST /api/tasks/{task_id}/retry`

**请求头:**
```
Authorization: Bearer {access_token}
```

**路径参数:**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| task_id | string | 原任务 ID |

**返回示例:**
```json
{
  "message": "Task retry initiated",
  "task_id": "new-task-uuid",
  "original_task_id": "original-task-uuid"
}
```

---

## 5. 支付接口 (Payments)

### 5.1 获取积分套餐列表

**接口说明:** 获取所有可用的积分购买套餐

**接口地址:** `GET /api/payments/packages`

**无需认证**

**返回示例:**
```json
{
  "packages": {
    "trial": {
      "name": "体验包",
      "credits": 500,
      "price": 50.0,
      "currency": "CNY",
      "unit_price": 0.10
    },
    "standard": {
      "name": "标准包",
      "credits": 1100,
      "price": 100.0,
      "currency": "CNY",
      "unit_price": 0.091
    },
    "value": {
      "name": "超值包",
      "credits": 6000,
      "price": 500.0,
      "currency": "CNY",
      "unit_price": 0.083
    },
    "premium": {
      "name": "豪华包",
      "credits": 13000,
      "price": 1000.0,
      "currency": "CNY",
      "unit_price": 0.076
    }
  },
  "credit_value_rmb": 0.1
}
```

---

### 5.2 创建 Stripe 支付

**接口说明:** 创建 Stripe 支付订单（国际支付）

**接口地址:** `POST /api/payments/stripe/create`

**请求头:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**请求参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| package | string | 是 | 套餐 ID: trial, standard, value, premium |
| return_url | string | 否 | 支付完成后的跳转 URL |

**请求示例:**
```json
{
  "package": "standard",
  "return_url": "https://sparkvideo.cc/payment/success"
}
```

**返回示例:**
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "amount": 100.0,
  "currency": "CNY",
  "credits_purchased": 1100,
  "payment_url": "https://checkout.stripe.com/pay/cs_test_xxxxx"
}
```

---

### 5.3 查询支付状态

**接口说明:** 查询支付订单状态

**接口地址:** `GET /api/payments/{payment_id}`

**请求头:**
```
Authorization: Bearer {access_token}
```

**路径参数:**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| payment_id | string | 支付订单 ID |

**返回示例:**
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "succeeded",
  "amount": 100.0,
  "currency": "CNY",
  "credits_purchased": 1100,
  "payment_url": "https://checkout.stripe.com/pay/cs_test_xxxxx",
  "created_at": "2025-01-15T10:00:00Z",
  "paid_at": "2025-01-15T10:05:00Z"
}
```

**支付状态:**
- `pending`: 待支付
- `succeeded`: 支付成功
- `failed`: 支付失败
- `refunded`: 已退款
- `partial_refunded`: 部分退款

---

### 5.4 Stripe Webhook

**接口说明:** Stripe 支付回调端点（由 Stripe 调用）

**接口地址:** `POST /api/payments/webhook/stripe`

**请求头:**
```
stripe-signature: {signature}
Content-Type: application/json
```

**注意:** 此端点由 Stripe 自动调用，需要配置 webhook secret 进行签名验证

---

## 6. 视频展示接口 (Showcase)

### 6.1 获取展示视频列表

**接口说明:** 获取首页展示的视频列表（分页）

**接口地址:** `GET /api/showcase/videos`

**查询参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| page | integer | 否 | 页码，默认 1 |
| page_size | integer | 否 | 每页数量，默认 12，最大 100 |

**请求示例:**
```
GET /api/showcase/videos?page=1&page_size=12
```

**返回示例:**
```json
{
  "total": 48,
  "page": 1,
  "page_size": 12,
  "total_pages": 4,
  "videos": [
    {
      "id": 1,
      "title": "Beautiful Sunset",
      "description": "A stunning sunset over the ocean",
      "video_url": "https://cdn.yourdomain.com/showcase/video1.mp4",
      "thumbnail_url": "https://cdn.yourdomain.com/showcase/thumb1.jpg",
      "duration": 10,
      "view_count": 1234,
      "tags": ["sunset", "ocean", "nature"],
      "created_at": "2025-01-10T12:00:00Z",
      "display_order": 100,
      "is_active": true
    }
  ]
}
```

---

### 6.2 获取单个视频详情

**接口说明:** 获取单个展示视频的详细信息（自动增加观看次数）

**接口地址:** `GET /api/showcase/videos/{video_id}`

**路径参数:**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| video_id | integer | 视频 ID |

**返回示例:**
```json
{
  "id": 1,
  "title": "Beautiful Sunset",
  "description": "A stunning sunset over the ocean",
  "video_url": "https://cdn.yourdomain.com/showcase/video1.mp4",
  "thumbnail_url": "https://cdn.yourdomain.com/showcase/thumb1.jpg",
  "duration": 10,
  "view_count": 1235,
  "tags": ["sunset", "ocean", "nature"],
  "created_at": "2025-01-10T12:00:00Z",
  "display_order": 100,
  "is_active": true
}
```

---

## 附录

### A. 积分价格表

| 服务 | 标准质量 | HD 质量 |
|------|---------|---------|
| 文生视频 (Text-to-Video) | 20 积分 | 30 积分 |
| 图生视频 (Image-to-Video) | 25 积分 | 35 积分 |

### B. 积分套餐对比

| 套餐 | 积分数 | 价格 (CNY) | 单价 (CNY/积分) | 性价比 |
|------|--------|-----------|----------------|--------|
| 体验包 | 500 | ¥50 | ¥0.100 | ★☆☆☆☆ |
| 标准包 | 1,100 | ¥100 | ¥0.091 | ★★☆☆☆ |
| 超值包 | 6,000 | ¥500 | ¥0.083 | ★★★★☆ |
| 豪华包 | 13,000 | ¥1,000 | ¥0.076 | ★★★★★ |

### C. 任务状态说明

| 后端状态 | 前端状态 | 说明 |
|---------|---------|------|
| PENDING | pending | 任务已创建，等待处理 |
| RUNNING | processing | 任务正在处理中 |
| SUCCEEDED | completed | 任务成功完成 |
| FAILED | failed | 任务失败 |
| CANCELLED | failed | 任务已取消 |
| TIMEOUT | failed | 任务超时 |

### D. 常见问题

#### Q1: 如何获取 JWT Token？
A: 通过 `/api/auth/google/login` 或 `/api/auth/test/login` 登录获取。

#### Q2: 积分何时扣除？
A: 创建视频生成任务时**立即扣除**，任务失败时**自动退款**。

#### Q3: 如何上传本地图片？
A: 先调用 `/api/videos/upload` 上传文件，获取 `file_url`，然后在图生视频接口中使用该 URL。

#### Q4: 视频生成需要多长时间？
A: 通常 2-5 分钟，具体取决于视频质量和队列长度。

#### Q5: 如何接收任务完成通知？
A: 在创建任务时提供 `webhook_url`，任务完成时会向该 URL 发送 POST 请求。

---

## 更新日志

### v1.0.0 - 2025-01-15
- ✅ 完整的 API 文档
- ✅ 所有接口的请求和返回示例
- ✅ 认证、用户、视频、任务、支付、展示等 6 大模块
- ✅ 23 个 API 端点详细说明
- ✅ 错误码和状态码说明
- ✅ 积分价格和套餐对比

---

**文档维护:** SparkVideo Backend Team
**技术支持:** https://api-sora2.sparkvideo.cc
**最后更新:** 2025-01-15
