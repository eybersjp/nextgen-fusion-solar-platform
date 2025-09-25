"""Initial migration

Revision ID: de8dcb612834
Revises: 
Create Date: 2025-09-25 16:38:17.669949

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision = 'de8dcb612834'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    pass


def downgrade() -> None:
    """Downgrade database schema."""
    pass