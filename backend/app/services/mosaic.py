from typing import Optional, Dict, Any
from app.config import settings
import httpx
from urllib.parse import quote
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
    
    This matches the Mosaic API format exactly:
    - Endpoint: GET https://api.mosaic.ag/v1/quote
    - Headers: x-api-key: <API_KEY>
    - Params: srcAsset, dstAsset, amount, sender, slippage
    
    Example usage (matches Mosaic docs):
        curl 'https://api.mosaic.ag/v1/quote?srcAsset=0x1::aptos_coin::AptosCoin&dstAsset=0x275f...::tokens::USDC&amount=1000000000&sender=0x...&slippage=10' \
        --header 'x-api-key: xxx'
    
    Args:
        src_asset: Source asset address (e.g., "0x1::aptos_coin::AptosCoin")
        dst_asset: Destination asset address (e.g., "0x275f...::tokens::USDC")
        amount: Amount to swap (in source asset's smallest unit, as string)
        sender: Sender address (0x... format)
        slippage: Slippage tolerance in basis points (default: 100 = 1%, 10 = 0.1%)
        receiver: Receiver address (optional, defaults to sender)
    
    Returns:
        Quote data with transaction details:
        {
            "srcAmount": str,
            "dstAmount": str,
            "tx": {
                "function": str,
                "typeArguments": List[str],
                "functionArguments": List[Any]
            },
            ...
        }
        Returns None if failed
    """
    try:
        url = "https://api.mosaic.ag/v1/quote"
        
        # URL encode asset addresses (the :: characters need to be encoded as %3A%3A)
        # But httpx should handle this automatically with params dict, so we'll pass as-is
        # However, let's log what we're sending to debug
        logger.info(f"[Mosaic] Requesting quote: {src_asset} -> {dst_asset}, amount={amount}")
        
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
            headers["x-api-key"] = settings.MOSAIC_API_KEY  # Using lowercase as per Mosaic API docs
        else:
            logger.warning("[Mosaic] No API key configured - request may fail")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
            
            # Log detailed error information
            if response.status_code != 200:
                logger.error(f"[Mosaic] API request failed with status {response.status_code}")
                logger.error(f"[Mosaic] Request URL: {url}")
                logger.error(f"[Mosaic] Request params: srcAsset={src_asset}, dstAsset={dst_asset}, amount={amount}, sender={sender}, slippage={slippage}")
                try:
                    error_data = response.json()
                    logger.error(f"[Mosaic] Error response: {error_data}")
                    # Extract field violations if present
                    if "details" in error_data:
                        for detail in error_data.get("details", []):
                            for violation in detail.get("fieldViolations", []):
                                logger.error(f"[Mosaic] Field violation: {violation.get('field')} - {violation.get('description')}")
                except:
                    logger.error(f"[Mosaic] Raw response: {response.text}")
            
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


async def estimate_slippage(
    src_asset: str,
    dst_asset: str,
    amount: str,
    sender: str
) -> Optional[Dict[str, Any]]:
    """
    Get quote and calculate slippage impact.
    
    Args:
        src_asset: Source asset address
        dst_asset: Destination asset address
        amount: Amount to swap (in source asset's smallest unit)
        sender: Sender address
    
    Returns:
        {
            "dst_amount": int,
            "slippage_pct": float,
            "price_impact": float,
            "effective_price": float
        }
    """
    try:
        # Get quote for the requested amount
        quote_data = await get_quote(
            src_asset=src_asset,
            dst_asset=dst_asset,
            amount=amount,
            sender=sender,
            slippage=100  # 1% slippage tolerance
        )
        
        if not quote_data:
            return None
        
        src_amount = float(quote_data.get("srcAmount", 0))
        dst_amount = float(quote_data.get("dstAmount", 0))
        
        if src_amount == 0 or dst_amount == 0:
            return None
        
        # Calculate effective price
        effective_price = dst_amount / src_amount
        
        # For accurate slippage calculation, we'd need to compare with a spot price
        # For now, estimate based on the paths returned by Mosaic
        paths = quote_data.get("paths", [])
        
        # Simple slippage estimation (this would be more accurate with on-chain data)
        # Assuming the aggregator already accounts for slippage in its routing
        estimated_slippage_pct = 0.1  # 0.1% baseline for aggregator efficiency
        
        # Price impact estimation (larger trades = higher impact)
        # This is a simplified model - actual impact depends on liquidity depth
        price_impact = min(float(amount) / 1000000, 2.0)  # Cap at 2%
        
        return {
            "dst_amount": int(dst_amount),
            "slippage_pct": estimated_slippage_pct,
            "price_impact": price_impact,
            "effective_price": effective_price,
            "paths": paths
        }
        
    except Exception as e:
        logger.error(f"Error estimating slippage: {e}", exc_info=True)
        return None


async def build_swap_transaction(
    quote_data: Dict[str, Any],
    signer_address: str
) -> Optional[Dict[str, Any]]:
    """
    Build transaction payload from Mosaic quote.
    Returns Aptos transaction structure ready for signing.
    
    This matches the format expected by Aptos SDK:
    - function: The function to call (from quote_data.tx.function)
    - typeArguments: Type arguments for the function (from quote_data.tx.typeArguments)
    - functionArguments: Function arguments (from quote_data.tx.functionArguments)
    
    In TypeScript/Aptos SDK, you would use:
    ```typescript
    const transaction = await aptos.transaction.build.simple({
      sender: user.accountAddress,
      data: {
        function: tx_data.function,
        typeArguments: tx_data.typeArguments,
        functionArguments: tx_data.functionArguments,
      },
    });
    ```
    
    Args:
        quote_data: Quote data from get_quote() - should have structure:
            {
                "tx": {
                    "function": str,
                    "typeArguments": List[str],
                    "functionArguments": List[Any]
                },
                ...
            }
        signer_address: Address that will sign the transaction
    
    Returns:
        {
            "function": str,
            "typeArguments": List[str],
            "functionArguments": List[Any]
        }
        This matches the format expected by aptos.transaction.build.simple()
    """
    try:
        tx_data = quote_data.get("tx")
        if not tx_data:
            logger.error("Quote data missing transaction information (no 'tx' field)")
            logger.debug(f"Quote data keys: {list(quote_data.keys())}")
            return None
        
        function = tx_data.get("function")
        type_arguments = tx_data.get("typeArguments", [])
        function_arguments = tx_data.get("functionArguments", [])
        
        if not function:
            logger.error("Transaction data missing 'function' field")
            return None
        
        logger.info(f"Built transaction: function={function}, typeArgs={len(type_arguments)}, funcArgs={len(function_arguments)}")
        
        return {
            "function": function,
            "typeArguments": type_arguments,
            "functionArguments": function_arguments
        }
        
    except Exception as e:
        logger.error(f"Error building swap transaction: {e}", exc_info=True)
        return None


async def get_swap_quote_for_strategy(
    src_token_symbol: str,
    dst_token_symbol: str,
    amount_usdc: float,
    sender: str,
    token_addresses: Optional[Dict[str, str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Get swap quote optimized for strategy execution.
    
    Args:
        src_token_symbol: Source token symbol (e.g., "USDC", "MOVE")
        dst_token_symbol: Destination token symbol
        amount_usdc: Amount in USDC terms
        sender: Sender address
        token_addresses: Optional dict mapping symbols to addresses
    
    Returns:
        Quote data with slippage estimation
    """
    try:
        # Default token addresses (Movement testnet)
        # IMPORTANT: Mosaic uses token IDs (from /v1/tokens endpoint), NOT module paths!
        # These are the actual token IDs that Mosaic recognizes
        default_addresses = {
            # Movement testnet token IDs (from Mosaic API)
            "USDC": "0x83121c9f9b0527d1f056e21a950d6bf3b9e9e2e8353d0e95ccea726713cbea39",  # USDC.e token ID
            "USDC.e": "0x83121c9f9b0527d1f056e21a950d6bf3b9e9e2e8353d0e95ccea726713cbea39",  # USDC.e token ID (alias)
            "MOVE": "0xa",  # MOVE coin ID (NOT 0x1::aptos_coin::AptosCoin!)
            "WETH.e": "0x908828f4fb0213d4034c3ded1630bbd904e8a3a6bf3c63270887f0b06653a376",  # WETH.e token ID
            "WETH": "0x908828f4fb0213d4034c3ded1630bbd904e8a3a6bf3c63270887f0b06653a376",  # WETH.e (alias)
            "ETH": "0x908828f4fb0213d4034c3ded1630bbd904e8a3a6bf3c63270887f0b06653a376"  # WETH.e (alias)
        }
        
        if token_addresses:
            default_addresses.update(token_addresses)
        
        src_asset = default_addresses.get(src_token_symbol)
        dst_asset = default_addresses.get(dst_token_symbol)
        
        if not src_asset or not dst_asset:
            logger.error(f"[Mosaic] Unknown token symbol: {src_token_symbol} or {dst_token_symbol}")
            logger.error(f"[Mosaic] Available symbols: {list(default_addresses.keys())}")
            return None
        
        logger.info(f"[Mosaic] Using asset addresses: src={src_asset}, dst={dst_asset}")
        
        # Convert USDC amount to smallest unit (6 decimals for USDC)
        amount_in_units = int(amount_usdc * 1_000_000)
        
        logger.info(f"[Mosaic] Requesting quote: {src_token_symbol} -> {dst_token_symbol}, amount={amount_usdc} USDC ({amount_in_units} units)")
        
        # Get quote
        quote_data = await get_quote(
            src_asset=src_asset,
            dst_asset=dst_asset,
            amount=str(amount_in_units),
            sender=sender,
            slippage=100  # 1% slippage
        )
        
        if not quote_data:
            return None
        
        # Add slippage estimation
        slippage_info = await estimate_slippage(
            src_asset=src_asset,
            dst_asset=dst_asset,
            amount=str(amount_in_units),
            sender=sender
        )
        
        if slippage_info:
            quote_data["slippage_info"] = slippage_info
        
        return quote_data
        
    except Exception as e:
        logger.error(f"Error getting swap quote for strategy: {e}", exc_info=True)
        return None


