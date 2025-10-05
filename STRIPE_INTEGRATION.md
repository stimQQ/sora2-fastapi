# Stripe Payment Integration Guide

## 📋 Overview

Complete Stripe payment integration for credit purchases with webhook support, refunds, and automatic credit delivery.

**Status**: ✅ Fully Implemented
**Last Updated**: 2025-10-05

---

## 🔑 Environment Configuration

### Required Environment Variables

Add to your `.env` file:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxx

# API Base URL (for webhook callbacks)
API_BASE_URL=https://api.yourdomain.com

# Frontend URL (for return URLs)
FRONTEND_URL=https://yourdomain.com
```

### Getting Stripe Keys

1. **Test Keys** (Development):
   - Login to [Stripe Dashboard](https://dashboard.stripe.com)
   - Navigate to **Developers > API keys**
   - Copy **Secret key** (`sk_test_...`) and **Publishable key** (`pk_test_...`)

2. **Webhook Secret**:
   - Go to **Developers > Webhooks**
   - Click **Add endpoint**
   - URL: `https://api.yourdomain.com/api/payments/webhook/stripe`
   - Events to select:
     - `checkout.session.completed`
     - `payment_intent.succeeded`
     - `payment_intent.payment_failed`
   - Copy the **Signing secret** (`whsec_...`)

---

## 🎯 API Endpoints

### 1. Get Available Packages

**GET** `/api/payments/packages`

**Response**:
```json
{
  "packages": {
    "trial": {
      "name": "体验包",
      "credits": 500,
      "price": "50.00",
      "currency": "CNY",
      "unit_price": 0.10
    },
    "standard": {
      "name": "标准包",
      "credits": 1100,
      "price": "100.00",
      "currency": "CNY",
      "unit_price": 0.091
    },
    "value": {
      "name": "超值包",
      "credits": 6000,
      "price": "500.00",
      "currency": "CNY",
      "unit_price": 0.083
    },
    "premium": {
      "name": "豪华包",
      "credits": 13000,
      "price": "1000.00",
      "currency": "CNY",
      "unit_price": 0.076
    }
  },
  "credit_value_rmb": 0.1
}
```

**cURL Example**:
```bash
curl -X GET "http://localhost:8000/api/payments/packages"
```

---

### 2. Create Stripe Payment

**POST** `/api/payments/stripe/create`

**Headers**:
```
Authorization: Bearer <JWT_TOKEN>
X-API-Key: <PROXY_API_KEY>
Content-Type: application/json
```

**Request Body**:
```json
{
  "package": "standard",
  "return_url": "https://yourdomain.com/payment/callback"
}
```

**Response**:
```json
{
  "payment_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "pending",
  "amount": "100.00",
  "currency": "CNY",
  "credits_purchased": 1100,
  "payment_url": "https://checkout.stripe.com/c/pay/cs_test_xxxxxxxxxxxxx"
}
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/api/payments/stripe/create" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-API-Key: YOUR_PROXY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "package": "standard",
    "return_url": "https://yourdomain.com/payment/success"
  }'
```

**Flow**:
1. Backend creates `PaymentOrder` in database (status: PENDING)
2. Backend creates Stripe Checkout Session
3. Frontend redirects user to `payment_url`
4. User completes payment on Stripe
5. Stripe sends webhook to `/api/payments/webhook/stripe`
6. Backend updates order status and adds credits

---

### 3. Stripe Webhook Handler

**POST** `/api/payments/webhook/stripe`

**Headers**:
```
stripe-signature: t=1234567890,v1=xxxxxxxxxxxxx
Content-Type: application/json
```

**Events Handled**:
- ✅ `checkout.session.completed` → Payment succeeded
- ✅ `payment_intent.succeeded` → Payment succeeded (alternative)
- ✅ `payment_intent.payment_failed` → Payment failed

**Response**:
```json
{
  "received": true
}
```

**Webhook Processing**:
1. Verify Stripe signature using `STRIPE_WEBHOOK_SECRET`
2. Extract `order_id` from metadata
3. Update `PaymentOrder` status to `SUCCEEDED`
4. Call `CreditManager.process_payment_credits()` to add credits
5. Create `CreditTransaction` record with 6-month expiry

**Testing Webhooks Locally**:
```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:8000/api/payments/webhook/stripe

# Trigger test webhook
stripe trigger checkout.session.completed
```

---

### 4. Get Payment Status

**GET** `/api/payments/{payment_id}`

**Headers**:
```
Authorization: Bearer <JWT_TOKEN>
```

