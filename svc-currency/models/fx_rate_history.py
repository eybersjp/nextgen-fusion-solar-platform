"""FX Rate History Models for NextGen Fusion Platform

Provides comprehensive foreign exchange rate history storage and management:
- Historical rate tracking with high precision
- Multiple data source support (central banks, financial APIs)
- Rate interpolation and gap filling
- Performance optimized queries with proper indexing
- Data validation and anomaly detection
- Compliance with financial data retention requirements
"""

from sqlalchemy import Column, String, Numeric, DateTime, Boolean, Text, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import uuid

from shared.database.base import BaseModel


class DataSource(str, Enum):
    """FX rate data sources"""
    ECB = "ecb"  # European Central Bank
    FED = "fed"  # Federal Reserve
    BOE = "boe"  # Bank of England
    RBA = "rba"  # Reserve Bank of Australia
    SARB = "sarb"  # South African Reserve Bank
    FIXER = "fixer"  # Fixer.io API
    EXCHANGERATE = "exchangerate"  # ExchangeRate-API
    ALPHA_VANTAGE = "alpha_vantage"  # Alpha Vantage
    YAHOO_FINANCE = "yahoo_finance"  # Yahoo Finance
    MANUAL = "manual"  # Manually entered


class RateType(str, Enum):
    """Types of exchange rates"""
    SPOT = "spot"  # Current market rate
    OFFICIAL = "official"  # Official central bank rate
    COMMERCIAL = "commercial"  # Commercial bank rate
    INTERBANK = "interbank"  # Interbank rate
    TOURIST = "tourist"  # Tourist/retail rate
    FORWARD = "forward"  # Forward rate


class DataQuality(str, Enum):
    """Data quality indicators"""
    HIGH = "high"  # Direct from authoritative source
    MEDIUM = "medium"  # From reliable API
    LOW = "low"  # Interpolated or estimated
    SUSPECT = "suspect"  # Flagged for review


class FXRateHistory(BaseModel):
    """Historical foreign exchange rates"""
    
    __tablename__ = "fx_rate_history"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Currency pair
    base_currency = Column(String(3), nullable=False, index=True)  # ISO 4217 code
    quote_currency = Column(String(3), nullable=False, index=True)  # ISO 4217 code
    
    # Rate information
    rate = Column(Numeric(20, 10), nullable=False)  # High precision rate
    rate_date = Column(DateTime(timezone=True), nullable=False, index=True)
    rate_type = Column(String(20), nullable=False, default=RateType.SPOT)
    
    # Data source and quality
    data_source = Column(String(50), nullable=False, index=True)
    source_reference = Column(String(255))  # External reference ID
    data_quality = Column(String(20), nullable=False, default=DataQuality.MEDIUM)
    
    # Metadata
    bid_rate = Column(Numeric(20, 10))  # Bid rate if available
    ask_rate = Column(Numeric(20, 10))  # Ask rate if available
    mid_rate = Column(Numeric(20, 10))  # Mid rate if available
    spread = Column(Numeric(10, 6))  # Bid-ask spread
    
    # Volume and market data
    volume = Column(Numeric(20, 2))  # Trading volume if available
    high_rate = Column(Numeric(20, 10))  # Daily high
    low_rate = Column(Numeric(20, 10))  # Daily low
    open_rate = Column(Numeric(20, 10))  # Opening rate
    close_rate = Column(Numeric(20, 10))  # Closing rate
    
    # Data processing flags
    is_interpolated = Column(Boolean, default=False, index=True)
    is_weekend_rate = Column(Boolean, default=False)
    is_holiday_rate = Column(Boolean, default=False)
    is_anomaly = Column(Boolean, default=False, index=True)
    
    # Additional metadata
    metadata = Column(JSONB)  # Additional source-specific data
    notes = Column(Text)  # Human-readable notes
    
    # Data lineage
    source_timestamp = Column(DateTime(timezone=True))  # When source published
    ingestion_timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Validation and approval
    is_validated = Column(Boolean, default=False, index=True)
    validated_by = Column(String(255))  # User who validated
    validated_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        # Unique constraint to prevent duplicate rates
        UniqueConstraint(
            'base_currency', 'quote_currency', 'rate_date', 'rate_type', 'data_source',
            name='uq_fx_rate_history_unique_rate'
        ),
        
        # Performance indexes
        Index('idx_fx_rate_history_currency_pair_date', 'base_currency', 'quote_currency', 'rate_date'),
        Index('idx_fx_rate_history_date_source', 'rate_date', 'data_source'),
        Index('idx_fx_rate_history_base_date', 'base_currency', 'rate_date'),
        Index('idx_fx_rate_history_quote_date', 'quote_currency', 'rate_date'),
        Index('idx_fx_rate_history_quality_validated', 'data_quality', 'is_validated'),
        Index('idx_fx_rate_history_ingestion_time', 'ingestion_timestamp'),
        
        # Check constraints
        CheckConstraint('rate > 0', name='ck_fx_rate_history_positive_rate'),
        CheckConstraint('bid_rate IS NULL OR bid_rate > 0', name='ck_fx_rate_history_positive_bid'),
        CheckConstraint('ask_rate IS NULL OR ask_rate > 0', name='ck_fx_rate_history_positive_ask'),
        CheckConstraint('spread IS NULL OR spread >= 0', name='ck_fx_rate_history_non_negative_spread'),
        CheckConstraint('volume IS NULL OR volume >= 0', name='ck_fx_rate_history_non_negative_volume'),
        CheckConstraint('base_currency != quote_currency', name='ck_fx_rate_history_different_currencies'),
        CheckConstraint('length(base_currency) = 3', name='ck_fx_rate_history_base_currency_length'),
        CheckConstraint('length(quote_currency) = 3', name='ck_fx_rate_history_quote_currency_length'),
    )
    
    def __repr__(self) -> str:
        return f"<FXRateHistory {self.base_currency}/{self.quote_currency} {self.rate} on {self.rate_date}>"
    
    @property
    def currency_pair(self) -> str:
        """Get currency pair string"""
        return f"{self.base_currency}/{self.quote_currency}"
    
    @property
    def inverse_rate(self) -> Decimal:
        """Calculate inverse rate"""
        return Decimal('1') / Decimal(str(self.rate))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'base_currency': self.base_currency,
            'quote_currency': self.quote_currency,
            'rate': float(self.rate),
            'rate_date': self.rate_date.isoformat(),
            'rate_type': self.rate_type,
            'data_source': self.data_source,
            'data_quality': self.data_quality,
            'is_interpolated': self.is_interpolated,
            'is_validated': self.is_validated,
            'metadata': self.metadata
        }


