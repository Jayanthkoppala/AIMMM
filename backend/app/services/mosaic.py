from typing import Optional, Dict, Any
from app.config import settings
import httpx
from app.utils.logger import logger


async def get_quote(
    src_asset: str,
    dst_asset: str,
    amount: str,
    sender: str,
    slippage: int = 100,
    receiver: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get a quote from Mosaic Aggregator API.
    
    Args:
        src_asset: Source asset address (e.g., "0x1::aptos_coin::AptosCoin")
        dst_asset: Destination asset address
        amount: Amount to swap (in source asset's smallest unit)
        sender: Sender address
        slippage: Slippage tolerance in basis points (default: 100 = 1%)
        receiver: Receiver address (optional, defaults to sender)
    
    Returns:
        Quote data with transaction details, or None if failed
    """
    try:
        url = "https://api.mosaic.ag/v1/quote"
        params = {
            "srcAsset": src_asset,
            "dstAsset": dst_asset,
            "amount": amount,
            "sender": sender,
            "slippage": str(slippage),
        }
        
        if receiver:
            params["receiver"] = receiver
        
        headers = {}
        if settings.MOSAIC_API_KEY:
            headers["X-API-Key"] = settings.MOSAIC_API_KEY
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0 and data.get("data"):
                logger.info(f"Mosaic quote received: {data['data'].get('srcAmount')} -> {data['data'].get('dstAmount')}")
                return data["data"]
            else:
                logger.error(f"Mosaic API error: {data.get('message', 'Unknown error')}")
                return None
                
    except httpx.HTTPStatusError as e:
        logger.error(f"Mosaic API HTTP error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Error getting Mosaic quote: {e}", exc_info=True)
        return None


async def execute_swap(
    token_a: str,
    token_b: str,
    direction: str,  # "X_TO_Y" or "Y_TO_X"
    amount_in: int,
    min_amount_out: int,
    signer_address: str,
    private_key: Optional[str] = None
) -> Optional[str]:
    """
    Execute a swap on Mosaic DEX via their API.
    
    Note: This function gets a quote and returns transaction data.
    The actual transaction signing and submission would typically happen
    on the frontend using the user's wallet, or via a service account.
    
    For now, this returns the quote data. In a production setup, you would:
    1. Get quote from Mosaic API
    2. Build transaction using Aptos SDK
    3. Sign transaction (requires private key)
    4. Submit to Movement network
    5. Wait for confirmation
    6. Return transaction hash
    
    Args:
        token_a: Source token address
        token_b: Destination token address
        direction: "X_TO_Y" or "Y_TO_X"
        amount_in: Input amount (in token's smallest unit)
        min_amount_out: Minimum output amount (slippage protection)
        signer_address: Address that will sign the transaction
        private_key: Optional private key (not used in current implementation)
    
    Returns:
        Transaction hash if successful, None otherwise
    """
    try:
        # Determine source and destination assets based on direction
        if direction == "X_TO_Y":
            src_asset = token_a
            dst_asset = token_b
        else:  # Y_TO_X
            src_asset = token_b
            dst_asset = token_a
        
        # Get quote from Mosaic
        quote_data = await get_quote(
            src_asset=src_asset,
            dst_asset=dst_asset,
            amount=str(amount_in),
            sender=signer_address,
            slippage=100,  # 1% slippage
            receiver=signer_address
        )
        
        if not quote_data:
            logger.error("Failed to get quote from Mosaic")
            return None
        
        # Verify the quote meets minimum output requirement
        dst_amount = quote_data.get("dstAmount", 0)
        if dst_amount < min_amount_out:
            logger.warning(
                f"Quote output {dst_amount} below minimum {min_amount_out}. "
                "Transaction would fail."
            )
            return None
        
        # Get transaction data from quote
        tx_data = quote_data.get("tx")
        if not tx_data:
            logger.error("Quote data missing transaction information")
            return None
        
        # In a production implementation, you would:
        # 1. Build transaction using Aptos SDK with tx_data
        # 2. Sign transaction (requires private key or wallet integration)
        # 3. Submit to Movement network
        # 4. Wait for confirmation
        # 5. Return transaction hash
        
        # For now, we return None as we don't have the private key
        # The frontend should handle transaction signing and submission
        logger.info(
            f"Mosaic swap quote ready: {amount_in} {src_asset} -> "
            f"{dst_amount} {dst_asset}. Transaction data prepared."
        )
        
        # TODO: Implement actual transaction submission when private key is available
        # or integrate with frontend wallet for signing
        logger.warning(
            "Transaction submission not implemented. "
            "Quote obtained but transaction needs to be signed and submitted."
        )
        return None
        
    except Exception as e:
        logger.error(f"Error executing Mosaic swap: {e}", exc_info=True)
        return None


async def get_pool_reserves(token_a: str, token_b: str) -> tuple[int, int, int]:
    """
    Get current pool reserves for token pair.
    
    Note: Mosaic is an aggregator, not a single pool.
    This function is kept for compatibility but returns placeholder values.
    For actual liquidity data, use the Mosaic quote API.
    
    Returns:
        (reserve_x, reserve_y, timestamp) - placeholder values
    """
    try:
        # Mosaic is an aggregator, so we can't get specific pool reserves
        # Instead, we can get a quote to understand available liquidity
        # For now, return placeholder
        logger.warning("get_pool_reserves called on Mosaic aggregator - returning placeholder")
        return (1000000, 1500000, 0)
    except Exception as e:
        logger.error(f"Error getting pool reserves: {e}", exc_info=True)
        return (0, 0, 0)


async def estimate_swap_output(
    amount_in: int,
    reserve_in: int,
    reserve_out: int
) -> int:
    """
    Estimate output amount for a swap.
    
    Note: For Mosaic, it's better to use get_quote() for accurate estimates
    as it aggregates across multiple DEXs. This function is kept for compatibility.
    
    Args:
        amount_in: Input amount
        reserve_in: Input reserve (not used with Mosaic)
        reserve_out: Output reserve (not used with Mosaic)
    
    Returns:
        Estimated output amount
    """
    # For Mosaic, we should use get_quote() instead
    # This is a placeholder for compatibility
    if reserve_in == 0 or reserve_out == 0:
        return 0
    
    # Simple constant product estimate (not accurate for aggregator)
    amount_in_with_fee = amount_in * 997
    numerator = amount_in_with_fee * reserve_out
    denominator = reserve_in * 1000 + amount_in_with_fee
    
    if denominator == 0:
        return 0
    
    return numerator // denominator


