# 🚀 Quick Reference Card

## ⚡ Start Services (Copy & Paste)

```bash
# Start all services
redis-server &
celery -A celery_app.worker worker --loglevel=info &
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 🔧 Setup Commands

```bash
# First time setup
cp .env.template .env
./setup_database_oss.sh

# Run migrations
alembic upgrade head

# Test connection
curl http://localhost:8000/health
```

## 🗄️ Database Commands

```bash
# Connect to database
psql -d video_animation_db

# List tables
\dt

# View migration status
alembic current

# Reset migrations (⚠️ deletes all data!)
alembic downgrade base && alembic upgrade head
```

## 📦 OSS Upload (Python)

```python
from app.utils.oss_helper import upload_image, upload_video

# Upload image
url = await upload_image(file_data, "photo.jpg")

# Upload video  
url = await upload_video(file_data, "video.mp4")

# Upload from path
from app.utils.oss_helper import OSSHelper
helper = OSSHelper()
url = await helper.upload_file_from_path("local/file.jpg")
```

## 💳 Stripe Payment (cURL)

```bash
# Get packages
curl http://localhost:8000/api/payments/packages

# Create payment
curl -X POST "http://localhost:8000/api/payments/stripe/create" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "X-API-Key: $PROXY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"package": "standard"}'

# Check status
curl "http://localhost:8000/api/payments/$PAYMENT_ID" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

## 🎬 Video Generation (cURL)

```bash
# Sora text-to-video
curl -X POST "http://localhost:8000/api/videos/sora/text-to-video" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "X-API-Key: $PROXY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A cat playing piano",
    "quality": "standard",
    "aspect_ratio": "landscape"
  }'

# Wan2.2 image-to-video
curl -X POST "http://localhost:8000/api/videos/animate-move" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "X-API-Key: $PROXY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://oss-url/image.jpg",
    "video_url": "https://oss-url/video.mp4",
    "mode": "wan-std"
  }'

# Check task status
curl "http://localhost:8000/api/tasks/$TASK_ID" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

## 🔐 Authentication (cURL)

```bash
# SMS login
curl -X POST "http://localhost:8000/api/auth/sms/login" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "86-13800138000",
    "code": "123456"
  }'

# Get user info
curl "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Check credits
curl "http://localhost:8000/api/users/credits" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

## 🧪 Testing

```bash
# Test Stripe
./test_stripe_payment.sh

# Test database
alembic current

# Test OSS
python3 << 'PYEOF'
import asyncio
from app.utils.oss_helper import OSSHelper
async def test():
    helper = OSSHelper()
    print("✅ OSS ready")
asyncio.run(test())
PYEOF

# Test API
curl http://localhost:8000/health
```

## 🐛 Troubleshooting

```bash
# Check logs
tail -f logs/app.log

# Check database connection
psql -d video_animation_db -c "SELECT 1"

# Check Redis
redis-cli ping

# Check environment
cat .env | grep -E "DATABASE_URL|OSS|STRIPE"

# Restart services
pkill -f uvicorn
pkill -f celery
pkill -f redis-server
# Then start again
```

## 📚 Documentation

| File | Purpose |
|------|---------|
| `README_SETUP.md` | Complete setup guide |
| `DATABASE_OSS_SETUP.md` | Database & OSS detailed guide |
| `STRIPE_INTEGRATION.md` | Stripe payment guide |
| `STRIPE_QUICKSTART.md` | 5-min Stripe setup |
| `stripe_api_examples.md` | API examples |
| `CLAUDE.md` | Project architecture |

## 🔑 Environment Variables (Required)

```bash
DATABASE_URL_MASTER="postgresql+asyncpg://..."
QWEN_VIDEO_API_KEY="..."
SORA_API_KEY="..."
ALIYUN_OSS_ACCESS_KEY="..."
ALIYUN_OSS_SECRET_KEY="..."
ALIYUN_OSS_BUCKET="..."
SECRET_KEY="..."
PROXY_API_KEY="..."
STRIPE_SECRET_KEY="sk_test_..."
```

See `.env.template` for full list.

## 📊 Default Values

| Setting | Value |
|---------|-------|
| New user credits | 100 |
| Credit expiry | 6 months |
| Wan2.2 standard | 10 credits/second |
| Wan2.2 pro | 14 credits/second |
| Sora standard | 20-25 credits/video |
| Sora HD | 30-35 credits/video |

## 🎯 Quick Links

- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Stripe Dashboard: https://dashboard.stripe.com
- OSS Console: https://oss.console.aliyun.com
- DashScope: https://dashscope.aliyun.com

---

**Print this for quick reference!** 📌
