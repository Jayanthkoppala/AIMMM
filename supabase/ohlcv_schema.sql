-- OHLCV Data Schema for Token Price History
-- This schema stores aggregated price data (candles) from Switchboard feeds

-- Token pairs table (track which pairs we're monitoring)
CREATE TABLE IF NOT EXISTS token_pairs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_a_address TEXT NOT NULL,
    token_b_address TEXT NOT NULL,
    token_a_symbol TEXT,
    token_b_symbol TEXT,
    switchboard_feed_id TEXT NOT NULL,  -- Switchboard aggregator address
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(token_a_address, token_b_address, switchboard_feed_id)
);

-- OHLCV candles table (stores aggregated price data)
CREATE TABLE IF NOT EXISTS ohlcv_candles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_pair_id UUID NOT NULL REFERENCES token_pairs(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    timeframe TEXT NOT NULL CHECK (timeframe IN ('1m', '5m', '15m', '1h', '4h', '1d')),
    open_price NUMERIC NOT NULL,
    high_price NUMERIC NOT NULL,
    low_price NUMERIC NOT NULL,
    close_price NUMERIC NOT NULL,
    volume NUMERIC DEFAULT 0,  -- Volume if available from DEX
    trade_count INTEGER DEFAULT 0,  -- Number of price updates in this candle
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(token_pair_id, timestamp, timeframe)
);

-- Raw price ticks table (stores every price update from Switchboard)
-- This is the source data for OHLCV aggregation
CREATE TABLE IF NOT EXISTS price_ticks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_pair_id UUID NOT NULL REFERENCES token_pairs(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    price NUMERIC NOT NULL,
    source TEXT NOT NULL DEFAULT 'switchboard',  -- 'switchboard', 'dex', etc.
    feed_id TEXT,  -- Switchboard aggregator address
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Technical indicators table (computed from OHLCV data)
CREATE TABLE IF NOT EXISTS technical_indicators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_pair_id UUID NOT NULL REFERENCES token_pairs(id) ON DELETE CASCADE,
    candle_id UUID REFERENCES ohlcv_candles(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    timeframe TEXT NOT NULL,
    indicator_name TEXT NOT NULL,  -- 'SMA_20', 'RSI_14', 'MACD', etc.
    indicator_value NUMERIC NOT NULL,
    indicator_params JSONB,  -- Store parameters like period, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(token_pair_id, timestamp, timeframe, indicator_name)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_token_pairs_feed_id ON token_pairs(switchboard_feed_id);
CREATE INDEX IF NOT EXISTS idx_token_pairs_active ON token_pairs(is_active);

CREATE INDEX IF NOT EXISTS idx_ohlcv_token_pair_timestamp ON ohlcv_candles(token_pair_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ohlcv_timeframe ON ohlcv_candles(timeframe);
CREATE INDEX IF NOT EXISTS idx_ohlcv_unique_lookup ON ohlcv_candles(token_pair_id, timestamp, timeframe);

CREATE INDEX IF NOT EXISTS idx_price_ticks_token_pair_timestamp ON price_ticks(token_pair_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_price_ticks_timestamp ON price_ticks(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_price_ticks_feed_id ON price_ticks(feed_id);

CREATE INDEX IF NOT EXISTS idx_technical_indicators_token_pair ON technical_indicators(token_pair_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_technical_indicators_name ON technical_indicators(indicator_name);
CREATE INDEX IF NOT EXISTS idx_technical_indicators_lookup ON technical_indicators(token_pair_id, timestamp, timeframe, indicator_name);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for token_pairs
CREATE TRIGGER update_token_pairs_updated_at BEFORE UPDATE ON token_pairs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) Policies
ALTER TABLE token_pairs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ohlcv_candles ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_ticks ENABLE ROW LEVEL SECURITY;
ALTER TABLE technical_indicators ENABLE ROW LEVEL SECURITY;

-- Service role can do everything
CREATE POLICY "Service role full access token_pairs" ON token_pairs
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access ohlcv" ON ohlcv_candles
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access price_ticks" ON price_ticks
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access technical_indicators" ON technical_indicators
    FOR ALL USING (auth.role() = 'service_role');

-- Public read access (for API)
CREATE POLICY "Public read token_pairs" ON token_pairs
    FOR SELECT USING (true);

CREATE POLICY "Public read ohlcv" ON ohlcv_candles
    FOR SELECT USING (true);

CREATE POLICY "Public read price_ticks" ON price_ticks
    FOR SELECT USING (true);

CREATE POLICY "Public read technical_indicators" ON technical_indicators
    FOR SELECT USING (true);

