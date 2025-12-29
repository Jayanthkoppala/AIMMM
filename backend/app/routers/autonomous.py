"""
Autonomous Trading Router
Endpoints for managing autonomous trading settings
"""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pydantic import BaseModel
from app.services import privy_service, autonomous_wallet
from app.utils.logger import logger

router = APIRouter(prefix="/autonomous", tags=["autonomous"])


class ToggleRequest(BaseModel):
    enabled: bool


@router.get("/status")
async def get_autonomous_status(
    authorization: Optional[str] = Header(None)
):
    """
    Get autonomous trading status for the authenticated Privy user.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    access_token = authorization.replace("Bearer ", "")
    
    # Verify Privy user
    privy_user = await privy_service.privy_service.verify_access_token(access_token)
    if not privy_user:
        raise HTTPException(status_code=401, detail="Invalid access token")
    
    privy_user_id = privy_user.get('id')
    
    # Get autonomous wallet status
    status = await autonomous_wallet.autonomous_wallet_service.get_autonomous_status(privy_user_id)
    
    if not status:
        # Wallet doesn't exist yet - create it
        await autonomous_wallet.autonomous_wallet_service.create_wallet_for_user(privy_user_id)
        status = await autonomous_wallet.autonomous_wallet_service.get_autonomous_status(privy_user_id)
    
    if not status:
        raise HTTPException(status_code=500, detail="Failed to get autonomous wallet status")
    
    return {
        "wallet_address": status.get('wallet_address'),
        "enabled": status.get('autonomous_enabled', False),
        "risk_per_trade": float(status.get('risk_per_trade', 0.02)),
        "max_position_size": float(status.get('max_position_size', 0.10))
    }


@router.post("/toggle")
async def toggle_autonomous(
    request: ToggleRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Enable or disable autonomous trading for the authenticated Privy user.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    access_token = authorization.replace("Bearer ", "")
    
    # Verify Privy user
    privy_user = await privy_service.privy_service.verify_access_token(access_token)
    if not privy_user:
        raise HTTPException(status_code=401, detail="Invalid access token")
    
    privy_user_id = privy_user.get('id')
    
    # Ensure wallet exists
    wallet_info = await autonomous_wallet.autonomous_wallet_service.get_wallet(privy_user_id)
    if not wallet_info:
        await autonomous_wallet.autonomous_wallet_service.create_wallet_for_user(privy_user_id)
    
    # Toggle autonomous mode
    success = await autonomous_wallet.autonomous_wallet_service.set_autonomous_enabled(
        privy_user_id,
        request.enabled
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update autonomous trading status")
    
    logger.info(f"Autonomous trading {'enabled' if request.enabled else 'disabled'} for user {privy_user_id}")
    
    return {
        "enabled": request.enabled,
        "message": f"Autonomous trading {'enabled' if request.enabled else 'disabled'}"
    }

