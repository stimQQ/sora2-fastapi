# 双系统架构设计：微信/支付 vs Google/Stripe

## 一、整体架构设计

### 系统架构图
```
┌──────────────────────────────────────────────────────┐
│                    用户访问层                          │
├──────────────────────────────────────────────────────┤
│   中国用户                    海外用户                  │
│      ↓                          ↓                     │
│  微信H5/小程序              Web App (Vercel)           │
└──────────────────────────────────────────────────────┘
                    ↓ 智能路由 ↓
┌──────────────────────────────────────────────────────┐
│                  统一API网关                           │
├──────────────────────────────────────────────────────┤
│           Region Detection & Routing                   │
│                     ↓                                 │
│    ┌─────────────────┴──────────────────┐            │
│    │                                    │            │
│  China Region                    Global Region        │
│    ↓                                    ↓            │
│  WeChat Auth                      Google Auth         │
│  WeChat Pay                       Stripe Pay          │
└──────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│                  数据层（统一）                        │
├──────────────────────────────────────────────────────┤
│  用户数据 | 任务数据 | 支付记录 | 文件存储             │
└──────────────────────────────────────────────────────┘
```

## 二、核心模块设计

### 1. 地域检测与路由

```python
# services/region_detector.py
from fastapi import Request
import geoip2.database
import httpx

class RegionDetector:
    def __init__(self):
        # GeoIP2数据库用于IP地理位置识别
        self.reader = geoip2.database.Reader('GeoLite2-Country.mmdb')

    async def detect_region(self, request: Request) -> str:
        """
        检测用户地域
        返回: 'CN' | 'GLOBAL'
        """
        # 1. 检查请求头中的地域标识
        region_header = request.headers.get('X-User-Region')
        if region_header:
            return region_header

        # 2. 通过IP地址检测
        client_ip = request.headers.get('X-Forwarded-For',
                                       request.client.host)
        try:
            response = self.reader.country(client_ip)
            country_code = response.country.iso_code

            # 中国大陆、香港、澳门用户使用中国服务
            if country_code in ['CN', 'HK', 'MO']:
                return 'CN'
            return 'GLOBAL'
        except:
            # 默认使用全球服务
            return 'GLOBAL'

    def get_services(self, region: str) -> dict:
        """根据地域返回相应的服务配置"""
        if region == 'CN':
            return {
                'auth': 'wechat',
                'payment': 'wechat_pay',
                'storage': 'oss',
                'cdn': 'aliyun_cdn'
            }
        else:
            return {
                'auth': 'google',
                'payment': 'stripe',
                'storage': 's3',
                'cdn': 'cloudflare'
            }
```

### 2. 双认证系统

```python
# services/auth/auth_factory.py
from abc import ABC, abstractmethod
from typing import Optional

class AuthProvider(ABC):
    @abstractmethod
    async def login(self, code: str) -> dict:
        pass

    @abstractmethod
    async def get_user_info(self, token: str) -> dict:
        pass

class WeChatAuth(AuthProvider):
    """微信认证实现"""
    def __init__(self):
        self.app_id = os.getenv('WECHAT_APP_ID')
        self.app_secret = os.getenv('WECHAT_APP_SECRET')

    async def login(self, code: str) -> dict:
        """微信登录"""
        # 1. 通过code获取access_token
        url = f"https://api.weixin.qq.com/sns/oauth2/access_token"
        params = {
            'appid': self.app_id,
            'secret': self.app_secret,
            'code': code,
            'grant_type': 'authorization_code'
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()

        # 2. 获取用户信息
        user_info = await self.get_user_info(
            data['access_token'],
            data['openid']
        )

        return {
            'provider': 'wechat',
            'openid': data['openid'],
            'unionid': data.get('unionid'),
            'user_info': user_info,
            'access_token': data['access_token']
        }

    async def get_user_info(self, token: str, openid: str) -> dict:
        url = "https://api.weixin.qq.com/sns/userinfo"
        params = {
            'access_token': token,
            'openid': openid,
            'lang': 'zh_CN'
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            return response.json()

class GoogleAuth(AuthProvider):
    """Google认证实现"""
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

    async def login(self, code: str) -> dict:
        """Google OAuth2登录"""
        from google.auth.transport import requests
        from google.oauth2 import id_token

        try:
            # 验证ID token
            idinfo = id_token.verify_oauth2_token(
                code,
                requests.Request(),
                self.client_id
            )

            return {
                'provider': 'google',
                'google_id': idinfo['sub'],
                'email': idinfo['email'],
                'user_info': {
                    'name': idinfo.get('name'),
                    'picture': idinfo.get('picture'),
                    'email_verified': idinfo.get('email_verified')
                }
            }
        except ValueError:
            raise HTTPException(status_code=401,
                              detail="Invalid Google token")

class AuthFactory:
    """认证工厂类"""
    @staticmethod
    def create_provider(region: str) -> AuthProvider:
        if region == 'CN':
            return WeChatAuth()
        else:
            return GoogleAuth()
```

