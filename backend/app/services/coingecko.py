"""
CoinGecko API Service (OPTIMIZED)
Uses the official coingecko_sdk package with proper error handling and retries.

KEY FIXES:
1. Better response parsing with comprehensive fallbacks
2. Improved meta_info extraction to handle various response formats
3. Added validation for candle data
4. Better error logging with response structure inspection
5. Fixed potential None/empty data handling
"""
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from coingecko_sdk import AsyncCoingecko, RateLimitError, NotFoundError, APIError
from app.config import settings
from app.utils.logger import logger
from app.services.api_tracker import api_tracker


# Initialize CoinGecko client
coingecko_api_key = os.environ.get("COINGECKO_PRO_API_KEY") or getattr(settings, "COINGECKO_PRO_API_KEY", "") or ""

if coingecko_api_key and coingecko_api_key.strip():
    coingecko_client = AsyncCoingecko(
        pro_api_key=coingecko_api_key.strip(),
        environment="pro",
        max_retries=3,
    )
    logger.info("CoinGecko client initialized with Pro API key")
else:
    coingecko_client = AsyncCoingecko(
        max_retries=3,
    )
    logger.warning("CoinGecko client initialized without API key (using free tier)")


def _extract_meta_info(response) -> Optional[Dict]:
    """
    Extract meta information from response with comprehensive fallback logic.
    
    Returns dict with 'base' and 'quote' keys, each containing symbol, name, address.
    """
    meta_info = None
    
    # Try to get meta from response
    if hasattr(response, 'meta'):
        meta_info = response.meta
    elif isinstance(response, dict) and 'meta' in response:
        meta_info = response['meta']
    
    if not meta_info:
        return None
    
    # Extract base and quote info
    def extract_token_info(token_obj) -> Dict:
        """Extract token info from various formats."""
        if not token_obj:
            return {'symbol': '', 'name': '', 'address': ''}
        
        # Try as Pydantic model
        if hasattr(token_obj, 'symbol'):
            return {
                'symbol': getattr(token_obj, 'symbol', ''),
                'name': getattr(token_obj, 'name', ''),
                'address': getattr(token_obj, 'address', ''),
            }
        # Try as dict
        elif isinstance(token_obj, dict):
            return {
                'symbol': token_obj.get('symbol', ''),
                'name': token_obj.get('name', ''),
                'address': token_obj.get('address', ''),
            }
        
        return {'symbol': '', 'name': '', 'address': ''}
    
    # Get base info
    base_info = None
    if hasattr(meta_info, 'base'):
        base_info = meta_info.base
    elif isinstance(meta_info, dict):
        base_info = meta_info.get('base')
    
    # Get quote info
    quote_info = None
    if hasattr(meta_info, 'quote'):
        quote_info = meta_info.quote
    elif isinstance(meta_info, dict):
        quote_info = meta_info.get('quote')
    
    if not base_info or not quote_info:
        return None
    
    return {
        'base': extract_token_info(base_info),
        'quote': extract_token_info(quote_info)
    }


def _parse_candle(candle_data, index: int) -> Optional[Dict]:
    """
    Parse a single candle from various formats.
    
    Args:
        candle_data: Candle in array, dict, or Pydantic model format
        index: Candle index for logging
    
    Returns:
        Dict with timestamp, open, high, low, close, volume or None if invalid
    """
    try:
        # Array format: [timestamp, open, high, low, close, volume]
        if isinstance(candle_data, list):
            if len(candle_data) < 5:
                logger.warning(f"Candle {index} has insufficient data: {len(candle_data)} elements")
                return None
            
            return {
                'timestamp': int(candle_data[0]) if candle_data[0] else None,
                'open': float(candle_data[1]) if candle_data[1] is not None else 0.0,
                'high': float(candle_data[2]) if candle_data[2] is not None else 0.0,
                'low': float(candle_data[3]) if candle_data[3] is not None else 0.0,
                'close': float(candle_data[4]) if candle_data[4] is not None else 0.0,
                'volume': float(candle_data[5]) if len(candle_data) > 5 and candle_data[5] is not None else 0.0,
            }
        
        # Dict format
        elif isinstance(candle_data, dict):
            return {
                'timestamp': candle_data.get('timestamp'),
                'open': float(candle_data.get('open', 0)),
                'high': float(candle_data.get('high', 0)),
                'low': float(candle_data.get('low', 0)),
                'close': float(candle_data.get('close', 0)),
                'volume': float(candle_data.get('volume', 0)),
            }
        
        # Pydantic model format
        elif hasattr(candle_data, 'timestamp'):
            return {
                'timestamp': getattr(candle_data, 'timestamp', None),
                'open': float(getattr(candle_data, 'open', 0)),
                'high': float(getattr(candle_data, 'high', 0)),
                'low': float(getattr(candle_data, 'low', 0)),
                'close': float(getattr(candle_data, 'close', 0)),
                'volume': float(getattr(candle_data, 'volume', 0)),
            }
        
        else:
            logger.warning(f"Candle {index} has unexpected format: {type(candle_data)}")
            return None
            
    except Exception as e:
        logger.error(f"Error parsing candle {index}: {e}", exc_info=True)
        return None


