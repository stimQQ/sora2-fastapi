# API Documentation - Video Generation Platform (Sora 2)

## Base URL
```
Development: http://localhost:8001
Production: https://api-sora2.sparkvideo.cc
```

## Authentication
Most endpoints require authentication via JWT token in the `Authorization` header:
```
Authorization: Bearer <access_token>
```

Some endpoints also require an API key via header:
```
X-API-Key: <your_api_key>
```

---

## 1. Authentication API (`/api/auth`)

### 1.1 Google OAuth Login
**Endpoint:** `POST /api/auth/google/login`

**Description:** Authenticate using Google OAuth and receive JWT tokens.

**Request:**
```json
{
  "code": "string",           // Required: Authorization code from Google OAuth
  "redirect_uri": "string"    // Optional: Redirect URI used in OAuth flow
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400         // Seconds until access token expires
}
```

**Errors:**
- `401 Unauthorized`: Invalid authorization code
- `500 Internal Server Error`: Authentication failed

---

### 1.2 Refresh Token
**Endpoint:** `POST /api/auth/refresh`

**Description:** Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "string"   // Required: Valid refresh token
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

---

### 1.3 Logout
**Endpoint:** `POST /api/auth/logout`

**Authentication:** Required (Bearer token)

**Response (200 OK):**
```json
{
  "message": "Successfully logged out"
}
```

---

### 1.4 Get Current User
**Endpoint:** `GET /api/auth/me`

**Authentication:** Required (Bearer token)

**Response (200 OK):**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "username": "username",
  "credits": 1000,
  "avatar_url": "https://...",
  "is_verified": true
}
```

---

### 1.5 Test Login (Development Only)
**Endpoint:** `POST /api/auth/test/login`

**Description:** Create or login a test user (not available in production).

**Query Parameters:**
- `email` (optional): Email address (default: test@example.com)

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Errors:**
- `403 Forbidden`: Not available in production

---

## 2. Video Generation API (`/api/videos`)

### 2.1 Upload File
**Endpoint:** `POST /api/videos/upload`

**Authentication:** Required (Bearer token + API key)

**Request (multipart/form-data):**
- `file`: File to upload (required)
- `file_type`: "image" or "video" (default: "image")

**Allowed Image Extensions:** .jpg, .jpeg, .png, .gif, .webp
**Allowed Video Extensions:** .mp4, .avi, .mov, .webm
**Max File Size:** 100 MB
**Min File Size:** 1 KB

**Response (200 OK):**
```json
{
  "success": true,
  "file_url": "https://oss.example.com/uploads/...",
  "storage_key": "uploads/image/user-id/2025/01/05/abc123_filename.jpg",
  "file_size": 1048576,
  "content_type": "image/jpeg",
  "file_type": "image",
  "message": "Image uploaded successfully"
}
```

**Errors:**
- `400 Bad Request`: Invalid file type or size
- `413 Payload Too Large`: File exceeds maximum size

---

### 2.2 Create Text-to-Video Task
**Endpoint:** `POST /api/videos/text-to-video`

**Authentication:** Required (Bearer token + API key)

**Description:** Generate video from text description using Sora 2. Credits are deducted immediately upon task creation and refunded if task fails.

**Pricing:**
- Standard quality: 20 credits per video
- HD quality: 30 credits per video

**Request:**
```json
{
  "prompt": "string",              // Required: Text description (1-5000 chars)
  "aspect_ratio": "landscape",     // Optional: "landscape" or "portrait" (default: landscape)
  "quality": "standard",           // Optional: "standard" or "hd" (default: standard)
  "webhook_url": "string"          // Optional: Webhook URL for completion notification
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "task_id": "uuid-string",
  "message": "Text-to-video task created successfully. Credits deducted.",
  "credits_estimated": 20,         // Credits deducted (20 for standard, 30 for hd)
  "estimated_time": 180            // Estimated processing time in seconds
}
```

**Errors:**
- `400 Bad Request`: Invalid parameters
- `402 Payment Required`: Insufficient credits
- `500 Internal Server Error`: Task creation failed

---

### 2.3 Create Image-to-Video Task
**Endpoint:** `POST /api/videos/image-to-video`

**Authentication:** Required (Bearer token + API key)

**Description:** Animate images based on text description using Sora 2. Credits are deducted immediately and refunded if task fails.

**Pricing:**
- Standard quality: 25 credits per video
- HD quality: 35 credits per video

**Request:**
```json
{
  "prompt": "string",              // Required: Text description of desired action (1-5000 chars)
  "image_urls": [                  // Required: Array of image URLs (min 1 image)
    "https://oss.example.com/image1.jpg"
  ],
  "aspect_ratio": "landscape",     // Optional: "landscape" or "portrait" (default: landscape)
  "quality": "standard",           // Optional: "standard" or "hd" (default: standard)
  "webhook_url": "string"          // Optional: Webhook URL for completion notification
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "task_id": "uuid-string",
  "message": "Image-to-video task created successfully. Credits deducted.",
  "credits_estimated": 25,         // Credits deducted (25 for standard, 35 for hd)
  "estimated_time": 180            // Estimated processing time in seconds
}
```

**Errors:**
- `400 Bad Request`: Invalid parameters or image URLs
- `402 Payment Required`: Insufficient credits
- `500 Internal Server Error`: Task creation failed

---

### 2.4 Get Task Status
**Endpoint:** `GET /api/videos/tasks/{task_id}`

**Authentication:** Required (API key)

**Description:** Query the status of a video generation task.

**Response (200 OK):**
```json
{
  "task_id": "uuid-string",
  "status": "PENDING",             // PENDING, PROCESSING, SUCCEEDED, FAILED
  "progress": 0.0,                 // 0.0 to 100.0
  "result_url": "https://...",     // Available when status is SUCCEEDED
  "error_message": "string",       // Available when status is FAILED
  "created_at": "2025-01-05T12:00:00Z",
  "updated_at": "2025-01-05T12:00:00Z",
  "completed_at": "2025-01-05T12:03:00Z"  // Available when completed
}
```

**Status Values:**
- `PENDING`: Task is queued
- `PROCESSING`: Task is being processed
- `SUCCEEDED`: Task completed successfully
- `FAILED`: Task failed

**Errors:**
- `404 Not Found`: Task not found

---

### 2.5 Sora Webhook Callback (Internal)
**Endpoint:** `POST /api/videos/sora/callback`

**Description:** Webhook endpoint for Sora API to notify task completion. This endpoint is called by Sora API, not by clients.

**Request:**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "sora-task-id",
    "model": "sora-2.0",
    "state": "success",            // "waiting", "success", "fail"
    "param": "{...}",              // JSON string of task parameters
    "resultJson": "{\"resultUrls\": [\"https://...\"]}",  // JSON string
    "costTime": 120000,            // Milliseconds
    "completeTime": 1704451200000, // Unix timestamp
    "createTime": 1704451080000
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Task completed successfully",
  "task_id": "uuid-string"
}
```

