from typing import Optional
import re


def validate_address(address: str) -> bool:
    """Validate Movement/Aptos address format"""
    if not address:
        return False
    
    # Remove 0x prefix if present
    addr = address[2:] if address.startswith("0x") else address
    
    # Check if it's a valid hex string and correct length
    # Movement addresses are 32 bytes = 64 hex chars
    if len(addr) != 64:
        return False
    
    try:
        int(addr, 16)
        return True
    except ValueError:
        return False


def validate_feed_id(feed_id: str) -> bool:
    """Validate Switchboard feed ID format"""
    if not feed_id:
        return False
    
    # Switchboard feed IDs are typically alphanumeric with dashes
    pattern = r'^[a-zA-Z0-9\-_]+$'
    return bool(re.match(pattern, feed_id))


def validate_amount(amount: int) -> bool:
    """Validate token amount"""
    return amount > 0

