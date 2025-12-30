# Optimization & Enhancement Plan

Based on the analysis of execution logs, here are the recommended updates and optimizations to improve the system's performance and reliability.

## 1. Fix Data Logging (COMPLETED)

**Issue**: Execution logs were not storing `trade_result` and `market_data` correctly in the database.
**Fix Applied**: 
- Updated `trading_graph.py` to return `market_data` and `trade_result`.
- Updated `strategy_executor.py` to extract these values correctly and pass them to the logging function.
- Re-enabled statistics calculation after execution.

## 2. Reduce Execution Latency (CRITICAL)

**Observation**: `deepseek/deepseek-r1` model calls are taking **60-80 seconds**.
- 09:45:25 -> 09:46:20 (55s)
- 09:47:43 -> 09:49:02 (79s)
- 09:49:02 -> 09:49:34 (32s)

**Recommendations**:
1. **Switch Model**: Consider using faster models for routine analysis:
   - `openai/gpt-4o` (typically < 10s)
   - `anthropic/claude-3-haiku` (very fast, good for structured tasks)
   - `meta-llama/llama-3-70b` (good balance)
2. **Optimize Prompts**: Reduce prompt size by summarizing OHLCV data (e.g., only last 24h + key pivots instead of full raw data).

## 3. Fix Data Availability for Indicators

**Observation**: `WARNING - Insufficient data for indicator calculation: 199 rows (need 200)`
- The gap filling logic fetches missing data but doesn't ensure *total* history meets the minimum required for indicators (e.g., EMA-200 needs 200+ candles).

**Recommendations**:
1. **Minimum History Fetch**: Update `ohlcv_service` to ensure that if total candles < 200, it fetches more historical data, not just the recent gap.
2. **Warmup Routine**: Implement a "warmup" phase for new strategies that pre-fetches 300+ candles before the first execution attempt.

## 4. Optimize Data Fetching

**Observation**: `Gap detected... Filling gap...` takes time during execution.
- 09:49:35 -> 09:49:42 (~7s) to fill gaps.

**Recommendations**:
1. **Background Polling**: Move OHLCV fetching to a separate background service that runs every minute for all active pools.
2. **Decoupled Execution**: Strategy execution should read *existing* data from DB (which is kept fresh by background workers) rather than fetching on-demand. This would make the "Market Data Agent" almost instant.

## 5. User Interface Enhancements

1. **Live Status**: Show "Gathering Data", "Analyzing", "Decision Pending" states in the frontend based on the new `agent_path` updates.
2. **Reasoning Display**: The `reasoning` field from `DecisionAgent` is rich and should be prominently displayed to explain "HOLD" decisions.

## 6. Token Handling Logic

**Observation**: Logs show `[Market Data Gathering] Pool info retrieved... Trading token: WETH.e`.
- The logic correctly identifies the non-stablecoin token. This is working well.

## Summary of Immediate Actions Taken

- ✅ **Fixed**: Database logging for execution results.
- ✅ **Fixed**: Statistics calculation restoration.
- ✅ **Fixed**: Data flow from LangGraph to Executor.

## Next Steps

1. **Monitor** the next few executions to verify DB rows are created.
2. **Evaluate** model performance and consider switching if latency remains high.
3. **Refine** the OHLCV fetching logic to prevent "insufficient data" warnings.

