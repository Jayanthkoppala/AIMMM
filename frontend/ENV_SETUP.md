# Frontend Environment Variables Setup

## How to Get Your Railway Backend API URL

1. **Deploy your backend to Railway** (if not already done)
   - Go to [railway.app](https://railway.app)
   - Create a new project and deploy from your GitHub repo
   - Railway will automatically detect and deploy your backend

2. **Find your backend URL**
   - In Railway dashboard, go to your backend service
   - Click on the service to view details
   - Look for the **"Public Domain"** or **"URL"** section
   - It will look like: `https://your-app-name.railway.app`
   - **This is your backend API endpoint!**

3. **Test the backend**
   - Visit: `https://your-app-name.railway.app/health`
   - You should see: `{"status":"ok"}`

## Frontend .env.local File

Create a file named `.env.local` in the `frontend/` directory with the following content:

```bash
# Backend API URL (REQUIRED for production)
# Get this from Railway dashboard after deploying backend
NEXT_PUBLIC_API_URL=https://your-backend.railway.app

# Privy Authentication (OPTIONAL)
# Get from https://dashboard.privy.io
NEXT_PUBLIC_PRIVY_APP_ID=your_privy_app_id

# Default Token Addresses (OPTIONAL)
# These are used as defaults in the UI
NEXT_PUBLIC_TOKEN_A_ADDRESS=0x...
NEXT_PUBLIC_TOKEN_B_ADDRESS=0x...

# Switchboard Feeds (OPTIONAL)
# Comma-separated list of Switchboard feed IDs
NEXT_PUBLIC_SWITCHBOARD_FEEDS=
```

## Quick Setup Steps

1. **Create the file:**
   ```bash
   cd frontend
   touch .env.local
   ```

2. **Add your Railway backend URL:**
   ```bash
   echo "NEXT_PUBLIC_API_URL=https://your-backend.railway.app" > .env.local
   ```

3. **Or manually edit `.env.local`** and add:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   ```

## Environment Variables Explained

### Required

- **`NEXT_PUBLIC_API_URL`** - Your Railway backend URL
  - Format: `https://your-app-name.railway.app`
  - **Leave empty for local development** - Next.js will proxy to `localhost:8000`
  - **Required for production** deployments

### Optional

- **`NEXT_PUBLIC_PRIVY_APP_ID`** - Privy App ID for social login
  - Get from: https://dashboard.privy.io
  - If not set, Privy authentication will be disabled

- **`NEXT_PUBLIC_TOKEN_A_ADDRESS`** - Default Token A address
  - Used as default in token selection UI

- **`NEXT_PUBLIC_TOKEN_B_ADDRESS`** - Default Token B address
  - Used as default in token selection UI

- **`NEXT_PUBLIC_SWITCHBOARD_FEEDS`** - Switchboard feed IDs
  - Comma-separated list

## Local Development

For local development, you can:
1. **Leave `NEXT_PUBLIC_API_URL` empty** - Next.js will automatically proxy `/api/*` to `http://localhost:8000/*`
2. **Or set it to** `http://localhost:8000` if you want to call the backend directly

## Production Deployment (Vercel/Netlify)

When deploying to Vercel or Netlify:
1. Go to your project settings
2. Navigate to "Environment Variables"
3. Add `NEXT_PUBLIC_API_URL` with your Railway backend URL
4. Redeploy your frontend

## Example .env.local

```bash
# Minimum required for production
NEXT_PUBLIC_API_URL=https://aimmm-backend.railway.app

# Optional: Add these as needed
NEXT_PUBLIC_PRIVY_APP_ID=cmjeh1f4z02eajs0cq5ok6k35
```

## Troubleshooting

**Can't find Railway URL?**
- Check Railway dashboard → Your Service → Settings → Domains
- Or check the "Deployments" tab for the public URL

**API calls failing?**
- Verify `NEXT_PUBLIC_API_URL` is set correctly (no trailing slash)
- Check backend is running: visit `https://your-backend.railway.app/health`
- Check CORS settings in backend (should include your frontend URL)

**Local development not working?**
- Make sure backend is running on `localhost:8000`
- Check browser console for errors
- Verify Next.js rewrites are working (check `next.config.ts`)

