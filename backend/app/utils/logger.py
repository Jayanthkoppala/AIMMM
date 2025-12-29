"""
Structured logging configuration for the application.
"""
import logging
import sys
from typing import Optional
from app.config import settings


def setup_logger(name: str = "ai_trading_agent", level: Optional[str] = None) -> logging.Logger:
    """
    Set up a structured logger with consistent formatting.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, uses LOG_LEVEL from settings or defaults to INFO
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Get log level from settings or environment
    if level is None:
        level = getattr(settings, "LOG_LEVEL", "INFO").upper()
    
    log_level = getattr(logging, level, logging.INFO)
    logger.setLevel(log_level)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger


# Create default logger instance
logger = setup_logger()



