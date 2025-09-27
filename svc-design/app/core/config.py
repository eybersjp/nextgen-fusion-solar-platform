"""Configuration settings for the Design Service.

Manages environment variables, database settings,
and application configuration.
"""

import os
from functools import lru_cache
from typing import Optional, List

from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application settings
    APP_NAME: str = "NextGen Fusion Design Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    RELOAD: bool = False
    
    # Security settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    
    # Password settings
    MIN_PASSWORD_LENGTH: int = 8
    REQUIRE_UPPERCASE: bool = True
    REQUIRE_LOWERCASE: bool = True
    REQUIRE_DIGITS: bool = True
    REQUIRE_SPECIAL_CHARS: bool = True
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./nextgen_design.db"
    DATABASE_ASYNC_URL: str = "sqlite+aiosqlite:///./nextgen_design.db"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # Async database settings
    ASYNC_DATABASE_URL: Optional[str] = None
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10
    REDIS_TIMEOUT: int = 5
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_HEADERS: List[str] = ["*"]
    
    # File storage settings
    STORAGE_TYPE: str = "local"  # local, s3, gcs, azure
    STORAGE_PATH: str = "./storage"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_FILE_TYPES: List[str] = [
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        "jpg", "jpeg", "png", "gif", "svg", "bmp", "tiff",
        "dwg", "dxf", "step", "stp", "iges", "igs",
        "zip", "rar", "7z", "tar", "gz",
        "txt", "csv", "json", "xml", "yaml", "yml"
    ]
    
    # AWS S3 settings (if using S3 storage)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: Optional[str] = None
    
    # External service URLs
    API_GATEWAY_URL: str = "http://localhost:8000"
    COMPLIANCE_SERVICE_URL: str = "http://localhost:8002"
    FINANCE_SERVICE_URL: str = "http://localhost:8003"
    PROCURE_SERVICE_URL: str = "http://localhost:8004"
    OPS_SERVICE_URL: str = "http://localhost:8005"
    SUPPORT_SERVICE_URL: str = "http://localhost:8006"
    
    # Weather API settings
    WEATHER_API_KEY: Optional[str] = None
    WEATHER_API_URL: str = "https://api.openweathermap.org/data/2.5"
    
    # Solar calculation settings
    PVLIB_CACHE_SIZE: int = 1000
    SOLAR_POSITION_CACHE_TTL: int = 3600  # 1 hour
    
    # Shading analysis settings
    MAX_SHADING_GRID_SIZE: int = 1000000  # 1M points
    SHADING_ANALYSIS_TIMEOUT: int = 3600  # 1 hour
    
    # BOM settings
    DEFAULT_CURRENCY: str = "USD"
    CURRENCY_UPDATE_INTERVAL: int = 3600  # 1 hour
    PRICE_CACHE_TTL: int = 1800  # 30 minutes
    
    # Monitoring and observability
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    ENABLE_TRACING: bool = False
    JAEGER_ENDPOINT: Optional[str] = None
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    ENABLE_RATE_LIMITING: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 100
    
    # Request size limiting
    MAX_REQUEST_SIZE: int = 16 * 1024 * 1024  # 16MB
    
    # HTTP caching
    ENABLE_HTTP_CACHE: bool = True
    HTTP_CACHE_TTL: int = 300  # 5 minutes
    
    # Security
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Background tasks
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Plugin system
    PLUGIN_REGISTRY_URL: str = "http://localhost:8000/api/v1/plugins"
    PLUGIN_CACHE_TTL: int = 300  # 5 minutes
    
    # Compliance settings
    DEFAULT_COUNTRY_CODE: str = "US"
    COMPLIANCE_CACHE_TTL: int = 3600  # 1 hour
    
    # AI/ML settings
    AI_MODEL_CACHE_SIZE: int = 100
    AI_PREDICTION_TIMEOUT: int = 30
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("CORS_METHODS", mode="before")
    @classmethod
    def parse_cors_methods(cls, v):
        if isinstance(v, str):
            return [method.strip() for method in v.split(",")]
        return v
    
    @field_validator("CORS_HEADERS", mode="before")
    @classmethod
    def parse_cors_headers(cls, v):
        if isinstance(v, str):
            return [header.strip() for header in v.split(",")]
        return v
    
    @field_validator("ALLOWED_FILE_TYPES", mode="before")
    @classmethod
    def parse_allowed_file_types(cls, v):
        if isinstance(v, str):
            return [file_type.strip().lower() for file_type in v.split(",")]
        return v
    
    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v
    
    @field_validator("RELOAD", mode="before")
    @classmethod
    def parse_reload(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v
    
    @field_validator("ENABLE_METRICS", mode="before")
    @classmethod
    def parse_enable_metrics(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v
    
    @field_validator("ENABLE_TRACING", mode="before")
    @classmethod
    def parse_enable_tracing(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v
    
    @field_validator("RATE_LIMIT_ENABLED", mode="before")
    @classmethod
    def parse_rate_limit_enabled(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


class DevelopmentSettings(Settings):
    """Development environment settings."""
    DEBUG: bool = True
    RELOAD: bool = True
    LOG_LEVEL: str = "DEBUG"
    ENVIRONMENT: str = "development"


class ProductionSettings(Settings):
    """Production environment settings."""
    DEBUG: bool = False
    RELOAD: bool = False
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "production"
    
    # Production security
    SECRET_KEY: str  # Must be set in production
    
    # Production database
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    
    # Production Redis
    REDIS_POOL_SIZE: int = 20


class TestingSettings(Settings):
    """Testing environment settings."""
    DEBUG: bool = True
    ENVIRONMENT: str = "testing"
    
    # Test database
    DATABASE_URL: str = "sqlite:///./test.db"
    
    # Test Redis
    REDIS_URL: str = "redis://localhost:6379/15"
    
    # Disable external services in tests
    WEATHER_API_KEY: Optional[str] = None
    ENABLE_METRICS: bool = False
    ENABLE_TRACING: bool = False
    RATE_LIMIT_ENABLED: bool = False


@lru_cache()
def get_settings() -> Settings:
    """Get application settings based on environment."""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return ProductionSettings()
    elif environment == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()


def get_database_url(async_db: bool = False) -> str:
    """Get database URL for sync or async connections."""
    settings = get_settings()
    
    if async_db:
        return settings.ASYNC_DATABASE_URL
    else:
        return settings.DATABASE_URL


def get_redis_url() -> str:
    """Get Redis URL."""
    settings = get_settings()
    return settings.REDIS_URL


def is_development() -> bool:
    """Check if running in development environment."""
    settings = get_settings()
    return settings.ENVIRONMENT == "development"


def is_production() -> bool:
    """Check if running in production environment."""
    settings = get_settings()
    return settings.ENVIRONMENT == "production"


def is_testing() -> bool:
    """Check if running in testing environment."""
    settings = get_settings()
    return settings.ENVIRONMENT == "testing"


def get_cors_settings() -> dict:
    """Get CORS settings for FastAPI."""
    settings = get_settings()
    
    return {
        "allow_origins": settings.CORS_ORIGINS,
        "allow_credentials": settings.CORS_CREDENTIALS,
        "allow_methods": settings.CORS_METHODS,
        "allow_headers": settings.CORS_HEADERS,
    }


def get_storage_settings() -> dict:
    """Get file storage settings."""
    settings = get_settings()
    
    return {
        "type": settings.STORAGE_TYPE,
        "path": settings.STORAGE_PATH,
        "max_file_size": settings.MAX_FILE_SIZE,
        "allowed_file_types": settings.ALLOWED_FILE_TYPES,
        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        "aws_region": settings.AWS_REGION,
        "aws_s3_bucket": settings.AWS_S3_BUCKET,
    }


def get_external_service_urls() -> dict:
    """Get external service URLs."""
    settings = get_settings()
    
    return {
        "api_gateway": settings.API_GATEWAY_URL,
        "compliance": settings.COMPLIANCE_SERVICE_URL,
        "finance": settings.FINANCE_SERVICE_URL,
        "procure": settings.PROCURE_SERVICE_URL,
        "ops": settings.OPS_SERVICE_URL,
        "support": settings.SUPPORT_SERVICE_URL,
    }


def get_monitoring_settings() -> dict:
    """Get monitoring and observability settings."""
    settings = get_settings()
    
    return {
        "enable_metrics": settings.ENABLE_METRICS,
        "metrics_port": settings.METRICS_PORT,
        "enable_tracing": settings.ENABLE_TRACING,
        "jaeger_endpoint": settings.JAEGER_ENDPOINT,
    }


def get_rate_limit_settings() -> dict:
    """Get rate limiting settings."""
    settings = get_settings()
    
    return {
        "enabled": settings.RATE_LIMIT_ENABLED,
        "requests": settings.RATE_LIMIT_REQUESTS,
        "window": settings.RATE_LIMIT_WINDOW,
    }


# Create settings instance
settings = get_settings()