---

## 3. Task Management API (`/api/tasks`)

### 3.1 Get Task Details
**Endpoint:** `GET /api/tasks/{task_id}`

**Authentication:** Required (API key)

**Response (200 OK):**
```json
{
  "task_id": "uuid-string",
  "user_id": "uuid-string",
  "task_type": "TEXT_TO_VIDEO",   // TEXT_TO_VIDEO, IMAGE_TO_VIDEO
  "status": "pending",             // pending, processing, completed, failed
  "progress": 50.0,
  "result_url": "https://...",
  "error_message": null,
  "created_at": "2025-01-05T12:00:00Z",
  "updated_at": "2025-01-05T12:01:00Z",
  "completed_at": null
}
```

**Status Mapping:**
- Backend `PENDING` → Frontend `pending`
- Backend `RUNNING` → Frontend `processing`
- Backend `SUCCEEDED` → Frontend `completed`
- Backend `FAILED/CANCELLED/TIMEOUT` → Frontend `failed`

**Errors:**
- `404 Not Found`: Task not found

---

### 3.2 List User Tasks
**Endpoint:** `GET /api/tasks/user/tasks`

**Authentication:** Required (Bearer token)

**Query Parameters:**
- `page` (integer, default: 1): Page number (≥1)
- `page_size` (integer, default: 10): Items per page (1-100)
- `status` (string, optional): Filter by status

**Response (200 OK):**
```json
{
  "tasks": [
    {
      "task_id": "uuid-string",
      "user_id": "uuid-string",
      "task_type": "TEXT_TO_VIDEO",
      "status": "completed",
      "progress": 100.0,
      "result_url": "https://...",
      "error_message": null,
      "created_at": "2025-01-05T12:00:00Z",
      "updated_at": "2025-01-05T12:03:00Z",
      "completed_at": "2025-01-05T12:03:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 10
}
```

---

### 3.3 Cancel Task
**Endpoint:** `DELETE /api/tasks/{task_id}`

**Authentication:** Required (Bearer token)

**Description:** Cancel a pending or running task.

**Response (200 OK):**
```json
{
  "message": "Task cancelled successfully"
}
```

