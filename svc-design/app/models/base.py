"""Base model classes for the Design Service.

This module contains base SQLAlchemy models and mixins that provide
common functionality for all database models.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Column, DateTime, String, Text, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from ..core.logging import get_logger

logger = get_logger(__name__)

# Create declarative base
Base = declarative_base()


class BaseModel(Base):
    """Base model class with common functionality."""
    
    __abstract__ = True
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique identifier"
    )
    
    @declared_attr
    def __tablename__(cls):
        """Generate table name from class name.
        
        Returns:
            str: Table name in snake_case
        """
        # Convert CamelCase to snake_case
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
    
    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert model to dictionary.
        
        Args:
            exclude: List of fields to exclude
            
        Returns:
            Dict[str, Any]: Model as dictionary
        """
        exclude = exclude or []
        result = {}
        
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                
                # Handle special types
                if isinstance(value, uuid.UUID):
                    value = str(value)
                elif isinstance(value, datetime):
                    value = value.isoformat()
                
                result[column.name] = value
        
        return result
    
    def update_from_dict(self, data: Dict[str, Any], exclude: Optional[List[str]] = None):
        """Update model from dictionary.
        
        Args:
            data: Data dictionary
            exclude: List of fields to exclude
        """
        exclude = exclude or ['id', 'created_at']
        
        for key, value in data.items():
            if key not in exclude and hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        """String representation of model.
        
        Returns:
            str: Model representation
        """
        return f"<{self.__class__.__name__}(id={self.id})>"


class TimestampMixin:
    """Mixin for automatic timestamp management."""
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        doc="Creation timestamp"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        doc="Last update timestamp"
    )
    
    @property
    def created_at_utc(self) -> datetime:
        """Get creation timestamp in UTC.
        
        Returns:
            datetime: UTC timestamp
        """
        if self.created_at.tzinfo is None:
            return self.created_at.replace(tzinfo=timezone.utc)
        return self.created_at.astimezone(timezone.utc)
    
    @property
    def updated_at_utc(self) -> datetime:
        """Get update timestamp in UTC.
        
        Returns:
            datetime: UTC timestamp
        """
        if self.updated_at.tzinfo is None:
            return self.updated_at.replace(tzinfo=timezone.utc)
        return self.updated_at.astimezone(timezone.utc)


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Soft delete timestamp"
    )
    
    deleted_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="User who deleted the record"
    )
    
    @property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted.
        
        Returns:
            bool: True if deleted
        """
        return self.deleted_at is not None
    
    def soft_delete(self, user_id: Optional[uuid.UUID] = None):
        """Soft delete the record.
        
        Args:
            user_id: ID of user performing deletion
        """
        self.deleted_at = datetime.now(timezone.utc)
        self.deleted_by = user_id
    
    def restore(self):
        """Restore soft deleted record."""
        self.deleted_at = None
        self.deleted_by = None


class AuditMixin:
    """Mixin for audit trail functionality."""
    
    created_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="User who created the record"
    )
    
    updated_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="User who last updated the record"
    )
    
    version = Column(
        String(50),
        nullable=True,
        doc="Record version for optimistic locking"
    )
    
    def set_created_by(self, user_id: uuid.UUID):
        """Set creator information.
        
        Args:
            user_id: User ID
        """
        self.created_by = user_id
    
    def set_updated_by(self, user_id: uuid.UUID):
        """Set updater information.
        
        Args:
            user_id: User ID
        """
        self.updated_by = user_id


class MetadataMixin:
    """Mixin for metadata storage."""
    
    metadata = Column(
        Text,
        nullable=True,
        doc="JSON metadata storage"
    )
    
    tags = Column(
        Text,
        nullable=True,
        doc="Comma-separated tags"
    )
    
    notes = Column(
        Text,
        nullable=True,
        doc="Additional notes"
    )
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata as dictionary.
        
        Returns:
            Dict[str, Any]: Metadata dictionary
        """
        if not self.metadata:
            return {}
        
        try:
            import json
            return json.loads(self.metadata)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Invalid metadata JSON for {self.__class__.__name__} {self.id}")
            return {}
    
    def set_metadata(self, metadata: Dict[str, Any]):
        """Set metadata from dictionary.
        
        Args:
            metadata: Metadata dictionary
        """
        try:
            import json
            self.metadata = json.dumps(metadata, default=str)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize metadata: {e}")
            raise
    
    def get_tags(self) -> List[str]:
        """Get tags as list.
        
        Returns:
            List[str]: List of tags
        """
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    def set_tags(self, tags: List[str]):
        """Set tags from list.
        
        Args:
            tags: List of tags
        """
        self.tags = ','.join(tags) if tags else None
    
    def add_tag(self, tag: str):
        """Add a tag.
        
        Args:
            tag: Tag to add
        """
        current_tags = self.get_tags()
        if tag not in current_tags:
            current_tags.append(tag)
            self.set_tags(current_tags)
    
    def remove_tag(self, tag: str):
        """Remove a tag.
        
        Args:
            tag: Tag to remove
        """
        current_tags = self.get_tags()
        if tag in current_tags:
            current_tags.remove(tag)
            self.set_tags(current_tags)


