# Serverless Troubleshooting Quick Reference

## Common Issues & Solutions

### Issue: CORS Preflight 400 Error

**Symptoms:**
```
OPTIONS /api/endpoint HTTP/1.1 400
Error: CORS policy: No 'Access-Control-Allow-Origin' header
```

**Quick Fix:**
1. Check `vercel.json` has CORS headers
2. Verify `api/main.py` has OPTIONS handler
3. Ensure middleware includes "OPTIONS" in allow_methods

**Test:**
```bash
curl -X OPTIONS -H "Origin: https://example.com" \
  -H "Access-Control-Request-Method: POST" \
  https://your-app.vercel.app/api/auth/login
```

Should return `200 OK` with CORS headers.

---

### Issue: AsyncPG Connection Warnings

**Symptoms:**
```
RuntimeWarning: coroutine 'Connection._cancel' was never awaited
Exception terminating connection <asyncpg.connection.Connection>
```

**Quick Fix:**
1. Verify `VERCEL=1` environment variable is set
2. Check `app/db/base.py` uses `NullPool` for serverless
3. Ensure sessions are properly closed in finally blocks

**Verification:**
```python
# Should see this log in Vercel:
"Serverless environment detected - using NullPool"
```

---

### Issue: Event Loop Errors

**Symptoms:**
```
Error: got Future <Future> attached to a different loop
RuntimeError: Event loop is closed
```

**Quick Fix:**
1. Use `NullPool` (see above)
2. Ensure all async resources closed in finally blocks
3. Never cache database connections globally

**Prevention:**
- Always use dependency injection: `db: AsyncSession = Depends(get_db)`
- Never store connections in module-level variables
- Always use context managers

---

### Issue: Table Does Not Exist

**Symptoms:**
```
sqlalchemy.exc.ProgrammingError: relation "table_name" does not exist
```

**Quick Fix:**
1. Run migrations: `alembic upgrade head`
2. For Vercel, check database URL is correct
3. Add graceful error handling (see showcase router)

**Check Migration Status:**
```bash
# Locally
alembic current

# On database directly
psql $DATABASE_URL -c "SELECT * FROM alembic_version;"
```

---

### Issue: Slow Cold Starts

**Symptoms:**
- First request takes >5 seconds
- Subsequent requests fast

**Optimization:**
1. Reduce dependencies in `requirements.txt`
2. Use `server_settings: {"jit": "off"}` in connect_args
3. Increase memory in `vercel.json`: `"memory": 1024`
4. Use regions close to database: `"regions": ["sin1"]`

---

### Issue: Timeout on AI API Calls

**Symptoms:**
```
Error: Function execution timed out
Task exceeded maximum duration
```

**Quick Fix:**
1. Increase `maxDuration` in vercel.json
2. Add timeout to httpx client
3. Consider background jobs for long tasks

**Vercel.json:**
```json
{
  "functions": {
    "api/main.py": {
      "maxDuration": 30  // Max 60s on Pro plan
    }
  }
}
```

---

### Issue: Database Connection Pool Exhausted

**Symptoms:**
```
QueuePool limit exceeded
Too many connections
```

**Quick Fix:**
- Use `NullPool` in serverless (no pooling)
- Each request gets new connection
- Connection closed after request

**Not Applicable in Serverless:**
This issue only occurs with connection pooling, which we disabled.

---

## Debugging Commands

### View Vercel Logs
```bash
# Real-time logs
vercel logs --follow

# Last 100 lines
vercel logs --limit 100

# Specific deployment
vercel logs <deployment-url>
```

### Test Database Connection
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1;"

# List tables
psql $DATABASE_URL -c "\dt"

# Check active connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"
```

### Test API Endpoints
```bash
# Health check
curl https://your-app.vercel.app/health

# OPTIONS preflight
curl -X OPTIONS https://your-app.vercel.app/api/tasks/user/tasks

# With auth
curl -H "Authorization: Bearer $TOKEN" \
  https://your-app.vercel.app/api/users/profile
```

---

## Environment Variables Checklist

Required in Vercel:
- [x] `DATABASE_URL_MASTER` - PostgreSQL connection string
- [x] `SECRET_KEY` - JWT secret (32+ chars)
- [x] `QWEN_VIDEO_API_KEY` - DashScope API key
- [x] `SORA_API_KEY` - Sora API key
- [x] `PROXY_API_KEY` - Internal API key
- [x] `VERCEL=1` - Serverless detection (auto-set)

Optional:
- [ ] `CORS_ALLOWED_ORIGINS` - Comma-separated origins
- [ ] `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR
- [ ] `DATABASE_URL_SLAVES` - Read replicas

---

## Performance Monitoring

### Key Metrics to Watch

1. **Cold Start Duration**
   - Target: <2 seconds
   - Check: First request after idle

2. **Database Query Time**
   - Target: <100ms for simple queries
   - Check: Enable `DATABASE_ECHO=True` temporarily

3. **Error Rate**
   - Target: <1%
   - Check: Vercel Analytics

4. **Memory Usage**
   - Target: <512MB
   - Check: Vercel Function logs

---

## Best Practices

### DO ✅
- Use `NullPool` for database
- Close all async resources in finally
- Handle missing tables gracefully
- Set explicit timeouts on API calls
- Use dependency injection
- Log errors with context

### DON'T ❌
- Don't use connection pooling
- Don't cache database connections
- Don't store state globally
- Don't ignore cleanup errors
- Don't use blocking I/O
- Don't skip error handling

---

## Quick Health Check

Run this script to verify all fixes are working:

```python
import asyncio
import httpx

async def health_check(base_url):
    async with httpx.AsyncClient() as client:
        # 1. Check OPTIONS
        r = await client.options(f"{base_url}/api/auth/login")
        assert r.status_code == 200, "OPTIONS failed"

        # 2. Check health
        r = await client.get(f"{base_url}/health")
        assert r.status_code == 200, "Health check failed"

        # 3. Check showcase (should not error)
        r = await client.get(f"{base_url}/api/showcase/videos")
        assert r.status_code in [200, 503], "Showcase failed"

        print("✅ All health checks passed!")

# Run
asyncio.run(health_check("https://your-app.vercel.app"))
```

---

## Support Resources

- **Vercel Docs**: https://vercel.com/docs/functions/serverless-functions
- **FastAPI Async**: https://fastapi.tiangolo.com/async/
- **SQLAlchemy Async**: https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html
- **AsyncPG**: https://magicstack.github.io/asyncpg/current/

---

**Last Updated**: 2025-10-05
