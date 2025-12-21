# AI Trading Agent Hackathon App

A production-ready hackathon application featuring AI trading agents on Movement Network. The system integrates Switchboard oracles, Uniswap V2 DEX, x402 payments, and OpenRouter LLM inference.

## Architecture

- **Smart Contracts**: Agent execution contract integrating with Uniswap V2 pools
- **Backend (FastAPI)**: Agent orchestration, LLM reasoning, oracle data fetching, x402 payment handling
- **Frontend (Next.js)**: User interface for agent execution, wallet connection, payment flow, trade visualization
- **Database (Supabase)**: User sessions, agent execution history, payment records

## Quick Start

### Prerequisites

- Node.js 18+
- pnpm 8+
- Python 3.10+
- Movement CLI
- Supabase account

### Installation

1. **Install root dependencies:**
   ```bash
   pnpm install
   ```

2. **Set up contracts:**
   ```bash
   cd contracts
   # Configure Move.toml with dependencies
   movement move compile
   ```

3. **Configure backend:**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your credentials
   pip install -r requirements.txt
   ```

4. **Configure frontend:**
   ```bash
   cd frontend
   cp .env.local.example .env.local
   # Edit .env.local with your credentials
   pnpm install
   ```

### Development

Run all services concurrently:
```bash
pnpm dev
```

Or run individually:
```bash
pnpm dev:frontend  # Frontend on :3000
pnpm dev:backend   # Backend on :8000
```

### Project Structure

```
ai-trading-agent/
├── contracts/          # Move smart contracts
├── backend/           # FastAPI backend
└── frontend/          # Next.js frontend
```

## Environment Variables

See individual package READMEs for detailed environment variable documentation:
- `backend/.env.example`
- `frontend/.env.local.example`

## License

MIT