### 3. 双支付系统

```python
# services/payment/payment_factory.py
from decimal import Decimal
import stripe
import hashlib
import time

class PaymentProvider(ABC):
    @abstractmethod
    async def create_payment(self, order_id: str, amount: Decimal,
                           description: str) -> dict:
        pass

    @abstractmethod
    async def verify_payment(self, payment_data: dict) -> bool:
        pass

class WeChatPay(PaymentProvider):
    """微信支付实现"""
    def __init__(self):
        self.app_id = os.getenv('WECHAT_APP_ID')
        self.mch_id = os.getenv('WECHAT_MCH_ID')
        self.api_key = os.getenv('WECHAT_PAY_KEY')
        self.notify_url = os.getenv('WECHAT_PAY_NOTIFY_URL')

    async def create_payment(self, order_id: str, amount: Decimal,
                           description: str) -> dict:
        """创建微信支付订单"""
        # 构建请求参数
        params = {
            'appid': self.app_id,
            'mch_id': self.mch_id,
            'nonce_str': self._generate_nonce_str(),
            'body': description,
            'out_trade_no': order_id,
            'total_fee': int(amount * 100),  # 转换为分
            'spbill_create_ip': '127.0.0.1',
            'notify_url': self.notify_url,
            'trade_type': 'JSAPI',
            'openid': ''  # 需要从用户session获取
        }

        # 生成签名
        params['sign'] = self._generate_sign(params)

        # 发起支付请求
        url = "https://api.mch.weixin.qq.com/pay/unifiedorder"
        # ... XML请求处理

        return {
            'provider': 'wechat_pay',
            'order_id': order_id,
            'prepay_id': '',  # 从响应获取
            'payment_params': {}  # 小程序/H5支付参数
        }

    def _generate_sign(self, params: dict) -> str:
        """生成微信支付签名"""
        # 按key排序
        sorted_params = sorted(params.items())
        # 拼接字符串
        string = '&'.join([f"{k}={v}" for k, v in sorted_params
                          if v and k != 'sign'])
        string += f"&key={self.api_key}"
        # MD5加密
        return hashlib.md5(string.encode()).hexdigest().upper()

class StripePay(PaymentProvider):
    """Stripe支付实现"""
    def __init__(self):
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    async def create_payment(self, order_id: str, amount: Decimal,
                           description: str) -> dict:
        """创建Stripe支付会话"""
        try:
            # 创建Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': description,
                        },
                        'unit_amount': int(amount * 100),  # 转换为分
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"{os.getenv('FRONTEND_URL')}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{os.getenv('FRONTEND_URL')}/payment/cancel",
                metadata={
                    'order_id': order_id
                }
            )

            return {
                'provider': 'stripe',
                'order_id': order_id,
                'session_id': session.id,
                'checkout_url': session.url
            }
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400,
                              detail=str(e))

    async def verify_payment(self, event_data: dict) -> dict:
        """验证Stripe webhook"""
        try:
            event = stripe.Webhook.construct_event(
                event_data['payload'],
                event_data['sig_header'],
                self.webhook_secret
            )

            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                return {
                    'success': True,
                    'order_id': session['metadata']['order_id'],
                    'payment_intent': session['payment_intent']
                }

            return {'success': False}
        except ValueError as e:
            raise HTTPException(status_code=400,
                              detail="Invalid payload")

class PaymentFactory:
    """支付工厂类"""
    @staticmethod
    def create_provider(region: str) -> PaymentProvider:
        if region == 'CN':
            return WeChatPay()
        else:
            return StripePay()
```

### 4. 统一API接口

