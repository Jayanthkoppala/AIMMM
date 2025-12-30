# Quick Deployment Guide

## 🚀 Fastest Path to Deployment

### Backend (Railway - Recommended)

1. **Sign up**: [railway.app](https://railway.app) (free $5 credit/month)

2. **Deploy**:
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway auto-detects `backend/Dockerfile`

3. **Set Environment Variables** (in Railway dashboard → Variables):
   ```
   DATABASE_URL=postgresql://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres
   OPENROUTER_API_KEY=your_key_here
   COINGECKO_PRO_API_KEY=your_key_here (optional)
   GROK_API_KEY=your_key_here (optional)
   PRIVY_APP_ID=your_app_id
   PRIVY_APP_SECRET=your_secret
   PRIVY_VERIFICATION_KEY=your_key
   CORS_ORIGINS=https://your-frontend.vercel.app
   X402_RECEIVER_ADDRESS=your_address
   AGENT_EXECUTOR_ADDRESS=your_contract_address
   ```

4. **Get Backend URL**: Railway provides URL like `https://your-app.railway.app`

### Frontend (Vercel - Recommended)

1. **Sign up**: [vercel.com](https://vercel.com) (free tier)

2. **Deploy**:
   - Click "Add New" → "Project"
   - Import your GitHub repository
   - Configure:
     - **Root Directory**: `frontend`
     - **Framework Preset**: Next.js (auto-detected)
     - **Build Command**: `pnpm build` (or leave default)
     - **Output Directory**: `.next` (default)

3. **Set Environment Variables**:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   NEXT_PUBLIC_PRIVY_APP_ID=your_app_id (optional)
   NEXT_PUBLIC_TOKEN_A_ADDRESS=0x... (optional)
   NEXT_PUBLIC_TOKEN_B_ADDRESS=0x... (optional)
   ```

4. **Deploy**: Click "Deploy"

5. **Get Frontend URL**: Vercel provides URL like `https://your-app.vercel.app`

### Final Step: Update CORS

1. Go back to Railway (backend)
2. Update `CORS_ORIGINS` variable:
   ```
   CORS_ORIGINS=https://your-frontend.vercel.app
   ```
3. Railway will automatically restart

## ✅ Test Your Deployment

1. Visit your frontend URL
2. Check browser console for errors
3. Test wallet connection
4. Test agent execution
5. Check backend logs in Railway dashboard

## 🔧 Troubleshooting

**CORS Errors?**
- Make sure `CORS_ORIGINS` in backend includes your exact frontend URL (no trailing slash)

**API Not Found?**
- Verify `NEXT_PUBLIC_API_URL` is set correctly in Vercel
- Check backend is running (visit `https://your-backend.railway.app/health`)

**Database Errors?**
- Verify `DATABASE_URL` format is correct
- Check Supabase connection from Railway

**Build Fails?**
- Check Railway/Vercel logs
- Ensure all dependencies are in `requirements.txt` (backend) or `package.json` (frontend)

## 📋 Minimum Required Variables

**Backend (Minimum):**
- `DATABASE_URL`
- `OPENROUTER_API_KEY`
- `CORS_ORIGINS`

**Frontend (Minimum):**
- `NEXT_PUBLIC_API_URL`

Everything else can be added later as needed!

