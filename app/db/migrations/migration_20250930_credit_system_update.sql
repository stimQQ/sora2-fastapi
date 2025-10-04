-- Migration: Credit System Update - 2025-09-30
-- Description: Add expiry tracking to credits and duration tracking to tasks
-- Author: Claude
-- Date: 2025-09-30

-- ============================================================================
-- PART 1: Update credit_transactions table
-- ============================================================================

-- Add expiry tracking fields to credit_transactions
ALTER TABLE credit_transactions
ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
ADD COLUMN is_expired BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN expired_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;

-- Add indexes for better query performance
CREATE INDEX idx_credit_transactions_expires_at ON credit_transactions(expires_at);
CREATE INDEX idx_credit_transactions_is_expired ON credit_transactions(is_expired);
CREATE INDEX idx_credit_transactions_expiry_lookup ON credit_transactions(user_id, is_expired, expires_at) WHERE is_expired = FALSE;

-- Add comment
COMMENT ON COLUMN credit_transactions.expires_at IS 'When the credits expire (6 months from creation)';
COMMENT ON COLUMN credit_transactions.is_expired IS 'Whether the credits have been marked as expired';
COMMENT ON COLUMN credit_transactions.expired_at IS 'When the credits were marked as expired';

-- ============================================================================
-- PART 2: Update tasks table
-- ============================================================================

-- Add video duration and credit calculation fields to tasks
ALTER TABLE tasks
ADD COLUMN output_duration_seconds FLOAT DEFAULT NULL,
ADD COLUMN credits_calculated INTEGER DEFAULT NULL,
ADD COLUMN credits_deducted BOOLEAN NOT NULL DEFAULT FALSE;

-- Add indexes
CREATE INDEX idx_tasks_credits_deducted ON tasks(credits_deducted);

-- Add comments
COMMENT ON COLUMN tasks.output_duration_seconds IS 'Actual output video duration in seconds';
COMMENT ON COLUMN tasks.credits_calculated IS 'Credits calculated based on duration';
COMMENT ON COLUMN tasks.credits_deducted IS 'Whether credits have been deducted for this task';

-- ============================================================================
-- PART 3: Update users table default credits
-- ============================================================================

-- Change default credits for new users from 10 to 100
ALTER TABLE users
ALTER COLUMN credits SET DEFAULT 100;

-- Update existing users with 10 credits to 100 (optional - uncomment if needed)
-- UPDATE users SET credits = 100 WHERE credits = 10 AND created_at > '2025-09-30';

-- Add comment
COMMENT ON COLUMN users.credits IS 'User credit balance (default 100 for new users, changed from 10 on 2025-09-30)';

-- ============================================================================
-- PART 4: Set expiry dates for existing credits (retroactive)
-- ============================================================================

-- Set expiry date for existing credits (6 months from their creation date)
-- This is retroactive and will expire old credits
UPDATE credit_transactions
SET expires_at = created_at + INTERVAL '6 months'
WHERE expires_at IS NULL
  AND amount > 0  -- Only for added credits (not spent)
  AND transaction_type IN ('earned', 'purchased', 'bonus', 'refunded');

-- Mark credits that should already be expired
UPDATE credit_transactions
SET is_expired = TRUE,
    expired_at = NOW()
WHERE expires_at IS NOT NULL
  AND expires_at < NOW()
  AND is_expired = FALSE
  AND amount > 0;

-- Recalculate user balances after marking expired credits
-- This creates a temporary table to calculate correct balances
CREATE TEMP TABLE user_balance_corrections AS
SELECT
    user_id,
    SUM(CASE
        WHEN amount > 0 AND (is_expired = FALSE OR is_expired IS NULL) THEN amount
        WHEN amount < 0 THEN amount
        ELSE 0
    END) as correct_balance
FROM credit_transactions
GROUP BY user_id;

-- Update user balances
UPDATE users u
SET credits = GREATEST(0, ubc.correct_balance)
FROM user_balance_corrections ubc
WHERE u.id = ubc.user_id;

-- Drop temporary table
DROP TABLE user_balance_corrections;

-- ============================================================================
-- PART 5: Verification queries (run these to verify migration)
-- ============================================================================

-- Check credit_transactions schema
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'credit_transactions'
-- ORDER BY ordinal_position;

-- Check tasks schema
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'tasks'
-- ORDER BY ordinal_position;

-- Check users default credits
-- SELECT column_name, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'users' AND column_name = 'credits';

-- Count expired credits
-- SELECT
--     COUNT(*) as total_expired_credits,
--     SUM(amount) as total_expired_amount,
--     COUNT(DISTINCT user_id) as users_affected
-- FROM credit_transactions
-- WHERE is_expired = TRUE;

-- ============================================================================
-- ROLLBACK SCRIPT (if needed)
-- ============================================================================

-- To rollback this migration, run the following:
/*
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
*/

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Log migration completion
-- INSERT INTO schema_migrations (version, applied_at)
-- VALUES ('20250930_credit_system_update', NOW())
-- ON CONFLICT DO NOTHING;