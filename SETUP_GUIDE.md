# Setup Guide

Complete setup instructions for the AI Trading Agent Hackathon App.

## Prerequisites

- Node.js 18+
- pnpm 8+
- Python 3.10+
- Movement CLI
- Supabase account
- OpenRouter API key
- Movement testnet wallet with funds

## Step 1: Install Root Dependencies

```bash
cd ai-trading-agent
pnpm install
```

## Step 2: Set Up Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials:
# - MOVEMENT_RPC
# - OPENROUTER_API_KEY
# - SUPABASE_URL and SUPABASE_KEY
# - X402_RECEIVER_ADDRESS
# - Token addresses
# - Switchboard feed IDs
```

## Step 3: Set Up Frontend

```bash
cd ../frontend

# Install dependencies
pnpm install

# Copy and configure environment
cp .env.local.example .env.local
# Edit .env.local with:
# - NEXT_PUBLIC_API_URL (default: http://localhost:8000)
# - NEXT_PUBLIC_PRIVY_APP_ID
# - Token addresses
# - Switchboard feed IDs
```

## Step 4: Set Up Supabase

1. Create a new Supabase project
2. Run the SQL schema:
   ```bash
   # In Supabase SQL Editor, paste contents of:
   cat supabase/schema.sql
   ```
3. Update RLS policies as needed
4. Copy Supabase URL and anon key to backend `.env`

## Step 5: Deploy Smart Contracts

```bash
cd contracts

# Update Move.toml with your address
# Edit [addresses] section

# Compile contracts
movement move compile

# Deploy (after setting up Movement CLI profile)
movement move publish --profile your-profile

# Initialize agent executor
movement move run \
  --function-id YOUR_ADDRESS::agent_executor::initialize \
  --profile your-profile
```

## Step 6: Run Development Servers

From the root directory:

```bash
# Run both frontend and backend
pnpm dev

# Or run individually:
pnpm dev:backend   # Backend on :8000
pnpm dev:frontend  # Frontend on :3000
```

## Step 7: Test the Application

1. Open http://localhost:3000
2. Connect your wallet (Privy or native)
3. Configure token pair and feed
4. Run agent execution
5. Approve payment when prompted
6. View results and trade history

## Environment Variables Reference

### Backend (.env)
- `MOVEMENT_RPC` - Movement testnet RPC URL
- `SWITCHBOARD_FEED_IDS` - Comma-separated feed IDs
- `UNISWAP_FACTORY_ADDRESS` - Factory contract address
- `TOKEN_A_ADDRESS`, `TOKEN_B_ADDRESS` - Token addresses
- `OPENROUTER_API_KEY` - OpenRouter API key
- `OPENROUTER_MODEL` - Model (default: openai/gpt-4o-mini)
- `X402_RECEIVER_ADDRESS` - Payment recipient address
- `X402_FACILITATOR_URL` - x402 facilitator URL
- `BASE_AGENT_COST_USDC` - Base cost in USDC
- `SUPABASE_URL`, `SUPABASE_KEY` - Supabase credentials
- `AGENT_EXECUTOR_ADDRESS` - Agent executor contract address

### Frontend (.env.local)
- `NEXT_PUBLIC_API_URL` - Backend API URL
- `NEXT_PUBLIC_PRIVY_APP_ID` - Privy App ID
- `NEXT_PUBLIC_TOKEN_A_ADDRESS` - Default Token A
- `NEXT_PUBLIC_TOKEN_B_ADDRESS` - Default Token B
- `NEXT_PUBLIC_SWITCHBOARD_FEEDS` - Comma-separated feed IDs

## Troubleshooting

### Backend won't start
- Check Python version (3.10+)
- Verify all dependencies installed
- Check .env file exists and is configured

### Frontend won't start
- Check Node.js version (18+)
- Run `pnpm install` again
- Check .env.local exists

### Wallet connection issues
- Verify Privy App ID is correct
- Check Movement network configuration
- Ensure wallet is on Movement testnet

### Payment issues
- Verify x402 facilitator URL is correct
- Check receiver address is valid
- Ensure wallet has sufficient funds

## Next Steps

- Integrate real Switchboard feeds
- Complete Movement SDK integration for swaps
- Add comprehensive error handling
- Implement trade history fetching from Supabase
- Add unit and integration tests

