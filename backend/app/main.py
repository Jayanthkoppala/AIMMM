from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.config import settings
from app.routers import agent, payment, ohlcv
from app.utils.logger import logger
from app.exceptions import BaseAPIException

app = FastAPI(
    title="AI Trading Agent API",
    description="Backend API for AI Trading Agent on Movement Network",
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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including database connection"""
    from app.utils.database import db_connection
    from app.services.supabase import supabase_service
    
    health_status = {
        "status": "ok",
        "api": "operational",
        "database": {
            "direct_postgres": "unknown",
            "supabase_client": "unknown"
        }
    }
    
    # Test direct PostgreSQL connection
    try:
        db_connected = db_connection.test_connection()
        health_status["database"]["direct_postgres"] = "connected" if db_connected else "disconnected"
    except Exception as e:
        health_status["database"]["direct_postgres"] = f"error: {str(e)}"
    
    # Check Supabase client
    if supabase_service.client:
        health_status["database"]["supabase_client"] = "connected"
    else:
        health_status["database"]["supabase_client"] = "not_configured"
    
    # Overall status
    if health_status["database"]["direct_postgres"] != "connected":
        health_status["status"] = "degraded"
    
    return health_status


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "AI Trading Agent API",
        "version": "0.1.0",
        "status": "running"
    }


@app.on_event("startup")
async def startup_event():
    """Start background services on application startup."""
    from app.services.ohlcv_collector import ohlcv_collector
    
    # Auto-start OHLCV collection if configured
    # You can disable this by setting AUTO_START_OHLCV=false in .env
    auto_start = getattr(settings, 'AUTO_START_OHLCV', 'true').lower() == 'true'
    
    if auto_start:
        logger.info("Auto-starting OHLCV collection...")
        await ohlcv_collector.start()
    else:
        logger.info("OHLCV collection auto-start disabled. Use /ohlcv/start to start manually.")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background services on application shutdown."""
    from app.services.ohlcv_collector import ohlcv_collector
    
    logger.info("Stopping background services...")
    await ohlcv_collector.stop()

