const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

export interface AgentRunRequest {
  mode: 'analysis' | 'trade' | 'autonomous';
  token_pair: {
    token_a: string;
    token_b: string;
  };
  pool_address?: string;  // CoinGecko pool address
  privy_access_token?: string;  // For autonomous mode
}

export interface AgentRunResponse {
  oracle_price: {
    token_a: number;
    token_b: number;
    timestamp: number;
  };
  llm_decision: {
    action: 'BUY' | 'SELL' | 'HOLD';
    confidence: number;
  };
  executed: boolean;
  tx_hash: string | null;
  execution_cost: string | null;
}

export interface PaymentRequirements {
  network: string;
  asset: string;
  payTo: string;
  maxAmountRequired: string;
  description: string;
}

export interface PaymentRequiredResponse {
  status: number;
  accepts: PaymentRequirements[];
}

export async function runAgent(
  request: AgentRunRequest,
  paymentHeader?: string
): Promise<AgentRunResponse | PaymentRequiredResponse> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  if (paymentHeader) {
    headers['X-PAYMENT'] = paymentHeader;
  }

  if (request.privy_access_token) {
    headers['Authorization'] = `Bearer ${request.privy_access_token}`;
  }

  const response = await fetch(`${API_BASE_URL}/agent/run`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
  });

  if (response.status === 402) {
    const data = await response.json();
    return data.detail as PaymentRequiredResponse;
  }

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json() as Promise<AgentRunResponse>;
}

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error('Health check failed');
  }
  return response.json();
}

// ============== STRATEGY BUILDER API ==============

// Pool interfaces
export interface Pool {
  id: number;
  pool_address: string;
  network: string;
  pool_name: string | null;
  token_a_symbol: string | null;
  token_a_address: string | null;
  token_b_symbol: string | null;
  token_b_address: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StrategyConfig {
  agent_configs: {
    ohlcv?: {
      tokens: string[];
      timeframes: string[];
      dataPoints?: number;
    };
    technical?: {
      timeframe: string;
      indicators: Array<{
        name: string;
        parameters: Record<string, any>;
        trigger_points?: Record<string, string>;
      }>;
    };
    sentiment?: {
      enabled: boolean;
      weight: number;
    };
  };
  paper_trading_config: {
    initial_capital_usdc: number;
    capital_per_trade: number;
    max_concurrent_positions: number;
    position_sizing_strategy?: string;
    max_position_pct?: number;
    stop_loss_pct: number;
    take_profit_pct: number;
    per_trade_range?: {
      min: number;
      max: number;
    };
    stop_loss_range?: {
      min: number;
      max: number;
    };
    take_profit_range?: {
      min: number;
      max: number;
    };
    trading_mode?: string;
  };
  llm_provider: string;
}

export interface Strategy {
  id: string;
  user_id: string;
  wallet_address: string | null;
  name: string;
  description: string | null;
  visibility: 'private' | 'public';
  is_active: boolean;
  pool_id?: number;  // Added pool_id (integer)
  pool_address?: string;  // Added pool_address
  strategy_config: StrategyConfig;
  created_at: string;
  updated_at: string;
  last_execution: string | null;
  execution_interval: number;
}

export interface TradingState {
  strategy_id: string;
  balances: Array<{
    token_symbol: string;
    balance: number;
    usd_value: number;
    current_price?: number;
    entry_price?: number;
    unrealized_pnl?: number;
  }>;
  total_portfolio_value: number;
  initial_capital: number;
  unrealized_pnl: number;  // Total P&L (for backward compatibility)
  realized_pnl?: number;   // Realized P&L from closed positions
  total_pnl?: number;      // Total P&L (realized + unrealized)
  unrealized_pnl_pct: number;  // Total P&L percentage
  total_pnl_pct?: number;  // Total P&L percentage
  active_positions: number;
}

export interface Execution {
  id: string;
  execution_timestamp: string;
  decision: string;
  confidence: number;
  reasoning: string;
  trade_executed: boolean;
  symbol: string | null;
  side: string | null;
  amount_in: number | null;
  amount_out: number | null;
  price: number | null;
}

export interface TradeStatistics {
  // Basic Stats
  total_trades: number;
  total_buys: number;
  total_sells: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  
  // P&L Stats
  total_profit: number;
  total_loss: number;
  net_pnl: number;
  avg_profit_per_trade: number;
  avg_loss_per_trade: number;
  largest_win: number;
  largest_loss: number;
  
  // Return Stats
  roi_pct: number;
  avg_return_pct: number;
  
  // Risk Metrics
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  max_drawdown: number;
  max_drawdown_pct: number;
  
  // Trade Quality Metrics
  profit_factor: number;
  expectancy: number;
  risk_reward_ratio: number;
  payoff_ratio: number;
  
  // Duration Stats
  avg_trade_duration_mins: number;
  avg_trade_duration_hours: number;
}

// Create Strategy
export async function createStrategy(
  data: Omit<Strategy, 'id' | 'user_id' | 'wallet_address' | 'created_at' | 'updated_at' | 'last_execution'>,
  accessToken?: string,
  walletAddress?: string | null | undefined
): Promise<Strategy> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  
  if (walletAddress != null) {
    headers['X-Wallet-Address'] = walletAddress;
  }

