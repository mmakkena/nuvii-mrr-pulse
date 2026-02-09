# Stripe Connect OAuth Setup Guide

## Why You Need This

To connect customer Stripe accounts with **read-only access**, you need to set up Stripe Connect OAuth. This allows customers to grant your app permission to monitor their Stripe data without giving you the ability to modify anything.

## Current Issue

When you click "Connect Stripe", it's redirecting to the wrong URL because `STRIPE_CLIENT_ID` is not configured.

## Complete Setup Instructions

### Step 1: Create Stripe Connect Application

1. **Go to Stripe Dashboard**: https://dashboard.stripe.com/test/settings/applications
   - Make sure you're in **Test Mode** (toggle in top right)

2. **Click "Get Started" under Connect**
   - If you don't see this, go to: https://dashboard.stripe.com/test/connect/accounts/overview

3. **Fill in OAuth Settings**:
   - **Integration name**: MRRPulse (or your app name)
   - **Redirect URIs**:
     ```
     http://localhost:8000/api/stripe/connect/callback
     ```
   - **Icon/Logo**: Optional but recommended

4. **Save and Get Credentials**:
   - After saving, you'll see your **Client ID** (starts with `ca_`)
   - Copy this - you'll need it!

### Step 2: Configure Backend Environment

Create `/Users/ravi/otherapps/nuvii-mrr-pulse/backend/.env`:

```bash
# Copy the example and fill in your values
cp backend/.env.example backend/.env

# Edit the file and add your Stripe credentials
nano backend/.env  # or use your preferred editor
```

**Minimum required configuration**:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mrrpulse

# Stripe Connect OAuth
STRIPE_CLIENT_ID=ca_xxxxxxxxxxxxxxxxxxxxx  # ← GET THIS FROM STRIPE DASHBOARD
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxx  # ← YOUR STRIPE SECRET KEY

# URLs
API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# SendGrid (for email alerts)
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxx  # ← GET THIS FROM SENDGRID

# JWT (generate a random string)
JWT_SECRET=your-random-secret-key-min-32-chars
```

### Step 3: Restart Backend

```bash
cd /Users/ravi/otherapps/nuvii-mrr-pulse/backend
source venv/bin/activate
python -m uvicorn app.main:app --reload
```

### Step 4: Test the OAuth Flow

1. **Navigate to**: http://localhost:3000/integrations
2. **Click**: "Connect Stripe" button
3. **You should be redirected to**:
   ```
   https://connect.stripe.com/oauth/authorize?
     response_type=code&
     client_id=ca_xxx&
     scope=read_only&
     redirect_uri=http://localhost:8000/api/stripe/connect/callback
   ```

4. **On Stripe page**:
   - You'll see "MRRPulse wants read-only access"
   - You can test with your Stripe test account
   - Click "Connect" to authorize

5. **After authorization**:
   - You'll be redirected back to your app
   - The Stripe account will be connected
   - You'll see it listed in the Integrations page

## Quick Test Without Full OAuth Setup

If you just want to test locally without setting up full OAuth:

```bash
# Use the test endpoint to create a mock connection
curl -X POST "http://localhost:8000/api/stripe/connect/test?workspace_id=YOUR_WORKSPACE_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Or use the Python script:

```python
# In backend directory
python test_stripe_connect.py
```

## Troubleshooting

### Issue: "Invalid redirect_uri"
**Solution**: Make sure you added `http://localhost:8000/api/stripe/connect/callback` to your Stripe Connect settings

### Issue: "No such application"
**Solution**: Your `STRIPE_CLIENT_ID` is incorrect. Double-check it in Stripe Dashboard → Settings → Connect

### Issue: Still redirecting to wrong URL
**Solution**:
1. Check that `.env` file exists in `backend/` directory
2. Verify `STRIPE_CLIENT_ID` is set in `.env`
3. Restart the backend server

### Issue: "Client secret mismatch"
**Solution**: Make sure you're using the secret key that matches your client ID (test mode vs live mode)

## What Happens After Connection

Once connected, MRRPulse will:
1. ✅ Receive webhooks for payments, disputes, refunds, etc.
2. ✅ Create alerts based on your rules
3. ✅ Send email notifications to configured addresses
4. ✅ Track metrics and display in dashboard

With **read-only** scope, MRRPulse:
- ❌ Cannot create charges or refunds
- ❌ Cannot modify subscriptions
- ❌ Cannot access full card numbers or bank accounts
- ❌ Cannot change any Stripe settings

## Need Help?

If you're still having issues:
1. Check the backend logs for error messages
2. Verify all environment variables are set correctly
3. Make sure you're in Stripe test mode
4. Confirm the redirect URI matches exactly (including http:// and port)
