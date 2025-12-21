# Frontend

Next.js frontend for AI Trading Agent application.

## Setup

1. Install dependencies:
```bash
pnpm install
```

2. Copy environment file:
```bash
cp .env.local.example .env.local
```

3. Configure environment variables in `.env.local`

4. Run development server:
```bash
pnpm dev
```

## Environment Variables

- `NEXT_PUBLIC_API_URL` - Backend API URL (default: http://localhost:8000)
- `NEXT_PUBLIC_PRIVY_APP_ID` - Privy App ID for social login
- `NEXT_PUBLIC_TOKEN_A_ADDRESS` - Default Token A address
- `NEXT_PUBLIC_TOKEN_B_ADDRESS` - Default Token B address
- `NEXT_PUBLIC_SWITCHBOARD_FEEDS` - Comma-separated Switchboard feed IDs

## Features

- Wallet connection (Privy + Native wallets)
- Agent dashboard with configuration
- Trade history display
- x402 payment integration

