#!/usr/bin/env python3
"""
Currency API endpoints for the Currency Service

Provides REST API endpoints for currency management including:
- Exchange rate retrieval
- Currency conversion
- Historical exchange rate data
- Currency preference management
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
import aiohttp

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from pydantic import BaseModel, Field, validator

from app.core.database import get_db, ExchangeRate, CurrencyPreference, MultiCurrencyTransaction, CurrencyConversionLog
from app.core.config import get_settings
from app.core.logging import get_logger

# Create a simple audit logger for now
class AuditLogger:
    def log_rate_update(self, source: str, count: int, timestamp: str):
        logger.info(f"Rate update: source={source}, count={count}, timestamp={timestamp}")
    
    def log_conversion(self, user_id: str, from_currency: str, to_currency: str, amount: float, rate: float, converted_amount: float):
        logger.info(f"Currency conversion: user={user_id}, {amount} {from_currency} -> {converted_amount} {to_currency} @ {rate}")

audit_logger = AuditLogger()

logger = get_logger(__name__)
settings = get_settings()
router = APIRouter()


# Pydantic models
class ExchangeRateResponse(BaseModel):
    base_currency: str = Field(..., description="Base currency code")
    target_currency: str = Field(..., description="Target currency code")
    rate: float = Field(..., description="Exchange rate")
    timestamp: datetime = Field(..., description="Rate timestamp")
    source: str = Field(..., description="Rate provider source")


class ExchangeRatesResponse(BaseModel):
    base_currency: str = Field(..., description="Base currency code")
    rates: Dict[str, float] = Field(..., description="Exchange rates by currency")
    timestamp: datetime = Field(..., description="Rates timestamp")
    source: str = Field(..., description="Rate provider source")


class CurrencyConversionRequest(BaseModel):
    from_currency: str = Field(..., min_length=3, max_length=3, description="Source currency code")
    to_currency: str = Field(..., min_length=3, max_length=3, description="Target currency code")
    amount: float = Field(..., gt=0, description="Amount to convert")
    
    @validator('from_currency', 'to_currency')
    def validate_currency_codes(cls, v):
        return v.upper()


class CurrencyConversionResponse(BaseModel):
    from_currency: str = Field(..., description="Source currency code")
    to_currency: str = Field(..., description="Target currency code")
    original_amount: float = Field(..., description="Original amount")
    converted_amount: float = Field(..., description="Converted amount")
    exchange_rate: float = Field(..., description="Exchange rate used")
    rate_timestamp: datetime = Field(..., description="Rate timestamp")
    conversion_timestamp: datetime = Field(..., description="Conversion timestamp")


class HistoricalRateRequest(BaseModel):
    base_currency: str = Field(..., min_length=3, max_length=3, description="Base currency code")
    target_currency: str = Field(..., min_length=3, max_length=3, description="Target currency code")
    start_date: datetime = Field(..., description="Start date for historical data")
    end_date: datetime = Field(..., description="End date for historical data")
    
    @validator('base_currency', 'target_currency')
    def validate_currency_codes(cls, v):
        return v.upper()
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class HistoricalRateResponse(BaseModel):
    base_currency: str = Field(..., description="Base currency code")
    target_currency: str = Field(..., description="Target currency code")
    rates: List[Dict[str, Any]] = Field(..., description="Historical rates with timestamps")
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")


class CurrencyPreferenceRequest(BaseModel):
    """Request model for currency preferences."""
    preferred_currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code")
    display_format: str = Field(default="symbol", pattern="^(symbol|code|name)$", description="Currency display format")
    decimal_places: int = Field(default=2, ge=0, le=6, description="Number of decimal places")
    thousands_separator: str = Field(default=",", max_length=1, description="Thousands separator character")
    decimal_separator: str = Field(default=".", max_length=1, description="Decimal separator character")
    region: Optional[str] = Field(None, max_length=10, description="User region code")
    timezone: Optional[str] = Field(None, max_length=50, description="User timezone")


class CurrencyPreferenceResponse(BaseModel):
    """Response model for currency preferences."""
    user_id: str
    preferred_currency: str = Field(..., min_length=3, max_length=3)
    display_format: str = Field(default="symbol", pattern="^(symbol|code|name)$")
    decimal_places: int = Field(default=2, ge=0, le=6)
    thousands_separator: str = Field(default=",", max_length=1)
    decimal_separator: str = Field(default=".", max_length=1)
    region: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    created_at: datetime
    updated_at: datetime


# Exchange rate service
class ExchangeRateService:
    """Service for managing exchange rates."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def fetch_latest_rates(self, base_currency: str = "USD") -> Dict[str, float]:
        """Fetch latest exchange rates from external API.
        
        Args:
            base_currency: Base currency for rates
            
        Returns:
            Dict[str, float]: Exchange rates by currency code
        """
        try:
            # Try multiple providers in order of preference
            providers = [
                ("exchangerate-api", self._fetch_from_exchangerate_api),
                ("fixer", self._fetch_from_fixer),
                ("currencylayer", self._fetch_from_currencylayer)
            ]
            
            for provider_name, fetch_func in providers:
                try:
                    rates = await fetch_func(base_currency)
                    if rates:
                        # Store rates in database
                        await self._store_rates(base_currency, rates, provider_name)
                        return rates
                except Exception as e:
                    logger.warning(f"Failed to fetch rates from {provider_name}: {e}")
                    continue
            
            # If all providers fail, get latest from database
            return await self._get_latest_from_db(base_currency)
            
        except Exception as e:
            logger.error(f"Failed to fetch exchange rates: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Exchange rate service temporarily unavailable"
            )
    
    async def _fetch_from_exchangerate_api(self, base_currency: str) -> Dict[str, float]:
        """Fetch rates from exchangerate-api.com."""
        url = f"{settings.EXCHANGE_RATE_API_URL}/{base_currency}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("rates", {})
                else:
                    raise Exception(f"API returned status {response.status}")
    
    async def _fetch_from_fixer(self, base_currency: str) -> Dict[str, float]:
        """Fetch rates from fixer.io."""
        if not settings.FIXER_API_KEY:
            raise Exception("Fixer API key not configured")
        
        url = f"{settings.FIXER_API_URL}?access_key={settings.FIXER_API_KEY}&base={base_currency}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        return data.get("rates", {})
                    else:
                        raise Exception(f"API error: {data.get('error', {}).get('info', 'Unknown error')}")
                else:
                    raise Exception(f"API returned status {response.status}")
    
    async def _fetch_from_currencylayer(self, base_currency: str) -> Dict[str, float]:
        """Fetch rates from currencylayer.com."""
        if not settings.CURRENCYLAYER_API_KEY:
            raise Exception("CurrencyLayer API key not configured")
        
        url = f"{settings.CURRENCYLAYER_API_URL}?access_key={settings.CURRENCYLAYER_API_KEY}&source={base_currency}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        # CurrencyLayer returns rates with currency prefixes (e.g., USDEUR)
                        quotes = data.get("quotes", {})
                        rates = {}
                        for key, value in quotes.items():
                            if key.startswith(base_currency):
                                target_currency = key[3:]  # Remove base currency prefix
                                rates[target_currency] = value
                        return rates
                    else:
                        raise Exception(f"API error: {data.get('error', {}).get('info', 'Unknown error')}")
                else:
                    raise Exception(f"API returned status {response.status}")
    
    async def _store_rates(self, base_currency: str, rates: Dict[str, float], source: str):
        """Store exchange rates in database."""
        timestamp = datetime.utcnow()
        
        for target_currency, rate in rates.items():
            if target_currency in settings.SUPPORTED_CURRENCIES:
                exchange_rate = ExchangeRate(
                    base_currency=base_currency,
                    target_currency=target_currency,
                    rate=Decimal(str(rate)),
                    source=source,
                    timestamp=timestamp
                )
                self.db.add(exchange_rate)
        
        await self.db.commit()
        
        # Log for audit
        audit_logger.log_rate_update(source, len(rates), timestamp.isoformat())
    
    async def _get_latest_from_db(self, base_currency: str) -> Dict[str, float]:
        """Get latest rates from database as fallback."""
        query = select(ExchangeRate).where(
            and_(
                ExchangeRate.base_currency == base_currency,
                ExchangeRate.is_active == True
            )
        ).order_by(desc(ExchangeRate.timestamp))
        
        result = await self.db.execute(query)
        rates_data = result.scalars().all()
        
        # Group by target currency and get latest rate for each
        rates = {}
        seen_currencies = set()
        
        for rate_record in rates_data:
            if rate_record.target_currency not in seen_currencies:
                rates[rate_record.target_currency] = float(rate_record.rate)
                seen_currencies.add(rate_record.target_currency)
        
        return rates