def _extract_ohlcv_list(response) -> List:
    """
    Extract OHLCV list from response with comprehensive fallback logic.
    
    Returns:
        List of candle data (in whatever format they are)
    """
    ohlcv_list = []
    
    try:
        # Try Pydantic model structure
        if hasattr(response, 'data'):
            data_obj = response.data
            
            # Check for attributes.ohlcv_list
            if hasattr(data_obj, 'attributes'):
                attributes = data_obj.attributes
                if hasattr(attributes, 'ohlcv_list'):
                    ohlcv_list = attributes.ohlcv_list
                elif hasattr(attributes, 'ohlcv'):
                    ohlcv_list = attributes.ohlcv
            # Check for direct ohlcv_list
            elif hasattr(data_obj, 'ohlcv_list'):
                ohlcv_list = data_obj.ohlcv_list
            elif hasattr(data_obj, 'ohlcv'):
                ohlcv_list = data_obj.ohlcv
        
        # Try dict structure
        elif isinstance(response, dict):
            data = response.get('data', {})
            if isinstance(data, dict):
                attributes = data.get('attributes', {})
                ohlcv_list = attributes.get('ohlcv_list', attributes.get('ohlcv', []))
            elif isinstance(data, list):
                ohlcv_list = data
        
        # Try direct list
        elif isinstance(response, list):
            ohlcv_list = response
        
    except Exception as e:
        logger.error(f"Error extracting OHLCV list: {e}", exc_info=True)
    
    return ohlcv_list if ohlcv_list else []


def _forward_fill_empty_candles(candles: List[Dict]) -> List[Dict]:
    """
    Forward-fill empty candles (those with all zero OHLCV values).
    
    For low-liquidity pools, CoinGecko may return empty intervals with zero values.
    This function fills them with the previous candle's close price.
    
    Args:
        candles: List of candle dicts sorted by timestamp
    
    Returns:
        List of candles with empty ones filled
    """
    if not candles:
        return candles
    
    # Sort by timestamp first
    candles = sorted(candles, key=lambda x: x.get('timestamp', 0))
    
    filled_candles = []
    last_valid_close = None
    
    for candle in candles:
        is_empty = all(candle.get(k, 0) == 0 for k in ['open', 'high', 'low', 'close'])
        
        if is_empty and last_valid_close is not None:
            # Fill with previous close (flat candle - no activity)
            filled_candle = {
                'timestamp': candle['timestamp'],
                'open': last_valid_close,
                'high': last_valid_close,
                'low': last_valid_close,
                'close': last_valid_close,
                'volume': 0.0  # No volume for synthetic candles
            }
            filled_candles.append(filled_candle)
        else:
            filled_candles.append(candle)
            # Update last valid close
            if candle.get('close', 0) > 0:
                last_valid_close = candle['close']
    
    # Count how many were filled
    empty_count = sum(1 for c in candles if all(c.get(k, 0) == 0 for k in ['open', 'high', 'low', 'close']))
    if empty_count > 0:
        logger.debug(f"Forward-filled {empty_count} empty candles out of {len(candles)}")
    
    return filled_candles


