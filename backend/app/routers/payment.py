from fastapi import APIRouter, HTTPException
from app.models.payment import PaymentVerifyRequest, PaymentVerifyResponse
from app.services import x402

router = APIRouter(prefix="/x402", tags=["payment"])


@router.post("/verify", response_model=PaymentVerifyResponse)
async def verify_payment(request: PaymentVerifyRequest):
    """
    Verify x402 payment.
    """
    try:
        # In production, this would verify the payment proof
        # For now, return success if invoice_id is provided
        if not request.invoice_id:
            return PaymentVerifyResponse(
                verified=False,
                error="Missing invoice_id"
            )
        
        # Placeholder verification
        # In production, verify with facilitator
        return PaymentVerifyResponse(
            verified=True,
            tx_hash=request.proof[:66] if len(request.proof) >= 66 else None
        )
        
    except Exception as e:
        return PaymentVerifyResponse(
            verified=False,
            error=str(e)
        )

