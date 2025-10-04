# 前端Vercel + 后端阿里云部署方案

## 一、架构设计

### 整体架构
```
用户 → Vercel前端(全球CDN) → API请求 → 阿里云后端(中国)
                              ↓
                    通过优化策略减少延迟
```

## 二、Vercel Functions API代理

### 创建 API 代理函数
在前端项目中创建 `api/proxy/[...path].js`:

```javascript
// api/proxy/[...path].js
export default async function handler(req, res) {
  const { path } = req.query;
  const apiPath = Array.isArray(path) ? path.join('/') : path;

  // 后端API地址
  const BACKEND_URL = process.env.BACKEND_API_URL || 'https://api.yourdomain.com';

  // 构建完整URL
  const url = `${BACKEND_URL}/${apiPath}`;

  try {
    const response = await fetch(url, {
      method: req.method,
      headers: {
        ...req.headers,
        'X-API-Key': process.env.PROXY_API_KEY,
        'X-Forwarded-For': req.headers['x-forwarded-for'] || req.connection.remoteAddress,
      },
      body: req.method !== 'GET' ? JSON.stringify(req.body) : undefined,
    });

    const data = await response.json();

    // 设置缓存策略
    res.setHeader('Cache-Control', 's-maxage=10, stale-while-revalidate');
    res.status(response.status).json(data);
  } catch (error) {
    res.status(500).json({ error: 'API request failed', message: error.message });
  }
}
```

## 三、前端配置

### 1. 环境变量 (.env.local)
```env
NEXT_PUBLIC_API_URL=/api/proxy
NEXT_PUBLIC_DIRECT_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_USE_PROXY=true
```

### 2. API 客户端封装
```javascript
// lib/api-client.js
class APIClient {
  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_USE_PROXY === 'true'
      ? process.env.NEXT_PUBLIC_API_URL
      : process.env.NEXT_PUBLIC_DIRECT_API_URL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;

    const config = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API Request failed:', error);
      throw error;
    }
  }

  // 任务相关API
  async createAnimateTask(type, data) {
    return this.request(`/wan-2.2-animate-${type}/task`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async queryTaskStatus(type, taskId) {
    return this.request(`/wan-2.2-animate-${type}/query/${taskId}`);
  }
}

export default new APIClient();
```

## 四、后端CORS配置更新

更新 FastAPI 后端的 CORS 设置：

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS配置 - 允许Vercel域名
origins = [
    "http://localhost:3000",  # 本地开发
    "https://your-app.vercel.app",  # Vercel生产域名
    "https://*.vercel.app",  # Vercel预览域名
    # 如果有自定义域名
    "https://yourdomain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # 预检请求缓存时间
)
```

## 五、性能优化策略

### 1. 请求优化
- **预连接**: 在HTML head中添加预连接
  ```html
  <link rel="preconnect" href="https://api.yourdomain.com">
  <link rel="dns-prefetch" href="https://api.yourdomain.com">
  ```

### 2. 缓存策略
- **浏览器缓存**: 对于不常变的数据设置缓存
- **SWR/React Query**: 使用数据获取库管理缓存
  ```javascript
  import useSWR from 'swr';

  function useTask(taskId) {
    const { data, error, mutate } = useSWR(
      taskId ? `/api/query/${taskId}` : null,
      fetcher,
      {
        refreshInterval: 2000, // 每2秒刷新
        revalidateOnFocus: false,
      }
    );

    return {
      task: data,
      isLoading: !error && !data,
      isError: error,
      refresh: mutate,
    };
  }
  ```

### 3. 并发请求优化
```javascript
// 批量请求处理
async function batchAPIRequests(requests) {
  const results = await Promise.allSettled(requests);
  return results.map(result =>
    result.status === 'fulfilled' ? result.value : null
  );
}
```

## 六、部署流程

### 1. Vercel部署
```bash
# 安装Vercel CLI
npm i -g vercel

# 登录
vercel login

# 部署
vercel --prod

# 设置环境变量
vercel env add BACKEND_API_URL
vercel env add PROXY_API_KEY
```

### 2. 域名配置
- Vercel自动分配: `your-app.vercel.app`
- 自定义域名: 在Vercel Dashboard添加域名
- API域名: 需要在阿里云备案

## 七、监控与调试

### 1. Vercel Analytics
- 自动性能监控
- 实时错误追踪
- 用户地理分布

### 2. API监控
```javascript
// 添加请求追踪
async function trackedRequest(url, options) {
  const startTime = Date.now();

  try {
    const response = await fetch(url, options);
    const duration = Date.now() - startTime;

    // 发送监控数据
    if (window.analytics) {
      window.analytics.track('API Request', {
        url,
        duration,
        status: response.status,
      });
    }

    return response;
  } catch (error) {
    // 错误上报
    console.error('API Error:', error);
    throw error;
  }
}
```

## 八、国际用户优化方案

### 方案1: 边缘函数加速
使用 Vercel Edge Functions 或 Cloudflare Workers：

```javascript
// api/edge-proxy.js
export const config = {
  runtime: 'edge',
};

export default async function handler(request) {
  const { searchParams } = new URL(request.url);

  // 根据用户地理位置选择最近的API节点
  const region = request.headers.get('x-vercel-ip-country');

  let apiUrl = 'https://api-cn.yourdomain.com'; // 默认中国节点

  if (['US', 'CA', 'MX'].includes(region)) {
    apiUrl = 'https://api-us.yourdomain.com'; // 美洲节点
  } else if (['GB', 'FR', 'DE'].includes(region)) {
    apiUrl = 'https://api-eu.yourdomain.com'; // 欧洲节点
  }

  // 转发请求
  const response = await fetch(apiUrl + request.url, {
    method: request.method,
    headers: request.headers,
    body: request.body,
  });

  return response;
}
```

### 方案2: 多地域API部署
- 主节点：阿里云中国
- 亚太节点：阿里云新加坡/香港
- 数据同步：使用消息队列同步

## 九、成本分析

### Vercel成本
- **Hobby(免费)**:
  - 100GB带宽/月
  - 无限静态请求
  - 100小时Functions执行时间

- **Pro($20/月)**:
  - 1TB带宽/月
  - 1000小时Functions执行时间
  - 团队协作

### 总成本对比
- 纯国内部署: ~¥2200/月
- Vercel+阿里云: ~¥1500/月 + $0-20
- 节省: 约30%成本

## 十、最佳实践建议

1. **渐进式优化**
   - 先部署基础版本
   - 根据用户分布优化
   - 逐步添加边缘节点

2. **监控指标**
   - API响应时间
   - 地域访问分布
   - 错误率统计

3. **备用方案**
   - 准备直连备用
   - 多CDN容灾
   - 静态资源本地化

这个方案特别适合：
- 初创项目（成本敏感）
- 用户分布全球
- 快速迭代需求
- 团队规模较小