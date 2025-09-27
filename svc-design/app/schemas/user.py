"""User authentication and session Pydantic schemas."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum

from .base import BaseSchema, TimestampSchema


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"
    MANAGER = "manager"
    VIEWER = "viewer"


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=255, description="User full name")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    company: Optional[str] = Field(None, max_length=255, description="Company name")
    title: Optional[str] = Field(None, max_length=100, description="Job title")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")

    @validator('email')
    def validate_email(cls, v):
        """Validate email format and normalize."""
        return v.lower().strip()

    @validator('name')
    def validate_name(cls, v):
        """Validate and normalize name."""
        return v.strip()


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="User password (min 8 characters)"
    )
    confirm_password: str = Field(
        ..., 
        description="Password confirmation"
    )

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate that passwords match."""
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)

    @validator('name')
    def validate_name(cls, v):
        """Validate and normalize name."""
        if v is not None:
            return v.strip()
        return v


class UserPasswordUpdate(BaseModel):
    """Schema for updating user password."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="New password"
    )
    confirm_password: str = Field(..., description="New password confirmation")

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate that passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserResponse(UserBase, TimestampSchema):
    """Schema for user response data."""
    id: str = Field(..., description="User ID")
    is_active: bool = Field(..., description="Whether user is active")
    is_verified: bool = Field(..., description="Whether user email is verified")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    password_changed_at: Optional[datetime] = Field(None, description="Password last changed")

    class Config:
        from_attributes = True


class UserProfile(UserResponse):
    """Extended user profile with additional information."""
    pass


class UserList(BaseModel):
    """Schema for paginated user list."""
    users: List[UserResponse]
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")


# Authentication Schemas
class LoginRequest(BaseModel):
    """Schema for user login request."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(default=False, description="Remember login session")

    @validator('email')
    def validate_email(cls, v):
        """Normalize email."""
        return v.lower().strip()


class LoginResponse(BaseModel):
    """Schema for login response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse = Field(..., description="User information")


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str = Field(..., description="Refresh token")


class RefreshTokenResponse(BaseModel):
    """Schema for token refresh response."""
    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    email: EmailStr = Field(..., description="User email")

    @validator('email')
    def validate_email(cls, v):
        """Normalize email."""
        return v.lower().strip()


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str = Field(..., description="Reset token")
    new_password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="New password"
    )
    confirm_password: str = Field(..., description="Password confirmation")

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate that passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class EmailVerificationRequest(BaseModel):
    """Schema for email verification request."""
    token: str = Field(..., description="Verification token")


# Session Schemas
class UserSessionBase(BaseModel):
    """Base user session schema."""
    ip_address: Optional[str] = Field(None, max_length=45, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    device_info: Optional[str] = Field(None, max_length=255, description="Device information")


class UserSessionCreate(UserSessionBase):
    """Schema for creating a user session."""
    user_id: str = Field(..., description="User ID")
    token_hash: str = Field(..., description="Hashed token")
    expires_at: datetime = Field(..., description="Session expiration")


class UserSessionResponse(UserSessionBase, TimestampSchema):
    """Schema for user session response."""
    id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    expires_at: datetime = Field(..., description="Session expiration")
    is_active: bool = Field(..., description="Whether session is active")
    revoked_at: Optional[datetime] = Field(None, description="Session revocation time")
    revoked_by: Optional[str] = Field(None, description="Who revoked the session")

    class Config:
        from_attributes = True


class UserSessionList(BaseModel):
    """Schema for user session list."""
    sessions: List[UserSessionResponse]
    total: int = Field(..., description="Total number of sessions")