```python
# main.py - 核心API路由
from fastapi import FastAPI, Request, Depends
from services.region_detector import RegionDetector
from services.auth.auth_factory import AuthFactory
from services.payment.payment_factory import PaymentFactory

app = FastAPI(title="Dual-Region API Service")

# 依赖注入：获取用户地域
async def get_user_region(request: Request) -> str:
    detector = RegionDetector()
    return await detector.detect_region(request)

# 统一登录接口
@app.post("/api/auth/login")
async def unified_login(
    request: Request,
    code: str,
    region: str = Depends(get_user_region)
):
    """
    统一登录接口
    - 国内用户：微信登录
    - 海外用户：Google登录
    """
    auth_provider = AuthFactory.create_provider(region)

    try:
        # 执行登录
        auth_result = await auth_provider.login(code)

        # 查找或创建用户
        user = await create_or_update_user(auth_result, region)

        # 生成JWT Token
        token = create_jwt_token(user)

        return {
            "success": True,
            "token": token,
            "user": {
                "id": user.id,
                "nickname": user.nickname,
                "avatar": user.avatar,
                "region": region,
                "auth_provider": auth_result['provider']
            }
        }
    except Exception as e:
        raise HTTPException(status_code=401,
                          detail=f"Login failed: {str(e)}")

# 统一支付接口
@app.post("/api/payment/create")
async def create_payment(
    amount: Decimal,
    description: str,
    region: str = Depends(get_user_region),
    current_user: dict = Depends(get_current_user)
):
    """
    创建支付订单
    - 国内：微信支付
    - 海外：Stripe支付
    """
    payment_provider = PaymentFactory.create_provider(region)

    # 创建订单
    order = await create_order(
        user_id=current_user['id'],
        amount=amount,
        description=description,
        region=region
    )

    # 创建支付
    payment_result = await payment_provider.create_payment(
        order_id=order.id,
        amount=amount,
        description=description
    )

    # 更新订单状态
    await update_order_status(order.id, 'pending_payment')

    return {
        "success": True,
        "order_id": order.id,
        "payment": payment_result
    }

# 支付回调 - 微信支付
@app.post("/api/payment/wechat/notify")
async def wechat_payment_notify(request: Request):
    """微信支付异步通知"""
    # 解析XML数据
    xml_data = await request.body()
    payment_data = parse_wechat_xml(xml_data)

    # 验证签名
    provider = WeChatPay()
    if await provider.verify_payment(payment_data):
        # 更新订单状态
        await process_payment_success(
            payment_data['out_trade_no'],
            payment_data['transaction_id']
        )
        return Response(content="<xml><return_code><![CDATA[SUCCESS]]></return_code></xml>",
                       media_type="application/xml")

    return Response(content="<xml><return_code><![CDATA[FAIL]]></return_code></xml>",
                   media_type="application/xml")

# 支付回调 - Stripe
@app.post("/api/payment/stripe/webhook")
async def stripe_webhook(request: Request):
    """Stripe支付Webhook"""
    payload = await request.body()
    sig_header = request.headers.get('Stripe-Signature')

    provider = StripePay()
    result = await provider.verify_payment({
        'payload': payload,
        'sig_header': sig_header
    })

    if result['success']:
        await process_payment_success(
            result['order_id'],
            result['payment_intent']
        )

    return {"received": True}
```

## 三、数据库设计

```sql
-- 用户表（支持多种登录方式）
CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    -- 通用字段
    nickname VARCHAR(100),
    avatar VARCHAR(500),
    email VARCHAR(200),
    phone VARCHAR(20),
    region ENUM('CN', 'GLOBAL') NOT NULL,

    -- 微信相关
    wechat_openid VARCHAR(200) UNIQUE,
    wechat_unionid VARCHAR(200),

    -- Google相关
    google_id VARCHAR(200) UNIQUE,
    google_email VARCHAR(200),

    -- 账户信息
    credits DECIMAL(10,2) DEFAULT 0,
    vip_level INT DEFAULT 0,
    vip_expire_at DATETIME,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_region (region),
    INDEX idx_wechat (wechat_openid),
    INDEX idx_google (google_id)
);

-- 支付订单表
CREATE TABLE payment_orders (
    id VARCHAR(64) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(10) NOT NULL,

    -- 支付方式
    payment_method ENUM('wechat_pay', 'stripe') NOT NULL,
    region ENUM('CN', 'GLOBAL') NOT NULL,

    -- 状态
    status ENUM('created', 'pending', 'success', 'failed', 'refunded'),

    -- 第三方信息
    external_order_id VARCHAR(200),  -- 微信/Stripe订单号
    transaction_id VARCHAR(200),     -- 交易流水号

    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    paid_at DATETIME,

    -- 元数据
    description TEXT,
    metadata JSON,

    INDEX idx_user (user_id),
    INDEX idx_status (status),
    INDEX idx_external (external_order_id)
);

-- 任务表（通用）
CREATE TABLE tasks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    dashscope_task_id VARCHAR(200),

    -- 输入输出
    input_image_url VARCHAR(500),
    input_video_url VARCHAR(500),
    output_video_url VARCHAR(500),

    -- 状态
    status VARCHAR(50),
    error_message TEXT,

    -- 成本计算
    credits_used DECIMAL(10,2),

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,

    INDEX idx_user_task (user_id, task_type),
    INDEX idx_status (status)
);
```