**Response**:
```json
{
  "payment_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "succeeded",
  "amount": 100.0,
  "currency": "CNY",
  "credits_purchased": 1100,
  "payment_url": "https://checkout.stripe.com/c/pay/cs_test_xxxxx",
  "created_at": "2025-10-05T10:30:00Z",
  "paid_at": "2025-10-05T10:32:15Z"
}
```

**cURL Example**:
```bash
curl -X GET "http://localhost:8000/api/payments/f47ac10b-58cc-4372-a567-0e02b2c3d479" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 5. Refund Payment (Admin Only)

**POST** `/api/payments/stripe/refund`

**Headers**:
```
Authorization: Bearer <ADMIN_JWT_TOKEN>
Content-Type: application/json
```

**Request Body**:
```json
{
  "payment_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "reason": "Customer request",
  "amount": null  // null = full refund
}
```

**Response**:
```json
{
  "success": true,
  "refund_id": "re_xxxxxxxxxxxxx",
  "amount": 100.0,
  "credits_refunded": 1100,
  "message": "Refund processed successfully"
}
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/api/payments/stripe/refund" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "reason": "Duplicate payment"
  }'
```

---

## 🔄 Payment Flow Diagram

```
┌─────────┐     1. Create Payment      ┌─────────────┐
│ Frontend│─────────────────────────────>│   Backend   │
└─────────┘                             └─────────────┘
                                               │
                                               │ 2. Create Order (DB)
                                               │ 3. Create Stripe Session
                                               ▼
                                        ┌─────────────┐
                                        │   Stripe    │
                                        └─────────────┘
                                               │
                                               │ 4. Return checkout URL
┌─────────┐     5. Redirect to Stripe   ┌─────┴───────┐
│  User   │<─────────────────────────────│   Backend   │
└─────────┘                             └─────────────┘
     │
     │ 6. Complete Payment
     ▼
┌─────────────┐
│   Stripe    │
└─────────────┘
     │
     │ 7. Send Webhook
     ▼
┌─────────────┐
│   Backend   │──┐
└─────────────┘  │ 8. Verify Signature
                 │ 9. Update Order Status
                 │ 10. Add Credits to User
                 │ 11. Create Transaction Record
                 └──> ✅ Complete
