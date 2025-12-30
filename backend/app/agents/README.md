# LangGraph Trading Agents

This directory contains the LangGraph-based agent system for paper trading execution.

## Architecture Overview

The system uses **7 specialized agents** that work together in a stateful workflow orchestrated by LangGraph:

1. **Market Data Agent** - Gathers OHLCV, technical indicators, and sentiment
2. **Portfolio Agent** - Tracks portfolio state and calculates P&L
3. **Monitoring Agent** - Checks for stop-loss/take-profit triggers
4. **Risk Agent** - Enforces safety rules and validates trades
5. **Analysis Agent** - Analyzes market data and generates insights
6. **Decision Agent** - Makes LLM-based trading decisions
7. **Execution Agent** - Executes trades and manages order flow

## Workflow

```
Start → Market Data → Portfolio → Monitoring
                                      ↓
                            (Exit positions?) 
                                 ↙        ↘
                           Execution    Risk Check
                                            ↓
                                     (Approved?)
                                       ↙     ↘
                                  Analysis  HOLD
                                      ↓
                                  Decision
                                      ↓
                                Risk Check (final)
                                      ↓
                                 (Approved?)
                                   ↙     ↘
                             Execution  HOLD
                                   ↓
                                  End
```

## Key Features

### 1. **Modularity**
Each agent has a single, well-defined responsibility and can be tested independently.

### 2. **State Management**
LangGraph manages state flow between agents, eliminating manual state passing.

### 3. **Error Recovery**
Built-in retry logic and error handling at each agent level.

### 4. **Decision Refinement**
Decision agent can iterate and refine decisions based on feedback from risk agent.

### 5. **Safety First**
Risk agent acts as a gatekeeper, enforcing position limits, capital requirements, and confidence thresholds.

### 6. **Observability**
Every agent logs its actions, and the agent path is tracked through the workflow.

## Usage

### Enable LangGraph Agents

Set in `.env` or `config.py`:

```python
USE_LANGGRAPH_AGENTS=true
```

### Execution

The system is automatically used when executing strategies through `strategy_executor.py`:

```python
from app.services.strategy_executor import strategy_executor

result = await strategy_executor.execute_strategy(
    strategy_id="...",
    user_id="...",
    execution_mode="analysis"
)
```

### Direct Graph Execution

You can also execute the trading graph directly:

```python
from app.agents.trading_graph import execute_trading_strategy

result = await execute_trading_strategy(
    strategy_id="...",
    user_id="...",
    strategy_config={...},
    execution_mode="analysis"
)
```

## State Schema

The `TradingState` (in `state.py`) contains:

- **Strategy context**: strategy_id, user_id, config, execution_mode
- **Market data**: OHLCV, technical indicators, sentiment
- **Portfolio state**: balances, positions, P&L
- **Analysis**: market insights, trend analysis
- **Decision**: action, confidence, reasoning
- **Risk assessment**: checks, approvals, warnings
- **Execution**: trade results, exit positions
- **Workflow control**: flags for routing decisions
- **Error handling**: errors list, retry count
- **Metadata**: timing, agent path

## Agent Details

### Market Data Agent (`market_data_agent.py`)

**Responsibilities:**
- Fetch OHLCV data from database
- Fetch technical indicators
- Fetch sentiment analysis
- Validate data completeness

**Outputs:**
- `market_data`: Dict with all market information
- `data_complete`: Boolean flag
- `data_errors`: List of errors encountered

### Portfolio Agent (`portfolio_agent.py`)

**Responsibilities:**
- Initialize paper trading balances
- Calculate portfolio value using current prices
- Track active positions
- Calculate P&L metrics

**Outputs:**
- `portfolio_state`: Complete portfolio information
- `active_positions`: List of non-USDC positions
- `usdc_balance`: Available capital
- `total_value`: Total portfolio value

### Monitoring Agent (`monitoring_agent.py`)

**Responsibilities:**
- Monitor open positions
- Check stop-loss triggers
- Check take-profit triggers
- Generate exit signals

**Outputs:**
- `exit_positions`: List of positions to exit
- `should_exit_positions`: Boolean flag

### Risk Agent (`risk_agent.py`)

**Responsibilities:**
- Check position limits
- Validate capital availability
- Enforce confidence thresholds
- Check gas efficiency
- Act as safety gatekeeper

**Outputs:**
- `risk_checks`: Dict of individual checks
- `risk_warnings`: List of warnings
- `risk_approved`: Boolean approval flag

### Analysis Agent (`analysis_agent.py`)

**Responsibilities:**
- Analyze market trends
- Interpret technical indicators
- Assess sentiment signals
- Generate market condition summary

