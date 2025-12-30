# Deployment Checklist

## Pre-Deployment Checklist

### ✅ Backend Requirements

#### 1. Environment Variables (Required)
Set these in your hosting platform's environment variables:

**Database:**
- `DATABASE_URL` - PostgreSQL connection string (Supabase format: `postgresql://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres`)

**API Keys:**
- `OPENROUTER_API_KEY` - Required for LLM agent reasoning
- `COINGECKO_PRO_API_KEY` - Optional but recommended for better rate limits
- `GROK_API_KEY` - Optional, for sentiment analysis

**Authentication:**
- `PRIVY_APP_ID` - Privy app ID
- `PRIVY_APP_SECRET` - Privy app secret
- `PRIVY_VERIFICATION_KEY` - Privy JWT verification key

**Network & Services:**
- `MOVEMENT_RPC` - Movement Network RPC URL (default: `https://testnet.movementnetwork.xyz/v1`)
- `MOVEMENT_NETWORK` - Network name (default: `movement-testnet`)
- `MOSAIC_API_KEY` - Mosaic DEX API key (default provided, but verify)
- `X402_RECEIVER_ADDRESS` - x402 payment receiver address
- `AGENT_EXECUTOR_ADDRESS` - Agent executor contract address

**CORS:**
- `CORS_ORIGINS` - Comma-separated list of allowed origins (e.g., `https://your-frontend.vercel.app,https://your-domain.com`)

**Optional:**
- `AUTONOMOUS_WALLET_ENCRYPTION_KEY` - For autonomous trading (generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- `AUTONOMOUS_TRADING_ENABLED` - Set to `true` or `false`
- `OHLCV_SCHEDULER_ENABLED` - Set to `true` or `false`
- `SENTIMENT_SCHEDULER_ENABLED` - Set to `true` or `false`

#### 2. Backend Deployment Platforms

**Option A: Railway (Recommended)**
1. Sign up at [railway.app](https://railway.app)
2. Create new project → "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect the Dockerfile
5. Add all environment variables in Railway dashboard
6. Deploy!

**Option B: Render**
1. Sign up at [render.com](https://render.com)
2. Go to "New" → "Blueprint"
3. Connect your GitHub repo
4. Render will use `render.yaml` configuration
5. Add environment variables in dashboard
6. Deploy!

**Option C: Fly.io**
1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Run: `cd backend && fly launch`
3. Update `fly.toml` if needed
4. Set secrets: `fly secrets set KEY=value`
5. Deploy: `fly deploy`

### ✅ Frontend Requirements

#### 1. Environment Variables (Required)
Set these in your hosting platform's environment variables:

**Required:**
- `NEXT_PUBLIC_API_URL` - Your backend API URL (e.g., `https://your-backend.railway.app` or `https://your-backend.onrender.com`)

**Optional:**
- `NEXT_PUBLIC_PRIVY_APP_ID` - Privy App ID for social login
- `NEXT_PUBLIC_TOKEN_A_ADDRESS` - Default Token A address
- `NEXT_PUBLIC_TOKEN_B_ADDRESS` - Default Token B address
- `NEXT_PUBLIC_POOL_ADDRESS` - Default pool address
- `NEXT_PUBLIC_SWITCHBOARD_FEEDS` - Comma-separated Switchboard feed IDs

#### 2. Frontend Deployment Platforms

**Option A: Vercel (Recommended for Next.js)**
1. Sign up at [vercel.com](https://vercel.com)
2. Import your GitHub repository
3. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `pnpm build` (or `cd frontend && pnpm build`)
   - **Output Directory**: `.next`
4. Add all `NEXT_PUBLIC_*` environment variables
5. Deploy!

**Option B: Netlify**
1. Sign up at [netlify.com](https://netlify.com)
2. Import from GitHub
3. Configure:
   - **Base directory**: `frontend`
   - **Build command**: `pnpm build`
   - **Publish directory**: `frontend/.next`
4. Add environment variables
5. Deploy!

**Option C: Render**
1. Sign up at [render.com](https://render.com)
2. New → "Static Site"
3. Connect GitHub repo
4. Configure:
   - **Build Command**: `cd frontend && pnpm install && pnpm build`
   - **Publish Directory**: `frontend/.next`
5. Add environment variables
6. Deploy!

## Critical Pre-Deployment Fixes

### ⚠️ Fix Frontend API Configuration

The `next.config.ts` has a hardcoded localhost URL that needs to be fixed for production. The rewrite should be conditional or removed.

**Current Issue:**
```typescript
destination: 'http://localhost:8000/:path*',  // ❌ Hardcoded localhost
```

**Solution:** The frontend should use `NEXT_PUBLIC_API_URL` environment variable instead of rewrites for production.

## Step-by-Step Deployment

### Step 1: Prepare Backend

1. **Test locally:**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **Verify health endpoint:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Check database connection:**
   - Ensure `DATABASE_URL` is set correctly
   - Test connection to Supabase

### Step 2: Deploy Backend

1. Choose your platform (Railway/Render/Fly.io)
2. Connect GitHub repository
3. Configure build settings (should auto-detect Dockerfile)
4. **Add ALL environment variables** from the checklist above
5. Deploy and note the backend URL

### Step 3: Update Frontend Configuration

1. **Fix `next.config.ts`** - Update API rewrite to use environment variable
2. Set `NEXT_PUBLIC_API_URL` to your deployed backend URL

### Step 4: Deploy Frontend

1. Choose your platform (Vercel recommended)
2. Connect GitHub repository
3. Set root directory to `frontend`
4. **Add ALL environment variables** including `NEXT_PUBLIC_API_URL`
5. Deploy

### Step 5: Update CORS

1. Go to your backend deployment
2. Update `CORS_ORIGINS` environment variable with your frontend URL
3. Restart backend service

### Step 6: Test Deployment

1. Visit your frontend URL
2. Test wallet connection
3. Test agent execution
4. Check backend logs for errors
5. Verify database connections

## Post-Deployment

### Monitoring

- **Backend Health**: `https://your-backend-url/health`
- **Detailed Health**: `https://your-backend-url/health/detailed`
- Check logs regularly for errors

### Common Issues

1. **CORS Errors**: Ensure `CORS_ORIGINS` includes your frontend URL
2. **Database Connection**: Verify `DATABASE_URL` format is correct
3. **API Timeouts**: Check if schedulers are running (they might timeout on free tiers)
4. **Environment Variables**: Double-check all required variables are set

### Scaling Considerations

- **Free Tier Limits**: 
  - Railway: $5/month free credit
  - Render: Free tier spins down after inactivity
  - Vercel: Generous free tier for Next.js
- **Database**: Supabase free tier is usually sufficient
- **API Rate Limits**: Monitor CoinGecko and OpenRouter usage

## Quick Reference

### Backend URLs by Platform
- Railway: `https://your-app.railway.app`
- Render: `https://your-app.onrender.com`
- Fly.io: `https://your-app.fly.dev`

### Frontend URLs by Platform
- Vercel: `https://your-app.vercel.app`
- Netlify: `https://your-app.netlify.app`
- Render: `https://your-app.onrender.com`

## Security Checklist

- [ ] All API keys are set as environment variables (never in code)
- [ ] Database password is strong and secure
- [ ] CORS is properly configured (not `*`)
- [ ] Privy secrets are set correctly
- [ ] Wallet encryption key is generated securely (if using autonomous trading)

