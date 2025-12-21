# OHLCV Data Collection Architecture

## Overview

This system collects price data from Switchboard oracles and aggregates it into OHLCV (Open, High, Low, Close, Volume) candles for technical analysis.

## The Challenge

**Switchboard provides spot prices, not OHLCV data.**

Switchboard gives us:
- Current price at a timestamp
- Single data point per query

We need:
- OHLCV candles (aggregated price data over time periods)
- Historical data for technical indicators

## Solution Architecture

### 1. Data Collection Layer

**Component**: `OHLCVCollector` (`app/services/ohlcv_collector.py`)

**Strategy**:
1. Poll Switchboard every N seconds (configurable, default: 10 seconds)
2. Store every price update as a "tick" in `price_ticks` table
3. Aggregate ticks into OHLCV candles (1m, 5m, 15m, 1h, 4h, 1d)
4. Store candles in `ohlcv_candles` table

**Flow**:
```
Switchboard → Price Tick → Database → OHLCV Aggregation → Candles → Technical Indicators
```

### 2. Database Schema

**Tables**:

1. **`token_pairs`**: Registered token pairs to monitor
   - Tracks which pairs we're collecting data for
   - Links to Switchboard feed IDs

2. **`price_ticks`**: Raw price data from Switchboard
   - Every price update stored here
   - Source of truth for historical prices
   - Used to build OHLCV candles

3. **`ohlcv_candles`**: Aggregated price candles
   - Open, High, Low, Close prices
   - Volume (if available)
   - Multiple timeframes (1m, 5m, 15m, 1h, 4h, 1d)

4. **`technical_indicators`**: Computed indicators
   - SMA, RSI, MACD, etc.
   - Computed from OHLCV candles

### 3. How OHLCV Aggregation Works

**Example**: Building a 1-minute candle

1. Collect price ticks every 10 seconds:
   ```
   10:00:00 → $100.50
   10:00:10 → $100.75
   10:00:20 → $100.60
   10:00:30 → $100.80
   10:00:40 → $100.70
   10:00:50 → $100.65
   ```

2. Aggregate into 1-minute candle:
   ```
   Timestamp: 10:00:00
   Open:  $100.50 (first price)
   High:  $100.80 (highest price)
   Low:   $100.50 (lowest price)
   Close: $100.65 (last price)
   Volume: 0 (if not available from Switchboard)
   ```

3. Store in `ohlcv_candles` table

### 4. API Endpoints

**Token Pair Management**:
- `POST /ohlcv/register` - Register a new token pair
- `GET /ohlcv/pairs` - List all registered pairs

**Collection Control**:
- `POST /ohlcv/start` - Start data collection
- `POST /ohlcv/stop` - Stop data collection
- `GET /ohlcv/status` - Check collection status

**Data Retrieval**:
- `GET /ohlcv/candles/{token_pair_id}` - Get OHLCV candles

### 5. Usage Example

**Step 1: Register a token pair**
```bash
curl -X POST http://localhost:8000/ohlcv/register \
  -H "Content-Type: application/json" \
  -d '{
    "token_a_address": "0x...",
    "token_b_address": "0x...",
    "switchboard_feed_id": "0x...",
    "token_a_symbol": "USDC",
    "token_b_symbol": "MOVE"
  }'
```

**Step 2: Collection starts automatically** (if `AUTO_START_OHLCV=true`)

**Step 3: Query candles**
```bash
curl http://localhost:8000/ohlcv/candles/{token_pair_id}?timeframe=1m&limit=100
```

## Configuration

**Environment Variables** (in `.env`):
```bash
# Auto-start OHLCV collection on server start
AUTO_START_OHLCV=true

# How often to poll Switchboard (seconds)
OHLCV_POLL_INTERVAL_SECONDS=10
```

## Technical Details

### Polling Strategy

- **Frequency**: Configurable (default: 10 seconds)
- **Why 10 seconds?**: Balance between data freshness and API rate limits
- **Aggregation**: Happens automatically after each price tick is stored

### Timeframe Support

- `1m` - 1 minute candles
- `5m` - 5 minute candles
- `15m` - 15 minute candles
- `1h` - 1 hour candles
- `4h` - 4 hour candles
- `1d` - Daily candles

Higher timeframes are aggregated from lower timeframes (e.g., 5m from 1m).

### Volume Data

**Current Limitation**: Switchboard doesn't provide volume data directly.

**Solutions**:
1. Query DEX (Uniswap) for volume data
2. Use trade count as proxy (stored in `trade_count` field)
3. Integrate with DEX subgraph/API for volume

## Next Steps

### 1. Volume Integration
- Query Uniswap/DEX for volume data
- Merge with price data when aggregating candles

### 2. Technical Indicators
- Implement indicator computation service
- Calculate SMA, EMA, RSI, MACD, etc.
- Store in `technical_indicators` table

### 3. Historical Data Backfill
- Query Switchboard API for historical prices (if available)
- Backfill missing candles
- Handle gaps in data

### 4. Real-time Updates
- WebSocket support for live price updates
- Push notifications for significant price changes

## Database Setup

Run the schema:
```bash
psql $DATABASE_URL -f supabase/ohlcv_schema.sql
```

Or via Supabase dashboard SQL editor.

## Monitoring

Check collection status:
```bash
curl http://localhost:8000/ohlcv/status
```

Check database:
```sql
-- View active token pairs
SELECT * FROM token_pairs WHERE is_active = TRUE;

-- View recent price ticks
SELECT * FROM price_ticks ORDER BY timestamp DESC LIMIT 10;

-- View recent candles
SELECT * FROM ohlcv_candles ORDER BY timestamp DESC LIMIT 10;
```

## Performance Considerations

1. **Indexing**: All tables have proper indexes for fast queries
2. **Partitioning**: Consider partitioning `price_ticks` by date for large datasets
3. **Retention**: Implement data retention policies (e.g., keep ticks for 30 days, candles forever)
4. **Batch Processing**: Aggregate multiple timeframes in parallel

## Error Handling

- Collection continues even if one pair fails
- Failed price fetches are logged but don't stop collection
- Database errors are caught and logged
- Collection can be restarted via API