**Outputs:**
- `analysis`: Complete analysis dict
- `trend_analysis`: Trend summary string
- `market_conditions`: Market condition summary

### Decision Agent (`decision_agent.py`)

**Responsibilities:**
- Aggregate all available context
- Call LLM for decision making
- Parse and validate decision
- Handle decision errors

**Outputs:**
- `decision`: Complete decision dict (action, token, amount, confidence, reasoning)
- `action`: Action string (BUY/SELL/HOLD/CLOSE_POSITION)
- `confidence`: Confidence score (0-1)
- `reasoning`: LLM reasoning text

### Execution Agent (`execution_agent.py`)

**Responsibilities:**
- Execute BUY orders (get quote, execute swap)
- Execute SELL orders
- Handle exit positions
- Manage slippage and gas fees
- Validate execution results

**Outputs:**
- `trade_result`: Trade execution result or None
- `should_execute_trade`: Boolean flag

## Configuration

### Feature Flag

```python
# config.py
USE_LANGGRAPH_AGENTS: bool = True  # Enable LangGraph agents
```

### Strategy Config

The strategy config is passed through the workflow and used by various agents:

```python
{
    "agent_configs": {
        "ohlcv": {...},
        "technical": {...},
        "sentiment": {...}
    },
    "paper_trading_config": {
        "initial_capital_usdc": 1000,
        "capital_per_trade": 100,
        "max_concurrent_positions": 5,
        "stop_loss_pct": 0.05,
        "take_profit_pct": 0.10
    },
    "llm_provider": "openai/gpt-4o-mini"
}
```

## Error Handling

### Agent-Level Errors

Each agent catches its own errors and returns error information in state updates:

```python
return {
    'errors': state.get('errors', []) + [f"Agent error: {str(e)}"]
}
```

### Retry Logic

Market data gathering includes retry logic:

```python
def should_retry_market_data(state):
    if not data_complete and retry_count < max_retries:
        return MARKET_DATA  # Retry
    return PORTFOLIO  # Proceed
```

### Fallback Behavior

If errors occur, the system defaults to safe behavior:
- Decision errors → HOLD action
- Risk check failures → HOLD action
- Execution errors → No trade executed

## Testing

### Unit Testing Individual Agents

```python
from app.agents.market_data_agent import market_data_agent
from app.agents.state import create_initial_state

state = create_initial_state(...)
result = await market_data_agent.process(state)
```

### Integration Testing

```python
from app.agents.trading_graph import trading_graph

result = await trading_graph.ainvoke(initial_state)
```

## Monitoring

### Agent Path Tracking

Every execution tracks which agents were involved:

```python
result['agent_path']  # ['MarketDataAgent', 'PortfolioAgent', ...]
```

### Metrics

Use the metrics module to track agent performance:

```python
from app.agents.metrics import agent_metrics

agent_metrics.log_summary()
```

## Migration from Legacy System

The system supports both legacy and LangGraph execution:

1. **Feature flag**: `USE_LANGGRAPH_AGENTS=true` enables new system
2. **Backward compatible**: Old code continues to work
3. **Gradual migration**: Can A/B test or migrate strategies one at a time
4. **Same API**: `strategy_executor.execute_strategy()` works with both

## Performance

### Benchmarks

Typical execution time: **2-5 seconds**
- Market Data: ~0.5s
- Portfolio: ~0.3s
- Monitoring: ~0.2s
- Risk: ~0.1s
- Analysis: ~0.2s
- Decision (LLM): ~1-3s
- Execution: ~0.5s

### Optimization Opportunities

1. **Parallel data fetching** in Market Data Agent
2. **Cache LLM responses** for similar market conditions
3. **Batch database queries** where possible
4. **Pre-compute** technical indicators

## Dependencies

```
langgraph>=0.2.0
langchain-core>=0.3.0
```

## Contributing

When adding new agents or modifying the workflow:

1. Extend `BaseAgent` class
2. Implement `process(state)` method
3. Add agent to `trading_graph.py`
4. Update routing logic if needed
5. Add tests
6. Update this documentation

## Troubleshooting

### Agent Not Executing

Check:
- Feature flag `USE_LANGGRAPH_AGENTS` is enabled
- Strategy config is valid
- Database connection is working
- Pool ID exists in database

### LLM Errors

Check:
- OpenRouter API key is set
- LLM provider in strategy config is valid
- Market data is being gathered successfully

### Execution Not Happening

Check:
- Risk agent is approving the decision
- Confidence threshold is met (>= 0.70)
- Action is BUY/SELL (not HOLD)
- Portfolio has sufficient capital

## Support

For issues or questions:
1. Check logs for agent path and errors
2. Review agent-specific output in state
3. Enable debug logging for detailed agent actions

