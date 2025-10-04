# Credit System Update Migration - 2025-09-30

## Overview

This migration updates the credit system to implement new business requirements including:
- **Post-payment model**: Credits deducted after task completion (not before)
- **Per-second pricing**: 10 credits/s (standard) or 14 credits/s (pro)
- **Credit expiry**: All credits expire after 6 months
- **Increased initial credits**: New users get 100 credits (was 10)
- **Updated rewards**: Invite (100), Daily sign-in (10), Share video (10)

## Migration Files

1. **migration_20250930_credit_system_update.sql** - Raw SQL migration
2. **alembic_migration_credit_system_update.py** - Alembic Python migration
3. **README_MIGRATION_20250930.md** - This file

## Database Changes

### 1. `credit_transactions` Table

**New columns:**
```sql
expires_at          TIMESTAMP WITH TIME ZONE  -- When credits expire (6 months from creation)
is_expired          BOOLEAN                   -- Whether credits are expired
expired_at          TIMESTAMP WITH TIME ZONE  -- When marked as expired
```

**New indexes:**
- `idx_credit_transactions_expires_at` - On expires_at
- `idx_credit_transactions_is_expired` - On is_expired
- `idx_credit_transactions_expiry_lookup` - Composite index for FIFO queries

### 2. `tasks` Table

**New columns:**
```sql
output_duration_seconds  FLOAT    -- Actual video duration in seconds
credits_calculated       INTEGER  -- Credits calculated based on duration
credits_deducted         BOOLEAN  -- Whether credits have been deducted
```

**New indexes:**
- `idx_tasks_credits_deducted` - On credits_deducted

### 3. `users` Table

**Changed:**
- Default value for `credits` column: 10 → 100

## Running the Migration

### Option 1: Using Raw SQL (Recommended for initial setup)

```bash
# Connect to your database
psql -h <host> -U <user> -d <database> -f app/db/migrations/migration_20250930_credit_system_update.sql

# Or using MySQL
mysql -h <host> -u <user> -p <database> < app/db/migrations/migration_20250930_credit_system_update.sql
```

### Option 2: Using Alembic (if configured)

```bash
# Place the alembic migration in your alembic/versions/ directory
# Then run:
alembic upgrade head
```

### Option 3: Programmatic Migration

```python
from app.db.migrations.alembic_migration_credit_system_update import upgrade
from app.db.session import engine

# Run migration
with engine.begin() as connection:
    upgrade()
```

## Verification Steps

After running the migration, verify the changes:

### 1. Check Schema Changes

```sql
-- Verify credit_transactions columns
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'credit_transactions'
  AND column_name IN ('expires_at', 'is_expired', 'expired_at')
ORDER BY ordinal_position;

-- Verify tasks columns
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'tasks'
  AND column_name IN ('output_duration_seconds', 'credits_calculated', 'credits_deducted')
ORDER BY ordinal_position;

-- Verify users default credits
SELECT column_name, column_default
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'credits';
```

### 2. Check Data Migration

```sql
-- Check expired credits
SELECT
    COUNT(*) as total_expired_transactions,
    SUM(amount) as total_expired_amount,
    COUNT(DISTINCT user_id) as users_affected
FROM credit_transactions
WHERE is_expired = TRUE;

-- Check expiry dates set
SELECT
    COUNT(*) as total_credits_with_expiry,
    MIN(expires_at) as earliest_expiry,
    MAX(expires_at) as latest_expiry
FROM credit_transactions
WHERE expires_at IS NOT NULL;

-- Sample user balance check
SELECT
    u.id,
    u.credits as user_balance,
    SUM(CASE WHEN ct.amount > 0 AND ct.is_expired = FALSE THEN ct.amount ELSE 0 END) as active_credits,
    SUM(CASE WHEN ct.amount < 0 THEN ct.amount ELSE 0 END) as spent_credits
FROM users u
LEFT JOIN credit_transactions ct ON u.id = ct.user_id
GROUP BY u.id, u.credits
LIMIT 10;
```

### 3. Test New Features

```python
# Test credit calculation
from app.services.credits.manager import CreditManager

# Calculate credits for 5-second video (standard)
credits_std = CreditManager.calculate_video_credits(5.0, is_pro=False)
print(f"5s standard video: {credits_std} credits")  # Should be 50

# Calculate credits for 5-second video (pro)
credits_pro = CreditManager.calculate_video_credits(5.0, is_pro=True)
print(f"5s pro video: {credits_pro} credits")  # Should be 70
```

## Rollback Instructions

If you need to rollback this migration:

### Using SQL

The rollback SQL is included in the migration file (commented out):

