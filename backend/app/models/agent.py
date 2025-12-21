from pydantic import BaseModel
from typing import Optional, Literal


class TokenPair(BaseModel):
    token_a: str
    token_b: str


class AgentRunRequest(BaseModel):
    mode: Literal["analysis", "trade"]
    token_pair: TokenPair
    switchboard_feed_id: Optional[str] = None


class OraclePrice(BaseModel):
    token_a: float
    token_b: float
    timestamp: int


class LLMDecision(BaseModel):
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float


class AgentRunResponse(BaseModel):
    oracle_price: OraclePrice
    llm_decision: LLMDecision
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