**Errors:**
- `404 Not Found`: Task not found
- `400 Bad Request`: Cannot cancel task with current status

---

### 3.4 Retry Task
**Endpoint:** `POST /api/tasks/{task_id}/retry`

**Authentication:** Required (Bearer token)

**Description:** Retry a failed task. Creates a new task with the same parameters.

**Response (200 OK):**
```json
{
  "message": "Task retry initiated",
  "task_id": "new-uuid-string",
  "original_task_id": "original-uuid-string"
}
```

**Errors:**
- `404 Not Found`: Task not found
- `400 Bad Request`: Task cannot be retried

---

## 4. Payment API (`/api/payments`)

### 4.1 Get Credit Packages
**Endpoint:** `GET /api/payments/packages`

**Authentication:** None required

**Description:** Get available credit packages for purchase.

**Response (200 OK):**
```json
{
  "packages": {
    "trial": {
      "name": "Trial Pack",
      "credits": 100,
      "price": 9.9,
      "currency": "CNY",
      "unit_price": 0.099
    },
    "standard": {
      "name": "Standard Pack",
      "credits": 500,
      "price": 49.0,
      "currency": "CNY",
      "unit_price": 0.098
    },
    "value": {
      "name": "Value Pack",
      "credits": 1200,
      "price": 99.0,
      "currency": "CNY",
      "unit_price": 0.0825
    },
    "premium": {
      "name": "Premium Pack",
      "credits": 3000,
      "price": 199.0,
      "currency": "CNY",
      "unit_price": 0.0663
    }
  },
  "credit_value_rmb": 0.1
}
```

---

### 4.2 Create Stripe Payment
**Endpoint:** `POST /api/payments/stripe/create`

**Authentication:** Required (Bearer token)

**Description:** Create a Stripe payment session for credit purchase.

**Request:**
```json
{
  "package": "standard",          // Required: trial, standard, value, or premium
  "return_url": "string"          // Optional: URL to redirect after payment
}
```

**Response (200 OK):**
```json
{
  "payment_id": "uuid-string",
  "status": "pending",
  "amount": 49.0,
  "currency": "CNY",
  "credits_purchased": 500,
  "payment_url": "https://checkout.stripe.com/..."  // Redirect user to this URL
}
```

**Errors:**
- `400 Bad Request`: Invalid package
- `500 Internal Server Error`: Payment creation failed

---

### 4.3 Get Payment Status
**Endpoint:** `GET /api/payments/{payment_id}`

**Authentication:** Required (Bearer token)

**Description:** Query payment status by ID.

**Response (200 OK):**
```json
{
  "payment_id": "uuid-string",
  "status": "succeeded",          // pending, succeeded, failed, refunded, partial_refunded
  "amount": 49.0,
  "currency": "CNY",
  "credits_purchased": 500,
  "payment_url": "https://checkout.stripe.com/...",
  "created_at": "2025-01-05T12:00:00Z",
  "paid_at": "2025-01-05T12:02:00Z"
}
```

**Errors:**
- `404 Not Found`: Payment not found

---

### 4.4 Stripe Webhook (Internal)
**Endpoint:** `POST /api/payments/webhook/stripe`

**Description:** Webhook endpoint for Stripe payment events. Called by Stripe, not by clients.

**Headers Required:**
- `stripe-signature`: Stripe signature for verification

**Response (200 OK):**
```json
{
  "received": true
}
```

---

### 4.5 Refund Payment (Admin Only)
**Endpoint:** `POST /api/payments/stripe/refund`

**Authentication:** Required (Bearer token, admin only)

**Description:** Refund a Stripe payment and deduct credits from user.

**Query Parameters:**
- `payment_id` (string, required): Payment ID to refund
- `reason` (string, optional): Refund reason
- `amount` (decimal, optional): Partial refund amount

**Response (200 OK):**
```json
{
  "success": true,
  "refund_id": "stripe-refund-id",
  "amount": 49.0,
  "credits_refunded": 500,
  "message": "Refund processed successfully"
}
```

**Errors:**
- `403 Forbidden`: Only administrators can issue refunds
- `404 Not Found`: Payment not found
- `400 Bad Request`: Cannot refund payment with current status

---

## 5. User Management API (`/api/users`)

### 5.1 Get User Profile
**Endpoint:** `GET /api/users/profile`

**Authentication:** Required (Bearer token)

