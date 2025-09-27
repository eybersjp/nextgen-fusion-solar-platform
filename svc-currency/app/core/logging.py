#!/usr/bin/env python3
"""
Logging configuration for the Currency Service.

Provides structured JSON logging with correlation IDs for request tracing
and compliance audit trails.
"""

import logging
import logging.config
import sys
from typing import Dict, Any

from .config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """Setup application logging configuration.
    
    Configures structured JSON logging for production environments
    and human-readable logging for development.
    """
    
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    if settings.ENVIRONMENT == "production":
        # Production: JSON structured logging
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d}',
                    "datefmt": "%Y-%m-%dT%H:%M:%S.%fZ"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": log_level,
                    "formatter": "json",
                    "stream": sys.stdout
                }
            },
            "root": {
                "level": log_level,
                "handlers": ["console"]
            },
            "loggers": {
                "uvicorn": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False
                },
                "uvicorn.access": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False
                },
                "sqlalchemy.engine": {
                    "level": "WARNING",
                    "handlers": ["console"],
                    "propagate": False
                }
            }
        }
    else:
        # Development: Human-readable logging
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]",
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": log_level,
                    "formatter": "detailed",
                    "stream": sys.stdout
                }
            },
            "root": {
                "level": log_level,
                "handlers": ["console"]
            },
            "loggers": {
                "uvicorn": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False
                },
                "uvicorn.access": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False
                },
                "sqlalchemy.engine": {
                    "level": "WARNING" if not settings.DATABASE_ECHO else "INFO",
                    "handlers": ["console"],
                    "propagate": False
                }
            }
        }
    
    logging.config.dictConfig(logging_config)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


class CorrelationFilter(logging.Filter):
    """Logging filter to add correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to log record if available.
        
        Args:
            record: Log record to filter
            
        Returns:
            bool: Always True (don't filter out records)
        """
        # Try to get correlation ID from context
        # This would be set by middleware in a real implementation
        correlation_id = getattr(record, 'correlation_id', None)
        if not correlation_id:
            # Generate a default correlation ID if none exists
            import uuid
            correlation_id = str(uuid.uuid4())[:8]
        
        record.correlation_id = correlation_id
        return True


class AuditLogger:
    """Specialized logger for financial compliance audit trails."""
    
    def __init__(self):
        self.logger = get_logger("currency.audit")
    
    def log_conversion(self, user_id: str, from_currency: str, to_currency: str, 
                      amount: float, rate: float, converted_amount: float,
                      transaction_id: str = None) -> None:
        """Log currency conversion for audit purposes.
        
        Args:
            user_id: User performing the conversion
            from_currency: Source currency code
            to_currency: Target currency code
            amount: Original amount
            rate: Exchange rate used
            converted_amount: Converted amount
            transaction_id: Optional transaction identifier
        """
        audit_data = {
            "event_type": "currency_conversion",
            "user_id": user_id,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "amount": amount,
            "exchange_rate": rate,
            "converted_amount": converted_amount,
            "transaction_id": transaction_id
        }
        
        self.logger.info(f"Currency conversion audit: {audit_data}")
    
    def log_rate_update(self, source: str, currency_pairs: int, timestamp: str) -> None:
        """Log exchange rate update for audit purposes.
        
        Args:
            source: Rate provider source
            currency_pairs: Number of currency pairs updated
            timestamp: Update timestamp
        """
        audit_data = {
            "event_type": "exchange_rate_update",
            "source": source,
            "currency_pairs_updated": currency_pairs,
            "update_timestamp": timestamp
        }
        
        self.logger.info(f"Exchange rate update audit: {audit_data}")
    
    def log_compliance_check(self, user_id: str, transaction_id: str, 
                           compliance_result: str, notes: str = None) -> None:
        """Log compliance check for audit purposes.
        
        Args:
            user_id: User being checked
            transaction_id: Transaction identifier
            compliance_result: Result of compliance check
            notes: Optional compliance notes
        """
        audit_data = {
            "event_type": "compliance_check",
            "user_id": user_id,
            "transaction_id": transaction_id,
            "compliance_result": compliance_result,
            "notes": notes
        }
        
        self.logger.info(f"Compliance check audit: {audit_data}")


# Global audit logger instance
audit_logger = AuditLogger()