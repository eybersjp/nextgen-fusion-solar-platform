#!/usr/bin/env python3
"""
Configuration settings for the Currency Service.

Manages environment variables, database connections, and service configuration
for the multi-currency support system.
"""

import os
from typing import List, Optional
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application settings
    APP_NAME: str = Field(default="Currency Service", env="APP_NAME")
    VERSION: str = Field(default="1.0.0", env="VERSION")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # Database settings
    DATABASE_URL: str = Field(
        default="sqlite:///./nextgen_currency.db",
        env="DATABASE_URL",
        description="Database connection URL"
    )
    DATABASE_ECHO: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Security settings
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY",
        description="Secret key for JWT token generation"
    )
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="ALLOWED_ORIGINS"
    )
    
    # External API settings
    EXCHANGE_RATE_API_KEY: Optional[str] = Field(default=None, env="EXCHANGE_RATE_API_KEY")
    EXCHANGE_RATE_API_URL: str = Field(
        default="https://api.exchangerate-api.com/v4/latest",
        env="EXCHANGE_RATE_API_URL"
    )
    
    # Alternative exchange rate providers
    FIXER_API_KEY: Optional[str] = Field(default=None, env="FIXER_API_KEY")
    FIXER_API_URL: str = Field(
        default="https://api.fixer.io/latest",
        env="FIXER_API_URL"
    )
    
    CURRENCYLAYER_API_KEY: Optional[str] = Field(default=None, env="CURRENCYLAYER_API_KEY")
    CURRENCYLAYER_API_URL: str = Field(
        default="https://api.currencylayer.com/live",
        env="CURRENCYLAYER_API_URL"
    )
    
    # Cache settings
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    CACHE_TTL_SECONDS: int = Field(default=3600, env="CACHE_TTL_SECONDS")  # 1 hour
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    
    # Monitoring
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Currency settings
    DEFAULT_BASE_CURRENCY: str = Field(default="USD", env="DEFAULT_BASE_CURRENCY")
    SUPPORTED_CURRENCIES: List[str] = Field(
        default=["USD", "EUR", "GBP", "ZAR", "AUD", "CAD", "JPY", "CHF"],
        env="SUPPORTED_CURRENCIES"
    )
    
    # Update intervals
    EXCHANGE_RATE_UPDATE_INTERVAL_MINUTES: int = Field(
        default=60,
        env="EXCHANGE_RATE_UPDATE_INTERVAL_MINUTES"
    )
    
    # Compliance settings
    FINANCIAL_COMPLIANCE_MODE: bool = Field(default=True, env="FINANCIAL_COMPLIANCE_MODE")
    AUDIT_LOG_ENABLED: bool = Field(default=True, env="AUDIT_LOG_ENABLED")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings.
    
    Returns:
        Settings: Application configuration settings
    """
    return Settings()