@router.get(
    "/rates",
    response_model=ExchangeRatesResponse,
    summary="Get current exchange rates",
    description="Retrieve current exchange rates for supported currencies"
)
async def get_exchange_rates(
    base_currency: str = Query("USD", description="Base currency code"),
    target_currencies: Optional[str] = Query(None, description="Comma-separated target currencies"),
    db: AsyncSession = Depends(get_db)
) -> ExchangeRatesResponse:
    """Get current exchange rates.
    
    Args:
        base_currency: Base currency code
        target_currencies: Optional comma-separated target currencies
        db: Database session
        
    Returns:
        Current exchange rates
    """
    try:
        logger.info(f"Fetching exchange rates for base currency: {base_currency}")
        
        service = ExchangeRateService(db)
        rates = await service.fetch_latest_rates(base_currency.upper())
        
        # Filter target currencies if specified
        if target_currencies:
            target_list = [c.strip().upper() for c in target_currencies.split(",")]
            rates = {k: v for k, v in rates.items() if k in target_list}
        
        response = ExchangeRatesResponse(
            base_currency=base_currency.upper(),
            rates=rates,
            timestamp=datetime.utcnow(),
            source="aggregated"
        )
        
        logger.info(f"Retrieved {len(rates)} exchange rates")
        return response
        
    except Exception as e:
        logger.error(f"Failed to get exchange rates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve exchange rates: {str(e)}"
        )


