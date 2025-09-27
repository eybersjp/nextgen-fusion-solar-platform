#!/usr/bin/env python3
"""
Configuration settings for the Compliance Service

This module defines all configuration settings using Pydantic for
environment variable management and validation.
"""

import os
from typing import List, Optional, Dict, Any
from functools import lru_cache

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    APP_NAME: str = Field("NextGen Fusion Compliance Service", env="APP_NAME")
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(False, env="DEBUG")
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8003, env="PORT")
    
    # Database settings
    DATABASE_URL: str = Field(
        "sqlite+aiosqlite:///./compliance.db",
        env="DATABASE_URL"
    )
    DATABASE_ECHO: bool = Field(False, env="DATABASE_ECHO")
    DATABASE_POOL_SIZE: int = Field(10, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(20, env="DATABASE_MAX_OVERFLOW")
    
    # Security settings
    SECRET_KEY: str = Field(
        "your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    ALGORITHM: str = Field("HS256", env="ALGORITHM")
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS"
    )
    
    # Compliance rule engine settings
    RULE_ENGINE_CACHE_TTL: int = Field(3600, env="RULE_ENGINE_CACHE_TTL")  # 1 hour
    RULE_VALIDATION_TIMEOUT: int = Field(30, env="RULE_VALIDATION_TIMEOUT")  # 30 seconds
    MAX_CONCURRENT_VALIDATIONS: int = Field(10, env="MAX_CONCURRENT_VALIDATIONS")
    
    # Regional compliance settings
    SUPPORTED_REGIONS: List[str] = Field(
        ["US", "EU", "AU", "ZA", "CA", "UK", "DE", "FR", "ES", "IT"],
        env="SUPPORTED_REGIONS"
    )
    DEFAULT_REGION: str = Field("US", env="DEFAULT_REGION")
    
    # Compliance standards
    SUPPORTED_STANDARDS: List[str] = Field(
        [
            "IEC_61215",    # PV module design qualification
            "IEC_61730",    # PV module safety qualification
            "UL_1703",      # Flat-plate PV modules and panels
            "IEEE_1547",    # Interconnection and interoperability
            "NEC_690",      # National Electrical Code Article 690
            "IBC_2021",     # International Building Code
            "ASCE_7",       # Minimum design loads for buildings
            "NFPA_70",      # National Electrical Code
            "EN_61215",     # European PV module standard
            "AS_5033",      # Australian installation standard
            "SANS_10142",   # South African wiring code
        ],
        env="SUPPORTED_STANDARDS"
    )
    
    # Cache settings
    REDIS_URL: Optional[str] = Field(None, env="REDIS_URL")
    CACHE_TTL: int = Field(3600, env="CACHE_TTL")  # 1 hour
    ENABLE_CACHING: bool = Field(True, env="ENABLE_CACHING")
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = Field(100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(60, env="RATE_LIMIT_WINDOW")  # 60 seconds
    
    # Monitoring settings
    ENABLE_METRICS: bool = Field(True, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(9003, env="METRICS_PORT")
    
    # Logging settings
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field("json", env="LOG_FORMAT")  # json or text
    LOG_FILE: Optional[str] = Field(None, env="LOG_FILE")
    
    # External API settings
    BUILDING_CODE_API_URL: Optional[str] = Field(None, env="BUILDING_CODE_API_URL")
    BUILDING_CODE_API_KEY: Optional[str] = Field(None, env="BUILDING_CODE_API_KEY")
    
    ELECTRICAL_CODE_API_URL: Optional[str] = Field(None, env="ELECTRICAL_CODE_API_URL")
    ELECTRICAL_CODE_API_KEY: Optional[str] = Field(None, env="ELECTRICAL_CODE_API_KEY")
    
    SAFETY_STANDARDS_API_URL: Optional[str] = Field(None, env="SAFETY_STANDARDS_API_URL")
    SAFETY_STANDARDS_API_KEY: Optional[str] = Field(None, env="SAFETY_STANDARDS_API_KEY")
    
    # Compliance validation settings
    VALIDATION_BATCH_SIZE: int = Field(50, env="VALIDATION_BATCH_SIZE")
    VALIDATION_RETRY_ATTEMPTS: int = Field(3, env="VALIDATION_RETRY_ATTEMPTS")
    VALIDATION_RETRY_DELAY: int = Field(5, env="VALIDATION_RETRY_DELAY")  # seconds
    
    # Report generation settings
    REPORT_STORAGE_PATH: str = Field("./reports", env="REPORT_STORAGE_PATH")
    REPORT_RETENTION_DAYS: int = Field(90, env="REPORT_RETENTION_DAYS")
    MAX_REPORT_SIZE_MB: int = Field(50, env="MAX_REPORT_SIZE_MB")
    
    # Compliance thresholds
    COMPLIANCE_SCORE_THRESHOLD: float = Field(0.85, env="COMPLIANCE_SCORE_THRESHOLD")
    CRITICAL_VIOLATION_THRESHOLD: int = Field(0, env="CRITICAL_VIOLATION_THRESHOLD")
    WARNING_VIOLATION_THRESHOLD: int = Field(5, env="WARNING_VIOLATION_THRESHOLD")
    
    # Notification settings
    ENABLE_NOTIFICATIONS: bool = Field(True, env="ENABLE_NOTIFICATIONS")
    NOTIFICATION_EMAIL_FROM: Optional[str] = Field(None, env="NOTIFICATION_EMAIL_FROM")
    NOTIFICATION_EMAIL_SMTP_HOST: Optional[str] = Field(None, env="NOTIFICATION_EMAIL_SMTP_HOST")
    NOTIFICATION_EMAIL_SMTP_PORT: int = Field(587, env="NOTIFICATION_EMAIL_SMTP_PORT")
    NOTIFICATION_EMAIL_USERNAME: Optional[str] = Field(None, env="NOTIFICATION_EMAIL_USERNAME")
    NOTIFICATION_EMAIL_PASSWORD: Optional[str] = Field(None, env="NOTIFICATION_EMAIL_PASSWORD")
    
    # Webhook settings
    WEBHOOK_TIMEOUT: int = Field(30, env="WEBHOOK_TIMEOUT")
    WEBHOOK_RETRY_ATTEMPTS: int = Field(3, env="WEBHOOK_RETRY_ATTEMPTS")
    
    # File upload settings
    MAX_UPLOAD_SIZE_MB: int = Field(100, env="MAX_UPLOAD_SIZE_MB")
    ALLOWED_FILE_TYPES: List[str] = Field(
        [".pdf", ".dwg", ".dxf", ".json", ".xml", ".csv"],
        env="ALLOWED_FILE_TYPES"
    )
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("SUPPORTED_REGIONS", pre=True)
    def parse_supported_regions(cls, v):
        """Parse supported regions from string or list."""
        if isinstance(v, str):
            return [region.strip().upper() for region in v.split(",")]
        return [region.upper() for region in v]
    
    @validator("SUPPORTED_STANDARDS", pre=True)
    def parse_supported_standards(cls, v):
        """Parse supported standards from string or list."""
        if isinstance(v, str):
            return [standard.strip().upper() for standard in v.split(",")]
        return [standard.upper() for standard in v]
    
    @validator("ALLOWED_FILE_TYPES", pre=True)
    def parse_allowed_file_types(cls, v):
        """Parse allowed file types from string or list."""
        if isinstance(v, str):
            return [ext.strip().lower() for ext in v.split(",")]
        return [ext.lower() for ext in v]
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()
    
    @validator("LOG_FORMAT")
    def validate_log_format(cls, v):
        """Validate log format."""
        valid_formats = ["json", "text"]
        if v.lower() not in valid_formats:
            raise ValueError(f"LOG_FORMAT must be one of {valid_formats}")
        return v.lower()
    
    @validator("DEFAULT_REGION")
    def validate_default_region(cls, v, values):
        """Validate default region is in supported regions."""
        if "SUPPORTED_REGIONS" in values and v.upper() not in values["SUPPORTED_REGIONS"]:
            raise ValueError(f"DEFAULT_REGION must be one of {values['SUPPORTED_REGIONS']}")
        return v.upper()
    
    @validator("COMPLIANCE_SCORE_THRESHOLD")
    def validate_compliance_score(cls, v):
        """Validate compliance score threshold."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("COMPLIANCE_SCORE_THRESHOLD must be between 0.0 and 1.0")
        return v
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Returns:
        Settings: Application settings
    """
    return Settings()