```sql
-- Remove new columns from credit_transactions
ALTER TABLE credit_transactions
DROP COLUMN IF EXISTS expires_at,
DROP COLUMN IF EXISTS is_expired,
DROP COLUMN IF EXISTS expired_at;

-- Remove indexes
DROP INDEX IF EXISTS idx_credit_transactions_expires_at;
DROP INDEX IF EXISTS idx_credit_transactions_is_expired;
DROP INDEX IF EXISTS idx_credit_transactions_expiry_lookup;

-- Remove new columns from tasks
ALTER TABLE tasks
DROP COLUMN IF EXISTS output_duration_seconds,
DROP COLUMN IF EXISTS credits_calculated,
DROP COLUMN IF EXISTS credits_deducted;

-- Remove index
DROP INDEX IF EXISTS idx_tasks_credits_deducted;

-- Revert users default credits to 10
ALTER TABLE users
ALTER COLUMN credits SET DEFAULT 10;
```

### Using Alembic

```bash
alembic downgrade -1
```

## Impact Assessment

### Existing Data
- **Existing credits**: Will have expiry dates set retroactively (6 months from creation)
- **Old credits**: Credits older than 6 months will be marked as expired immediately
- **User balances**: Will be recalculated to exclude expired credits

### Existing Tasks
- **Completed tasks**: Will have NULL values for new fields (normal)
- **Running tasks**: Will complete with old pricing (safe)
- **New tasks**: Will use new post-payment model

### API Behavior
- **Task creation**: No longer deducts credits immediately (soft check only)
- **Task completion**: New callback endpoint deducts credits based on duration
- **Credit balance**: Now shows only non-expired credits

## Monitoring Recommendations

After migration, monitor:

1. **Credit deductions**: Ensure completion callback is being called
2. **Expired credits**: Daily task should run and log results
3. **User complaints**: About missing credits (may need manual adjustment)
4. **Task completion rate**: Ensure no tasks are stuck without credit deduction

## Support Queries

### Find users affected by expiry

```sql
SELECT
    u.id,
    u.email,
    u.credits as current_balance,
    SUM(CASE WHEN ct.is_expired = TRUE AND ct.amount > 0 THEN ct.amount ELSE 0 END) as expired_amount,
    MIN(ct.expired_at) as first_expiry
FROM users u
JOIN credit_transactions ct ON u.id = ct.user_id
WHERE ct.is_expired = TRUE AND ct.amount > 0
GROUP BY u.id, u.email, u.credits
ORDER BY expired_amount DESC
LIMIT 100;
```

### Find tasks without credit deduction

```sql
SELECT
    t.id,
    t.user_id,
    t.status,
    t.created_at,
    t.output_duration_seconds,
    t.credits_calculated,
    t.credits_deducted
FROM tasks t
WHERE t.status = 'SUCCEEDED'
  AND t.completed_at IS NOT NULL
  AND t.credits_deducted = FALSE
ORDER BY t.completed_at DESC
LIMIT 50;
```

## Configuration Updates

Ensure these settings are in your `.env`:

```env
# Credit System (Updated 2025-09-30)
DEFAULT_USER_CREDITS=100
CREDITS_PER_SECOND_STANDARD=10
CREDITS_PER_SECOND_PRO=14
CREDIT_VALUE_RMB=0.1
CREDITS_INVITE_REWARD=100
CREDITS_DAILY_SIGNIN=10
CREDITS_SHARE_VIDEO=10
CREDIT_EXPIRY_MONTHS=6

# API endpoint for Celery callback
API_BASE_URL=http://localhost:8000
```

## Troubleshooting

### Issue: User balance incorrect after migration

**Solution:**
```sql
-- Recalculate balance for specific user
WITH user_balance AS (
    SELECT
        user_id,
        SUM(CASE
            WHEN amount > 0 AND is_expired = FALSE THEN amount
            WHEN amount < 0 THEN amount
            ELSE 0
        END) as correct_balance
    FROM credit_transactions
    WHERE user_id = '<user_id>'
    GROUP BY user_id
)
UPDATE users u
SET credits = GREATEST(0, ub.correct_balance)
FROM user_balance ub
WHERE u.id = ub.user_id;
```

### Issue: Credits not being deducted after task completion

**Check:**
1. Celery worker is running
2. Completion endpoint is accessible from worker
3. PROXY_API_KEY is configured correctly
4. Check logs for callback errors

### Issue: Expired credits not being cleaned up

**Check:**
1. Celery beat scheduler is running
2. Check task execution logs: `expire_credits_daily`
3. Manually run: `celery -A celery_app.worker call celery_app.tasks.credit_expiry_task.expire_credits_daily`

## Contact

For issues or questions about this migration:
- Check logs in `/logs/app.log`
- Review error tracking in Sentry (if configured)
- Contact DevOps team

---

**Migration Version:** 20250930_credit_system
**Date:** 2025-09-30
**Author:** Claude AI
**Approved By:** [To be filled]