#!/usr/bin/env python3
"""
Database configuration and models for the Currency Service.

Provides SQLAlchemy setup, database models for exchange rates, currency preferences,
and transaction history. Enhanced with multi-tenant connection pooling and performance optimization.
"""

import logging
import sys
import os
from datetime import datetime
from typing import Optional, AsyncGenerator
from decimal import Decimal

from sqlalchemy import (
    Column, String, DateTime, Numeric, Boolean, Text, Integer,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .config import get_settings

# Add shared module to path for enhanced pooling
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared'))

# Try to import enhanced pooling system
try:
    from database import (
        ServiceType, ServiceDatabaseManager, 
        get_service_db_manager, initialize_service_database
    )
    ENHANCED_POOLING_AVAILABLE = True
except ImportError:
    ENHANCED_POOLING_AVAILABLE = False

logger = logging.getLogger(__name__)
settings = get_settings()

# Global variables for database components
_engine = None
_session_factory = None
_service_manager = None


def init_database(tenant_id: Optional[str] = None) -> None:
    """Initialize database with enhanced pooling support.
    
    Args:
        tenant_id: Optional tenant identifier for multi-tenant isolation
    """
    global _engine, _session_factory, _service_manager
    
    if ENHANCED_POOLING_AVAILABLE:
        # Use enhanced pooling system
        _service_manager = initialize_service_database(
            service_type=ServiceType.CURRENCY,
            database_url=settings.DATABASE_URL,
            tenant_id=tenant_id
        )
        _engine = _service_manager.get_async_engine(tenant_id)
        _session_factory = _service_manager.get_async_session_factory(tenant_id)
    else:
        # Fallback to legacy pooling
        _engine = create_async_engine(
            settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://"),
            echo=settings.DATABASE_ECHO,
            future=True
        )
        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False
        )


def get_engine() -> create_async_engine:
    """Get the database engine."""
    if _engine is None:
        init_database()
    return _engine


def get_session_factory() -> async_sessionmaker:
    """Get the session factory."""
    if _session_factory is None:
        init_database()
    return _session_factory


# Legacy compatibility
engine = get_engine()
AsyncSessionLocal = get_session_factory()

# Base class for all models
Base = declarative_base()


class ExchangeRate(Base):
    """Exchange rate model for storing currency conversion rates."""
    
    __tablename__ = "exchange_rates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    base_currency = Column(String(3), nullable=False, index=True)
    target_currency = Column(String(3), nullable=False, index=True)
    rate = Column(Numeric(precision=18, scale=8), nullable=False)
    source = Column(String(50), nullable=False)  # API source (e.g., 'fixer', 'exchangerate-api')
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now())
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_exchange_rates_base_target', 'base_currency', 'target_currency'),
        Index('idx_exchange_rates_timestamp', 'timestamp'),
        Index('idx_exchange_rates_active', 'is_active'),
        UniqueConstraint('base_currency', 'target_currency', 'timestamp', name='uq_exchange_rate_time')
    )


class CurrencyPreference(Base):
    """User currency preferences model."""
    
    __tablename__ = "currency_preferences"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    preferred_currency = Column(String(3), nullable=False)
    display_format = Column(String(20), default="symbol")  # 'symbol', 'code', 'name'
    decimal_places = Column(Integer, default=2)
    thousands_separator = Column(String(1), default=",")
    decimal_separator = Column(String(1), default=".")
    
    # Regional settings
    region = Column(String(10), nullable=True)  # ISO country code
    timezone = Column(String(50), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_currency_preferences_user', 'user_id'),
        UniqueConstraint('user_id', name='uq_currency_preference_user')
    )


