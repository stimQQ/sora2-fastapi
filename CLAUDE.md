# CLAUDE.md - Video Animation Platform Development Reference

## Project Overview
**Name**: Video Animation Generation Platform (Wan2.2-Animate)
**Type**: FastAPI Backend for AI-powered video animation service
**Location**: `/Users/crusialee/Desktop/SparkInc/011-video-anime-qwen/fastapi-backend（Wan2.2-Animate）`
**Last Updated**: 2025-09-29

## Core Features
1. **Image-to-Motion (wan2.2-animate-move)**: Transfer video motion to static images
2. **Video Face Swap (wan2.2-animate-mix)**: Replace characters in videos
3. **Dual Authentication**: WeChat (China) + Google OAuth (Global)
4. **Dual Payment**: WeChat Pay (China) + Stripe (Global)
5. **Multi-region Storage**: Aliyun OSS (China) + AWS S3 (Global)

## Architecture Decisions (Confirmed)

### Frontend Deployment
- **Strategy**: One codebase, multiple deployment targets
- **China**: Aliyun OSS + CDN
- **Global**: Vercel with automatic deployment
- **Routing**: DNS-based intelligent routing

### Backend Infrastructure
- **Main Region**: Aliyun (Beijing, China)
- **Acceleration Nodes**: Hong Kong/Singapore for overseas users
- **Database**: MySQL 8.0 with master-slave replication (read-write separation)
  - Master: 4C8G for write operations
  - Slaves: 2C4G x2 for read operations
- **Cache**: Redis cluster for sessions, caching, and queues
- **Load Balancing**: Aliyun SLB

### Modular Design Principles
1. **Authentication System**:
   - Abstract authentication interface
   - Plugin-based providers (WeChat, Google, extensible)
   - JWT-based session management

2. **Payment System**:
   - Unified payment gateway interface
   - Dynamic provider loading (WeChat Pay, Stripe, extensible)
   - Transaction abstraction layer

3. **Storage System**:
   - Abstract storage interface
   - Provider-based implementation (OSS, S3)
   - Automatic region-based selection

## Technology Stack

### Backend
- **Framework**: FastAPI 0.115.0 + Uvicorn
- **Database**: SQLAlchemy 2.0 + Alembic (migrations)
- **Async Tasks**: Celery + Redis
- **Authentication**: python-jose[cryptography] (JWT)
- **Validation**: Pydantic 2.9.2
- **HTTP Client**: httpx 0.27.0
- **File Storage**: boto3 (S3), oss2 (Aliyun OSS)
- **Payment**: wechatpayv3, stripe
- **Monitoring**: Prometheus + Grafana
- **Logging**: structlog

### Security
- **API Keys**: Environment variables (.env)
- **CORS**: Configured for specific origins
- **Rate Limiting**: slowapi
- **Input Validation**: Pydantic models
- **SQL Injection**: SQLAlchemy ORM
- **XSS/CSRF**: FastAPI security utilities

## Project Structure
```
fastapi-backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth/          # Authentication endpoints
│   │   │   ├── tasks/         # Task management
│   │   │   ├── payments/      # Payment processing
│   │   │   └── videos/        # Video processing
│   │   └── v2/                # Future API version
│   ├── core/
│   │   ├── config.py          # Configuration management
│   │   ├── security.py        # Security utilities
│   │   └── dependencies.py    # Dependency injection
│   ├── models/                # SQLAlchemy models
│   ├── schemas/               # Pydantic schemas
│   ├── services/
│   │   ├── auth/              # Auth providers
│   │   ├── payment/           # Payment providers
│   │   ├── storage/           # Storage providers
│   │   └── dashscope/         # DashScope API integration
│   ├── middleware/
│   │   ├── region.py          # Region detection
│   │   ├── rate_limit.py     # Rate limiting
│   │   └── logging.py         # Request logging
│   ├── db/
│   │   ├── base.py           # Database configuration
│   │   ├── session.py        # Session management
│   │   └── migrations/       # Alembic migrations
│   └── utils/
│       ├── region.py         # GeoIP utilities
│       └── validators.py     # Custom validators
├── celery_app/
│   ├── tasks/                # Async tasks
│   └── worker.py            # Celery worker
├── tests/                    # Test suite
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .env                      # Environment variables
├── .env.example             # Example configuration
├── requirements.txt         # Dependencies
├── alembic.ini             # Database migrations config
└── main.py                 # Application entry point
```

## API Endpoints Structure

**Simple, clear structure without versioning:**