  const response = await fetch(`${API_BASE_URL}/strategies`, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create strategy');
  }

  return response.json();
}

// Get Strategies
export async function getStrategies(
  accessToken?: string,
  params?: {
    visibility?: 'private' | 'public';
    is_active?: boolean;
    limit?: number;
    offset?: number;
  },
  walletAddress?: string
): Promise<{ strategies: Strategy[]; count: number }> {
  const queryParams = new URLSearchParams();
  if (params?.visibility) queryParams.append('visibility', params.visibility);
  if (params?.is_active !== undefined) queryParams.append('is_active', String(params.is_active));
  if (params?.limit) queryParams.append('limit', String(params.limit));
  if (params?.offset) queryParams.append('offset', String(params.offset));

  const headers: HeadersInit = {};
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  if (walletAddress) {
    headers['X-Wallet-Address'] = walletAddress;
  }

  const response = await fetch(`${API_BASE_URL}/strategies?${queryParams}`, {
    headers,
  });

  if (!response.ok) {
    throw new Error('Failed to fetch strategies');
  }

  return response.json();
}

// Get Strategy
export async function getStrategy(strategyId: string, accessToken?: string, walletAddress?: string): Promise<Strategy> {
  const headers: HeadersInit = {};
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  if (walletAddress) {
    headers['X-Wallet-Address'] = walletAddress;
  }

  const response = await fetch(`${API_BASE_URL}/strategies/${strategyId}`, {
    headers,
  });

  if (!response.ok) {
    throw new Error('Failed to fetch strategy');
  }

  return response.json();
}

// Execute Strategy
export async function executeStrategy(
  strategyId: string,
  executionMode: 'analysis' | 'trade',
  accessToken?: string,
  walletAddress?: string
): Promise<any> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  if (walletAddress) {
    headers['X-Wallet-Address'] = walletAddress;
  }

  const response = await fetch(`${API_BASE_URL}/strategies/${strategyId}/execute`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ execution_mode: executionMode }),
  });

  if (!response.ok) {
    throw new Error('Failed to execute strategy');
  }

  return response.json();
}

// Get Trading State
export async function getTradingState(
  strategyId: string,
  accessToken?: string,
  walletAddress?: string
): Promise<TradingState> {
  const headers: HeadersInit = {};
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  if (walletAddress) {
    headers['X-Wallet-Address'] = walletAddress;
  }

  const response = await fetch(`${API_BASE_URL}/strategies/${strategyId}/trading-state`, {
    headers,
  });

  if (!response.ok) {
    throw new Error('Failed to fetch trading state');
  }

  return response.json();
}

// Get Executions
export async function getExecutions(
  strategyId: string,
  accessToken?: string,
  params?: {
    limit?: number;
    offset?: number;
    include_market_data?: boolean;
  },
  walletAddress?: string
): Promise<{ executions: Execution[]; count: number }> {
  const queryParams = new URLSearchParams();
  if (params?.limit) queryParams.append('limit', String(params.limit));
  if (params?.offset) queryParams.append('offset', String(params.offset));
  if (params?.include_market_data) queryParams.append('include_market_data', 'true');

  const headers: HeadersInit = {};
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  if (walletAddress) {
    headers['X-Wallet-Address'] = walletAddress;
  }

  const response = await fetch(
    `${API_BASE_URL}/strategies/${strategyId}/executions?${queryParams}`,
    {
      headers,
    }
  );

  if (!response.ok) {
    throw new Error('Failed to fetch executions');
  }

  return response.json();
}

// Get Trade Statistics
export async function getTradeStatistics(
  strategyId: string,
  accessToken?: string,
  walletAddress?: string
): Promise<{ strategy_id: string; statistics: TradeStatistics }> {
  const headers: HeadersInit = {};
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  if (walletAddress) {
    headers['X-Wallet-Address'] = walletAddress;
  }

  const response = await fetch(
    `${API_BASE_URL}/strategies/${strategyId}/statistics`,
    {
      headers,
    }
  );

  if (!response.ok) {
    throw new Error('Failed to fetch trade statistics');
  }

  return response.json();
}

// Activate Strategy
export async function activateStrategy(
  strategyId: string,
  intervalMinutes: number,
  executionMode: 'analysis' | 'trade',
  accessToken?: string,
  walletAddress?: string
): Promise<any> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  if (walletAddress) {
    headers['X-Wallet-Address'] = walletAddress;
  }

  const response = await fetch(`${API_BASE_URL}/strategies/${strategyId}/activate`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      interval_minutes: intervalMinutes,
      execution_mode: executionMode,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to activate strategy');
  }

  return response.json();
}

// Deactivate Strategy
export async function deactivateStrategy(
  strategyId: string,
  accessToken?: string,
  walletAddress?: string
): Promise<any> {
  const headers: HeadersInit = {};
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  if (walletAddress) {
    headers['X-Wallet-Address'] = walletAddress;
  }

  const response = await fetch(`${API_BASE_URL}/strategies/${strategyId}/deactivate`, {
    method: 'POST',
    headers,
  });

  if (!response.ok) {
    throw new Error('Failed to deactivate strategy');
  }

  return response.json();
}

