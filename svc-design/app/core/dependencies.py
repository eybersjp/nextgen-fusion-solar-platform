"""Core dependencies for the Design Service.

Provides common FastAPI dependencies for authentication,
database sessions, pagination, and validation.
"""

from typing import Optional, Tuple
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .auth import AuthService
from .exceptions import AuthenticationError, ValidationError

# Security scheme for JWT tokens
security = HTTPBearer()


def get_db_session() -> Session:
    """Get database session dependency."""
    return next(get_db())


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session),
):
    """Get current authenticated user from JWT token."""
    try:
        auth_service = AuthService()
        
        # Verify the JWT token and get user
        user = await auth_service.get_current_user(credentials.credentials, db)
        
        if not user:
            raise AuthenticationError("User not found")
        
        return user
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user = Depends(get_current_user),
):
    """Get current active user (not disabled)."""
    if getattr(current_user, 'is_active', True) is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def get_pagination_params(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
) -> Tuple[int, int]:
    """Get pagination parameters."""
    return skip, limit


def validate_uuid(uuid_str: str) -> UUID:
    """Validate and convert string to UUID."""
    try:
        return UUID(uuid_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid UUID format: {uuid_str}"
        )


def get_sort_params(
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
) -> Tuple[str, str]:
    """Get sorting parameters."""
    return sort_by, sort_order


# Alias for backward compatibility
get_sorting_params = get_sort_params


def get_search_params(
    search: Optional[str] = Query(None, description="Search query"),
    search_fields: Optional[str] = Query(None, description="Comma-separated list of fields to search"),
) -> Tuple[Optional[str], Optional[list]]:
    """Get search parameters."""
    fields = None
    if search_fields:
        fields = [field.strip() for field in search_fields.split(",") if field.strip()]
    return search, fields


def get_date_range_params(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
) -> Tuple[Optional[str], Optional[str]]:
    """Get date range parameters."""
    return start_date, end_date