```

---

## 💳 Credit Packages Configuration

Defined in `app/core/config.py`:

```python
CREDIT_PACKAGES: Dict[str, Dict[str, Any]] = {
    "trial": {
        "name": "体验包",
        "credits": 500,
        "price": 50.0,
        "unit_price": 0.10
    },
    "standard": {
        "name": "标准包",
        "credits": 1100,
        "price": 100.0,
        "unit_price": 0.091
    },
    "value": {
        "name": "超值包",
        "credits": 6000,
        "price": 500.0,
        "unit_price": 0.083
    },
    "premium": {
        "name": "豪华包",
        "credits": 13000,
        "price": 1000.0,
        "unit_price": 0.076
    }
}
```

---

## 🔐 Security Features

### ✅ Implemented Security
1. **Webhook Signature Verification**: Stripe signature validation using `STRIPE_WEBHOOK_SECRET`
2. **Idempotency**: Duplicate webhook protection (checks if order already processed)
3. **Database Locking**: Row-level locks (`with_for_update()`) prevent race conditions
4. **Authentication**: JWT token required for payment creation
5. **Authorization**: Admin-only refund endpoint
6. **HTTPS Only**: Stripe requires HTTPS for webhooks in production

### 🔒 Best Practices
- Never expose `STRIPE_SECRET_KEY` in frontend
- Always verify webhook signatures
- Use test keys in development
- Enable Stripe Radar for fraud detection
- Set up Stripe alerts for failed payments

---

## 🧪 Testing Guide

### Test Cards (Stripe Test Mode)

| Card Number         | Description                    | Result   |
|---------------------|--------------------------------|----------|
| 4242 4242 4242 4242 | Visa - Success                 | ✅ Success |
| 4000 0000 0000 9995 | Visa - Insufficient funds      | ❌ Declined |
| 4000 0000 0000 0002 | Visa - Card declined           | ❌ Declined |
| 4000 0025 0000 3155 | Visa - 3D Secure required      | 🔐 Auth    |

**Expiry**: Any future date (e.g., 12/34)
**CVC**: Any 3 digits (e.g., 123)
**ZIP**: Any 5 digits (e.g., 12345)

### Test Scenarios

#### ✅ Successful Payment Flow
```bash
# 1. Create payment
PAYMENT_RESPONSE=$(curl -X POST "http://localhost:8000/api/payments/stripe/create" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "X-API-Key: $PROXY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"package": "trial"}')

PAYMENT_ID=$(echo $PAYMENT_RESPONSE | jq -r '.payment_id')
PAYMENT_URL=$(echo $PAYMENT_RESPONSE | jq -r '.payment_url')

# 2. Open payment URL in browser
echo "Open this URL: $PAYMENT_URL"

# 3. Complete payment with test card 4242 4242 4242 4242

# 4. Check webhook logs
tail -f logs/app.log | grep "Stripe webhook"

# 5. Verify credits added
curl -X GET "http://localhost:8000/api/users/credits" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

#### ❌ Failed Payment Flow
```bash
# Use Stripe CLI to trigger failed payment
stripe trigger payment_intent.payment_failed
```

---

## 📊 Database Schema

### PaymentOrder Table
```sql
CREATE TABLE payment_orders (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    provider VARCHAR(50) NOT NULL,  -- 'stripe'
    provider_order_id VARCHAR(100) UNIQUE,  -- Stripe session ID
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'CNY',
    credits_purchased INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,  -- pending|processing|succeeded|failed
    payment_url VARCHAR(500),
    transaction_id VARCHAR(100),
    error_message TEXT,
    return_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    paid_at TIMESTAMP
);
```

### CreditTransaction Table (Auto-created on Payment)
```sql
CREATE TABLE credit_transactions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    transaction_type VARCHAR(50) NOT NULL,  -- 'purchased'
    amount INTEGER NOT NULL,  -- Positive for purchased credits
    balance_after INTEGER NOT NULL,
    payment_order_id VARCHAR(36) REFERENCES payment_orders(id),
    description TEXT,
    expires_at TIMESTAMP,  -- 6 months from purchase
    is_expired BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🐛 Troubleshooting

### Issue: Webhook Not Received
**Symptoms**: Payment succeeds but credits not added

**Solutions**:
1. Check webhook endpoint is accessible:
   ```bash
   curl -X POST "https://api.yourdomain.com/api/payments/webhook/stripe"
   ```

2. Verify webhook secret matches Stripe dashboard:
   ```bash
   echo $STRIPE_WEBHOOK_SECRET
   ```

3. Check webhook logs in Stripe Dashboard:
   - Go to **Developers > Webhooks**
   - Click on your endpoint
   - Check **Recent deliveries**

4. Test locally with Stripe CLI:
   ```bash
   stripe listen --forward-to localhost:8000/api/payments/webhook/stripe
   ```

---

### Issue: Signature Verification Failed
**Symptoms**: 400 error "Invalid webhook signature"

**Solutions**:
1. Ensure webhook secret is correct in `.env`
2. Check you're passing raw body to Stripe verification (not parsed JSON)
3. Verify `stripe-signature` header is present

---

### Issue: Credits Not Added
**Symptoms**: Webhook received but credits not in user account

**Solutions**:
1. Check database logs:
   ```bash
   tail -f logs/app.log | grep "process_payment_credits"
   ```

2. Verify `CreditTransaction` was created:
   ```sql
   SELECT * FROM credit_transactions
   WHERE payment_order_id = 'payment_id_here';
   ```

3. Check user balance:
   ```sql
   SELECT id, credits, total_credits_earned
   FROM users WHERE id = 'user_id_here';
   ```

---

## 🚀 Production Deployment Checklist

- [ ] Replace test keys with live keys in production `.env`
- [ ] Update webhook URL to production domain
- [ ] Enable HTTPS (Stripe requires it for webhooks)
- [ ] Test webhook delivery in production
- [ ] Set up Stripe webhook alerts (email on failure)
- [ ] Enable Stripe Radar (fraud detection)
- [ ] Configure payment receipt emails in Stripe Dashboard
- [ ] Set up refund policies
- [ ] Monitor payment success rate
- [ ] Test end-to-end payment flow

---

## 📚 Additional Resources

- [Stripe Checkout Documentation](https://stripe.com/docs/payments/checkout)
- [Stripe Webhooks Guide](https://stripe.com/docs/webhooks)
- [Stripe API Reference](https://stripe.com/docs/api)
- [Stripe Testing Cards](https://stripe.com/docs/testing)
- [Stripe CLI Documentation](https://stripe.com/docs/stripe-cli)

---

## 🆘 Support

For issues or questions:
1. Check this documentation
2. Review Stripe Dashboard logs
3. Check application logs: `tail -f logs/app.log`
4. Test with Stripe CLI
5. Contact development team

**Last Updated**: 2025-10-05
