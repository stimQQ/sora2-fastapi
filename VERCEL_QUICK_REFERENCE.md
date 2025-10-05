# Vercel Quick Reference

## 🚀 Deployment Commands

```bash
# First time setup
vercel link

# Deploy to preview (testing)
vercel

# Deploy to production
vercel --prod

# Use deployment script (recommended)
./deploy-vercel.sh
```

## 📊 Monitoring Commands

```bash
# View all deployments
vercel ls

# Real-time logs
vercel logs --follow

# Function-specific logs
vercel logs function api/index.py

# Deployment details
vercel inspect <deployment-url>
```

## 🔧 Environment Variables

```bash
# Add environment variable
vercel env add SECRET_KEY production

# List all env vars
vercel env ls

# Pull env vars to local .env
vercel env pull

# Remove env var
vercel env rm SECRET_KEY production
```

## 🌐 Domain Management

```bash
# Add custom domain
vercel domains add yourdomain.com

# List domains
vercel domains ls

# Remove domain
vercel domains rm yourdomain.com
```

## 🔄 Rollback & Management

```bash
# Rollback to previous deployment
vercel rollback <deployment-url>

# Promote preview to production
vercel promote <deployment-url>

# Delete deployment
vercel rm <deployment-url>
```

## 🧪 Testing

```bash
# Test locally (simulates serverless)
vercel dev

# Test with serverless mode locally
export VERCEL=1
uvicorn api.index:app --reload --port 8000

# Health check
curl https://your-app.vercel.app/health

# API docs
open https://your-app.vercel.app/docs
```

## 📝 Required Environment Variables

Set these in Vercel Dashboard (Project Settings → Environment Variables):

### Core
- `SECRET_KEY` - App secret (min 32 chars)
- `ENVIRONMENT` - production/staging
- `PROXY_API_KEY` - Proxy API key

### Database
- `DATABASE_URL_MASTER` - PostgreSQL connection string
- `DATABASE_URL_SLAVES` - Optional read replicas

### APIs
- `SORA_API_KEY` - Sora video API key
- `QWEN_VIDEO_API_KEY` - Qwen video API (optional)

### Storage (OSS)
- `ALIYUN_OSS_ACCESS_KEY`
- `ALIYUN_OSS_SECRET_KEY`
- `ALIYUN_OSS_BUCKET`
- `ALIYUN_OSS_ENDPOINT`
- `ALIYUN_OSS_REGION`

### Authentication
- `JWT_SECRET_KEY` - JWT signing key (min 32 chars)
- `GOOGLE_CLIENT_ID` - Google OAuth
- `GOOGLE_CLIENT_SECRET` - Google OAuth

### Payment
- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_WEBHOOK_SECRET`

### Other
- `CORS_ALLOWED_ORIGINS` - Comma-separated origins
- `REDIS_URL` - Redis connection (for sessions/cache)

## 🏗️ Project Structure

```
fastapi-backend/
├── api/
│   └── index.py              # ⭐ Vercel entry point
├── app/                      # Your FastAPI app
├── vercel.json              # ⭐ Vercel config
├── requirements-vercel.txt  # ⭐ Minimal deps
├── .vercelignore           # Files to exclude
└── .env                    # Local dev (gitignored)
```

## ⚙️ vercel.json Structure

```json
{
  "version": 2,
  "builds": [{
    "src": "api/index.py",
    "use": "@vercel/python",
    "config": {
      "runtime": "python3.12",
      "maxLambdaSize": "15mb"
    }
  }],
  "routes": [{
    "src": "/(.*)",
    "dest": "api/index.py"
  }],
  "regions": ["sin1"]
}
```

## 🐛 Troubleshooting

### Cold start too slow?
- Check bundle size: `vercel inspect <url>`
- Reduce dependencies in `requirements-vercel.txt`
- Remove unused imports

### Module not found?
- Use absolute imports: `from app.core.config import settings`
- Ensure `sys.path.insert(0, str(ROOT_DIR))` in `api/index.py`

### Database connection issues?
- Use `postgresql+asyncpg://` (not `postgresql://`)
- Check database allows Vercel IPs
- Verify region: Vercel `sin1` → Aliyun Singapore

### Bundle too large (>250MB)?
- Use `requirements-vercel.txt` (not `requirements.txt`)
- Check `.vercelignore` excludes: `tests/`, `docs/`, `data/*.mmdb`

## 📈 Performance Targets

| Metric | Target | Check With |
|--------|--------|------------|
| Cold Start | <3s | `vercel logs --follow` |
| Warm Request | <500ms | `/health` endpoint |
| Bundle Size | <50MB | `vercel inspect` |
| Error Rate | <1% | Vercel dashboard |

## 🔗 Useful Links

- **Vercel Dashboard**: https://vercel.com/dashboard
- **API Docs**: https://your-app.vercel.app/docs
- **Health Check**: https://your-app.vercel.app/health
- **Logs**: `vercel logs --follow`

## 📚 Documentation

- `VERCEL_DEPLOYMENT_GUIDE.md` - Step-by-step deployment
- `VERCEL_ARCHITECTURE_ANALYSIS.md` - Technical deep dive
- `deploy-vercel.sh` - Automated deployment script

## 🎯 Quick Deploy Checklist

- [ ] Install Vercel CLI: `npm i -g vercel`
- [ ] Link project: `vercel link`
- [ ] Set env vars in Vercel dashboard
- [ ] Test locally: `vercel dev`
- [ ] Deploy preview: `vercel`
- [ ] Test preview deployment
- [ ] Deploy production: `vercel --prod`
- [ ] Verify: `curl https://your-app.vercel.app/health`

## 💡 Pro Tips

1. **Always test preview first**: `vercel` → test → `vercel --prod`
2. **Use deployment script**: `./deploy-vercel.sh` (validates before deploy)
3. **Monitor logs**: `vercel logs --follow` (during first deploys)
4. **Region matters**: Deploy to `sin1` (Singapore) if DB is in Asia
5. **External workers**: Run Celery on separate server for long tasks
6. **Use Cloudflare**: For region detection (CF-IPCountry header)

## 🆘 Getting Help

1. Check logs: `vercel logs --follow`
2. Inspect deployment: `vercel inspect <url>`
3. Review guide: `VERCEL_DEPLOYMENT_GUIDE.md`
4. Vercel docs: https://vercel.com/docs/functions/serverless-functions/runtimes/python

---

**Last Updated**: 2025-10-05
**Python Runtime**: 3.12
**Vercel Region**: sin1 (Singapore)
