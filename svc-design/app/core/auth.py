"""Authentication utilities for the Design Service.

Handles JWT token verification, user authentication,
and authorization logic.
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .exceptions import AuthenticationError, AuthorizationError

settings = get_settings()


class User:
    """Simple user model for authentication."""
    
    def __init__(
        self,
        id: UUID,
        email: str,
        name: str,
        roles: list = None,
        organizations: list = None,
        is_active: bool = True,
        **kwargs
    ):
        self.id = id
        self.email = email
        self.name = name
        self.roles = roles or []
        self.organizations = organizations or []
        self.is_active = is_active
        
        # Additional attributes
        for key, value in kwargs.items():
            setattr(self, key, value)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Check if token has expired
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise AuthenticationError("Token has expired")
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")
    except Exception as e:
        raise AuthenticationError(f"Token verification failed: {str(e)}")


async def get_user_from_token(payload: Dict[str, Any], db: Session) -> Optional[User]:
    """Get user information from JWT token payload."""
    try:
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Token missing user ID")
        
        # Convert string UUID to UUID object
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise AuthenticationError("Invalid user ID format")
        
        # In a real implementation, you would fetch user from database
        # For now, we'll create a user from token payload
        user_data = {
            "id": user_uuid,
            "email": payload.get("email", ""),
            "name": payload.get("name", ""),
            "roles": payload.get("roles", []),
            "organizations": payload.get("organizations", []),
            "is_active": payload.get("is_active", True),
        }
        
        # Add any additional claims from the token
        for key, value in payload.items():
            if key not in ["sub", "exp", "iat", "email", "name", "roles", "organizations", "is_active"]:
                user_data[key] = value
        
        return User(**user_data)
        
    except Exception as e:
        raise AuthenticationError(f"Failed to get user from token: {str(e)}")


def check_user_permission(
    user: User,
    resource: str,
    action: str,
    resource_id: Optional[UUID] = None,
    organization_id: Optional[UUID] = None
) -> bool:
    """Check if user has permission to perform action on resource."""
    try:
        # Super admin has all permissions
        if "super_admin" in user.roles:
            return True
        
        # Admin has most permissions within their organizations
        if "admin" in user.roles:
            if organization_id:
                user_org_ids = [org.get("id") if isinstance(org, dict) else org for org in user.organizations]
                if organization_id in user_org_ids:
                    return True
            else:
                return True
        
        # Resource-specific permission checks
        if resource == "design":
            return check_design_permission(user, action, resource_id, organization_id)
        elif resource == "layout":
            return check_layout_permission(user, action, resource_id, organization_id)
        elif resource == "shading":
            return check_shading_permission(user, action, resource_id, organization_id)
        elif resource == "bom":
            return check_bom_permission(user, action, resource_id, organization_id)
        
        # Default deny
        return False
        
    except Exception:
        # On error, deny access
        return False


def check_design_permission(
    user: User,
    action: str,
    design_id: Optional[UUID] = None,
    organization_id: Optional[UUID] = None
) -> bool:
    """Check design-specific permissions."""
    # Design engineers can create, read, update designs
    if "design_engineer" in user.roles:
        if action in ["create", "read", "update"]:
            return True
        elif action == "delete" and "senior_design_engineer" in user.roles:
            return True
    
    # Project managers can read and approve designs
    if "project_manager" in user.roles:
        if action in ["read", "approve"]:
            return True
    
    # Viewers can only read
    if "viewer" in user.roles and action == "read":
        return True
    
    return False


def check_layout_permission(
    user: User,
    action: str,
    layout_id: Optional[UUID] = None,
    organization_id: Optional[UUID] = None
) -> bool:
    """Check layout-specific permissions."""
    # Layout engineers can create, read, update layouts
    if "layout_engineer" in user.roles or "design_engineer" in user.roles:
        if action in ["create", "read", "update"]:
            return True
        elif action == "delete" and "senior_design_engineer" in user.roles:
            return True
    
    # Project managers can read layouts
    if "project_manager" in user.roles and action == "read":
        return True
    
    # Viewers can only read
    if "viewer" in user.roles and action == "read":
        return True
    
    return False


def check_shading_permission(
    user: User,
    action: str,
    analysis_id: Optional[UUID] = None,
    organization_id: Optional[UUID] = None
) -> bool:
    """Check shading analysis permissions."""
    # Shading analysts and design engineers can perform analysis
    if "shading_analyst" in user.roles or "design_engineer" in user.roles:
        if action in ["create", "read", "update", "analyze"]:
            return True
        elif action == "delete" and "senior_design_engineer" in user.roles:
            return True
    
    # Project managers can read analysis
    if "project_manager" in user.roles and action == "read":
        return True
    
    # Viewers can only read
    if "viewer" in user.roles and action == "read":
        return True
    
    return False


def check_bom_permission(
    user: User,
    action: str,
    bom_id: Optional[UUID] = None,
    organization_id: Optional[UUID] = None
) -> bool:
    """Check BOM-specific permissions."""
    # BOM engineers and procurement can manage BOMs
    if "bom_engineer" in user.roles or "procurement" in user.roles or "design_engineer" in user.roles:
        if action in ["create", "read", "update"]:
            return True
        elif action == "delete" and "senior_design_engineer" in user.roles:
            return True
    
    # Project managers can read BOMs
    if "project_manager" in user.roles and action == "read":
        return True
    
    # Viewers can only read
    if "viewer" in user.roles and action == "read":
        return True
    
    return False


def require_permission(
    resource: str,
    action: str,
    resource_id: Optional[UUID] = None,
    organization_id: Optional[UUID] = None
):
    """Decorator to require specific permissions."""
    def permission_checker(user: User):
        if not check_user_permission(user, resource, action, resource_id, organization_id):
            raise AuthorizationError(
                f"Permission denied: {action} on {resource}"
            )
        return user
    
    return permission_checker


def get_user_organizations(user: User) -> list:
    """Get list of organization IDs the user belongs to."""
    if not user.organizations:
        return []
    
    org_ids = []
    for org in user.organizations:
        if isinstance(org, dict):
            org_ids.append(org.get("id"))
        elif hasattr(org, "id"):
            org_ids.append(org.id)
        else:
            org_ids.append(org)
    
    return org_ids


def filter_by_organization(
    user: User,
    query,
    organization_field: str = "organization_id"
):
    """Filter query results by user's organizations."""
    # Super admin sees everything
    if "super_admin" in user.roles:
        return query
    
    # Filter by user's organizations
    user_org_ids = get_user_organizations(user)
    if user_org_ids:
        return query.filter(getattr(query.column_descriptions[0]['type'], organization_field).in_(user_org_ids))
    
    # If user has no organizations, return empty result
    return query.filter(False)