class MultiCurrencyTransaction(Base):
    """Multi-currency transaction model for audit and compliance."""
    
    __tablename__ = "multi_currency_transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String, nullable=False, index=True)  # External transaction reference
    user_id = Column(String, nullable=False, index=True)
    
    # Original amount and currency
    original_amount = Column(Numeric(precision=18, scale=8), nullable=False)
    original_currency = Column(String(3), nullable=False)
    
    # Converted amount and currency
    converted_amount = Column(Numeric(precision=18, scale=8), nullable=False)
    converted_currency = Column(String(3), nullable=False)
    
    # Exchange rate used
    exchange_rate = Column(Numeric(precision=18, scale=8), nullable=False)
    rate_source = Column(String(50), nullable=False)
    rate_timestamp = Column(DateTime(timezone=True), nullable=False)
    
    # Transaction metadata
    transaction_type = Column(String(50), nullable=False)  # 'quote', 'invoice', 'payment'
    description = Column(Text, nullable=True)
    
    # Compliance fields
    compliance_checked = Column(Boolean, default=False)
    compliance_notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_multi_currency_transaction', 'transaction_id'),
        Index('idx_multi_currency_user', 'user_id'),
        Index('idx_multi_currency_created', 'created_at'),
        Index('idx_multi_currency_type', 'transaction_type')
    )


class CurrencyConversionLog(Base):
    """Log of currency conversion requests for analytics and debugging."""
    
    __tablename__ = "currency_conversion_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    
    # Conversion details
    from_currency = Column(String(3), nullable=False)
    to_currency = Column(String(3), nullable=False)
    amount = Column(Numeric(precision=18, scale=8), nullable=False)
    converted_amount = Column(Numeric(precision=18, scale=8), nullable=False)
    exchange_rate = Column(Numeric(precision=18, scale=8), nullable=False)
    
    # Request metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    api_endpoint = Column(String(200), nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    
    # Status
    status = Column(String(20), nullable=False, default="success")  # 'success', 'error', 'rate_limited'
    error_message = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_conversion_log_request', 'request_id'),
        Index('idx_conversion_log_user', 'user_id'),
        Index('idx_conversion_log_created', 'created_at'),
        Index('idx_conversion_log_currencies', 'from_currency', 'to_currency')
    )


async def get_db(tenant_id: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session with optional tenant isolation.
    
    Args:
        tenant_id: Optional tenant identifier for multi-tenant sessions
        
    Yields:
        AsyncSession: Database session
    """
    if ENHANCED_POOLING_AVAILABLE and _service_manager and tenant_id:
        # Use enhanced pooling with tenant isolation
        async with _service_manager.get_async_session(tenant_id) as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
    else:
        # Use standard session factory
        session_factory = get_session_factory()
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


async def get_db_session(tenant_id: Optional[str] = None) -> AsyncSession:
    """Get a single database session (not a generator).
    
    Args:
        tenant_id: Optional tenant identifier for multi-tenant sessions
        
    Returns:
        AsyncSession: Database session
    """
    if ENHANCED_POOLING_AVAILABLE and _service_manager and tenant_id:
        return _service_manager.get_async_session(tenant_id)
    else:
        session_factory = get_session_factory()
        return session_factory()


async def check_database_health(tenant_id: Optional[str] = None) -> dict:
    """Check database health with optional tenant context.
    
    Args:
        tenant_id: Optional tenant identifier
        
    Returns:
        dict: Health check results
    """
    if ENHANCED_POOLING_AVAILABLE and _service_manager:
        return await _service_manager.health_check(tenant_id)
    else:
        # Basic health check
        try:
            async with get_db_session(tenant_id) as session:
                await session.execute("SELECT 1")
            return {"status": "healthy", "tenant_id": tenant_id}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "tenant_id": tenant_id}


async def create_tables(tenant_id: Optional[str] = None):
    """Create all database tables.
    
    Args:
        tenant_id: Optional tenant identifier
        
    This function creates all tables defined in the models.
    """
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


async def drop_tables(tenant_id: Optional[str] = None):
    """Drop all database tables.
    
    Args:
        tenant_id: Optional tenant identifier
        
    Warning: This will delete all data!
    """
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


async def close_database_connections():
    """Close all database connections and dispose engines."""
    global _engine, _session_factory, _service_manager
    
    try:
        if ENHANCED_POOLING_AVAILABLE and _service_manager:
            await _service_manager.close_all_connections()
        elif _engine:
            await _engine.dispose()
        
        # Reset global variables
        _engine = None
        _session_factory = None
        _service_manager = None
        
        logger.info("Database connections closed successfully")
        
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")