class FXRateSnapshot(BaseModel):
    """Daily snapshots of FX rates for fast querying"""
    
    __tablename__ = "fx_rate_snapshots"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Currency pair and date
    base_currency = Column(String(3), nullable=False, index=True)
    quote_currency = Column(String(3), nullable=False, index=True)
    snapshot_date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Primary rates (best available)
    spot_rate = Column(Numeric(20, 10), nullable=False)
    official_rate = Column(Numeric(20, 10))
    commercial_rate = Column(Numeric(20, 10))
    
    # Rate statistics for the day
    high_rate = Column(Numeric(20, 10))
    low_rate = Column(Numeric(20, 10))
    open_rate = Column(Numeric(20, 10))
    close_rate = Column(Numeric(20, 10))
    avg_rate = Column(Numeric(20, 10))
    
    # Data quality indicators
    primary_source = Column(String(50), nullable=False)
    data_quality = Column(String(20), nullable=False)
    source_count = Column(Integer, default=1)  # Number of sources contributing
    
    # Flags
    is_business_day = Column(Boolean, default=True)
    is_interpolated = Column(Boolean, default=False)
    has_anomaly = Column(Boolean, default=False)
    
    # Metadata
    last_updated = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        # Unique constraint for daily snapshots
        UniqueConstraint(
            'base_currency', 'quote_currency', 'snapshot_date',
            name='uq_fx_rate_snapshots_daily'
        ),
        
        # Performance indexes
        Index('idx_fx_snapshots_currency_pair_date', 'base_currency', 'quote_currency', 'snapshot_date'),
        Index('idx_fx_snapshots_date_quality', 'snapshot_date', 'data_quality'),
        Index('idx_fx_snapshots_business_day', 'is_business_day', 'snapshot_date'),
        
        # Check constraints
        CheckConstraint('spot_rate > 0', name='ck_fx_snapshots_positive_spot_rate'),
        CheckConstraint('source_count > 0', name='ck_fx_snapshots_positive_source_count'),
    )