def create_service_token(service_name: str, permissions: list = None) -> str:
    """Create a service-to-service authentication token."""
    data = {
        "sub": f"service:{service_name}",
        "service": service_name,
        "permissions": permissions or [],
        "type": "service"
    }
    
    # Service tokens have longer expiration
    expires_delta = timedelta(hours=24)
    
    return create_access_token(data, expires_delta)


def verify_service_token(token: str, required_service: str = None) -> Dict[str, Any]:
    """Verify a service-to-service token."""
    payload = verify_token(token)
    
    # Check if it's a service token
    if payload.get("type") != "service":
        raise AuthenticationError("Invalid service token")
    
    # Check specific service if required
    if required_service and payload.get("service") != required_service:
        raise AuthenticationError(f"Token not valid for service: {required_service}")
    
    return payload


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    try:
        import bcrypt
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except ImportError:
        # Fallback to simple hashing (not recommended for production)
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ImportError:
        # Fallback verification
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest() == hashed_password


def generate_api_key() -> str:
    """Generate a random API key."""
    import secrets
    import string
    
    # Generate a 32-character API key
    alphabet = string.ascii_letters + string.digits
    api_key = ''.join(secrets.choice(alphabet) for _ in range(32))
    
    return f"sk-{api_key}"


def validate_api_key(api_key: str) -> bool:
    """Validate API key format."""
    if not api_key.startswith("sk-"):
        return False
    
    key_part = api_key[3:]
    if len(key_part) != 32:
        return False
    
    # Check if all characters are alphanumeric
    return key_part.isalnum()


# FastAPI security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """FastAPI dependency to get current authenticated user."""
    try:
        # Verify the JWT token
        payload = verify_token(credentials.credentials)
        
        # Get user from token payload
        user = await get_user_from_token(payload, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
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