async def get_pool_ohlcv(
    pool_address: str,
    network: str = "movement",
    timeframe: str = "minute",
    aggregate: int = 1,
    limit: int = 500,
    currency: str = "usd",
    token: str = "quote",
    before_timestamp: Optional[int] = None,
    include_empty_intervals: bool = True  # Include empty intervals to avoid gaps in low-liquidity pools
) -> Tuple[List[Dict], Optional[Dict]]:
    """
    Get OHLCV candles for a pool on CoinGecko.
    
    Args:
        pool_address: Pool address
        network: Network ID (default: "movement")
        timeframe: "minute", "hour", or "day"
        aggregate: Aggregation factor (1, 5, 15, etc.)
        limit: Maximum number of candles (up to 1000)
        currency: Currency for pricing (default: "usd")
        token: "base" or "quote" (default: "quote")
        before_timestamp: Optional timestamp for pagination (fetches candles BEFORE this time)
        include_empty_intervals: Include empty intervals (default: False)
    
    Returns:
        Tuple of (candles, meta_info):
        - candles: List of candle dicts with keys: timestamp, open, high, low, close, volume
        - meta_info: Dict with 'base' and 'quote' token info, or None
    """
    # Check API limits before making request
    if not api_tracker.can_make_request():
        logger.warning(f"Cannot fetch OHLCV for pool {pool_address[:20]}... - API limit reached")
        return [], None
    
    try:
        # Use the SDK's onchain pools OHLCV endpoint
        response = await coingecko_client.onchain.networks.pools.ohlcv.get_timeframe(
            timeframe=timeframe,
            network=network,
            pool_address=pool_address,
            token=token,
            aggregate=str(aggregate) if aggregate else None,
            limit=limit if limit else None,
            currency=currency,
            before_timestamp=before_timestamp,
            include_empty_intervals=include_empty_intervals
        )
        
        # Record API call
        api_tracker.record_call()
        
        # Extract OHLCV list
        ohlcv_list = _extract_ohlcv_list(response)
        
        if not ohlcv_list:
            logger.warning(f"No OHLCV data in response for pool {pool_address[:20]}...")
            logger.debug(f"Response type: {type(response)}, has data: {hasattr(response, 'data')}")
            return [], None
        
        # Parse candles
        candles = []
        for i, candle_data in enumerate(ohlcv_list):
            parsed_candle = _parse_candle(candle_data, i)
            if parsed_candle and parsed_candle.get('timestamp'):
                candles.append(parsed_candle)
        
        # Extract meta info
        meta_info = _extract_meta_info(response)
        
        # Log results
        if meta_info and meta_info.get('base') and meta_info.get('quote'):
            base_symbol = meta_info['base'].get('symbol', 'UNKNOWN')
            quote_symbol = meta_info['quote'].get('symbol', 'UNKNOWN')
            logger.info(f"Retrieved {len(candles)} OHLCV candles for {base_symbol}/{quote_symbol} pool {pool_address[:20]}...")
        else:
            logger.info(f"Retrieved {len(candles)} OHLCV candles for pool {pool_address[:20]}...")
        
        # Validate candles
        if candles:
            # Forward-fill empty candles (zero OHLCV values) with previous candle's close
            candles = _forward_fill_empty_candles(candles)
            
            # Check for reasonable price values
            first_candle = candles[0]
            if all(first_candle[k] == 0 for k in ['open', 'high', 'low', 'close']):
                logger.warning(f"First candle has all zero prices - data may be incomplete")
            
            # Check timestamps are in order
            timestamps = [c['timestamp'] for c in candles if c.get('timestamp')]
            if len(timestamps) > 1:
                if timestamps != sorted(timestamps):
                    logger.warning(f"Candle timestamps are not in chronological order")
                    # Sort by timestamp
                    candles.sort(key=lambda x: x.get('timestamp', 0))
        
        return candles, meta_info
        
    except RateLimitError as e:
        logger.error(f"CoinGecko rate limit exceeded: {e}")
        return [], None
    except NotFoundError as e:
        logger.warning(f"Pool not found on CoinGecko: {pool_address[:20]}... - {e}")
        return [], None
    except APIError as e:
        logger.error(f"CoinGecko API error for pool {pool_address[:20]}...: {e}")
        return [], None
    except Exception as e:
        logger.error(f"Unexpected error fetching CoinGecko OHLCV for pool {pool_address[:20]}...: {e}", exc_info=True)
        # Log response structure for debugging
        try:
            logger.debug(f"Exception occurred with response type: {type(response) if 'response' in locals() else 'N/A'}")
        except:
            pass
        return [], None


async def get_token_price(
    coin_id: str,
    vs_currency: str = "usd"
) -> Optional[float]:
    """
    Get current price for a token by CoinGecko ID.
    
    Args:
        coin_id: CoinGecko coin ID (e.g., "bitcoin", "ethereum")
        vs_currency: Currency to compare against (default: "usd")
    
    Returns:
        Price as float or None if error
    """
    try:
        response = await coingecko_client.simple.price.get(
            ids=coin_id,
            vs_currencies=vs_currency
        )
        
        # Extract price from response
        if hasattr(response, coin_id):
            coin_data = getattr(response, coin_id)
            price = float(getattr(coin_data, vs_currency, 0))
            logger.debug(f"Token {coin_id} price: {price} {vs_currency}")
            return price
        elif isinstance(response, dict) and coin_id in response:
            coin_data = response[coin_id]
            if isinstance(coin_data, dict):
                price = float(coin_data.get(vs_currency, 0))
            else:
                price = float(getattr(coin_data, vs_currency, 0))
            logger.debug(f"Token {coin_id} price: {price} {vs_currency}")
            return price
        
        logger.warning(f"Could not find price for {coin_id} in response")
        return None
        
    except RateLimitError:
        logger.error("CoinGecko rate limit exceeded. Please try again later.")
        return None
    except NotFoundError:
        logger.warning(f"Token not found on CoinGecko: {coin_id}")
        return None
    except APIError as e:
        logger.error(f"CoinGecko API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching CoinGecko price: {e}", exc_info=True)
        return None


async def get_pool_price(
    pool_address: str,
    network: str = "movement",
    currency: str = "usd",
    token: str = "quote"
) -> Optional[float]:
    """
    Get current price from pool OHLCV (latest candle close price).
    
    Args:
        pool_address: Pool address
        network: Network ID (default: "movement")
        currency: Currency for pricing (default: "usd")
        token: "base" or "quote" (default: "quote")
    
    Returns:
        Current price as float or None if error
    """
    candles, _ = await get_pool_ohlcv(
        pool_address=pool_address,
        network=network,
        timeframe="minute",
        aggregate=1,
        limit=1,
        currency=currency,
        token=token
    )
    
    if candles and len(candles) > 0:
        latest_candle = candles[-1]
        close_price = latest_candle.get('close', 0)
        if close_price > 0:
            logger.debug(f"Pool {pool_address[:20]}... current price: {close_price} {currency}")
            return close_price
        else:
            logger.warning(f"Latest candle for pool {pool_address[:20]}... has zero close price")
    
    return None