**Response (200 OK):**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "username": "username",
  "avatar_url": "https://...",
  "region": "CN",                 // CN, US, EU, etc.
  "language": "zh-CN",            // zh-CN, zh-TW, en, ja, ko
  "credits": 1000,
  "created_at": "2025-01-01T00:00:00Z",
  "last_login_at": "2025-01-05T12:00:00Z"
}
```

**Errors:**
- `404 Not Found`: User not found

---

### 5.2 Update User Profile
**Endpoint:** `PUT /api/users/profile`

**Authentication:** Required (Bearer token)

**Request:**
```json
{
  "username": "new_username",     // Optional: 3-50 characters
  "avatar_url": "https://...",    // Optional: Avatar URL
  "language": "zh-CN"             // Optional: zh-CN, zh-TW, en, ja, ko
}
```

**Response (200 OK):**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "username": "new_username",
  "avatar_url": "https://...",
  "region": "CN",
  "language": "zh-CN",
  "credits": 1000,
  "created_at": "2025-01-01T00:00:00Z",
  "last_login_at": "2025-01-05T12:00:00Z"
}
```

**Errors:**
- `400 Bad Request`: Invalid language or username
- `404 Not Found`: User not found

---

### 5.3 Get User Credits
**Endpoint:** `GET /api/users/credits`

**Authentication:** Required (Bearer token)

**Response (200 OK):**
```json
{
  "user_id": "uuid-string",
  "credits": 1000,
  "total_earned": 2000,
  "total_spent": 1000
}
```

---

### 5.4 Get Credit Transaction History
**Endpoint:** `GET /api/users/credits/transactions`

**Authentication:** Required (Bearer token)

**Query Parameters:**
- `page` (integer, default: 1): Page number (≥1)
- `page_size` (integer, default: 20): Items per page (1-100)
- `transaction_type` (string, optional): Filter by type (earned, spent, purchased, refunded, bonus)

**Response (200 OK):**
```json
{
  "total": 42,
  "page": 1,
  "page_size": 20,
  "transactions": [
    {
      "id": "uuid-string",
      "transaction_type": "spent",
      "amount": -20,
      "balance_before": 1020,
      "balance_after": 1000,
      "reference_type": "sora_task_creation",
      "reference_id": "task-uuid",
      "description": "Sora text-to-video (standard): A beautiful sunset...",
      "task_id": "task-uuid",
      "payment_order_id": null,
      "created_at": "2025-01-05T12:00:00Z",
      "expires_at": "2025-04-05T12:00:00Z",  // For purchased credits
      "is_expired": false
    }
  ]
}
```

**Transaction Types:**
- `earned`: Credits earned (e.g., referrals)
- `spent`: Credits spent (e.g., video generation)
- `purchased`: Credits purchased via payment
- `refunded`: Credits refunded (e.g., failed task)
- `bonus`: Bonus credits (e.g., signup bonus)

---

### 5.5 Delete Account
**Endpoint:** `DELETE /api/users/account`

**Authentication:** Required (Bearer token)

**Description:** Soft delete account (marks as inactive).

**Response (200 OK):**
```json
{
  "message": "Account deletion requested. Your account will be deleted within 30 days."
}
```

---

## 6. Video Showcase API (`/api/showcase`)

### 6.1 Get Showcase Videos
**Endpoint:** `GET /api/showcase/videos`

**Authentication:** None required

**Description:** Get paginated list of showcase videos for homepage display.

**Query Parameters:**
- `page` (integer, default: 1): Page number (≥1)
- `page_size` (integer, default: 12): Items per page (1-100)

**Response (200 OK):**
```json
{
  "total": 48,
  "page": 1,
  "page_size": 12,
  "total_pages": 4,
  "videos": [
    {
      "id": 1,
      "title": "Sunset Animation",
      "description": "A beautiful sunset over the ocean",
      "video_url": "https://cdn.example.com/video1.mp4",
      "thumbnail_url": "https://cdn.example.com/thumb1.jpg",
      "task_type": "TEXT_TO_VIDEO",
      "quality": "hd",
      "aspect_ratio": "landscape",
      "duration_seconds": 5.0,
      "view_count": 1234,
      "like_count": 56,
      "display_order": 100,
      "is_active": true,
      "created_at": "2025-01-05T12:00:00Z"
    }
  ]
}
```

**Note:** If the table doesn't exist yet, returns empty array with message.

---

### 6.2 Get Video Detail
**Endpoint:** `GET /api/showcase/videos/{video_id}`

**Authentication:** None required

**Description:** Get single video detail and increment view count.

