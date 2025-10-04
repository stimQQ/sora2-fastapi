# 🚀 北京代理服务器部署指南（Cloudflare + Nginx）

## 📋 前置要求
- ✅ 一台中国北京的服务器（阿里云/腾讯云）
- ✅ 域名已托管在 Cloudflare
- ✅ Python 3.8+

---

## 🔧 部署步骤

### 1️⃣ **Cloudflare 配置**

#### A. 添加 DNS 记录
```
登录 Cloudflare → 选择你的域名 → DNS → Records

类型: A
名称: video-proxy（子域名，可自定义）
IPv4地址: 你的北京服务器公网IP
代理状态: ✅ 已代理（橙色云朵图标）
TTL: Auto
```

#### B. SSL/TLS 设置
```
SSL/TLS → 概述
加密模式: Full (strict) 或 Full

如果选择 Full (strict)，需要配置 Origin Certificate（推荐）
如果选择 Full，使用自签名证书也可以
```

#### C. 生成 Origin Certificate（推荐）
```
SSL/TLS → Origin Server → Create Certificate

1. 选择私钥类型: RSA (2048)
2. 主机名:
   - video-proxy.yourdomain.com
   - *.yourdomain.com (可选)
3. 有效期: 15 years
4. 点击 Create

5. 下载证书:
   - Origin Certificate (cert.pem)
   - Private Key (key.pem)
```

---

### 2️⃣ **服务器初始化**

```bash
# SSH 登录北京服务器
ssh root@你的服务器IP

# 更新系统
apt update && apt upgrade -y

# 安装必要软件
apt install -y python3-pip nginx git

# 创建工作目录
mkdir -p /opt/video-proxy
cd /opt/video-proxy
```

---

### 3️⃣ **部署代理服务**

```bash
# 上传代码到服务器（从本地上传）
# 或者使用 git clone（如果代码在仓库中）

# 安装 Python 依赖
pip3 install -r requirements.txt

# 配置环境变量
nano .env

# 填入以下内容：
QWEN_VIDEO_API_KEY=sk-your-dashscope-key
PROXY_API_KEY=your-strong-random-key

# 保存并退出（Ctrl+X, Y, Enter）
```

---

### 4️⃣ **配置 SSL 证书**

```bash
# 创建证书目录
mkdir -p /etc/ssl/cloudflare

# 上传 Cloudflare Origin Certificate
# 方法1: 使用 nano 直接粘贴
nano /etc/ssl/cloudflare/cert.pem
# 粘贴 Origin Certificate 内容，保存

nano /etc/ssl/cloudflare/key.pem
# 粘贴 Private Key 内容，保存

# 方法2: 使用 scp 从本地上传
# scp cert.pem root@服务器IP:/etc/ssl/cloudflare/
# scp key.pem root@服务器IP:/etc/ssl/cloudflare/

# 设置权限
chmod 600 /etc/ssl/cloudflare/key.pem
chmod 644 /etc/ssl/cloudflare/cert.pem
```

---

### 5️⃣ **配置 Nginx**

```bash
# 复制 nginx 配置
cp nginx.conf /etc/nginx/sites-available/video-proxy

# 修改配置中的域名
nano /etc/nginx/sites-available/video-proxy
# 将 video-proxy.yourdomain.com 改为你的实际域名

# 启用站点
ln -s /etc/nginx/sites-available/video-proxy /etc/nginx/sites-enabled/

# 测试配置
nginx -t

# 如果显示 "syntax is ok" 和 "test is successful"，则重启 nginx
systemctl restart nginx
systemctl enable nginx
```

---

### 6️⃣ **启动 FastAPI 服务**

#### 方法 A: 使用 systemd（推荐，开机自启）

```bash
# 创建 systemd 服务文件
nano /etc/systemd/system/video-proxy.service
```

**内容：**
```ini
[Unit]
Description=Video Proxy API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/video-proxy
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 重载 systemd
systemctl daemon-reload

# 启动服务
systemctl start video-proxy

# 设置开机自启
systemctl enable video-proxy

# 查看状态
systemctl status video-proxy
```

#### 方法 B: 使用 Screen（临时测试）

```bash
# 安装 screen
apt install screen -y

# 创建新会话
screen -S video-proxy

# 启动服务
cd /opt/video-proxy
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000

# 按 Ctrl+A, D 退出 screen（服务继续运行）
# 重新连接: screen -r video-proxy
```

---

### 7️⃣ **验证部署**