```
/api/
├── /auth/                     # Authentication
│   ├── POST /login            # Email/password login
│   ├── POST /wechat/login     # WeChat OAuth login
│   ├── POST /google/login     # Google OAuth login
│   ├── POST /refresh          # Refresh JWT token
│   ├── POST /logout           # Logout user
│   └── GET  /me               # Get current user
├── /videos/                   # Video processing
│   ├── POST /animate-move     # Create motion transfer task
│   ├── POST /animate-mix      # Create face swap task
│   ├── GET  /tasks/{task_id}  # Query task status
│   └── POST /upload           # Upload files
├── /tasks/                    # Task management
│   ├── GET    /{task_id}      # Get task details
│   ├── GET    /user/tasks     # List user tasks
│   ├── DELETE /{task_id}      # Cancel task
│   └── POST   /{task_id}/retry # Retry failed task
├── /payments/                 # Payment processing
│   ├── POST /wechat/create    # Create WeChat payment
│   ├── POST /stripe/create    # Create Stripe payment
│   ├── POST /webhook/wechat   # WeChat payment callback
│   ├── POST /webhook/stripe   # Stripe webhook
│   └── GET  /{payment_id}     # Get payment status
└── /users/                    # User management
    ├── GET    /profile        # Get user profile
    ├── PUT    /profile        # Update profile
    ├── GET    /credits        # Get credit balance
    └── DELETE /account        # Delete account
```

**Total: 23 endpoints** organized into 5 clear functional groups.

## Database Schema

### Core Tables
- **users**: User accounts with multi-provider auth
- **tasks**: Video processing tasks
- **payment_orders**: Payment transactions
- **credits_transactions**: Credit usage history
- **auth_providers**: OAuth provider configurations
- **files**: Uploaded file metadata

### Read-Write Separation Strategy
- **Write Operations**: Master database only
- **Read Operations**: Load balanced across slaves
- **Cache Layer**: Redis for frequent reads

## Environment Variables
```env
# API Keys
QWEN_VIDEO_API_KEY=xxx
PROXY_API_KEY=xxx

# Database
DATABASE_URL_MASTER=mysql+asyncmy://user:pass@master:3306/db
DATABASE_URL_SLAVE1=mysql+asyncmy://user:pass@slave1:3306/db
DATABASE_URL_SLAVE2=mysql+asyncmy://user:pass@slave2:3306/db

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# Storage
ALIYUN_OSS_ACCESS_KEY=xxx
ALIYUN_OSS_SECRET_KEY=xxx
ALIYUN_OSS_BUCKET=xxx
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_S3_BUCKET=xxx

# Authentication
JWT_SECRET_KEY=xxx
WECHAT_APP_ID=xxx
WECHAT_APP_SECRET=xxx
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx

# Payment
WECHAT_PAY_MERCHANT_ID=xxx
WECHAT_PAY_API_KEY=xxx
STRIPE_SECRET_KEY=xxx
STRIPE_WEBHOOK_SECRET=xxx

# Region Detection
GEOIP_DATABASE_PATH=/path/to/GeoLite2-City.mmdb
```

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start Redis
redis-server

# Start Celery worker
celery -A celery_app.worker worker --loglevel=info

# Start FastAPI development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Scale workers
docker-compose scale worker=3
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py
```

## API Testing Examples

### Create Animation Task
```bash
curl -X POST "http://localhost:8000/api/v1/tasks/animate-move" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/image.jpg",
    "video_url": "https://example.com/video.mp4",
    "mode": "wan-std"
  }'
```

### Query Task Status
```bash
curl -X GET "http://localhost:8000/api/v1/tasks/{task_id}" \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

## Monitoring & Logging

### Metrics Collection
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Metrics Exported**:
  - Request count/duration
  - Task processing time
  - Payment success rate
  - Storage usage

### Log Management
- **Structured Logging**: JSON format with structlog
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log Rotation**: Daily rotation with 30-day retention
- **Error Tracking**: Sentry integration

## Security Best Practices

1. **API Security**:
   - JWT tokens with expiration
   - API key rotation
   - Request signing for webhooks

2. **Data Protection**:
   - Encryption at rest and in transit
   - PII data masking in logs
   - GDPR/PIPL compliance

3. **Rate Limiting**:
   - Per-user limits
   - IP-based throttling
   - Endpoint-specific limits

4. **Input Validation**:
   - Pydantic model validation
   - File type/size restrictions
   - SQL injection prevention

## Deployment Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Redis cluster running
- [ ] SSL certificates installed
- [ ] CORS origins configured
- [ ] Rate limits set
- [ ] Monitoring dashboards configured
- [ ] Backup strategy implemented
- [ ] Load testing completed
- [ ] Security audit passed

## Support & Documentation

### Internal Documentation
- API Documentation: http://localhost:8000/docs (Swagger UI)
- ReDoc: http://localhost:8000/redoc
- Architecture Diagrams: `/docs/architecture/`

### External Resources
- FastAPI Docs: https://fastapi.tiangolo.com
- DashScope API: https://dashscope.aliyun.com
- WeChat Pay: https://pay.weixin.qq.com
- Stripe API: https://stripe.com/docs/api

## Contact & Maintenance

- **Project Lead**: [Your Name]
- **Repository**: [Git Repository URL]
- **Issue Tracker**: [Issue Tracking System]
- **CI/CD**: GitHub Actions / GitLab CI

---

*This document serves as the primary reference for Claude AI and developers working on this project. Keep it updated with any architectural changes or important decisions.*