**Response (200 OK):**
```json
{
  "id": 1,
  "title": "Sunset Animation",
  "description": "A beautiful sunset over the ocean",
  "video_url": "https://cdn.example.com/video1.mp4",
  "thumbnail_url": "https://cdn.example.com/thumb1.jpg",
  "task_type": "TEXT_TO_VIDEO",
  "quality": "hd",
  "aspect_ratio": "landscape",
  "duration_seconds": 5.0,
  "view_count": 1235,            // Incremented
  "like_count": 56,
  "display_order": 100,
  "is_active": true,
  "created_at": "2025-01-05T12:00:00Z"
}
```

**Errors:**
- `404 Not Found`: Video not found
- `503 Service Unavailable`: Showcase feature being set up

---

## Common Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid parameters"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 402 Payment Required
```json
{
  "detail": "Insufficient credits. You need X credits but only have Y available."
}
```

### 403 Forbidden
```json
{
  "detail": "Permission denied"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "prompt"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limits

- **Authentication endpoints:** 5 requests per minute
- **Video generation endpoints:** 10 requests per minute per user
- **Task query endpoints:** 60 requests per minute
- **Other endpoints:** 30 requests per minute

---

## Webhook Integration

### Sora Webhook Callback
When creating tasks with `webhook_url`, Sora API will POST to your webhook URL when the task completes:

**Webhook Request (from Sora):**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "sora-task-id",
    "state": "success",
    "resultJson": "{\"resultUrls\": [\"https://video-url.mp4\"]}"
  }
}
```

**Your webhook should respond:**
```json
{
  "received": true
}
```

---

## Credit Pricing Summary

### Sora Video Generation (Fixed pricing per video)
- **Text-to-Video (Standard):** 20 credits
- **Text-to-Video (HD):** 30 credits
- **Image-to-Video (Standard):** 25 credits
- **Image-to-Video (HD):** 35 credits

### Credit Packages
- **Trial Pack:** 100 credits for ¥9.9 (¥0.099/credit)
- **Standard Pack:** 500 credits for ¥49 (¥0.098/credit)
- **Value Pack:** 1,200 credits for ¥99 (¥0.0825/credit)
- **Premium Pack:** 3,000 credits for ¥199 (¥0.0663/credit)

### Credit Expiration
- **Purchased credits:** Expire after 90 days
- **Bonus credits:** Expire after 30 days
- **Deduction follows FIFO (First In First Out)** - oldest credits expire first

---

## Testing with Postman/APIPOST

### 1. Get Access Token
```bash
# Development test login
POST http://localhost:8001/api/auth/test/login?email=test@example.com

# Production Google OAuth
POST http://localhost:8001/api/auth/google/login
{
  "code": "google-auth-code",
  "redirect_uri": "http://localhost:3000/auth/callback"
}
```

### 2. Set Authorization Header
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
X-API-Key: your-api-key
```

### 3. Upload Image
```bash
POST http://localhost:8001/api/videos/upload
Content-Type: multipart/form-data

file: [select file]
file_type: image
```

### 4. Create Video Task
```bash
POST http://localhost:8001/api/videos/text-to-video
{
  "prompt": "A beautiful sunset over the ocean with waves crashing",
  "aspect_ratio": "landscape",
  "quality": "standard"
}
```

### 5. Check Task Status
```bash
GET http://localhost:8001/api/videos/tasks/{task_id}
```

---

## Environment Variables Reference

```env
# API Configuration
API_BASE_URL=http://localhost:8001
FRONTEND_URL=http://localhost:3000
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Stripe Payment
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Sora API
SORA_API_KEY=your-sora-api-key
SORA_API_BASE_URL=https://api.sora.com

# Storage (Aliyun OSS)
ALIYUN_OSS_ACCESS_KEY=your-access-key
ALIYUN_OSS_SECRET_KEY=your-secret-key
ALIYUN_OSS_BUCKET=your-bucket-name
ALIYUN_OSS_ENDPOINT=https://oss-cn-beijing.aliyuncs.com
ALIYUN_OSS_CDN_DOMAIN=cdn.yourdomain.com

# Credits
DEFAULT_USER_CREDITS=100
CREDIT_VALUE_RMB=0.1
```

---

## Development Notes

1. **Base64/Blob URLs not supported:** Always upload files first using `/api/videos/upload` endpoint
2. **Credit deduction:** Credits are deducted immediately for Sora tasks and refunded if task fails
3. **Task status polling:** Poll `/api/videos/tasks/{task_id}` every 5-10 seconds until completion
4. **Webhook recommended:** Use webhook_url for automatic task completion notifications
5. **CDN URLs:** Video URLs are automatically converted to CDN URLs in showcase endpoints

---

## Support

For API support, please contact:
- **Email:** support@example.com
- **Documentation:** https://docs.example.com
- **Status Page:** https://status.example.com
