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
- **Terminal/Developer UI Redesign** - Complete aesthetic overhaul:
  - Color palette: Base Black (#0a0a0a), Terminal Green (#00ff00)
  - Monospace fonts: JetBrains Mono, IBM Plex Mono
  - Terminal window chrome with red/yellow/green dots
  - Blinking cursor animation, scanline effect
  - Command-line style buttons (./login, ./execute, cat README.md)
  - Glow effects on text and borders
  - Code execution simulation on landing page
  - Log-style activity feed formatting
- Fixed login redirect to check both Privy authentication and wallet connection
- **MyStrategies Page Redesign** (Dec 2024):
  - Strategy Dock at TOP: Strategy tabs, selected strategy info (name, description, model, interval, mode), Start/Pause button
  - 2/3 - 1/3 Layout: Execution Terminal (left) + Trading Metrics (right)
  - Execution logs as PRIMARY focus with lazy loading (10 logs at a time, loads more on scroll)
  - Filter buttons: [ALL] [BUYS] [SELLS] [HOLDS]
  - Trading metrics panel: Portfolio value, P&L, ROI, Statistics (win rate, Sharpe, drawdown), Active positions
  - Removed Execute button - only Start/Pause remains