class StatusMixin:
    """Mixin for status management."""
    
    status = Column(
        String(50),
        nullable=False,
        default='draft',
        doc="Record status"
    )
    
    status_changed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Status change timestamp"
    )
    
    status_changed_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="User who changed the status"
    )
    
    def change_status(self, new_status: str, user_id: Optional[uuid.UUID] = None):
        """Change record status.
        
        Args:
            new_status: New status
            user_id: User making the change
        """
        old_status = self.status
        self.status = new_status
        self.status_changed_at = datetime.now(timezone.utc)
        self.status_changed_by = user_id
        
        logger.info(
            f"Status changed for {self.__class__.__name__} {self.id}: "
            f"{old_status} -> {new_status}"
        )


# Event listeners for automatic timestamp updates
@event.listens_for(TimestampMixin, 'before_update', propagate=True)
def update_timestamp(mapper, connection, target):
    """Update timestamp before update.
    
    Args:
        mapper: SQLAlchemy mapper
        connection: Database connection
        target: Target object
    """
    target.updated_at = datetime.now(timezone.utc)


@event.listens_for(StatusMixin, 'before_update', propagate=True)
def update_status_timestamp(mapper, connection, target):
    """Update status timestamp when status changes.
    
    Args:
        mapper: SQLAlchemy mapper
        connection: Database connection
        target: Target object
    """
    # Check if status has changed
    state = target.__dict__
    if 'status' in state.get('_sa_instance_state').committed_state:
        old_status = state['_sa_instance_state'].committed_state['status']
        if old_status != target.status:
            target.status_changed_at = datetime.now(timezone.utc)


# Query helpers
class QueryMixin:
    """Mixin for common query operations."""
    
    @classmethod
    def get_by_id(cls, session: Session, record_id: uuid.UUID):
        """Get record by ID.
        
        Args:
            session: Database session
            record_id: Record ID
            
        Returns:
            Model instance or None
        """
        return session.query(cls).filter(cls.id == record_id).first()
    
    @classmethod
    def get_active(cls, session: Session):
        """Get all active (non-deleted) records.
        
        Args:
            session: Database session
            
        Returns:
            Query: SQLAlchemy query
        """
        query = session.query(cls)
        
        # Add soft delete filter if applicable
        if hasattr(cls, 'deleted_at'):
            query = query.filter(cls.deleted_at.is_(None))
        
        return query
    
    @classmethod
    def get_by_status(cls, session: Session, status: str):
        """Get records by status.
        
        Args:
            session: Database session
            status: Status value
            
        Returns:
            Query: SQLAlchemy query
        """
        query = cls.get_active(session)
        
        if hasattr(cls, 'status'):
            query = query.filter(cls.status == status)
        
        return query
    
    @classmethod
    def search(cls, session: Session, search_term: str, fields: Optional[List[str]] = None):
        """Search records by text fields.
        
        Args:
            session: Database session
            search_term: Search term
            fields: Fields to search (defaults to common text fields)
            
        Returns:
            Query: SQLAlchemy query
        """
        from sqlalchemy import or_, func
        
        query = cls.get_active(session)
        
        if not search_term:
            return query
        
        # Default search fields
        if fields is None:
            fields = []
            for column in cls.__table__.columns:
                if column.type.python_type == str and column.name not in ['id', 'status']:
                    fields.append(column.name)
        
        # Build search conditions
        conditions = []
        search_pattern = f"%{search_term}%"
        
        for field in fields:
            if hasattr(cls, field):
                column = getattr(cls, field)
                conditions.append(func.lower(column).like(func.lower(search_pattern)))
        
        if conditions:
            query = query.filter(or_(*conditions))
        
        return query


# Base model with all mixins
class FullBaseModel(BaseModel, TimestampMixin, SoftDeleteMixin, AuditMixin, MetadataMixin, StatusMixin, QueryMixin):
    """Full base model with all common functionality."""
    
    __abstract__ = True


# Utility functions
def create_tables(engine):
    """Create all tables.
    
    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")


def drop_tables(engine):
    """Drop all tables.
    
    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.drop_all(bind=engine)
    logger.info("Database tables dropped")


def get_table_names() -> List[str]:
    """Get list of all table names.
    
    Returns:
        List[str]: Table names
    """
    return list(Base.metadata.tables.keys())


def get_model_by_tablename(table_name: str):
    """Get model class by table name.
    
    Args:
        table_name: Table name
        
    Returns:
        Model class or None
    """
    for mapper in Base.registry.mappers:
        model = mapper.class_
        if hasattr(model, '__tablename__') and model.__tablename__ == table_name:
            return model
    return None