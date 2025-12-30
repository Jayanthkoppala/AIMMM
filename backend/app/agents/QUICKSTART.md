# Quick Start Guide - LangGraph Trading Agents

Get up and running with the LangGraph agent system in 5 minutes.

---

## 1. Install Dependencies (1 minute)

```bash
cd backend
pip install -r requirements.txt
```

This installs:
- `langgraph>=0.2.0`
- `langchain-core>=0.3.0`

---

## 2. Enable Feature Flag (30 seconds)

Add to your `.env` file:

```bash
USE_LANGGRAPH_AGENTS=true
```

Or set in `config.py`:

```python
USE_LANGGRAPH_AGENTS: bool = True
```

---

## 3. Verify Installation (1 minute)

Test that agents can be imported:

```bash
python -c "from app.agents import trading_graph; print('✓ LangGraph agents ready!')"
```

Expected output:
```
✓ LangGraph agents ready!
```

---

## 4. Run Your First Strategy (2 minutes)

### Option A: Use Existing API

No code changes needed! Just execute a strategy:

```python
from app.services.strategy_executor import strategy_executor

result = await strategy_executor.execute_strategy(
    strategy_id="your-strategy-id",
    user_id="your-user-id",
    execution_mode="analysis"
)

print(f"Decision: {result['decision']['action']}")
print(f"Agent Path: {' -> '.join(result['agent_path'])}")
```

### Option B: Direct Graph Execution

```python
from app.agents.trading_graph import execute_trading_strategy

result = await execute_trading_strategy(
    strategy_id="your-strategy-id",
    user_id="your-user-id",
    strategy_config={
        "agent_configs": {...},
        "paper_trading_config": {
            "initial_capital_usdc": 1000,
            "capital_per_trade": 100,
            "max_concurrent_positions": 5
        }
    },
    execution_mode="analysis",
    pool_id=1
)
```

---

## 5. Verify It's Working

Check the response for agent-specific fields:

```python
# New fields from LangGraph system:
result['agent_path']  # ['MarketDataAgent', 'PortfolioAgent', ...]
result['errors']      # [] (empty if no errors)
result['duration']    # Execution time in seconds

# Existing fields (unchanged):
result['status']           # 'success' or 'error'
result['decision']         # LLM decision
result['trading_state']    # Portfolio info
result['trade_executed']   # Boolean
```

Example output:

```json
{
  "status": "success",
  "decision": {
    "action": "BUY",
    "confidence": 0.85,
    "token": "MOVE",
    "amount_usdc": 100,
    "reasoning": "Strong bullish signals..."
  },
  "trading_state": {
    "total_portfolio_value": 1050.00,
    "unrealized_pnl": 50.00,
    "active_positions": 1
  },
  "trade_executed": true,
  "duration": 3.2,
  "agent_path": [
    "MarketDataAgent",
    "PortfolioAgent",
    "MonitoringAgent",
    "RiskAgent",
    "AnalysisAgent",
    "DecisionAgent",
    "RiskAgent",
    "ExecutionAgent"
  ],
  "errors": []
}
```

---

## 6. Test Different Scenarios

### Scenario 1: HOLD Decision (Risk Blocked)

```python
# Strategy with insufficient capital
result = await execute_trading_strategy(...)

# Expected:
# - agent_path will show RiskAgent blocked it
# - decision['action'] = 'HOLD'
# - risk_warnings will explain why
```

### Scenario 2: Exit Position (Stop-Loss)

```python
# Strategy with position that hit stop-loss
result = await execute_trading_strategy(...)

# Expected:
# - MonitoringAgent detects exit signal
# - ExecutionAgent sells position
# - trade_executed = True
```

### Scenario 3: Market Data Retry

```python
# Strategy with incomplete data
result = await execute_trading_strategy(...)

# Expected:
# - MarketDataAgent retries up to 3 times
# - agent_path shows 'MarketDataAgent' multiple times
# - Eventually proceeds with available data
```

---

## Common Commands

### Check Logs

```bash
# View agent activity
tail -f logs/app.log | grep "Agent"

# View specific agent
tail -f logs/app.log | grep "DecisionAgent"

# View execution results
tail -f logs/app.log | grep "TradingGraph"
```

