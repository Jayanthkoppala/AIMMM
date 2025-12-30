from pydantic_settings import BaseSettings
from typing import List, Union
from pydantic import field_validator
import os


class Settings(BaseSettings):
    # Movement Network
    MOVEMENT_RPC: str = "https://testnet.movementnetwork.xyz/v1"
    MOVEMENT_NETWORK: str = "movement-testnet"
    
    # CoinGecko
    COINGECKO_PRO_API_KEY: str = ""  # Load from environment variable COINGECKO_PRO_API_KEY
    
    # Mosaic DEX
    MOSAIC_API_KEY: str = "RgutcJWyaiBNCYDig52D3pkW6M8VEl-7"
    MOSAIC_API_URL: str = "https://api.mosaic.ag/v1"
    
    # OpenRouter
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "deepseek/deepseek-r1"  # Default reasoning model
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # Grok AI (X.AI) - Sentiment Analysis
    GROK_API_KEY: str = ""
    
    # x402 Payment
    X402_RECEIVER_ADDRESS: str = ""
    X402_FACILITATOR_URL: str = "https://facilitator.stableyard.fi"
    BASE_AGENT_COST_USDC: float = 0.001
    
    
    # Direct PostgreSQL Connection (alternative to Supabase client)
    # Can use DATABASE_URL (recommended) or individual settings below
    # Supabase format: postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
    # Replace [YOUR-PASSWORD] with your actual Supabase database password
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
    
    # OHLCV Cache (CoinGecko)
    OHLCV_CACHE_TTL_SECONDS: int = 300  # Cache OHLCV data for scheduler (5 minutes)
    OHLCV_FRONTEND_CACHE_TTL_SECONDS: int = 60  # Cache for frontend requests (1 minute)
    
    # OHLCV Scheduler - API Usage Management
    OHLCV_SCHEDULER_ENABLED: bool = True  # Enable automatic OHLCV data fetching
    OHLCV_SCHEDULER_RESERVE_FOR_MANUAL: float = 0.2  # Reserve 20% of API calls for manual/frontend requests
    OHLCV_SCHEDULER_MAX_POOLS: int = 10  # Maximum pools to monitor
    OHLCV_SCHEDULER_INTERVAL_SECONDS: int = 324  # Dynamic interval (5.4 min for 2 pools) - will be calculated automatically
    OHLCV_SCHEDULER_LOOKBACK_MINUTES: int = 240  # Fetch last 4 hours on initial run (fallback if backfill not triggered)
    
    # Sentiment Scheduler
    SENTIMENT_SCHEDULER_ENABLED: bool = True  # Enable automatic sentiment analysis (runs every 24 hours)
    
    # Privy Configuration
    PRIVY_APP_ID: str = ""
    PRIVY_APP_SECRET: str = ""
    PRIVY_VERIFICATION_KEY: str = ""  # For JWT verification
    
    # Autonomous Trading
    AUTONOMOUS_WALLET_ENCRYPTION_KEY: str = ""  # AES-256 key for encrypting private keys (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    AUTONOMOUS_TRADING_ENABLED: bool = True
    
    # LangGraph Agent System
    USE_LANGGRAPH_AGENTS: bool = True  # Enable new LangGraph agent-based execution
    
    # Runtime Mode
    # RUN_MODE=api → HTTP server only (no schedulers, no background workers)
    # RUN_MODE=worker → background schedulers only (no HTTP traffic)
    RUN_MODE: str = "api"  # Default to API mode for safety
    
    # CoinGecko API Limits
    COINGECKO_API_LIMIT_MONTHLY: int = 10000  # Monthly API call limit
    COINGECKO_API_LIMIT_PER_MINUTE: int = 30  # Rate limit: 30 requests per minute
    COINGECKO_API_CALLS_THIS_MONTH: int = 0  # Track API usage (reset monthly)
    
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
        extra = "ignore"  # Ignore extra fields from .env (like old UNISWAP_FACTORY_ADDRESS)
    


settings = Settings()

