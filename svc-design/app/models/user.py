"""User authentication models for the Design Service.

This module contains SQLAlchemy models for user authentication,
sessions, and user management functionality.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, String, Text, Index,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash

from .base import BaseModel, TimestampMixin, SoftDeleteMixin, AuditMixin


class User(BaseModel, TimestampMixin, SoftDeleteMixin):
    """User model for authentication and user management."""
    
    __tablename__ = "users"
    
    # Basic user information
    email = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        doc="User email address (unique)"
    )
    
    password_hash = Column(
        String(255),
        nullable=False,
        doc="Hashed password"
    )
    
    name = Column(
        String(255),
        nullable=False,
        doc="User full name"
    )
    
    role = Column(
        String(50),
        nullable=False,
        default="user",
        doc="User role (admin, user, viewer)"
    )
    
    # Account status
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Account active status"
    )
    
    is_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="Email verification status"
    )
    
    # Profile information
    company = Column(
        String(255),
        nullable=True,
        doc="Company name"
    )
    
    title = Column(
        String(100),
        nullable=True,
        doc="Job title"
    )
    
    phone = Column(
        String(50),
        nullable=True,
        doc="Phone number"
    )
    
    # Authentication timestamps
    last_login_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last login timestamp"
    )
    
    password_changed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
        doc="Password last changed timestamp"
    )
    
    # Verification tokens
    verification_token = Column(
        String(255),
        nullable=True,
        doc="Email verification token"
    )
    
    reset_token = Column(
        String(255),
        nullable=True,
        doc="Password reset token"
    )
    
    reset_token_expires = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Password reset token expiration"
    )
    
    # Relationships
    projects = relationship(
        "Project",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    sessions = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # Table constraints and indexes
    __table_args__ = (
        Index("idx_users_email_active", "email", "is_active"),
        Index("idx_users_role", "role"),
        Index("idx_users_company", "company"),
        UniqueConstraint("email", name="uq_users_email"),
    )
    
    def set_password(self, password: str) -> None:
        """Set user password with hashing.
        
        Args:
            password: Plain text password
        """
        self.password_hash = generate_password_hash(password)
        self.password_changed_at = datetime.now(timezone.utc)
    
    def check_password(self, password: str) -> bool:
        """Check if provided password matches stored hash.
        
        Args:
            password: Plain text password to check
            
        Returns:
            bool: True if password matches
        """
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self) -> None:
        """Update last login timestamp."""
        self.last_login_at = datetime.now(timezone.utc)
    
    def is_password_expired(self, max_age_days: int = 90) -> bool:
        """Check if password has expired.
        
        Args:
            max_age_days: Maximum password age in days
            
        Returns:
            bool: True if password is expired
        """
        if not self.password_changed_at:
            return True
        
        age = datetime.now(timezone.utc) - self.password_changed_at
        return age.days > max_age_days
    
    def can_access_project(self, project_id: uuid.UUID) -> bool:
        """Check if user can access a specific project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            bool: True if user has access
        """
        # Admin users can access all projects
        if self.role == "admin":
            return True
        
        # Users can access their own projects
        return any(p.id == project_id for p in self.projects)
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert user to dictionary.
        
        Args:
            include_sensitive: Include sensitive fields
            
        Returns:
            dict: User data
        """
        exclude = ["password_hash", "verification_token", "reset_token"]
        if not include_sensitive:
            exclude.extend(["reset_token_expires"])
        
        return super().to_dict(exclude=exclude)
    
    def __repr__(self) -> str:
        """String representation of user."""
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class UserSession(BaseModel, TimestampMixin):
    """User session model for JWT token management."""
    
    __tablename__ = "user_sessions"
    
    # Foreign key to user
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="User identifier"
    )
    
    # Session information
    token_hash = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        doc="Hashed JWT token"
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Session expiration timestamp"
    )
    
    # Session metadata
    ip_address = Column(
        String(45),  # IPv6 max length
        nullable=True,
        doc="Client IP address"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        doc="Client user agent string"
    )
    
    device_info = Column(
        String(255),
        nullable=True,
        doc="Device information"
    )
    
    # Session status
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Session active status"
    )
    
    revoked_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Session revocation timestamp"
    )
    
    revoked_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="User who revoked the session"
    )
    
    # Relationships
    user = relationship(
        "User",
        back_populates="sessions"
    )
    
    # Table constraints and indexes
    __table_args__ = (
        Index("idx_sessions_user_active", "user_id", "is_active"),
        Index("idx_sessions_expires", "expires_at"),
        Index("idx_sessions_token", "token_hash"),
        Index("idx_sessions_ip", "ip_address"),
    )
    
    def is_expired(self) -> bool:
        """Check if session is expired.
        
        Returns:
            bool: True if session is expired
        """
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if session is valid (active and not expired).
        
        Returns:
            bool: True if session is valid
        """
        return self.is_active and not self.is_expired() and not self.revoked_at
    
    def revoke(self, revoked_by: Optional[uuid.UUID] = None) -> None:
        """Revoke the session.
        
        Args:
            revoked_by: User who revoked the session
        """
        self.is_active = False
        self.revoked_at = datetime.now(timezone.utc)
        self.revoked_by = revoked_by
    
    def __repr__(self) -> str:
        """String representation of session."""
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"