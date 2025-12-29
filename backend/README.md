# Backend API

FastAPI backend for AI Trading Agent application.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Configure environment variables in `.env`

4. Run development server:
```bash
uvicorn app.main:app --reload
```

## Environment Variables

See `.env.example` for all required environment variables.

## API Endpoints

- `GET /health` - Health check
- `POST /agent/run` - Run AI trading agent
- `POST /x402/verify` - Verify x402 payment

## Development

The backend uses FastAPI with async/await patterns. All external API calls (OpenRouter, CoinGecko) are async.

## Architecture

- **CoinGecko Integration**: Fetches pre-aggregated OHLCV candles on-demand (no background polling)
- **Supabase**: User sessions, agent execution history, payment records
- **Mosaic DEX**: Swap execution on Movement Network
- **OpenRouter**: LLM-powered trading decisions

