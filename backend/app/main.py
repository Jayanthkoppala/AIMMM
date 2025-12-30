from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.config import settings
from app.routers import agent, payment, ohlcv, sentiment, autonomous, strategies, pools
from app.utils.logger import logger
from app.exceptions import BaseAPIException

app = FastAPI(
    title="AIMMM API",
    description="Backend API for AIMMM on Movement Network",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-PAYMENT-RESPONSE"]
)


# Global exception handlers
@app.exception_handler(BaseAPIException)
async def api_exception_handler(request: Request, exc: BaseAPIException):
    """Handle custom API exceptions."""
    logger.error(
        f"API exception: {exc.error_code} - {exc.message}",
        extra={"status_code": exc.status_code, "error_code": exc.error_code, "details": exc.details}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors()
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred",
                "details": {}
            }
        }
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info(f"{request.method} {request.url.path} - Client: {request.client.host if request.client else 'unknown'}")
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} - Status: {response.status_code}")
    return response


# Include routers
app.include_router(agent.router)
app.include_router(payment.router)
app.include_router(ohlcv.router)
app.include_router(sentiment.router)
app.include_router(autonomous.router)
app.include_router(strategies.router)
app.include_router(pools.router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check"""
    from app.services.supabase import supabase_service
    
    health_status = {
        "status": "ok",
        "api": "operational",
        "database": {
            "supabase_client": "unknown"
        }
    }
    
    # Check Supabase client
    if supabase_service.client:
        health_status["database"]["supabase_client"] = "connected"
    else:
        health_status["database"]["supabase_client"] = "not_configured"
        health_status["status"] = "degraded"
    
    return health_status


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "AIMMM API",
        "version": "0.1.0",
        "status": "running"
    }


@app.on_event("startup")
async def startup_event():
    """Start background services on application startup."""
    # Initialize CoinGecko database tables
    from app.utils.db_init import init_coingecko_tables, init_strategy_tables, init_users_table, reset_sequence
    if init_coingecko_tables():
        logger.info("CoinGecko database tables initialized")
        # Ensure ID sequence is correct after initialization
        reset_sequence()
    else:
        logger.error("Failed to initialize CoinGecko database tables")
    
    # Initialize users table first (required for strategy tables)
    if init_users_table():
        logger.info("Users table initialized")
    else:
        logger.error("Failed to initialize users table")
    
    # Initialize strategy builder tables
    if init_strategy_tables():
        logger.info("Strategy builder tables initialized")
    else:
        logger.error("Failed to initialize strategy builder tables")
    
    # Start OHLCV scheduler if enabled
    if settings.OHLCV_SCHEDULER_ENABLED:
        from app.services.ohlcv_scheduler import ohlcv_scheduler
        ohlcv_scheduler.start()
        logger.info("OHLCV scheduler started - fetching and storing data every minute")
    else:
        logger.info("OHLCV scheduler disabled - data will be fetched on-demand only")
    
    # Start sentiment scheduler if enabled
    if settings.SENTIMENT_SCHEDULER_ENABLED:
        from app.services.sentiment_scheduler import sentiment_scheduler
        sentiment_scheduler.start()
        logger.info("Sentiment scheduler started - will analyze sentiment every 24 hours")
    else:
        logger.info("Sentiment scheduler disabled - sentiment will be fetched on-demand only")
    
    # Start autonomous trading scheduler if enabled
    if settings.AUTONOMOUS_TRADING_ENABLED:
        from app.services.autonomous_scheduler import autonomous_scheduler
        autonomous_scheduler.start()
        logger.info("Autonomous trading scheduler started - checking markets every 5 minutes")
    else:
        logger.info("Autonomous trading scheduler disabled")
    
    # Start strategy scheduler (always enabled)
    from app.services.strategy_scheduler import strategy_scheduler
    strategy_scheduler.start()
    logger.info("Strategy scheduler started - checking active strategies every minute")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    if settings.OHLCV_SCHEDULER_ENABLED:
        from app.services.ohlcv_scheduler import ohlcv_scheduler
        ohlcv_scheduler.stop()
        logger.info("OHLCV scheduler stopped")
    
    if settings.SENTIMENT_SCHEDULER_ENABLED:
        from app.services.sentiment_scheduler import sentiment_scheduler
        sentiment_scheduler.stop()
        logger.info("Sentiment scheduler stopped")
    
    if settings.AUTONOMOUS_TRADING_ENABLED:
        from app.services.autonomous_scheduler import autonomous_scheduler
        autonomous_scheduler.stop()
        logger.info("Autonomous trading scheduler stopped")
    
    # Stop strategy scheduler
    from app.services.strategy_scheduler import strategy_scheduler
    strategy_scheduler.stop()
    logger.info("Strategy scheduler stopped")

