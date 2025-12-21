# Smart Contracts

Move smart contracts for AI Trading Agent.

## Setup

1. Install Movement CLI (if not already installed)

2. Configure `Move.toml` with your address

3. Compile contracts:
```bash
movement move compile
```

4. Run tests:
```bash
movement move test
```

## Contracts

- `agent_executor.move` - Main agent execution contract that integrates with Uniswap V2

## Deployment

1. Deploy Uniswap V2 factory and pools first (if not already deployed)

2. Deploy agent executor:
```bash
movement move publish --profile your-profile
```

3. Initialize the contract:
```bash
movement move run --function-id YOUR_ADDRESS::agent_executor::initialize
```