## 四、前端适配方案

### 1. 自动检测和切换

```typescript
// utils/region-detector.ts
export interface RegionConfig {
  region: 'CN' | 'GLOBAL';
  authProvider: 'wechat' | 'google';
  paymentProvider: 'wechat_pay' | 'stripe';
  currency: 'CNY' | 'USD';
  language: 'zh-CN' | 'en-US';
}

export class RegionDetector {
  static async detectRegion(): Promise<RegionConfig> {
    // 1. 检查本地存储的用户偏好
    const savedRegion = localStorage.getItem('user_region');
    if (savedRegion) {
      return JSON.parse(savedRegion);
    }

    // 2. 通过浏览器语言判断
    const browserLang = navigator.language.toLowerCase();
    const isChineseUser = browserLang.includes('zh');

    // 3. 通过时区判断
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const isAsiaTimezone = timezone.includes('Asia');

    // 4. 通过IP检测（调用后端API）
    try {
      const response = await fetch('/api/detect-region');
      const data = await response.json();

      return {
        region: data.region,
        authProvider: data.region === 'CN' ? 'wechat' : 'google',
        paymentProvider: data.region === 'CN' ? 'wechat_pay' : 'stripe',
        currency: data.region === 'CN' ? 'CNY' : 'USD',
        language: data.region === 'CN' ? 'zh-CN' : 'en-US'
      };
    } catch {
      // 默认配置
      return {
        region: isChineseUser ? 'CN' : 'GLOBAL',
        authProvider: isChineseUser ? 'wechat' : 'google',
        paymentProvider: isChineseUser ? 'wechat_pay' : 'stripe',
        currency: isChineseUser ? 'CNY' : 'USD',
        language: isChineseUser ? 'zh-CN' : 'en-US'
      };
    }
  }
}
```

### 2. 动态登录组件

```tsx
// components/LoginButton.tsx
import { useEffect, useState } from 'react';
import { RegionDetector, RegionConfig } from '@/utils/region-detector';

export function LoginButton() {
  const [config, setConfig] = useState<RegionConfig | null>(null);

  useEffect(() => {
    RegionDetector.detectRegion().then(setConfig);
  }, []);

  const handleLogin = async () => {
    if (!config) return;

    if (config.authProvider === 'wechat') {
      // 微信登录流程
      const appId = process.env.NEXT_PUBLIC_WECHAT_APPID;
      const redirectUri = encodeURIComponent(window.location.origin + '/auth/callback');
      const state = Math.random().toString(36).substring(7);

      // 跳转到微信授权页
      window.location.href = `https://open.weixin.qq.com/connect/oauth2/authorize?appid=${appId}&redirect_uri=${redirectUri}&response_type=code&scope=snsapi_userinfo&state=${state}#wechat_redirect`;
    } else {
      // Google登录流程
      const { google } = window as any;
      google.accounts.id.initialize({
        client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
        callback: handleGoogleCallback
      });
      google.accounts.id.prompt();
    }
  };

  const handleGoogleCallback = async (response: any) => {
    // 发送token到后端验证
    const result = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code: response.credential,
        provider: 'google'
      })
    });

    const data = await result.json();
    if (data.success) {
      localStorage.setItem('token', data.token);
      window.location.href = '/dashboard';
    }
  };

  if (!config) return <div>Loading...</div>;

  return (
    <button onClick={handleLogin} className="login-btn">
      {config.authProvider === 'wechat' ? (
        <>
          <WeChatIcon />
          微信登录
        </>
      ) : (
        <>
          <GoogleIcon />
          Sign in with Google
        </>
      )}
    </button>
  );
}
```

### 3. 动态支付组件

```tsx
// components/PaymentButton.tsx
import { loadStripe } from '@stripe/stripe-js';