@router.post(
    "/convert",
    response_model=CurrencyConversionResponse,
    summary="Convert currency amount",
    description="Convert an amount from one currency to another"
)
async def convert_currency(
    conversion_request: CurrencyConversionRequest,
    user_id: Optional[str] = Query(None, description="User identifier for audit logging"),
    db: AsyncSession = Depends(get_db)
) -> CurrencyConversionResponse:
    """Convert currency amount.
    
    Args:
        conversion_request: Currency conversion parameters
        user_id: Optional user identifier
        db: Database session
        
    Returns:
        Currency conversion result
    """
    try:
        logger.info(f"Converting {conversion_request.amount} {conversion_request.from_currency} to {conversion_request.to_currency}")
        
        # Handle same currency conversion
        if conversion_request.from_currency == conversion_request.to_currency:
            return CurrencyConversionResponse(
                from_currency=conversion_request.from_currency,
                to_currency=conversion_request.to_currency,
                original_amount=conversion_request.amount,
                converted_amount=conversion_request.amount,
                exchange_rate=1.0,
                rate_timestamp=datetime.utcnow(),
                conversion_timestamp=datetime.utcnow()
            )
        
        service = ExchangeRateService(db)
        
        # Get exchange rate
        rates = await service.fetch_latest_rates(conversion_request.from_currency)
        
        if conversion_request.to_currency not in rates:
            # Try reverse conversion
            reverse_rates = await service.fetch_latest_rates(conversion_request.to_currency)
            if conversion_request.from_currency in reverse_rates:
                exchange_rate = 1.0 / reverse_rates[conversion_request.from_currency]
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Exchange rate not available for {conversion_request.from_currency} to {conversion_request.to_currency}"
                )
        else:
            exchange_rate = rates[conversion_request.to_currency]
        
        # Perform conversion
        converted_amount = conversion_request.amount * exchange_rate
        conversion_timestamp = datetime.utcnow()
        
        # Log conversion for audit
        if user_id:
            audit_logger.log_conversion(
                user_id=user_id,
                from_currency=conversion_request.from_currency,
                to_currency=conversion_request.to_currency,
                amount=conversion_request.amount,
                rate=exchange_rate,
                converted_amount=converted_amount
            )
        
        response = CurrencyConversionResponse(
            from_currency=conversion_request.from_currency,
            to_currency=conversion_request.to_currency,
            original_amount=conversion_request.amount,
            converted_amount=converted_amount,
            exchange_rate=exchange_rate,
            rate_timestamp=datetime.utcnow(),
            conversion_timestamp=conversion_timestamp
        )
        
        logger.info(f"Conversion completed: {conversion_request.amount} {conversion_request.from_currency} = {converted_amount} {conversion_request.to_currency}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to convert currency: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert currency: {str(e)}"
        )


@router.get(
    "/historical",
    response_model=HistoricalRateResponse,
    summary="Get historical exchange rates",
    description="Retrieve historical exchange rates for a currency pair"
)
async def get_historical_rates(
    base_currency: str = Query(..., description="Base currency code"),
    target_currency: str = Query(..., description="Target currency code"),
    start_date: datetime = Query(..., description="Start date (ISO format)"),
    end_date: datetime = Query(..., description="End date (ISO format)"),
    db: AsyncSession = Depends(get_db)
) -> HistoricalRateResponse:
    """Get historical exchange rates.
    
    Args:
        base_currency: Base currency code
        target_currency: Target currency code
        start_date: Start date for historical data
        end_date: End date for historical data
        db: Database session
        
    Returns:
        Historical exchange rates
    """
    try:
        logger.info(f"Fetching historical rates for {base_currency}/{target_currency} from {start_date} to {end_date}")
        
        # Validate date range
        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_date must be after start_date"
            )
        
        # Limit historical data range to prevent abuse
        max_days = 365
        if (end_date - start_date).days > max_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Date range cannot exceed {max_days} days"
            )
        
        # Query historical rates from database
        query = select(ExchangeRate).where(
            and_(
                ExchangeRate.base_currency == base_currency.upper(),
                ExchangeRate.target_currency == target_currency.upper(),
                ExchangeRate.timestamp >= start_date,
                ExchangeRate.timestamp <= end_date,
                ExchangeRate.is_active == True
            )
        ).order_by(ExchangeRate.timestamp)
        
        result = await db.execute(query)
        rates_data = result.scalars().all()
        
        # Format response
        rates = [
            {
                "timestamp": rate.timestamp.isoformat(),
                "rate": float(rate.rate),
                "source": rate.source
            }
            for rate in rates_data
        ]
        
        response = HistoricalRateResponse(
            base_currency=base_currency.upper(),
            target_currency=target_currency.upper(),
            rates=rates,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"Retrieved {len(rates)} historical rates")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get historical rates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve historical rates: {str(e)}"
        )


