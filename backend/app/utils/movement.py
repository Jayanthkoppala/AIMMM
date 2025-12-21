"""
Movement Network SDK utilities.
Placeholder for Movement SDK integration.
"""

from app.config import settings


def get_movement_client():
    """
    Get Movement/Aptos client instance.
    In production, this would initialize the SDK client.
    """
    # Placeholder - would use actual SDK
    # from aptos_sdk import AptosClient
    # return AptosClient(settings.MOVEMENT_RPC)
    return None


def format_address(address: str) -> str:
    """Format Movement address to standard format"""
    if address.startswith("0x"):
        return address
    return f"0x{address}"

