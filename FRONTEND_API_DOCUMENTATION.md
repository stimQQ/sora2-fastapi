# 前端开发 API 文档

**项目**: Video Animation Platform (Wan2.2-Animate)
**后端框架**: FastAPI
**前端框架**: Next.js
**API Base URL**: `http://localhost:8000/api` (开发环境)
**API Base URL**: `https://api.your-domain.com/api` (生产环境)

---

## 目录

1. [认证接口 (Authentication)](#1-认证接口-authentication)
2. [视频处理接口 (Videos)](#2-视频处理接口-videos)
3. [任务管理接口 (Tasks)](#3-任务管理接口-tasks)
4. [用户管理接口 (Users)](#4-用户管理接口-users)
5. [支付接口 (Payments)](#5-支付接口-payments)
6. [Next.js 集成示例](#6-nextjs-集成示例)
7. [错误处理](#7-错误处理)

---

## 通用说明

### 认证方式

所有需要认证的接口都使用 **JWT Token** 认证：

```
Authorization: Bearer <access_token>
```

部分接口还需要 **API Key**：

```
X-API-Key: <your_api_key>
```

### 响应格式

成功响应：
```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

错误响应：
```json
{
  "detail": "错误信息"
}
```

### 积分价格

- **1 积分 = ¥0.1 元**
- 新用户赠送 100 积分

---

## 1. 认证接口 (Authentication)

### 1.1 发送短信验证码

**POST** `/api/auth/sms/send`

发送 6 位数短信验证码到用户手机。

**请求参数**:
```typescript
{
  phone_number: string;  // 带国家码的手机号，如 "86-13800138000"
}
```

**响应**:
```typescript
{
  message: string;          // "Verification code sent successfully"
  phone_number: string;     // 手机号
  expires_in: number;       // 过期时间（秒），300 = 5分钟
  remaining_requests: number;  // 剩余可用次数
}
```

**限流规则**:
- 每小时最多 5 次请求
- 验证码 5 分钟过期

**示例**:
```bash
curl -X POST "http://localhost:8000/api/auth/sms/send" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "86-13800138000"
  }'
```

---

### 1.2 短信登录/注册

**POST** `/api/auth/sms/login`

验证短信验证码并登录，如果用户不存在则自动注册。

**请求参数**:
```typescript
{
  phone_number: string;   // 手机号
  code: string;           // 6位验证码
  username?: string;      // 可选：用户名（新用户注册时）
}
```

**响应**:
```typescript
{
  access_token: string;   // JWT 访问令牌
  refresh_token: string;  // 刷新令牌
  token_type: string;     // "bearer"
  expires_in: number;     // 过期时间（秒），86400 = 24小时
}
```

**示例**:
```bash
curl -X POST "http://localhost:8000/api/auth/sms/login" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "86-13800138000",
    "code": "123456",
    "username": "张三"
  }'
```

---

### 1.3 Google OAuth 登录

**POST** `/api/auth/google/login`

使用 Google OAuth 授权码登录。

**请求参数**:
```typescript
{
  code: string;           // Google OAuth 授权码
  redirect_uri?: string;  // 重定向 URI（可选）
}
```

**响应**:
```typescript
{
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}
```

**前端流程**:
1. 前端跳转到 Google OAuth 授权页
2. 用户授权后，Google 回调返回 `code`
3. 前端将 `code` 发送到此接口
4. 后端验证并返回 JWT Token

---

### 1.4 刷新 Token

**POST** `/api/auth/refresh`

使用 refresh_token 刷新 access_token。

**请求参数**:
```typescript
{
  refresh_token: string;
}
```

**响应**:
```typescript
{
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}
```

---

### 1.5 登出

**POST** `/api/auth/logout`

**认证**: 需要 JWT Token

登出当前用户，使 token 失效。

**请求头**:
```
Authorization: Bearer <access_token>
```

**响应**:
```typescript
{
  message: "Successfully logged out"
}
```

---

### 1.6 获取当前用户信息

**GET** `/api/auth/me`

**认证**: 需要 JWT Token

获取当前登录用户的信息。

**响应**:
```typescript
{
  id: string;
  phone_number?: string;
  email?: string;
  username: string;
  credits: number;
  avatar_url?: string;
  region: string;
}
```

---

## 2. 视频处理接口 (Videos)

### 2.1 图像动画化 - animate-move

**POST** `/api/videos/animate-move`

**认证**: 需要 JWT Token + API Key

将视频的动作迁移到静态图片上。

**请求参数**:
```typescript
{
  image_url: string;      // 输入图片 URL
  video_url: string;      // 参考视频 URL
  check_image?: boolean;  // 是否检查图片质量，默认 true
  mode?: "wan-std" | "wan-pro";  // 处理模式，默认 "wan-std"
  webhook_url?: string;   // 任务完成回调 URL（可选）
}
```

**响应**:
```typescript
{
  success: boolean;
  task_id: string;        // 任务 ID
  message: string;
  estimated_time?: number;  // 预计处理时间（秒）
}
```

**积分消耗**:
- **按视频时长计费**（任务完成后扣费）
- 标准版：10 积分/秒
- 专业版：14 积分/秒

**示例**:
```bash
curl -X POST "http://localhost:8000/api/videos/animate-move" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "X-API-Key: <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg",
    "video_url": "https://example.com/video.mp4",
    "mode": "wan-std"
  }'
```

---

### 2.2 视频换脸 - animate-mix

**POST** `/api/videos/animate-mix`

**认证**: 需要 JWT Token + API Key

将图片中的人物替换到视频中。

**请求参数**:
```typescript
{
  image_url: string;      // 输入人脸图片 URL
  video_url: string;      // 目标视频 URL
  check_image?: boolean;  // 是否检查图片质量，默认 true
  mode?: "wan-std" | "wan-pro";  // 处理模式
  webhook_url?: string;   // 任务完成回调 URL
}
```

**响应**:
```typescript
{
  success: boolean;
  task_id: string;
  message: string;
  estimated_time?: number;
}
```

**积分消耗**:
- 标准版：10 积分/秒
- 专业版：14 积分/秒

---

### 2.3 文本生成视频 (Sora2)

**POST** `/api/videos/text-to-video`

**认证**: 需要 JWT Token + API Key

使用 Sora2 根据文本描述生成视频。

**请求参数**:
```typescript
{
  prompt: string;         // 视频描述（最多 5000 字符）
  aspect_ratio?: "landscape" | "portrait";  // 画面比例，默认 "landscape"
  quality?: "standard" | "hd";  // 视频质量，默认 "standard"
  webhook_url?: string;   // 任务完成回调 URL
}
```

**响应**:
```typescript
{
  success: boolean;
  task_id: string;
  message: string;        // "Text-to-video task created successfully. Credits deducted."
  credits_estimated: number;  // 扣除的积分
  estimated_time?: number;    // 预计 180 秒
}
```

**积分消耗（立即扣费）**:
- Standard 质量：**20 积分**
- HD 质量：**30 积分**

**重要**:
- 积分在任务创建时**立即扣除**
- 如果任务失败，积分会**自动退款**

**示例**:
```bash
curl -X POST "http://localhost:8000/api/videos/text-to-video" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "X-API-Key: <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "一个美丽的日落场景，海浪轻轻拍打着沙滩",
    "aspect_ratio": "landscape",
    "quality": "standard"
  }'
```

---

### 2.4 图片生成视频 (Sora2)

**POST** `/api/videos/image-to-video`

**认证**: 需要 JWT Token + API Key

使用 Sora2 将静态图片动画化。

**请求参数**:
```typescript
{
  prompt: string;         // 动画描述（最多 5000 字符）
  image_urls: string[];   // 图片 URL 数组（至少 1 张）
  aspect_ratio?: "landscape" | "portrait";
  quality?: "standard" | "hd";
  webhook_url?: string;
}
```

**响应**:
```typescript
{
  success: boolean;
  task_id: string;
  message: string;        // "Image-to-video task created successfully. Credits deducted."
  credits_estimated: number;
  estimated_time?: number;
}
```

**积分消耗（立即扣费）**:
- Standard 质量：**25 积分**
- HD 质量：**35 积分**

**重要**:
- 积分在任务创建时**立即扣除**
- 如果任务失败，积分会**自动退款**

---

### 2.5 文件上传

**POST** `/api/videos/upload`

**认证**: 需要 JWT Token + API Key

上传图片或视频文件到云存储。

**请求参数** (multipart/form-data):
```typescript
{
  file: File;             // 文件对象
  file_type: "image" | "video";  // 文件类型
}
```

**响应**:
```typescript
{
  success: boolean;
  file_url: string;       // 文件 URL
  storage_key: string;    // 存储键
  file_size: number;      // 文件大小（字节）
  content_type: string;   // MIME 类型
  file_type: string;      // "image" 或 "video"
  message: string;
}
```

**限制**:
- 最大文件大小：100MB
- 支持的图片格式：.jpg, .jpeg, .png, .webp
- 支持的视频格式：.mp4, .mov, .avi, .webm

**示例** (Next.js):
```typescript
const formData = new FormData();
formData.append('file', file);
formData.append('file_type', 'image');

const response = await fetch('/api/videos/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'X-API-Key': apiKey,
  },
  body: formData,
});
```

---

### 2.6 查询任务状态

**GET** `/api/videos/tasks/{task_id}`

**认证**: 需要 API Key

查询视频处理任务的状态。

**路径参数**:
- `task_id`: 任务 ID

**响应**:
```typescript
{
  task_id: string;
  status: string;         // "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED" | "TIMEOUT"
  progress?: number;      // 进度 0-100
  result_url?: string;    // 结果视频 URL（成功时）
  error_message?: string; // 错误信息（失败时）
  created_at: string;     // ISO 8601 时间
  updated_at: string;
  completed_at?: string;
}
```

**示例**:
```bash
curl -X GET "http://localhost:8000/api/videos/tasks/abc123" \
  -H "X-API-Key: <API_KEY>"
```

---

## 3. 任务管理接口 (Tasks)

### 3.1 获取任务详情

**GET** `/api/tasks/{task_id}`

**认证**: 需要 API Key

获取任务详细信息。

**响应**:
```typescript
{
  task_id: string;
  user_id: string;
  task_type: string;      // "animate-move" | "animate-mix" | "text-to-video" | "image-to-video"
  status: string;
  progress?: number;
  result_url?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}
```

---

### 3.2 列出用户任务

**GET** `/api/tasks/user/tasks`

**认证**: 需要 JWT Token

获取当前用户的所有任务列表。

**查询参数**:
```typescript
{
  page?: number;          // 页码，默认 1
  page_size?: number;     // 每页数量，默认 10，最大 100
  status?: string;        // 过滤状态（可选）
}
```

**响应**:
```typescript
{
  tasks: Array<{
    task_id: string;
    user_id: string;
    task_type: string;
    status: string;
    progress?: number;
    result_url?: string;
    error_message?: string;
    created_at: string;
    updated_at: string;
    completed_at?: string;
  }>;
  total: number;          // 总任务数
  page: number;           // 当前页码
  page_size: number;      // 每页数量
}
```

**示例**:
```bash
curl -X GET "http://localhost:8000/api/tasks/user/tasks?page=1&page_size=20" \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

---

### 3.3 取消任务

**DELETE** `/api/tasks/{task_id}`

**认证**: 需要 JWT Token

取消正在处理的任务。

**响应**:
```typescript
{
  message: "Task cancellation requested"
}
```

---

### 3.4 重试任务

**POST** `/api/tasks/{task_id}/retry`

**认证**: 需要 JWT Token

重试失败的任务。

**响应**:
```typescript
{
  message: "Task retry initiated";
  new_task_id: string;
}
```

---

## 4. 用户管理接口 (Users)

### 4.1 获取用户资料

**GET** `/api/users/profile`

**认证**: 需要 JWT Token

获取当前用户的个人资料。

**响应**:
```typescript
{
  id: string;
  email: string;
  username?: string;
  avatar_url?: string;
  region: string;         // "CN" | "US" | "EU" | "ASIA"
  credits: number;
  created_at: string;
  last_login_at?: string;
}
```

---

### 4.2 更新用户资料

**PUT** `/api/users/profile`

**认证**: 需要 JWT Token

更新用户资料。

**请求参数**:
```typescript
{
  username?: string;      // 用户名（3-50 字符）
  avatar_url?: string;    // 头像 URL
}
```

**响应**:
```typescript
{
  id: string;
  email: string;
  username?: string;
  avatar_url?: string;
  region: string;
  credits: number;
  created_at: string;
  last_login_at?: string;
}
```

---

### 4.3 获取积分余额

**GET** `/api/users/credits`

**认证**: 需要 JWT Token

获取用户积分余额及统计。

**响应**:
```typescript
{
  user_id: string;
  credits: number;        // 当前积分
  total_earned: number;   // 累计获得
  total_spent: number;    // 累计消费
}
```

---

### 4.4 删除账户

**DELETE** `/api/users/account`

**认证**: 需要 JWT Token

删除用户账户（软删除）。

**响应**:
```typescript
{
  message: "Account deletion requested. Your account will be deleted within 30 days."
}
```

---

## 5. 支付接口 (Payments)

### 5.1 创建微信支付订单

**POST** `/api/payments/wechat/create`

**认证**: 需要 JWT Token

**状态**: 未实现（501）

**请求参数**:
```typescript
{
  amount: number;         // 金额（元）
  currency: string;       // 货币，默认 "CNY"
  credits: number;        // 购买积分数
  return_url?: string;    // 支付成功返回 URL
}
```

---

### 5.2 创建 Stripe 支付订单

**POST** `/api/payments/stripe/create`

**认证**: 需要 JWT Token

**状态**: 未实现（501）

**请求参数**: 同微信支付

---

### 5.3 查询支付状态

**GET** `/api/payments/{payment_id}`

**认证**: 需要 JWT Token

查询支付订单状态。

**响应**:
```typescript
{
  payment_id: string;
  status: string;         // "pending" | "completed" | "failed"
  amount: number;
  currency: string;
}
```

---

## 6. Next.js 集成示例

### 6.1 创建 API 客户端

创建 `lib/api-client.ts`:

```typescript
// lib/api-client.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

interface FetchOptions extends RequestInit {
  requireAuth?: boolean;
  requireApiKey?: boolean;
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const {
    requireAuth = false,
    requireApiKey = false,
    headers = {},
    ...fetchOptions
  } = options;

  const url = `${API_BASE_URL}${endpoint}`;

  // 构建请求头
  const requestHeaders: HeadersInit = {
    'Content-Type': 'application/json',
    ...headers,
  };

  // 添加 JWT Token
  if (requireAuth) {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new APIError('Not authenticated', 401);
    }
    requestHeaders['Authorization'] = `Bearer ${token}`;
  }

  // 添加 API Key
  if (requireApiKey) {
    requestHeaders['X-API-Key'] = API_KEY;
  }

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      headers: requestHeaders,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new APIError(
        error.detail || `HTTP ${response.status}`,
        response.status,
        error.detail
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError('Network error', 0, String(error));
  }
}
```

---

### 6.2 认证相关 Hook

创建 `hooks/useAuth.ts`:

```typescript
// hooks/useAuth.ts
import { useState, useEffect } from 'react';
import { apiRequest } from '@/lib/api-client';

interface User {
  id: string;
  username: string;
  email?: string;
  credits: number;
  avatar_url?: string;
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUser();
  }, []);

  const loadUser = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setLoading(false);
        return;
      }

      const userData = await apiRequest<User>('/auth/me', {
        requireAuth: true,
      });

      setUser(userData);
    } catch (error) {
      console.error('Failed to load user:', error);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    } finally {
      setLoading(false);
    }
  };

  const login = async (accessToken: string, refreshToken: string) => {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    await loadUser();
  };

  const logout = async () => {
    try {
      await apiRequest('/auth/logout', {
        method: 'POST',
        requireAuth: true,
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
    }
  };

  return { user, loading, login, logout, refreshUser: loadUser };
}
```

---

### 6.3 短信登录组件示例

```typescript
// components/SMSLogin.tsx
'use client';

import { useState } from 'react';
import { apiRequest } from '@/lib/api-client';
import { useAuth } from '@/hooks/useAuth';

export default function SMSLogin() {
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [step, setStep] = useState<'phone' | 'code'>('phone');
  const [loading, setLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const { login } = useAuth();

  const sendCode = async () => {
    setLoading(true);
    try {
      await apiRequest('/auth/sms/send', {
        method: 'POST',
        body: JSON.stringify({ phone_number: phone }),
      });

      setStep('code');
      setCountdown(60);

      // 倒计时
      const timer = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (error: any) {
      alert(error.detail || '发送验证码失败');
    } finally {
      setLoading(false);
    }
  };

  const verifyCode = async () => {
    setLoading(true);
    try {
      const response = await apiRequest<{
        access_token: string;
        refresh_token: string;
      }>('/auth/sms/login', {
        method: 'POST',
        body: JSON.stringify({
          phone_number: phone,
          code: code,
        }),
      });

      await login(response.access_token, response.refresh_token);
      alert('登录成功！');
    } catch (error: any) {
      alert(error.detail || '验证失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">手机号登录</h2>

      {step === 'phone' ? (
        <div>
          <input
            type="tel"
            placeholder="86-13800138000"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="w-full px-4 py-2 border rounded mb-4"
          />
          <button
            onClick={sendCode}
            disabled={loading || !phone}
            className="w-full bg-blue-600 text-white py-2 rounded disabled:opacity-50"
          >
            {loading ? '发送中...' : '发送验证码'}
          </button>
        </div>
      ) : (
        <div>
          <input
            type="text"
            placeholder="请输入 6 位验证码"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            maxLength={6}
            className="w-full px-4 py-2 border rounded mb-4"
          />
          <button
            onClick={verifyCode}
            disabled={loading || code.length !== 6}
            className="w-full bg-blue-600 text-white py-2 rounded disabled:opacity-50 mb-2"
          >
            {loading ? '验证中...' : '登录'}
          </button>
          <button
            onClick={() => setStep('phone')}
            disabled={countdown > 0}
            className="w-full text-gray-600 disabled:opacity-50"
          >
            {countdown > 0 ? `${countdown}秒后重新发送` : '重新发送'}
          </button>
        </div>
      )}
    </div>
  );
}
```

---

### 6.4 视频生成组件示例

```typescript
// components/VideoGenerator.tsx
'use client';

import { useState } from 'react';
import { apiRequest, APIError } from '@/lib/api-client';

export default function VideoGenerator() {
  const [prompt, setPrompt] = useState('');
  const [quality, setQuality] = useState<'standard' | 'hd'>('standard');
  const [taskId, setTaskId] = useState('');
  const [loading, setLoading] = useState(false);

  const generateVideo = async () => {
    setLoading(true);
    try {
      const response = await apiRequest<{
        success: boolean;
        task_id: string;
        message: string;
        credits_estimated: number;
      }>('/videos/text-to-video', {
        method: 'POST',
        requireAuth: true,
        requireApiKey: true,
        body: JSON.stringify({
          prompt,
          quality,
          aspect_ratio: 'landscape',
        }),
      });

      setTaskId(response.task_id);
      alert(`任务创建成功！扣除 ${response.credits_estimated} 积分`);

      // 开始轮询任务状态
      pollTaskStatus(response.task_id);
    } catch (error) {
      if (error instanceof APIError) {
        if (error.status === 402) {
          alert('积分不足，请充值');
        } else {
          alert(error.detail || '创建任务失败');
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const pollTaskStatus = async (id: string) => {
    const interval = setInterval(async () => {
      try {
        const status = await apiRequest<{
          task_id: string;
          status: string;
          result_url?: string;
        }>(`/videos/tasks/${id}`, {
          requireApiKey: true,
        });

        if (status.status === 'SUCCEEDED') {
          clearInterval(interval);
          alert(`视频生成成功！URL: ${status.result_url}`);
        } else if (status.status === 'FAILED') {
          clearInterval(interval);
          alert('任务失败，积分已自动退款');
        }
      } catch (error) {
        console.error('Poll error:', error);
      }
    }, 5000); // 每 5 秒轮询一次
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">文本生成视频 (Sora2)</h2>

      <textarea
        placeholder="描述你想生成的视频场景..."
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        maxLength={5000}
        rows={6}
        className="w-full px-4 py-2 border rounded mb-4"
      />

      <div className="mb-4">
        <label className="block mb-2">质量</label>
        <select
          value={quality}
          onChange={(e) => setQuality(e.target.value as any)}
          className="px-4 py-2 border rounded"
        >
          <option value="standard">标准 (20 积分)</option>
          <option value="hd">高清 (30 积分)</option>
        </select>
      </div>

      <button
        onClick={generateVideo}
        disabled={loading || !prompt}
        className="w-full bg-green-600 text-white py-3 rounded disabled:opacity-50"
      >
        {loading ? '创建中...' : '生成视频'}
      </button>

      {taskId && (
        <div className="mt-4 p-4 bg-gray-100 rounded">
          <p>任务 ID: {taskId}</p>
          <p className="text-sm text-gray-600">正在处理，请稍候...</p>
        </div>
      )}
    </div>
  );
}
```

---

### 6.5 环境变量配置

创建 `.env.local`:

```bash
# API 配置
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
NEXT_PUBLIC_API_KEY=your-api-key-here

# Google OAuth (如果使用)
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id
```

---

## 7. 错误处理

### 常见 HTTP 状态码

| 状态码 | 说明 | 处理建议 |
|--------|------|----------|
| 200 | 成功 | 正常处理响应数据 |
| 400 | 请求参数错误 | 检查请求参数格式 |
| 401 | 未认证 | 重新登录或刷新 Token |
| 402 | 积分不足 | 提示用户充值 |
| 403 | 无权限 | 提示用户权限不足 |
| 404 | 资源不存在 | 检查 URL 或资源 ID |
| 422 | 验证错误 | 显示字段级错误信息 |
| 429 | 请求过于频繁 | 显示限流提示，稍后重试 |
| 500 | 服务器错误 | 提示用户稍后重试 |
| 501 | 功能未实现 | 提示该功能正在开发中 |

### 错误响应示例

```json
{
  "detail": "Insufficient credits. Required: 20 credits (standard quality). Available: 10 credits."
}
```

或字段级验证错误：

```json
{
  "detail": [
    {
      "loc": ["body", "prompt"],
      "msg": "ensure this value has at most 5000 characters",
      "type": "value_error.any_str.max_length"
    }
  ]
}
```

---

## 附录

### A. 积分价格表

| 功能 | 计费方式 | 标准版 | 专业版/HD |
|------|----------|--------|-----------|
| **DashScope (Wan2.2)** | | | |
| animate-move | 按秒 | 10 积分/秒 | 14 积分/秒 |
| animate-mix | 按秒 | 10 积分/秒 | 14 积分/秒 |
| **Sora2** | | | |
| text-to-video | 固定 | 20 积分 | 30 积分 |
| image-to-video | 固定 | 25 积分 | 35 积分 |

### B. 充值套餐

| 套餐 | 积分 | 价格 | 单价 |
|------|------|------|------|
| 体验包 | 500 | ¥50 | ¥0.10/积分 |
| 标准包 | 1,100 | ¥100 | ¥0.091/积分 |
| 超值包 | 6,000 | ¥500 | ¥0.083/积分 |
| 豪华包 | 13,000 | ¥1,000 | ¥0.076/积分 |

---

**文档版本**: 1.0
**更新日期**: 2025-10-04
**联系方式**: [您的联系方式]