export function PaymentButton({ amount, description }: Props) {
  const [config, setConfig] = useState<RegionConfig | null>(null);

  const handlePayment = async () => {
    if (!config) return;

    // 创建订单
    const orderResponse = await fetch('/api/payment/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ amount, description })
    });

    const orderData = await orderResponse.json();

    if (config.paymentProvider === 'wechat_pay') {
      // 微信支付
      if (isWeChatBrowser()) {
        // 微信内置浏览器，使用JSAPI支付
        WeixinJSBridge.invoke('getBrandWCPayRequest',
          orderData.payment.payment_params,
          (res: any) => {
            if (res.err_msg === "get_brand_wcpay_request:ok") {
              // 支付成功
              window.location.href = '/payment/success';
            }
          }
        );
      } else {
        // H5支付
        window.location.href = orderData.payment.h5_url;
      }
    } else {
      // Stripe支付
      const stripe = await loadStripe(
        process.env.NEXT_PUBLIC_STRIPE_PUBLIC_KEY!
      );

      // 跳转到Stripe Checkout
      await stripe?.redirectToCheckout({
        sessionId: orderData.payment.session_id
      });
    }
  };

  return (
    <button onClick={handlePayment} className="payment-btn">
      {config?.paymentProvider === 'wechat_pay' ? (
        <>微信支付 ¥{amount}</>
      ) : (
        <>Pay ${amount} with Card</>
      )}
    </button>
  );
}
```

## 五、部署架构

### 1. 多区域部署策略

```yaml
# docker-compose.yml
version: '3.8'

services:
  # API服务 - 主节点（中国）
  api-cn:
    image: your-api:latest
    environment:
      - REGION=CN
      - DATABASE_URL=${CN_DATABASE_URL}
      - REDIS_URL=${CN_REDIS_URL}
      - WECHAT_APP_ID=${WECHAT_APP_ID}
      - WECHAT_APP_SECRET=${WECHAT_APP_SECRET}
    ports:
      - "8001:8000"
    deploy:
      replicas: 2

  # API服务 - 全球节点（新加坡）
  api-global:
    image: your-api:latest
    environment:
      - REGION=GLOBAL
      - DATABASE_URL=${GLOBAL_DATABASE_URL}
      - REDIS_URL=${GLOBAL_REDIS_URL}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
    ports:
      - "8002:8000"
    deploy:
      replicas: 2

  # Nginx负载均衡
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
      - "443:443"
```

### 2. Nginx配置

```nginx
# nginx.conf
http {
    # GeoIP2模块，根据IP判断地域
    geoip2 /usr/share/GeoIP/GeoLite2-Country.mmdb {
        $geoip2_country_code country iso_code;
    }

    # 地域映射
    map $geoip2_country_code $backend_pool {
        default global_backend;
        CN china_backend;
        HK china_backend;
        MO china_backend;
    }

    # 中国区后端
    upstream china_backend {
        server api-cn:8000;
    }

    # 全球后端
    upstream global_backend {
        server api-global:8000;
    }

    server {
        listen 80;
        server_name api.yourdomain.com;

        # 根据地域路由
        location /api/ {
            proxy_pass http://$backend_pool;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-User-Region $geoip2_country_code;
        }

        # 微信支付回调（固定路由到中国节点）
        location /api/payment/wechat/ {
            proxy_pass http://china_backend;
        }

        # Stripe webhook（固定路由到全球节点）
        location /api/payment/stripe/ {
            proxy_pass http://global_backend;
        }
    }
}
```

## 六、监控与分析

### 1. 用户分布监控

```python
# monitoring/analytics.py
from dataclasses import dataclass
from typing import Dict
import asyncio

@dataclass
class UserMetrics:
    region: str
    auth_provider: str
    payment_provider: str
    total_users: int
    active_users: int
    revenue: Decimal

