# AI Trading Agent

## Overview
An AI-powered trading agent application built for Movement Network. This is a monorepo with a Next.js frontend and FastAPI Python backend.

## Project Architecture

### Frontend (Next.js 15)
- Location: `frontend/`
- Port: 5000
- Framework: Next.js with React 19, TypeScript, Tailwind CSS
- Key features: Wallet integration (Aptos, Privy), AI trading dashboard

### Backend (FastAPI)
- Location: `backend/`
- Port: 8000
- Framework: FastAPI with Python 3.11
- Services: CoinGecko API, Supabase, Sentiment Analysis, OHLCV data

## Running the Application

### Frontend Only (default workflow)
```bash
pnpm --filter frontend dev
```

### Backend Only
```bash
cd backend && uvicorn app.main:app --reload --host localhost --port 8000
```

## Environment Variables

### Frontend
- `NEXT_PUBLIC_PRIVY_APP_ID` - Privy authentication app ID (optional - app works without it)

### Backend
- `DATABASE_URL` - PostgreSQL connection string
- `COINGECKO_PRO_API_KEY` - CoinGecko API key
- `OPENROUTER_API_KEY` - OpenRouter LLM API key
- `GROK_API_KEY` - Grok AI for sentiment analysis
- `PRIVY_APP_ID`, `PRIVY_APP_SECRET` - Privy authentication
- `AUTONOMOUS_WALLET_ENCRYPTION_KEY` - For encrypted wallet storage

## Package Manager
- Uses pnpm with workspaces
- Node.js 18+ required
- Python 3.11 for backend

## Recent Changes
- Configured frontend to run on port 5000 for Replit compatibility
- Made Privy provider optional to allow app to run without API key
- Updated next.config.ts with proper turbopack configuration
- Implemented complete cyberpunk finance UI redesign per UI_DESIGN_SPECIFICATION.md
- Created new components: LandingPage, Dashboard, ActivityFeed, MarketOverview
- Redesigned Header with glass morphism and gradient effects
- Updated globals.css with cyberpunk color scheme (Deep Space Black #0A0E17, Electric Indigo #6366F1)
- Fixed Tailwind 4 compatibility by using explicit class names instead of dynamic interpolation
