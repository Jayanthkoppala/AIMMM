-- Supabase Schema for AI Trading Agent

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_address TEXT UNIQUE NOT NULL,
    privy_user_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agent executions table
CREATE TABLE IF NOT EXISTS agent_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mode TEXT NOT NULL CHECK (mode IN ('analysis', 'trade')),
    token_a_address TEXT NOT NULL,
    token_b_address TEXT NOT NULL,
    switchboard_feed_id TEXT,
    oracle_price_a NUMERIC NOT NULL,
    oracle_price_b NUMERIC NOT NULL,
    llm_action TEXT NOT NULL CHECK (llm_action IN ('BUY', 'SELL', 'HOLD')),
    llm_confidence NUMERIC NOT NULL CHECK (llm_confidence >= 0 AND llm_confidence <= 1),
    executed BOOLEAN NOT NULL DEFAULT FALSE,
    tx_hash TEXT,
    execution_cost NUMERIC NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Payments table
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_execution_id UUID NOT NULL REFERENCES agent_executions(id) ON DELETE CASCADE,
    invoice_id TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    tx_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'verified', 'failed')) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_wallet_address ON users(wallet_address);
CREATE INDEX IF NOT EXISTS idx_agent_executions_user_id ON agent_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_executions_created_at ON agent_executions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_payments_agent_execution_id ON payments(agent_execution_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);

-- Row Level Security (RLS) Policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

-- Policy: Users can read their own data
CREATE POLICY "Users can read own data" ON users
    FOR SELECT
    USING (auth.uid()::text = privy_user_id OR wallet_address = current_setting('app.current_wallet', true));

-- Policy: Users can read their own executions
CREATE POLICY "Users can read own executions" ON agent_executions
    FOR SELECT
    USING (user_id IN (SELECT id FROM users WHERE privy_user_id = auth.uid()::text OR wallet_address = current_setting('app.current_wallet', true)));

-- Policy: Service role can do everything (for backend)
CREATE POLICY "Service role full access" ON users
    FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access executions" ON agent_executions
    FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access payments" ON payments
    FOR ALL
    USING (auth.role() = 'service_role');