class FXRateSource(BaseModel):
    """Configuration for FX rate data sources"""
    
    __tablename__ = "fx_rate_sources"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Source information
    source_name = Column(String(50), nullable=False, unique=True)
    source_type = Column(String(20), nullable=False)  # api, file, manual
    description = Column(Text)
    
    # API configuration
    api_url = Column(String(500))
    api_key_required = Column(Boolean, default=False)
    rate_limit_per_hour = Column(Integer)
    
    # Data characteristics
    supported_currencies = Column(JSONB)  # List of supported currency codes
    update_frequency = Column(String(20))  # daily, hourly, real-time
    data_delay_minutes = Column(Integer, default=0)  # How delayed the data is
    
    # Quality and reliability
    reliability_score = Column(Numeric(3, 2), default=Decimal('0.5'))  # 0.0 to 1.0
    data_quality_default = Column(String(20), default=DataQuality.MEDIUM)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    last_successful_fetch = Column(DateTime(timezone=True))
    last_error = Column(Text)
    error_count = Column(Integer, default=0)
    
    # Configuration
    fetch_config = Column(JSONB)  # Source-specific configuration
    
    __table_args__ = (
        Index('idx_fx_sources_active_type', 'is_active', 'source_type'),
        CheckConstraint('reliability_score >= 0 AND reliability_score <= 1', 
                       name='ck_fx_sources_reliability_range'),
    )


class FXRateAlert(BaseModel):
    """Alerts for significant FX rate changes"""
    
    __tablename__ = "fx_rate_alerts"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Currency pair
    base_currency = Column(String(3), nullable=False, index=True)
    quote_currency = Column(String(3), nullable=False, index=True)
    
    # Alert details
    alert_type = Column(String(50), nullable=False)  # threshold, anomaly, volatility
    threshold_value = Column(Numeric(10, 6))  # Threshold percentage
    current_rate = Column(Numeric(20, 10), nullable=False)
    previous_rate = Column(Numeric(20, 10), nullable=False)
    change_percentage = Column(Numeric(10, 6), nullable=False)
    
    # Timing
    alert_time = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    rate_time = Column(DateTime(timezone=True), nullable=False)
    
    # Status
    is_acknowledged = Column(Boolean, default=False, index=True)
    acknowledged_by = Column(String(255))
    acknowledged_at = Column(DateTime(timezone=True))
    
    # Metadata
    severity = Column(String(20), default='medium')  # low, medium, high, critical
    message = Column(Text)
    
    __table_args__ = (
        Index('idx_fx_alerts_currency_time', 'base_currency', 'quote_currency', 'alert_time'),
        Index('idx_fx_alerts_severity_ack', 'severity', 'is_acknowledged'),
        CheckConstraint('change_percentage IS NOT NULL', name='ck_fx_alerts_change_required'),
    )


# Utility functions for working with FX rate history

def get_currency_pair_key(base: str, quote: str) -> str:
    """Get standardized currency pair key"""
    return f"{base.upper()}/{quote.upper()}"


def normalize_currency_pair(base: str, quote: str) -> Tuple[str, str, bool]:
    """Normalize currency pair to standard order
    
    Returns:
        Tuple of (base, quote, is_inverted)
    """
    # Define major currencies in order of preference
    major_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD']
    
    base_upper = base.upper()
    quote_upper = quote.upper()
    
    # If both are major currencies, use the order from the list
    if base_upper in major_currencies and quote_upper in major_currencies:
        base_idx = major_currencies.index(base_upper)
        quote_idx = major_currencies.index(quote_upper)
        
        if base_idx < quote_idx:
            return base_upper, quote_upper, False
        else:
            return quote_upper, base_upper, True
    
    # If only one is major, it should be the base
    elif quote_upper in major_currencies and base_upper not in major_currencies:
        return quote_upper, base_upper, True
    elif base_upper in major_currencies and quote_upper not in major_currencies:
        return base_upper, quote_upper, False
    
    # If neither is major, use alphabetical order
    else:
        if base_upper < quote_upper:
            return base_upper, quote_upper, False
        else:
            return quote_upper, base_upper, True


def calculate_cross_rate(rate1: Decimal, rate2: Decimal, 
                        pair1: Tuple[str, str], pair2: Tuple[str, str],
                        target_pair: Tuple[str, str]) -> Optional[Decimal]:
    """Calculate cross rate from two currency pairs
    
    Args:
        rate1: Rate for pair1
        rate2: Rate for pair2  
        pair1: (base, quote) for rate1
        pair2: (base, quote) for rate2
        target_pair: (base, quote) for desired cross rate
        
    Returns:
        Cross rate if calculable, None otherwise
    """
    # This is a simplified implementation
    # In practice, you'd need more sophisticated logic to handle all combinations
    
    target_base, target_quote = target_pair
    
    # Try to find a path through the available rates
    # This would need to be expanded for a production system
    
    return None  # Placeholder