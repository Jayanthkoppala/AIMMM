from pydantic import BaseModel
from typing import Optional, Literal


class TokenPair(BaseModel):
    token_a: str
    token_b: str


class AgentRunRequest(BaseModel):
    mode: Literal["analysis", "trade", "autonomous"]
    token_pair: TokenPair
    pool_address: Optional[str] = None  # CoinGecko pool address
    privy_access_token: Optional[str] = None  # For autonomous mode


class OraclePrice(BaseModel):
    token_a: float
    token_b: float
    timestamp: int


class LLMDecision(BaseModel):
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float


class TokenSentiment(BaseModel):
    """Sentiment data for a single token"""
    token_symbol: str
    token_address: str
    sentiment_score: float  # -1 to 1
    sentiment_label: str    # bullish/bearish/neutral
    confidence: float       # 0 to 1
    key_factors: list[str]
    social_volume: int
    mentions_24h: int
    dominant_emotion: str


class SentimentAnalysis(BaseModel):
    """Sentiment analysis for a token pair"""
    token_a: TokenSentiment
    token_b: TokenSentiment
    timeframe: str
    timestamp: str


class RiskManagementData(BaseModel):
    """Risk management calculations for the trade"""
    position_size: float
    position_value_usd: float
    risk_amount_usd: float
    risk_percentage: float
    position_percentage: float
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    reward_ratio: Optional[float] = None


class AgentRunResponse(BaseModel):
    oracle_price: OraclePrice
    llm_decision: LLMDecision
    sentiment: Optional[SentimentAnalysis] = None
    risk_management: Optional[RiskManagementData] = None
    executed: bool
    tx_hash: Optional[str] = None
    execution_cost: Optional[str] = None


class PaymentRequirements(BaseModel):
    network: str
    asset: str
    payTo: str
    maxAmountRequired: str
    description: str


class PaymentRequiredResponse(BaseModel):
    status: int = 402
    accepts: list[PaymentRequirements]