```bash
# 本地测试（服务器内）
curl http://127.0.0.1:8000/health

# 应该返回: {"status":"healthy"}

# 外部测试（从你的电脑）
curl https://video-proxy.yourdomain.com/health

# 测试 API Key 认证
curl -H "X-API-Key: your-proxy-key" \
  https://video-proxy.yourdomain.com/
```

---

## 🔒 安全加固（可选但推荐）

### 1. 配置防火墙

```bash
# 安装 ufw
apt install ufw -y

# 允许 SSH
ufw allow 22/tcp

# 允许 HTTP/HTTPS（Cloudflare 访问）
ufw allow 80/tcp
ufw allow 443/tcp

# 启用防火墙
ufw enable

# 查看状态
ufw status
```

### 2. 限制只允许 Cloudflare IP 访问

```bash
# 编辑 nginx 配置
nano /etc/nginx/sites-available/video-proxy

# 在 server 块内添加（443 端口那个）:
# Cloudflare IP 白名单
allow 173.245.48.0/20;
allow 103.21.244.0/22;
allow 103.22.200.0/22;
allow 103.31.4.0/22;
allow 141.101.64.0/18;
allow 108.162.192.0/18;
allow 190.93.240.0/20;
allow 188.114.96.0/20;
allow 197.234.240.0/22;
allow 198.41.128.0/17;
allow 162.158.0.0/15;
allow 104.16.0.0/13;
allow 104.24.0.0/14;
allow 172.64.0.0/13;
allow 131.0.72.0/22;
deny all;

# 重启 nginx
systemctl restart nginx
```

### 3. Cloudflare 防火墙规则

```
Cloudflare 后台 → 安全性 → WAF

添加规则:
- 限制请求频率（Rate Limiting）
- 地理位置过滤（如只允许特定国家）
- Bot 检测
```

---

## 📊 监控和日志

### 查看日志

```bash
# FastAPI 服务日志
journalctl -u video-proxy -f

# Nginx 访问日志
tail -f /var/log/nginx/video-proxy-access.log

# Nginx 错误日志
tail -f /var/log/nginx/video-proxy-error.log
```

### 重启服务

```bash
# 重启 FastAPI
systemctl restart video-proxy

# 重启 Nginx
systemctl restart nginx

# 查看服务状态
systemctl status video-proxy
systemctl status nginx
```

---

## 🌐 主服务器调用示例

```python
import httpx

# 配置
PROXY_URL = "https://video-proxy.yourdomain.com"
PROXY_API_KEY = "your-strong-random-key"

# 调用代理
async def create_video_task():
    headers = {
        "X-API-Key": PROXY_API_KEY
    }

    response = await httpx.post(
        f"{PROXY_URL}/wan-2.2-animate-move/task",
        headers=headers,
        json={
            "image_url": "https://example.com/image.jpg",
            "video_url": "https://example.com/video.mp4",
            "check_image": True,
            "mode": "wan-std"
        },
        timeout=30.0
    )

    return response.json()

# 查询结果
async def query_task(task_id: str):
    headers = {
        "X-API-Key": PROXY_API_KEY
    }

    response = await httpx.get(
        f"{PROXY_URL}/wan-2.2-animate-move/query/{task_id}",
        headers=headers,
        timeout=30.0
    )

    return response.json()
```

---

## ✅ 完成！

现在你的架构是：

```
用户请求
  ↓
主服务器（全球任意位置）
  ↓ HTTPS + API Key
Cloudflare CDN（免费 SSL）
  ↓ HTTPS
北京代理服务器（Nginx + FastAPI）
  ↓
阿里云 DashScope API
```

**优势：**
- ✅ 全程 HTTPS 加密
- ✅ Cloudflare 免费 SSL + CDN
- ✅ API Key 双重认证
- ✅ DDoS 防护
- ✅ 全球加速

---

## 🆘 常见问题

### Q: 502 Bad Gateway
```bash
# 检查 FastAPI 是否运行
systemctl status video-proxy

# 检查端口是否监听
netstat -tlnp | grep 8000

# 查看错误日志
journalctl -u video-proxy -n 50
```

### Q: SSL 证书错误
```bash
# 确认证书文件存在
ls -l /etc/ssl/cloudflare/

# 确认 Cloudflare SSL 模式为 Full
# 确认 nginx 配置正确
nginx -t
```

### Q: API Key 验证失败
```bash
# 确认 .env 文件配置正确
cat /opt/video-proxy/.env

# 确认环境变量加载
systemctl restart video-proxy
```