// Delete Strategy
export async function deleteStrategy(
  strategyId: string,
  accessToken?: string,
  walletAddress?: string
): Promise<void> {
  const headers: HeadersInit = {};
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  if (walletAddress) {
    headers['X-Wallet-Address'] = walletAddress;
  }

  const response = await fetch(`${API_BASE_URL}/strategies/${strategyId}`, {
    method: 'DELETE',
    headers,
  });

  if (!response.ok) {
    throw new Error('Failed to delete strategy');
  }
}

// ============== POOLS API ==============

// Get Pools
export async function getPools(params?: {
  is_active?: boolean;
  network?: string;
  limit?: number;
  search?: string;
}): Promise<Pool[]> {
  const queryParams = new URLSearchParams();
  if (params?.is_active !== undefined) queryParams.append('is_active', String(params.is_active));
  if (params?.network) queryParams.append('network', params.network);
  if (params?.limit) queryParams.append('limit', String(params.limit));
  if (params?.search) queryParams.append('search', params.search);

  const response = await fetch(`${API_BASE_URL}/pools?${queryParams}`);

  if (!response.ok) {
    throw new Error('Failed to fetch pools');
  }

  return response.json();
}

// Get Pool by ID
export async function getPool(poolId: number): Promise<Pool> {
  const response = await fetch(`${API_BASE_URL}/pools/${poolId}`);

  if (!response.ok) {
    throw new Error('Failed to fetch pool');
  }

  return response.json();
}

// ============== ANALYTICS API ==============

export interface OHLCVCandle {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface OHLCVResponse {
  status: string;
  data: {
    pool_address: string;
    pool_name: string | null;
    pair: string;
    timeframe: string;
    candles: OHLCVCandle[];
    count: number;
    source: string;
  };
}

export interface IndicatorData {
  timestamp: number;
  momentum: {
    rsi: number | null;
    stoch: number | null;
    stoch_signal: number | null;
    williams_r: number | null;
    mfi: number | null;
    cci: number | null;
    ao: number | null;
    kama: number | null;
    roc: number | null;
  };
  trend: {
    macd: number | null;
    macd_signal: number | null;
    macd_diff: number | null;
    sma_20: number | null;
    sma_50: number | null;
    sma_200: number | null;
    ema_12: number | null;
    ema_26: number | null;
    ema_50: number | null;
    adx: number | null;
    trix: number | null;
  };
  volatility: {
    bb_hband: number | null;
    bb_lband: number | null;
    bb_mavg: number | null;
    bb_pband: number | null;
    bb_wband: number | null;
    atr: number | null;
  };
  volume: {
    obv: number | null;
    vwap: number | null;
    cmf: number | null;
  };
}

export interface IndicatorsResponse {
  status: string;
  data: {
    pool_address: string;
    pool_name: string | null;
    pair: string;
    indicators: IndicatorData[];
    count: number;
  };
}

export interface TokenSentimentData {
  symbol: string;
  score: number;
  label: string;
  confidence: number;
  key_factors: string[];
  dominant_emotion: string;
  social_volume?: number;
  mentions_24h?: number;
}

export interface SentimentResponse {
  status: string;
  data: {
    pool_address: string;
    sentiment: {
      token_a: TokenSentimentData;
      token_b: TokenSentimentData;
      timeframe: string;
      analyzed_at: string;
    } | null;
    message?: string;
  };
}

// Get OHLCV Candles from DB
export async function getOHLCV(
  poolAddress: string,
  limit: number = 100,
  hoursBack?: number
): Promise<OHLCVResponse> {
  const queryParams = new URLSearchParams();
  queryParams.append('pool_address', poolAddress);
  queryParams.append('limit', String(limit));
  queryParams.append('from_db', 'true');
  if (hoursBack) queryParams.append('hours_back', String(hoursBack));

  const response = await fetch(`${API_BASE_URL}/ohlcv/candles?${queryParams}`);

  if (!response.ok) {
    throw new Error('Failed to fetch OHLCV data');
  }

  return response.json();
}

// Get Technical Indicators from DB
export async function getIndicators(
  poolAddress: string,
  limit: number = 1
): Promise<IndicatorsResponse> {
  const queryParams = new URLSearchParams();
  queryParams.append('pool_address', poolAddress);
  queryParams.append('limit', String(limit));

  const response = await fetch(`${API_BASE_URL}/ohlcv/indicators?${queryParams}`);

  if (!response.ok) {
    throw new Error('Failed to fetch indicators');
  }

  return response.json();
}

// Get Sentiment from DB
export async function getSentiment(poolAddress: string): Promise<SentimentResponse> {
  const queryParams = new URLSearchParams();
  queryParams.append('pool_address', poolAddress);

  const response = await fetch(`${API_BASE_URL}/ohlcv/sentiment?${queryParams}`);

  if (!response.ok) {
    throw new Error('Failed to fetch sentiment');
  }

  return response.json();
}