def get_filter_params(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    type: Optional[str] = Query(None, description="Filter by type"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
) -> dict:
    """Get common filter parameters."""
    filters = {}
    
    if status:
        filters["status"] = status
    if category:
        filters["category"] = category
    if type:
        filters["type"] = type
    if tags:
        filters["tags"] = [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    return filters


def validate_coordinates(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude in decimal degrees"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude in decimal degrees"),
) -> Tuple[float, float]:
    """Validate geographic coordinates."""
    return latitude, longitude


def validate_positive_number(
    value: float,
    field_name: str = "value",
    allow_zero: bool = False,
) -> float:
    """Validate that a number is positive."""
    if allow_zero and value < 0:
        raise ValidationError(f"{field_name} must be non-negative")
    elif not allow_zero and value <= 0:
        raise ValidationError(f"{field_name} must be positive")
    return value


def validate_percentage(
    value: float,
    field_name: str = "percentage",
) -> float:
    """Validate that a value is a valid percentage (0-100)."""
    if not 0 <= value <= 100:
        raise ValidationError(f"{field_name} must be between 0 and 100")
    return value


def validate_currency_code(
    currency: str = Query(..., pattern="^[A-Z]{3}$", description="ISO 4217 currency code"),
) -> str:
    """Validate ISO 4217 currency code."""
    # Common currency codes validation
    valid_currencies = {
        "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY",
        "SEK", "NZD", "MXN", "SGD", "HKD", "NOK", "ZAR", "TRY",
        "BRL", "INR", "RUB", "KRW", "PLN", "THB", "IDR", "HUF",
        "CZK", "ILS", "CLP", "PHP", "AED", "COP", "SAR", "MYR",
        "RON", "BGN", "HRK", "DKK", "ISK", "EGP", "QAR", "KWD"
    }
    
    if currency not in valid_currencies:
        raise ValidationError(f"Unsupported currency code: {currency}")
    
    return currency


def validate_country_code(
    country: str = Query(..., pattern="^[A-Z]{2}$", description="ISO 3166-1 alpha-2 country code"),
) -> str:
    """Validate ISO 3166-1 alpha-2 country code."""
    # Common country codes validation
    valid_countries = {
        "US", "CA", "GB", "DE", "FR", "IT", "ES", "NL", "BE", "AT",
        "CH", "SE", "NO", "DK", "FI", "IE", "PT", "GR", "PL", "CZ",
        "HU", "SK", "SI", "HR", "BG", "RO", "LT", "LV", "EE", "MT",
        "CY", "LU", "AU", "NZ", "JP", "KR", "CN", "IN", "SG", "HK",
        "MY", "TH", "ID", "PH", "VN", "TW", "BD", "PK", "LK", "MM",
        "BR", "AR", "CL", "CO", "PE", "VE", "UY", "PY", "BO", "EC",
        "MX", "GT", "CR", "PA", "DO", "CU", "JM", "TT", "BB", "BS",
        "ZA", "NG", "KE", "GH", "UG", "TZ", "ZW", "BW", "ZM", "MW",
        "MZ", "MG", "MU", "SC", "RE", "YT", "EG", "MA", "DZ", "TN",
        "LY", "SD", "ET", "SO", "DJ", "ER", "SS", "CF", "TD", "CM",
        "GQ", "GA", "CG", "CD", "AO", "NA", "SZ", "LS", "RU", "UA",
        "BY", "MD", "GE", "AM", "AZ", "KZ", "UZ", "TM", "KG", "TJ",
        "AF", "PK", "IR", "IQ", "SY", "LB", "JO", "IL", "PS", "SA",
        "YE", "OM", "AE", "QA", "BH", "KW", "TR", "CY", "GR"
    }
    
    if country not in valid_countries:
        raise ValidationError(f"Unsupported country code: {country}")
    
    return country


def validate_timezone(
    timezone: str = Query(..., description="IANA timezone identifier"),
) -> str:
    """Validate IANA timezone identifier."""
    try:
        import pytz
        if timezone not in pytz.all_timezones:
            raise ValidationError(f"Invalid timezone: {timezone}")
        return timezone
    except ImportError:
        # Fallback validation for common timezones
        common_timezones = {
            "UTC", "America/New_York", "America/Chicago", "America/Denver",
            "America/Los_Angeles", "Europe/London", "Europe/Paris",
            "Europe/Berlin", "Europe/Rome", "Europe/Madrid", "Europe/Amsterdam",
            "Asia/Tokyo", "Asia/Shanghai", "Asia/Kolkata", "Asia/Dubai",
            "Australia/Sydney", "Australia/Melbourne", "Australia/Perth",
            "Africa/Johannesburg", "Africa/Cairo", "Africa/Lagos"
        }
        
        if timezone not in common_timezones:
            raise ValidationError(f"Unsupported timezone: {timezone}")
        
        return timezone


def get_organization_context(
    organization_id: Optional[UUID] = Query(None, description="Organization ID for multi-tenant context"),
    current_user = Depends(get_current_active_user),
) -> Optional[UUID]:
    """Get organization context for multi-tenant operations."""
    # If organization_id is provided, validate user has access
    if organization_id:
        # Check if user belongs to the organization
        user_orgs = getattr(current_user, 'organizations', [])
        if organization_id not in [org.id for org in user_orgs]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to organization"
            )
    
    return organization_id


def require_admin_role(
    current_user = Depends(get_current_active_user),
):
    """Require admin role for the current user."""
    user_roles = getattr(current_user, 'roles', [])
    if 'admin' not in user_roles and 'super_admin' not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user


def require_role(required_role: str):
    """Create a dependency that requires a specific role."""
    def role_checker(current_user = Depends(get_current_active_user)):
        user_roles = getattr(current_user, 'roles', [])
        if required_role not in user_roles and 'super_admin' not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return current_user
    
    return role_checker


def get_request_context(
    user_agent: Optional[str] = Query(None, description="User agent string"),
    client_ip: Optional[str] = Query(None, description="Client IP address"),
    request_id: Optional[str] = Query(None, description="Request ID for tracing"),
) -> dict:
    """Get request context for logging and tracing."""
    return {
        "user_agent": user_agent,
        "client_ip": client_ip,
        "request_id": request_id,
    }