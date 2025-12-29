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


def validate_pool_address(pool_address: str) -> bool:
    """Validate CoinGecko pool address format"""
    if not pool_address:
        return False
    
    # Pool addresses are hex strings with 0x prefix, typically 66 chars (0x + 64 hex)
    if not pool_address.startswith("0x"):
        return False
    
    addr = pool_address[2:]
    if len(addr) != 64:
        return False
    
    try:
        int(addr, 16)
        return True
    except ValueError:
        return False

