# Workflow Execution with Two Services

## ✅ How Workflows Work with API + Worker Split

### **Request-Triggered Workflows** (API Service - `RUN_MODE=api`)

These workflows run **on-demand** when users make API calls:

1. **`POST /agent/run`** → Triggers LangGraph trading workflow
   - ✅ Works in API mode
   - Executes synchronously/asynchronously
   - Returns result to user

2. **`POST /strategies/{id}/execute`** → Manually execute strategy
   - ✅ Works in API mode
   - Triggers LangGraph workflow or legacy execution
   - Returns execution result

3. **Any API endpoint that triggers workflows**
   - ✅ All work in API mode
   - These are **request-driven**, not scheduled

### **Background Scheduled Workflows** (Worker Service - `RUN_MODE=worker`)

These workflows run **automatically** on a schedule:

1. **Strategy Scheduler** → Executes active strategies every minute
   - ❌ Only works in worker mode
   - Checks database for active strategies
   - Automatically executes based on `execution_interval`

2. **Autonomous Trading Scheduler** → Executes trades every 5 minutes
   - ❌ Only works in worker mode
   - Monitors market conditions
   - Executes trades for users with autonomous mode enabled

3. **OHLCV Scheduler** → Fetches market data periodically
   - ❌ Only works in worker mode
   - Populates database for API endpoints

4. **Sentiment Scheduler** → Analyzes sentiment every 24 hours
   - ❌ Only works in worker mode
   - Updates sentiment data in database

---

## 🎯 Summary

| Workflow Type | API Service | Worker Service | Notes |
|--------------|-------------|----------------|-------|
| **Manual execution** (`POST /agent/run`) | ✅ Yes | ✅ Yes | Works in both |
| **Manual strategy execution** (`POST /strategies/{id}/execute`) | ✅ Yes | ✅ Yes | Works in both |
| **Automatic strategy execution** (every minute) | ❌ No | ✅ Yes | Only worker |
| **Automatic autonomous trading** (every 5 min) | ❌ No | ✅ Yes | Only worker |
| **OHLCV data fetching** (periodic) | ❌ No | ✅ Yes | Only worker |
| **Sentiment analysis** (every 24h) | ❌ No | ✅ Yes | Only worker |

---

## 🔍 What This Means

### ✅ **Workflows DO Run** with two services:

1. **User clicks "Run Agent"** → API service executes workflow → ✅ Works
2. **User clicks "Execute Strategy"** → API service executes workflow → ✅ Works
3. **Strategy set to auto-execute** → Worker service executes automatically → ✅ Works (if worker running)

### ❌ **Workflows DON'T Run** if:

1. **Only API service running** → Automatic scheduled executions won't happen
   - Strategies won't auto-execute
   - Autonomous trading won't work
   - Market data won't be fetched automatically

2. **Only Worker service running** → Manual API calls won't work
   - Users can't trigger workflows via API
   - Frontend can't execute strategies on-demand

---

## 🚀 **Solution: You Need BOTH Services**

### **API Service** (`RUN_MODE=api`):
- Handles HTTP requests
- Executes workflows **on-demand** when users call APIs
- Fast response times (<200ms for reads)
- No background schedulers

### **Worker Service** (`RUN_MODE=worker`):
- Runs background schedulers
- Executes workflows **automatically** on schedule
- No HTTP traffic (but routes still available)
- Populates database for API service

---

## 📝 Example Scenarios

### Scenario 1: User Manually Executes Strategy
```
User → Frontend → POST /strategies/{id}/execute → API Service → Workflow Executes → ✅ Works
```

### Scenario 2: Strategy Auto-Executes Every 5 Minutes
```
Worker Service → Strategy Scheduler → Checks DB → Executes Strategy → ✅ Works
```

### Scenario 3: User Runs Agent
```
User → Frontend → POST /agent/run → API Service → LangGraph Workflow → ✅ Works
```

---

## ⚠️ **Important Notes**

1. **Both services share the same database** → They can coordinate
2. **API service can trigger workflows** → Manual execution works
3. **Worker service triggers workflows automatically** → Scheduled execution works
4. **You need BOTH for full functionality** → Manual + Automatic

---

## ✅ **Current Status**

Your code is **correctly configured**:
- API service handles request-triggered workflows ✅
- Worker service handles scheduled workflows ✅
- Both can execute the same workflows ✅
- They just trigger differently (manual vs automatic)

---

**Bottom line**: Workflows **DO run** with two services. Manual execution works in API mode, automatic execution works in worker mode. You need both services for full functionality.

