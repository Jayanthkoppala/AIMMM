"""
Pydantic models for strategy builder
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from decimal import Decimal


class IndicatorConfig(BaseModel):
    """Configuration for a technical indicator"""
    name: str
    parameters: Dict[str, Any]
    trigger_points: Optional[Dict[str, str]] = None


class OHLCVConfig(BaseModel):
    """OHLCV agent configuration"""
    tokens: List[str] = Field(default_factory=lambda: ["MOVE-USDC"])
    timeframes: List[str] = Field(default_factory=lambda: ["1m"])
    dataPoints: int = 100


class TechnicalConfig(BaseModel):
    """Technical indicators agent configuration"""
    timeframe: str = "1m"
    indicators: List[IndicatorConfig] = Field(default_factory=list)


class SentimentConfig(BaseModel):
    """Sentiment analysis agent configuration"""
    enabled: bool = True
    weight: float = Field(default=0.3, ge=0.0, le=1.0)


class AgentConfigs(BaseModel):
    """All agent configurations"""
    ohlcv: Optional[OHLCVConfig] = None
    technical: Optional[TechnicalConfig] = None
    sentiment: Optional[SentimentConfig] = None


class PaperTradingConfig(BaseModel):
    """Paper trading configuration"""
    initial_capital_usdc: float = Field(default=1000.0, gt=0)
    capital_per_trade: float = Field(default=100.0, gt=0)
    max_concurrent_positions: int = Field(default=5, ge=1)
    position_sizing_strategy: Literal["fixed", "kelly", "volatility_adjusted"] = "fixed"
    max_position_pct: float = Field(default=0.2, ge=0.01, le=1.0)
    stop_loss_pct: float = Field(default=0.05, ge=0.01, le=0.5)
    take_profit_pct: float = Field(default=0.10, ge=0.01, le=2.0)
    
    @field_validator('capital_per_trade')
    @classmethod
    def validate_capital_per_trade(cls, v, info):
        """Ensure capital per trade doesn't exceed initial capital"""
        if 'initial_capital_usdc' in info.data:
            if v > info.data['initial_capital_usdc']:
                raise ValueError('capital_per_trade cannot exceed initial_capital_usdc')
        return v


class StrategyConfig(BaseModel):
    """Complete strategy configuration"""
    agent_configs: AgentConfigs
    paper_trading_config: PaperTradingConfig = Field(default_factory=PaperTradingConfig)
    llm_provider: str = "openai/gpt-4o-mini"


class CreateStrategyRequest(BaseModel):
    """Request to create a new strategy"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    visibility: Literal["private", "public"] = "private"
    pool_id: Optional[int] = None
    pool_address: Optional[str] = None
    execution_interval: int = Field(default=5, ge=1, le=1440)  # 1 min to 24 hours
    strategy_config: StrategyConfig


class UpdateStrategyRequest(BaseModel):
    """Request to update an existing strategy"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    visibility: Optional[Literal["private", "public"]] = None
    is_active: Optional[bool] = None
    pool_id: Optional[int] = None
    pool_address: Optional[str] = None
    execution_interval: Optional[int] = Field(None, ge=1, le=1440)  # 1 min to 24 hours
    strategy_config: Optional[StrategyConfig] = None


class StrategyResponse(BaseModel):
    """Response containing strategy data"""
    id: str
    user_id: str
    wallet_address: Optional[str]
    name: str
    description: Optional[str]
    visibility: str
    is_active: bool
    pool_id: Optional[int] = None
    pool_address: Optional[str] = None
    strategy_config: Dict[str, Any]  # JSONB as dict
    created_at: datetime
    updated_at: datetime
    last_execution: Optional[datetime]
    execution_interval: int


class TradeDetails(BaseModel):
    """Details about a specific trade"""
    trade_executed: bool
    tx_hash: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    amount_in: Optional[Decimal] = None
    amount_out: Optional[Decimal] = None
    price: Optional[Decimal] = None


class ExecutionResponse(BaseModel):
    """Response containing execution data"""
    id: str
    strategy_id: str
    user_id: str
    execution_timestamp: datetime
    llm_model: str
    decision: str
    confidence: Decimal
    reasoning: Optional[str]
    execution_mode: str
    duration_seconds: Optional[Decimal]
    llm_cost: Optional[Decimal]
    trade_details: Optional[TradeDetails] = None
    market_data: Optional[Dict[str, Any]] = None


class TokenBalance(BaseModel):
    """Token balance in paper trading portfolio"""
    token_address: str
    token_symbol: str
    balance: Decimal
    usd_value: Optional[Decimal]
    updated_at: datetime


class TradingState(BaseModel):
    """Current trading state for a strategy"""
    strategy_id: str
    balances: List[TokenBalance]
    total_portfolio_value: Decimal
    initial_capital: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_pct: float
    active_positions: int


class ExecuteStrategyRequest(BaseModel):
    """Request to execute a strategy"""
    execution_mode: Literal["analysis", "trade"] = "analysis"


class ActivateStrategyRequest(BaseModel):
    """Request to activate automated strategy execution"""
    interval_minutes: int = Field(default=5, ge=1, le=1440)
    execution_mode: Literal["analysis", "trade"] = "analysis"


class ParseNaturalLanguageRequest(BaseModel):
    """Request to parse natural language strategy"""
    text: str = Field(..., min_length=10, max_length=2000)


class ParseNaturalLanguageResponse(BaseModel):
    """Response from natural language parsing"""
    success: bool
    parameters: Optional[StrategyConfig] = None
    original_text: str
    error: Optional[str] = None


class ExecutionDecision(BaseModel):
    """LLM decision for strategy execution"""
    action: Literal["BUY", "SELL", "HOLD", "CLOSE_POSITION"]
    token: Optional[str] = None  # Token to trade (e.g., "MOVE", "ETH")
    amount_usdc: Optional[float] = None  # Amount in USDC to trade
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str


class ExecutionResult(BaseModel):
    """Result of strategy execution"""
    status: str
    execution_id: str
    decision: ExecutionDecision
    trading_state: TradingState
    cost: Optional[Decimal] = None
    duration: Optional[Decimal] = None
    error: Optional[str] = None