### Test Individual Agent

```python
from app.agents.market_data_agent import market_data_agent
from app.agents.state import create_initial_state

state = create_initial_state(
    strategy_id="test",
    user_id="test",
    strategy_config={...},
    pool_id=1
)

result = await market_data_agent.process(state)
print(result)
```

### Get Agent Metrics

```python
from app.agents.metrics import agent_metrics

# After some executions
agent_metrics.log_summary()

# Get specific agent metrics
metrics = agent_metrics.get_metrics("DecisionAgent")
print(f"Avg time: {metrics['avg_time']:.3f}s")
print(f"Success rate: {metrics['success_rate']:.1f}%")
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'langgraph'"

**Solution:**
```bash
pip install langgraph>=0.2.0 langchain-core>=0.3.0
```

### Issue: Still using legacy system

**Check:**
```python
from app.config import settings
print(settings.USE_LANGGRAPH_AGENTS)  # Should be True
```

**Fix:** Set `USE_LANGGRAPH_AGENTS=true` in `.env`

### Issue: Agent path is empty

**Cause:** Legacy system is being used

**Solution:** Verify feature flag is enabled and restart application

### Issue: LLM errors

**Check:**
1. OpenRouter API key is set
2. LLM model in strategy config is valid
3. Market data is being gathered

**Debug:**
```python
result = await execute_trading_strategy(...)
if result['status'] == 'error':
    print(f"Error: {result['error']}")
    print(f"Agent path: {result['agent_path']}")
```

---

## Next Steps

### Learn More

1. **Full Documentation:** [README.md](README.md)
2. **Migration Guide:** [MIGRATION.md](MIGRATION.md)
3. **Workflow Diagram:** [WORKFLOW_DIAGRAM.txt](WORKFLOW_DIAGRAM.txt)
4. **Implementation Details:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

### Customize Agents

Each agent can be customized:

```python
# Example: Customize risk thresholds
from app.agents.risk_agent import risk_agent

# Agents are configurable through strategy_config
strategy_config = {
    "paper_trading_config": {
        "max_concurrent_positions": 3,  # Lower limit
        "capital_per_trade": 50,         # Smaller trades
        "stop_loss_pct": 0.03,           # Tighter stop-loss
    }
}
```

### Add Custom Agent

```python
# 1. Create new agent
from app.agents.base_agent import BaseAgent

class MyCustomAgent(BaseAgent):
    def __init__(self):
        super().__init__("MyCustomAgent")
    
    async def process(self, state):
        # Your logic here
        return {"custom_field": "value"}

# 2. Add to trading_graph.py
from app.agents.my_custom_agent import my_custom_agent

workflow.add_node("custom", AgentNode(my_custom_agent))
workflow.add_edge("analysis", "custom")
workflow.add_edge("custom", "decision")
```

### Run Tests

```bash
# Unit tests (when available)
pytest backend/tests/agents/

# Integration test
python -c "
from app.agents.trading_graph import trading_graph
from app.agents.state import create_initial_state

state = create_initial_state(...)
result = await trading_graph.ainvoke(state)
print('✓ Integration test passed!')
"
```

---

## Performance Tips

1. **Enable Caching:** LLM responses can be cached for similar conditions
2. **Parallel Fetching:** Market data sources can be fetched in parallel
3. **Database Pooling:** Connection pooling improves query performance
4. **Pre-compute Indicators:** Calculate technical indicators in background

---

## Support

Need help?

1. Check logs: `tail -f logs/app.log | grep "Agent"`
2. Review `result['errors']` for error messages
3. Check `result['agent_path']` to see which agents ran
4. Verify feature flag: `USE_LANGGRAPH_AGENTS=true`
5. Ensure all dependencies installed: `pip install -r requirements.txt`

---

## Summary

You've successfully:
- ✅ Installed LangGraph dependencies
- ✅ Enabled the agent system
- ✅ Run your first strategy with agents
- ✅ Verified agent execution

The LangGraph agent system is now handling your trading strategies with improved modularity, error handling, and observability!

---

**Time to Production:** ~5 minutes  
**Breaking Changes:** None  
**Rollback:** Set `USE_LANGGRAPH_AGENTS=false`

