"""
Custom exception classes for the application.
"""
from typing import Optional, Dict, Any


class BaseAPIException(Exception):
    """Base exception for all API exceptions."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or f"ERROR_{status_code}"
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BaseAPIException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details={"field": field, **(details or {})}
        )


class PaymentRequiredError(BaseAPIException):
    """Raised when payment is required (402)."""
    
    def __init__(self, payment_requirements: Dict[str, Any]):
        super().__init__(
            message="Payment required",
            status_code=402,
            error_code="PAYMENT_REQUIRED",
            details={"accepts": [payment_requirements]}
        )


class PaymentVerificationError(BaseAPIException):
    """Raised when payment verification fails."""
    
    def __init__(self, message: str = "Payment verification failed"):
        super().__init__(
            message=message,
            status_code=402,
            error_code="PAYMENT_VERIFICATION_FAILED"
        )


class OracleError(BaseAPIException):
    """Raised when oracle price fetching fails."""
    
    def __init__(self, message: str = "Failed to fetch oracle prices"):
        super().__init__(
            message=message,
            status_code=503,
            error_code="ORACLE_ERROR"
        )


class LLMError(BaseAPIException):
    """Raised when LLM service fails."""
    
    def __init__(self, message: str = "LLM service error"):
        super().__init__(
            message=message,
            status_code=503,
            error_code="LLM_ERROR"
        )


class DatabaseError(BaseAPIException):
    """Raised when database operation fails."""
    
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR"
        )


class TradeExecutionError(BaseAPIException):
    """Raised when trade execution fails."""
    
    def __init__(self, message: str = "Trade execution failed"):
        super().__init__(
            message=message,
            status_code=500,
            error_code="TRADE_EXECUTION_ERROR"
        )



