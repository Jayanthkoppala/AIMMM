from pydantic_settings import BaseSettings
from typing import List, Union
from pydantic import field_validator
import os


class Settings(BaseSettings):
    # Movement Network
    MOVEMENT_RPC: str = "https://testnet.movementnetwork.xyz/v1"
    MOVEMENT_NETWORK: str = "movement-testnet"
    
    # Switchboard
    # Aggregator addresses (on-chain addresses) - comma-separated
    # These are the addresses of Aggregator objects deployed on Movement
    # Format: 0x... (64-character hex addresses)
    SWITCHBOARD_FEED_IDS: str = ""  # Comma-separated aggregator addresses
    SWITCHBOARD_API_URL: str = "https://api.switchboard.xyz/api"  # Fallback API (if available)
    
    # Uniswap V2
    UNISWAP_FACTORY_ADDRESS: str = ""
    TOKEN_A_ADDRESS: str = ""
    TOKEN_B_ADDRESS: str = ""
    
    # OpenRouter
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # x402 Payment
    X402_RECEIVER_ADDRESS: str = ""
    X402_FACILITATOR_URL: str = "https://facilitator.stableyard.fi"
    BASE_AGENT_COST_USDC: float = 0.001
    
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    
    # Direct PostgreSQL Connection (alternative to Supabase client)
    # Can use DATABASE_URL (Supabase format) or individual settings
    DATABASE_URL: str = ""  # Format: postgresql://user:password@host:port/dbname
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_HOST: str = ""
    DB_PORT: str = "5432"
    DB_NAME: str = ""
    
    # Agent Executor Contract
    AGENT_EXECUTOR_ADDRESS: str = ""
    
    # CORS (can be comma-separated string or list)
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # OHLCV Collection
    AUTO_START_OHLCV: str = "true"  # Auto-start OHLCV collection on server start
    OHLCV_POLL_INTERVAL_SECONDS: int = 10  # How often to poll Switchboard (seconds)
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def get_switchboard_feeds(self) -> List[str]:
        """Parse comma-separated feed IDs into list"""
        if not self.SWITCHBOARD_FEED_IDS:
            return []
        return [feed_id.strip() for feed_id in self.SWITCHBOARD_FEED_IDS.split(",")]


settings = Settings()

