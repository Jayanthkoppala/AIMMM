import httpx
import json
import base64
import binascii
from typing import Optional, Dict
from app.config import settings
from app.utils.logger import logger


async def verify_payment(
    payment_header: str,
    payment_requirements: Dict
) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Verify x402 payment with facilitator.
    Returns (verified, tx_hash, invoice_id)
    """
    try:
        # Parse X-PAYMENT header
        payment_data = json.loads(base64.b64decode(payment_header).decode())
        
        # Extract invoice_id if available
        invoice_id = payment_data.get("invoice_id") or payment_data.get("invoiceId") or ""
        
        # Verify with facilitator
        async with httpx.AsyncClient() as client:
            verify_response = await client.post(
                f"{settings.X402_FACILITATOR_URL}/verify",
                json={
                    "payment": payment_data,
                    "requirements": payment_requirements
                },
                timeout=30.0
            )
            verify_response.raise_for_status()
            verify_result = verify_response.json()
            
            if verify_result.get("verified"):
                # Settle payment
                settle_response = await client.post(
                    f"{settings.X402_FACILITATOR_URL}/settle",
                    json={
                        "payment": payment_data
                    },
                    timeout=30.0
                )
                settle_response.raise_for_status()
                settle_result = settle_response.json()
                
                tx_hash = settle_result.get("txHash")
                return (True, tx_hash, invoice_id)
            else:
                return (False, None, None)
                
    except httpx.HTTPError as e:
        logger.error(f"x402 facilitator HTTP error: {e}", exc_info=True)
        return (False, None, None)
    except Exception as e:
        logger.error(f"Error verifying payment: {e}", exc_info=True)
        return (False, None, None)


def get_payment_requirements(cost_usdc: float) -> Dict:
    """
    Generate payment requirements for agent execution.
    Converts USDC cost to MOVE (simplified - in production, use actual price oracle).
    """
    # Simplified conversion: 1 USDC ≈ 1 MOVE (8 decimals)
    # In production, fetch actual USDC/MOVE rate
    cost_move = int(cost_usdc * 1_000_000_000)  # 9 decimals for MOVE
    
    return {
        "network": settings.MOVEMENT_NETWORK,
        "asset": "0x1::aptos_coin::AptosCoin",
        "payTo": settings.X402_RECEIVER_ADDRESS,
        "maxAmountRequired": str(cost_move),
        "description": "Agent execution fee"
    }


def check_payment_header(request_headers: Dict) -> Optional[str]:
    """
    Extract X-PAYMENT header from request.
    Returns payment header value or None.
    """
    # Check various header name formats
    for header_name in ["X-PAYMENT", "x-payment", "X-Payment"]:
        if header_name in request_headers:
            return request_headers[header_name]
    return None


def extract_wallet_address(payment_header: str) -> Optional[str]:
    """
    Extract wallet address from x402 payment header.
    
    Args:
        payment_header: Base64-encoded payment header string
    
    Returns:
        Wallet address (0x-prefixed hex string) or None if extraction fails
    """
    try:
        # Parse X-PAYMENT header
        payment_data = json.loads(base64.b64decode(payment_header).decode())
        
        # Try to extract wallet address from payment data
        # x402 payment structure may vary, try common fields
        wallet_address = (
            payment_data.get("from") or
            payment_data.get("payer") or
            payment_data.get("wallet_address") or
            payment_data.get("address")
        )
        
        if wallet_address:
            # Ensure 0x prefix
            if not wallet_address.startswith("0x"):
                wallet_address = f"0x{wallet_address}"
            return wallet_address
        
        logger.warning("Could not extract wallet address from payment header")
        return None
        
    except (json.JSONDecodeError, binascii.Error, Exception) as e:
        logger.error(f"Error extracting wallet address from payment: {e}", exc_info=True)
        return None

