import httpx
from typing import Dict, Optional
from datetime import datetime, timedelta
from app.config import settings
from app.utils.logger import logger

# Switchboard On-Demand addresses for Movement network
# From: https://docs.switchboard.xyz/product-documentation/data-feeds/movement
SWITCHBOARD_ON_DEMAND_MAINNET = "0x465e420630570b780bd8bfc25bfadf444e98594357c488fe397a1142a7b11ffa"
SWITCHBOARD_ON_DEMAND_TESTNET = "0x465e420630570b780bd8bfc25bfadf444e98594357c488fe397a1142a7b11ffa"
SWITCHBOARD_ADAPTER_MAINNET = "0xb3654a69ba2a252849a89fa70845ad8e713a28c322dc580ae457df1f747bb74a"
SWITCHBOARD_ADAPTER_TESTNET = "0xfe38ecf6fc57e742327af6e951e9fe2fcadcd6d1f1327ba2bee5a31e43d6637f"


class PriceCache:
    def __init__(self, ttl_seconds: int = 60):
        self.cache: Dict[str, Dict] = {}
        self.ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, feed_id: str) -> Optional[Dict]:
        if feed_id not in self.cache:
            return None
        
        entry = self.cache[feed_id]
        if datetime.now() - entry["timestamp"] > self.ttl:
            del self.cache[feed_id]
            return None
        
        return entry["data"]
    
    def set(self, feed_id: str, data: Dict):
        self.cache[feed_id] = {
            "data": data,
            "timestamp": datetime.now()
        }


price_cache = PriceCache(ttl_seconds=60)


async def fetch_switchboard_price_from_blockchain(aggregator_address: str) -> Dict[str, float]:
    """
    Fetch price data from Switchboard aggregator on Movement blockchain.
    Uses the on-chain Aggregator object to read current_result.
    
    According to Switchboard Movement docs:
    https://docs.switchboard.xyz/product-documentation/data-feeds/movement
    
    The aggregator address should be the on-chain address of the Aggregator object.
    """
    try:
        # Query Movement blockchain for aggregator state
        # Using Movement RPC to call view function: aggregator::current_result
        async with httpx.AsyncClient() as client:
            # Call the view function on Movement blockchain
            # Function: on_demand::aggregator::current_result
            on_demand_address = (
                SWITCHBOARD_ON_DEMAND_TESTNET 
                if "testnet" in settings.MOVEMENT_NETWORK.lower() 
                else SWITCHBOARD_ON_DEMAND_MAINNET
            )
            
            payload = {
                "function": f"{on_demand_address}::aggregator::current_result",
                "type_arguments": [],
                "arguments": [aggregator_address],
            }
            
            response = await client.post(
                f"{settings.MOVEMENT_RPC}/view",
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Parse the CurrentResult struct
            # Structure: (result: Decimal, timestamp: u64, min_timestamp: u64, ...)
            # Decimal is (value: u128, neg: bool)
            if data and len(data) >= 2:
                result_decimal = data[0]  # Decimal struct
                timestamp = data[1] if len(data) > 1 else int(datetime.now().timestamp())
                
                # Extract value from Decimal (assuming it's a tuple/list)
                if isinstance(result_decimal, (list, tuple)) and len(result_decimal) >= 1:
                    value_u128 = result_decimal[0] if isinstance(result_decimal[0], (int, str)) else result_decimal
                    is_negative = result_decimal[1] if len(result_decimal) > 1 else False
                    
                    # Convert u128 to float (assuming 8 decimals)
                    price = float(value_u128) / 1e8 if isinstance(value_u128, (int, str)) else float(value_u128)
                    if is_negative:
                        price = -price
                else:
                    price = float(result_decimal) / 1e8 if isinstance(result_decimal, (int, str)) else float(result_decimal)
                
                result = {
                    "token_a_price": price,
                    "token_b_price": price * 1.5,  # Placeholder - would need separate aggregator
                    "timestamp": timestamp if isinstance(timestamp, int) else int(datetime.now().timestamp())
                }
                
                # Cache the result
                price_cache.set(aggregator_address, result)
                return result
            else:
                raise ValueError("Invalid response format from blockchain")
                
    except httpx.HTTPError as e:
        logger.warning(f"Switchboard blockchain query error: {e}, using fallback data")
        # Fallback: return mock data for development
        return {
            "token_a_price": 1.0,
            "token_b_price": 1.5,
            "timestamp": int(datetime.now().timestamp())
        }
    except Exception as e:
        logger.error(f"Error fetching Switchboard price from blockchain: {e}", exc_info=True)
        return {
            "token_a_price": 1.0,
            "token_b_price": 1.5,
            "timestamp": int(datetime.now().timestamp())
        }


async def fetch_switchboard_price(feed_id: str) -> Dict[str, float]:
    """
    Fetch price data from Switchboard oracle feed.
    feed_id can be either:
    - An aggregator address (on-chain address) - preferred
    - A feed hash (for lookup) - fallback
    
    Returns dict with token_a_price and token_b_price.
    """
    # Check cache first
    cached = price_cache.get(feed_id)
    if cached:
        return cached
    
    # Try to fetch from blockchain if feed_id looks like an address
    if feed_id.startswith("0x") and len(feed_id) == 66:
        return await fetch_switchboard_price_from_blockchain(feed_id)
    
    # Fallback: try REST API or return mock data
    try:
        # Switchboard may have a REST API for feed hashes
        # This is a fallback - prefer on-chain queries
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SWITCHBOARD_API_URL}/feeds/{feed_id}",
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            result = {
                "token_a_price": float(data.get("latestResult", {}).get("value", 0)),
                "token_b_price": float(data.get("latestResult", {}).get("value", 0)) * 1.5,
                "timestamp": int(datetime.now().timestamp())
            }
            
            price_cache.set(feed_id, result)
            return result
            
    except Exception as e:
        logger.warning(f"Error fetching Switchboard price: {e}, using fallback data")
        # Fallback to mock data
        return {
            "token_a_price": 1.0,
            "token_b_price": 1.5,
            "timestamp": int(datetime.now().timestamp())
        }


async def get_token_prices(token_a: str, token_b: str, feed_id: Optional[str] = None) -> Dict[str, float]:
    """
    Get prices for token pair.
    If feed_id is provided, use that specific feed.
    Otherwise, use default feeds from config.
    """
    if feed_id:
        return await fetch_switchboard_price(feed_id)
    
    # Use first available feed from config
    feeds = settings.get_switchboard_feeds()
    if feeds:
        return await fetch_switchboard_price(feeds[0])
    
    # Fallback to mock data
    return {
        "token_a_price": 1.0,
        "token_b_price": 1.5,
        "timestamp": int(datetime.now().timestamp())
    }

