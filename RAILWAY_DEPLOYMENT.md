# Railway Deployment Guide - API + Worker Split

## ✅ Code Status
**The code is ready!** The `RUN_MODE` refactor is complete and tested.

## 🚀 Railway Setup (Two Services)

Railway supports multiple services in one project. You need to create **two services**:

1. **API Service** - Handles HTTP requests (`RUN_MODE=api`)
2. **Worker Service** - Runs background schedulers (`RUN_MODE=worker`)

### Step 1: Create API Service

1. Go to [railway.app](https://railway.app)
2. Create new project → "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect `backend/Dockerfile`
5. **Service Name**: `api` (or `aimmm-api`)
6. **Set Environment Variable**:
   ```
   RUN_MODE=api
   ```
7. Add all other environment variables (see below)
8. Railway will generate a public URL (e.g., `https://your-api.railway.app`)

### Step 2: Create Worker Service

1. In the **same Railway project**, click **"+ New"** → **"Service"**
2. Select **"GitHub Repo"** → Choose the same repository
3. Railway will auto-detect `backend/Dockerfile`
4. **Service Name**: `worker` (or `aimmm-worker`)
5. **Set Environment Variable**:
   ```
   RUN_MODE=worker
   ```
6. **Copy all environment variables** from API service (same DB, same keys)
7. **Important**: Worker service doesn't need a public domain (no HTTP traffic)

### Step 3: Environment Variables

Both services need these variables (set them in Railway dashboard → Variables):

#### Required for Both Services
```bash
# Runtime Mode (DIFFERENT per service)
RUN_MODE=api          # For API service
RUN_MODE=worker       # For Worker service

# Database
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres

# API Keys
OPENROUTER_API_KEY=your_key_here
COINGECKO_PRO_API_KEY=your_key_here
GROK_API_KEY=your_key_here

# Authentication
PRIVY_APP_ID=your_app_id
PRIVY_APP_SECRET=your_secret
PRIVY_VERIFICATION_KEY=your_key

# Network & Services
MOVEMENT_RPC=https://testnet.movementnetwork.xyz/v1
MOVEMENT_NETWORK=movement-testnet
MOSAIC_API_KEY=RgutcJWyaiBNCYDig52D3pkW6M8VEl-7
X402_RECEIVER_ADDRESS=your_address
AGENT_EXECUTOR_ADDRESS=your_contract_address

# CORS (only needed for API service, but safe to set for both)
CORS_ORIGINS=https://your-frontend.vercel.app

# Optional
AUTONOMOUS_WALLET_ENCRYPTION_KEY=your_key
AUTONOMOUS_TRADING_ENABLED=true
OHLCV_SCHEDULER_ENABLED=true
SENTIMENT_SCHEDULER_ENABLED=true
```

### Step 4: Verify Deployment

#### API Service
```bash
# Health check
curl https://your-api.railway.app/health
# Should return: {"status":"ok"}

# Check logs - should see:
# "RUN_MODE=api detected - running HTTP server only (no background schedulers)"
```

#### Worker Service
```bash
# Check logs - should see:
# "RUN_MODE=worker detected - starting background schedulers"
# "OHLCV scheduler started..."
# "Strategy scheduler started..."
```

## 📊 Service Comparison

| Feature | API Service | Worker Service |
|---------|-------------|----------------|
| **RUN_MODE** | `api` | `worker` |
| **HTTP Routes** | ✅ Yes | ✅ Yes (but not used) |
| **Schedulers** | ❌ No | ✅ Yes |
| **Public Domain** | ✅ Required | ❌ Optional |
| **Database** | ✅ Same | ✅ Same |
| **Environment Vars** | ✅ Same | ✅ Same |

## 🔍 Troubleshooting

### API Service Returns 502 Errors
- Check logs for scheduler startup attempts (should be none)
- Verify `RUN_MODE=api` is set correctly
- Check Railway service is running

### Worker Service Not Running Schedulers
- Check logs for `RUN_MODE=worker` confirmation
- Verify `RUN_MODE=worker` is set correctly
- Check individual scheduler flags (`OHLCV_SCHEDULER_ENABLED`, etc.)

### Both Services Using Same Database
✅ **This is correct!** Both services share the same database. The API service reads/writes data, and the worker service updates it via schedulers.

## 💰 Railway Pricing

- **Free Tier**: $5/month credit
- **API Service**: ~$0.50-2/month (depending on traffic)
- **Worker Service**: ~$1-3/month (always running)
- **Total**: ~$1.50-5/month (well within free tier)

## 🎯 Quick Commands

### Check API Service Logs
```bash
railway logs --service api
```

### Check Worker Service Logs
```bash
railway logs --service worker
```

### Set Environment Variable (CLI)
```bash
# API Service
railway variables set RUN_MODE=api --service api

# Worker Service
railway variables set RUN_MODE=worker --service worker
```

## ✅ Final Checklist

- [ ] API service deployed with `RUN_MODE=api`
- [ ] Worker service deployed with `RUN_MODE=worker`
- [ ] Both services have all environment variables set
- [ ] API service has public domain
- [ ] `/health` endpoint returns 200
- [ ] Worker logs show schedulers starting
- [ ] No 502 errors on API routes
- [ ] Frontend updated with API service URL

---

**Your code is ready!** Just follow the steps above to deploy both services on Railway.

