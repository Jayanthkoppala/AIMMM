from pydantic import BaseModel
from typing import Optional


class PaymentVerifyRequest(BaseModel):
    invoice_id: str
    proof: str


class PaymentVerifyResponse(BaseModel):
    verified: bool
    tx_hash: Optional[str] = None
    error: Optional[str] = None

