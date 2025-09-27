#!/usr/bin/env python3
"""
Configuration settings for the Project Management Service

This module defines all configuration settings using Pydantic for
environment variable management and validation.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    APP_NAME: str = "NextGen Fusion Project Management Service"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8003
    
    # Database settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./project_management.db"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Security settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = ["*"]
    ALLOWED_METHODS: List[str] = ["*"]
    ALLOWED_HEADERS: List[str] = ["*"]
    
    # Project Management settings
    MAX_TASKS_PER_PROJECT: int = 1000
    MAX_MILESTONES_PER_PROJECT: int = 50
    DEFAULT_TASK_PRIORITY: str = "medium"
    AUTO_ASSIGN_TASKS: bool = True
    ENABLE_TIME_TRACKING: bool = True
    
    # Gantt Chart settings
    GANTT_MAX_DURATION_DAYS: int = 365
    GANTT_MIN_TASK_DURATION_HOURS: int = 1
    GANTT_WORKING_HOURS_PER_DAY: int = 8
    GANTT_WORKING_DAYS_PER_WEEK: int = 5
    
    # Notification settings
    ENABLE_NOTIFICATIONS: bool = True
    EMAIL_NOTIFICATIONS: bool = True
    SLACK_NOTIFICATIONS: bool = False
    TEAMS_NOTIFICATIONS: bool = False
    NOTIFICATION_BATCH_SIZE: int = 100
    
    # Task automation settings
    AUTO_CREATE_SUBTASKS: bool = False
    AUTO_UPDATE_PROGRESS: bool = True
    AUTO_CLOSE_COMPLETED_TASKS: bool = True
    TASK_REMINDER_HOURS: int = 24
    
    # Resource management
    MAX_TEAM_MEMBERS_PER_PROJECT: int = 50
    ENABLE_RESOURCE_ALLOCATION: bool = True
    TRACK_RESOURCE_UTILIZATION: bool = True
    RESOURCE_CONFLICT_DETECTION: bool = True
    
    # Cache settings
    REDIS_URL: Optional[str] = None
    CACHE_TTL_SECONDS: int = 300
    ENABLE_CACHING: bool = True
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    ENABLE_RATE_LIMITING: bool = True
    
    # Monitoring settings
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9003
    LOG_LEVEL: str = "INFO"
    ENABLE_TRACING: bool = False
    JAEGER_ENDPOINT: Optional[str] = None
    
    # Logging settings
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "30 days"
    
    # External integrations
    JIRA_INTEGRATION: bool = False
    JIRA_URL: Optional[str] = None
    JIRA_USERNAME: Optional[str] = None
    JIRA_API_TOKEN: Optional[str] = None
    
    ASANA_INTEGRATION: bool = False
    ASANA_ACCESS_TOKEN: Optional[str] = None
    
    TRELLO_INTEGRATION: bool = False
    TRELLO_API_KEY: Optional[str] = None
    TRELLO_TOKEN: Optional[str] = None
    
    # Calendar integration
    GOOGLE_CALENDAR_INTEGRATION: bool = False
    GOOGLE_CALENDAR_CREDENTIALS: Optional[str] = None
    
    OUTLOOK_INTEGRATION: bool = False
    OUTLOOK_CLIENT_ID: Optional[str] = None
    OUTLOOK_CLIENT_SECRET: Optional[str] = None
    
    # File storage
    FILE_STORAGE_TYPE: str = "local"  # local, s3, azure, gcp
    FILE_UPLOAD_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        "jpg", "jpeg", "png", "gif", "svg", "txt", "csv"
    ]
    
    # AWS S3 settings (if using S3)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: Optional[str] = None
    
    # Reporting settings
    ENABLE_REPORTS: bool = True
    REPORT_GENERATION_TIMEOUT: int = 300  # seconds
    MAX_REPORT_SIZE_MB: int = 50
    REPORT_FORMATS: List[str] = ["pdf", "excel", "csv"]
    
    # Analytics settings
    ENABLE_ANALYTICS: bool = True
    ANALYTICS_RETENTION_DAYS: int = 90
    TRACK_USER_ACTIVITY: bool = True
    TRACK_PERFORMANCE_METRICS: bool = True
    
    # Backup settings
    ENABLE_BACKUP: bool = True
    BACKUP_INTERVAL_HOURS: int = 24
    BACKUP_RETENTION_DAYS: int = 30
    BACKUP_LOCATION: str = "./backups"
    
    # Security settings
    ENABLE_AUDIT_LOG: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 365
    REQUIRE_MFA: bool = False
    SESSION_TIMEOUT_MINUTES: int = 480  # 8 hours
    
    # Performance settings
    MAX_CONCURRENT_REQUESTS: int = 100
    REQUEST_TIMEOUT_SECONDS: int = 30
    DATABASE_CONNECTION_TIMEOUT: int = 30
    
    # Feature flags
    ENABLE_ADVANCED_ANALYTICS: bool = False
    ENABLE_AI_RECOMMENDATIONS: bool = False
    ENABLE_CUSTOM_WORKFLOWS: bool = True
    ENABLE_API_VERSIONING: bool = True
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("ALLOWED_FILE_TYPES", pre=True)
    def parse_file_types(cls, v):
        if isinstance(v, str):
            return [file_type.strip() for file_type in v.split(",")]
        return v
    
    @validator("REPORT_FORMATS", pre=True)
    def parse_report_formats(cls, v):
        if isinstance(v, str):
            return [format.strip() for format in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()