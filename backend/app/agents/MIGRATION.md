# Migration Guide: Legacy to LangGraph Agents

This guide explains how to migrate from the legacy monolithic strategy executor to the new LangGraph agent system.

## Overview

The new LangGraph agent system provides:
- ✅ Better modularity and testability
- ✅ Improved error handling and recovery
- ✅ State management between steps
- ✅ Clear agent responsibilities
- ✅ Decision refinement capabilities
- ✅ Better observability

## Migration Steps

### 1. Install Dependencies

Ensure LangGraph dependencies are installed:

```bash
pip install -r requirements.txt
```

This will install:
- `langgraph>=0.2.0`
- `langchain-core>=0.3.0`

### 2. Enable Feature Flag

Add to your `.env` file or set in config:

```bash
USE_LANGGRAPH_AGENTS=true
```

Or in `config.py`:

```python
USE_LANGGRAPH_AGENTS: bool = True
```

### 3. Test with Existing Strategies

No code changes needed! The existing API works with both systems:

```python
# This works with both legacy and LangGraph systems
result = await strategy_executor.execute_strategy(
    strategy_id="your-strategy-id",
    user_id="your-user-id",
    execution_mode="analysis"
)
```

The system automatically routes to LangGraph when the feature flag is enabled.

### 4. Verify Results

Check that executions are working:

```python
# Response structure remains the same
{
    "status": "success",
    "decision": {
        "action": "BUY",
        "confidence": 0.85,
        "reasoning": "...",
        "token": "MOVE",
        "amount_usdc": 100
    },
    "trading_state": {
        "total_portfolio_value": 1050.00,
        "unrealized_pnl": 50.00,
        ...
    },
    "trade_executed": True,
    "duration": 3.5,
    
    # New fields in LangGraph
    "agent_path": ["MarketDataAgent", "PortfolioAgent", ...],
    "errors": []
}
```

## Comparison: Legacy vs LangGraph

### Legacy System

**Pros:**
- Simple, linear execution
- Well-tested
- No additional dependencies

**Cons:**
- Monolithic structure
- Limited error recovery
- No state management
- Hard to test individual components
- No decision refinement

### LangGraph System

**Pros:**
- Modular agent architecture
- Built-in state management
- Retry and error handling
- Testable components
- Decision refinement support
- Clear agent responsibilities
- Better observability

**Cons:**
- Additional dependencies (LangGraph)
- Slightly more complex architecture
- New system (needs validation)

## A/B Testing

You can run both systems side-by-side for comparison:

```python
# Test with LangGraph
settings.USE_LANGGRAPH_AGENTS = True
result_langgraph = await strategy_executor.execute_strategy(...)

# Test with legacy
settings.USE_LANGGRAPH_AGENTS = False
result_legacy = await strategy_executor.execute_strategy(...)

# Compare results
compare_results(result_langgraph, result_legacy)
```

## Rollback

If you need to rollback to the legacy system:

1. Set feature flag to `false`:
   ```bash
   USE_LANGGRAPH_AGENTS=false
   ```

2. Restart the application

3. All strategies will use the legacy executor

## Monitoring During Migration

### Check Agent Path

New field in responses shows which agents processed the request:

```python
result['agent_path']
# ['MarketDataAgent', 'PortfolioAgent', 'MonitoringAgent', ...]
```

### Check for Errors

```python
if result.get('errors'):
    print("Errors encountered:", result['errors'])
```

### Compare Performance

```python
print(f"Execution time: {result['duration']:.2f}s")
```

## Common Issues

### Issue: "No module named 'langgraph'"

**Solution:** Install dependencies:
```bash
pip install langgraph>=0.2.0 langchain-core>=0.3.0
```

### Issue: Execution takes longer than legacy

**Cause:** LangGraph adds state management overhead

**Solution:** Normal. Typical increase is 0.5-1s for state management. Benefits outweigh the cost.

### Issue: Different decision from legacy

**Cause:** LangGraph includes risk refinement loop

**Solution:** This is expected. LangGraph may catch issues that legacy system missed.

### Issue: Agent path shows errors

**Cause:** An agent encountered an error but continued

**Solution:** Check `result['errors']` for details. System gracefully handles errors.

## Best Practices

### 1. Test in Development First

```python
# Development
USE_LANGGRAPH_AGENTS=true

# Test thoroughly before production
```

### 2. Monitor Initial Executions

Watch logs for agent behavior:

```bash
tail -f logs/strategy_execution.log | grep "Agent"
```

### 3. Gradual Rollout

Enable for a subset of strategies first:

```python
# In strategy_executor.py
if strategy_config.get('use_langgraph', False) or settings.USE_LANGGRAPH_AGENTS:
    return await self._execute_with_langgraph(...)
```

### 4. Compare Metrics

Track success rates, execution times, and P&L:

```python
from app.agents.metrics import agent_metrics

agent_metrics.log_summary()
```

## Feature Parity

Both systems support:

- ✅ Paper trading
- ✅ Live trading
- ✅ Strategy scheduling
- ✅ Portfolio tracking
- ✅ Risk management
- ✅ Stop-loss/take-profit
- ✅ Technical indicators
- ✅ Sentiment analysis
- ✅ LLM decisions

LangGraph adds:

- ✅ Modular agent architecture
- ✅ State management
- ✅ Retry logic
- ✅ Agent path tracking
- ✅ Better error messages
- ✅ Decision refinement

## Timeline Recommendation

**Week 1:** Install dependencies, enable in development
**Week 2:** Test with non-critical strategies
**Week 3:** A/B test with production strategies
**Week 4:** Full rollout if metrics look good

## Support

For issues during migration:

1. Check logs for detailed agent activity
2. Review `result['agent_path']` and `result['errors']`
3. Compare with legacy execution
4. Disable LangGraph if needed: `USE_LANGGRAPH_AGENTS=false`

## Success Criteria

Migration is successful when:

- ✅ All strategies execute without errors
- ✅ Execution time is acceptable (< 10s)
- ✅ Decision quality is equal or better
- ✅ P&L metrics are consistent
- ✅ No unexpected HOLD decisions
- ✅ Risk checks are working properly

## Next Steps

After successful migration:

1. Monitor for a week
2. Compare P&L between systems
3. Gather team feedback
4. Keep legacy code for 1-2 months as backup
5. Eventually remove legacy execution code

## Conclusion

The LangGraph agent system provides significant architectural improvements while maintaining full compatibility with existing code. The migration is low-risk with easy rollback options.