@router.get(
    "/preferences/{user_id}",
    response_model=CurrencyPreferenceResponse,
    summary="Get user currency preferences",
    description="Retrieve currency preferences for a specific user"
)
async def get_user_preferences(
    user_id: str = Path(..., description="User identifier"),
    db: AsyncSession = Depends(get_db)
) -> CurrencyPreferenceResponse:
    """Get user currency preferences.
    
    Args:
        user_id: User identifier
        db: Database session
        
    Returns:
        User currency preferences
    """
    try:
        logger.info(f"Fetching currency preferences for user: {user_id}")
        
        query = select(CurrencyPreference).where(CurrencyPreference.user_id == user_id)
        result = await db.execute(query)
        preference = result.scalar_one_or_none()
        
        if not preference:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Currency preferences not found for user {user_id}"
            )
        
        response = CurrencyPreferenceResponse(
            user_id=preference.user_id,
            preferred_currency=preference.preferred_currency,
            display_format=preference.display_format,
            decimal_places=preference.decimal_places,
            thousands_separator=preference.thousands_separator,
            decimal_separator=preference.decimal_separator,
            region=preference.region,
            timezone=preference.timezone,
            created_at=preference.created_at,
            updated_at=preference.updated_at
        )
        
        logger.info(f"Retrieved preferences for user {user_id}: {preference.preferred_currency}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user preferences: {str(e)}"
        )


@router.post(
    "/preferences/{user_id}",
    response_model=CurrencyPreferenceResponse,
    summary="Set user currency preferences",
    description="Create or update currency preferences for a specific user"
)
async def set_user_preferences(
    user_id: str = Path(..., description="User identifier"),
    preference_request: CurrencyPreferenceRequest = Body(...),
    db: AsyncSession = Depends(get_db)
) -> CurrencyPreferenceResponse:
    """Set user currency preferences.
    
    Args:
        user_id: User identifier
        preference_request: Currency preference data
        db: Database session
        
    Returns:
        Updated user currency preferences
    """
    try:
        logger.info(f"Setting currency preferences for user: {user_id}")
        
        # Check if preferences already exist
        query = select(CurrencyPreference).where(CurrencyPreference.user_id == user_id)
        result = await db.execute(query)
        existing_preference = result.scalar_one_or_none()
        
        if existing_preference:
            # Update existing preferences
            existing_preference.preferred_currency = preference_request.preferred_currency
            existing_preference.display_format = preference_request.display_format
            existing_preference.decimal_places = preference_request.decimal_places
            existing_preference.thousands_separator = preference_request.thousands_separator
            existing_preference.decimal_separator = preference_request.decimal_separator
            existing_preference.region = preference_request.region
            existing_preference.timezone = preference_request.timezone
            
            preference = existing_preference
        else:
            # Create new preferences
            preference = CurrencyPreference(
                user_id=user_id,
                preferred_currency=preference_request.preferred_currency,
                display_format=preference_request.display_format,
                decimal_places=preference_request.decimal_places,
                thousands_separator=preference_request.thousands_separator,
                decimal_separator=preference_request.decimal_separator,
                region=preference_request.region,
                timezone=preference_request.timezone
            )
            db.add(preference)
        
        await db.commit()
        await db.refresh(preference)
        
        response = CurrencyPreferenceResponse(
            user_id=preference.user_id,
            preferred_currency=preference.preferred_currency,
            display_format=preference.display_format,
            decimal_places=preference.decimal_places,
            thousands_separator=preference.thousands_separator,
            decimal_separator=preference.decimal_separator,
            region=preference.region,
            timezone=preference.timezone,
            created_at=preference.created_at,
            updated_at=preference.updated_at
        )
        
        logger.info(f"Updated preferences for user {user_id}: {preference.preferred_currency}")
        return response
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to set user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set user preferences: {str(e)}"
        )