class AnalyticsService:
    async def get_user_distribution(self) -> Dict[str, UserMetrics]:
        """获取用户分布数据"""
        query = """
        SELECT
            region,
            COUNT(*) as total_users,
            COUNT(CASE WHEN last_active > NOW() - INTERVAL 7 DAY
                  THEN 1 END) as active_users,
            SUM(total_spent) as revenue
        FROM users
        GROUP BY region
        """

        results = await database.fetch_all(query)

        return {
            row['region']: UserMetrics(
                region=row['region'],
                auth_provider='wechat' if row['region'] == 'CN' else 'google',
                payment_provider='wechat_pay' if row['region'] == 'CN' else 'stripe',
                total_users=row['total_users'],
                active_users=row['active_users'],
                revenue=row['revenue'] or Decimal('0')
            )
            for row in results
        }

    async def track_conversion_rate(self):
        """追踪转化率"""
        return {
            'CN': {
                'registration_rate': 0.65,  # 微信登录转化率
                'payment_rate': 0.12,       # 支付转化率
                'arpu': 58.0                # 平均用户收入（元）
            },
            'GLOBAL': {
                'registration_rate': 0.45,  # Google登录转化率
                'payment_rate': 0.08,       # 支付转化率
                'arpu': 12.5                # 平均用户收入（美元）
            }
        }
```

### 2. 性能监控

```python
# monitoring/performance.py
import time
from functools import wraps

def monitor_api_performance(region: str):
    """API性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # 记录成功请求
                await log_metric({
                    'type': 'api_request',
                    'region': region,
                    'endpoint': func.__name__,
                    'duration': duration,
                    'status': 'success'
                })

                return result
            except Exception as e:
                duration = time.time() - start_time

                # 记录失败请求
                await log_metric({
                    'type': 'api_request',
                    'region': region,
                    'endpoint': func.__name__,
                    'duration': duration,
                    'status': 'error',
                    'error': str(e)
                })

                raise

        return wrapper
    return decorator
```

## 七、成本优化策略

### 1. 智能缓存

```python
# services/cache_strategy.py
class RegionAwareCacheStrategy:
    """地域感知的缓存策略"""

    def __init__(self):
        self.cn_cache = Redis(host='cn-redis')
        self.global_cache = Redis(host='global-redis')

    async def get_cache(self, key: str, region: str):
        cache = self.cn_cache if region == 'CN' else self.global_cache
        return await cache.get(key)

    async def set_cache(self, key: str, value: any,
                       region: str, ttl: int = 3600):
        cache = self.cn_cache if region == 'CN' else self.global_cache

        # 热点数据跨区域同步
        if await self.is_hot_data(key):
            await self.cn_cache.set(key, value, ttl)
            await self.global_cache.set(key, value, ttl)
        else:
            await cache.set(key, value, ttl)
```

### 2. 成本分析

```
月度成本估算：

中国区域:
- 阿里云ECS: ¥800
- RDS数据库: ¥400
- Redis缓存: ¥200
- OSS存储: ¥300
- CDN流量: ¥500
- 微信支付手续费: 0.6%
小计: ¥2200 + 交易手续费

全球区域:
- AWS EC2: $150
- RDS数据库: $100
- Redis缓存: $50
- S3存储: $50
- CloudFront: $100
- Stripe手续费: 2.9% + $0.30
小计: $450 + 交易手续费

总计: 约¥5500/月（不含交易手续费）
```

## 八、合规性要求

### 1. 中国地区
- ICP备案（必须）
- 数据安全法合规
- 个人信息保护法合规
- 支付业务许可

### 2. 全球地区
- GDPR合规（欧洲用户）
- CCPA合规（加州用户）
- PCI DSS合规（支付卡行业）
- 数据本地化要求

## 九、灾备方案

### 1. 数据备份
```bash
# 自动备份脚本
#!/bin/bash

# 中国区数据备份
mysqldump -h cn-rds.aliyuncs.com -u root -p$CN_DB_PASS \
  --databases main_db > backup_cn_$(date +%Y%m%d).sql

# 全球区数据备份
mysqldump -h global-rds.amazonaws.com -u root -p$GLOBAL_DB_PASS \
  --databases main_db > backup_global_$(date +%Y%m%d).sql

# 上传到对象存储
ossutil cp backup_cn_*.sql oss://backup-bucket/cn/
aws s3 cp backup_global_*.sql s3://backup-bucket/global/
```

### 2. 故障切换
- 主备自动切换
- 跨区域容灾
- 降级服务策略

这个双系统架构可以很好地服务全球用户，同时满足不同地区的支付和登录习惯！