"""Create currency and compliance tables

Revision ID: create_currency_compliance
Revises: create_project_management
Create Date: 2025-01-27 10:02:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'create_currency_compliance'
down_revision = 'create_project_management'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create currency and compliance tables."""
    
    # Create exchange_rates table
    op.create_table(
        'exchange_rates',
        sa.Column('id', sa.String(36), primary_key=True, default=sa.text('(lower(hex(randomblob(4))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(6))))')),
        sa.Column('base_currency', sa.String(3), nullable=False),
        sa.Column('target_currency', sa.String(3), nullable=False),
        sa.Column('rate', sa.DECIMAL(12, 6), nullable=False),
        sa.Column('rate_date', sa.Date, nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp())
    )
    
    # Create unique constraint and indexes for exchange_rates
    op.create_index('idx_exchange_rates_unique', 'exchange_rates', ['base_currency', 'target_currency', 'rate_date', 'source'], unique=True)
    op.create_index('idx_exchange_rates_currencies', 'exchange_rates', ['base_currency', 'target_currency'])
    op.create_index('idx_exchange_rates_date', 'exchange_rates', ['rate_date'])
    op.create_index('idx_exchange_rates_active', 'exchange_rates', ['is_active'])
    
    # Create multi_currency_transactions table
    op.create_table(
        'multi_currency_transactions',
        sa.Column('id', sa.String(36), primary_key=True, default=sa.text('(lower(hex(randomblob(4))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(6))))')),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('original_amount', sa.DECIMAL(12, 2), nullable=False),
        sa.Column('original_currency', sa.String(3), nullable=False),
        sa.Column('converted_amount', sa.DECIMAL(12, 2), nullable=False),
        sa.Column('converted_currency', sa.String(3), nullable=False),
        sa.Column('exchange_rate', sa.DECIMAL(12, 6), nullable=False),
        sa.Column('conversion_fee', sa.DECIMAL(12, 2), default=0),
        sa.Column('transaction_type', sa.String(50), nullable=False),
        sa.Column('reference_id', sa.String(36)),
        sa.Column('transaction_date', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'))
    )
    
    # Create indexes for multi_currency_transactions
    op.create_index('idx_multi_currency_transactions_project_id', 'multi_currency_transactions', ['project_id'])
    op.create_index('idx_multi_currency_transactions_date', 'multi_currency_transactions', ['transaction_date'])
    op.create_index('idx_multi_currency_transactions_type', 'multi_currency_transactions', ['transaction_type'])
    
    # Create currency_preferences table
    op.create_table(
        'currency_preferences',
        sa.Column('id', sa.String(36), primary_key=True, default=sa.text('(lower(hex(randomblob(4))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(6))))')),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('preferred_currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('display_currencies', sa.Text, default='["USD", "ZAR", "AUD"]'),  # JSON array as TEXT
        sa.Column('auto_convert', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp())
    )
    
    # Create unique constraint for currency_preferences
    op.create_index('idx_currency_preferences_user_id', 'currency_preferences', ['user_id'], unique=True)
    
    # Create compliance_rules table
    op.create_table(
        'compliance_rules',
        sa.Column('id', sa.String(36), primary_key=True, default=sa.text('(lower(hex(randomblob(4))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(6))))')),
        sa.Column('region', sa.String(10), nullable=False),
        sa.Column('rule_category', sa.String(100), nullable=False),
        sa.Column('rule_name', sa.String(200), nullable=False),
        sa.Column('rule_code', sa.String(50)),
        sa.Column('rule_definition', sa.Text, nullable=False),  # JSON as TEXT
        sa.Column('validation_logic', sa.Text),  # JSON as TEXT
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('effective_date', sa.Date, nullable=False),
        sa.Column('expiry_date', sa.Date),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('severity', sa.String(20), default='error'),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp())
    )
    
    # Create unique constraint and indexes for compliance_rules
    op.create_index('idx_compliance_rules_unique', 'compliance_rules', ['region', 'rule_code', 'version'], unique=True)
    op.create_index('idx_compliance_rules_region', 'compliance_rules', ['region'])
    op.create_index('idx_compliance_rules_active', 'compliance_rules', ['is_active'])
    op.create_index('idx_compliance_rules_category', 'compliance_rules', ['rule_category'])
    
    # Create compliance_validations table
    op.create_table(
        'compliance_validations',
        sa.Column('id', sa.String(36), primary_key=True, default=sa.text('(lower(hex(randomblob(4))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(6))))')),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('design_id', sa.String(36), sa.ForeignKey('design_3d_models.id', ondelete='SET NULL')),
        sa.Column('region', sa.String(10), nullable=False),
        sa.Column('validation_type', sa.String(50), nullable=False),
        sa.Column('overall_status', sa.String(20), nullable=False),
        sa.Column('rule_results', sa.Text, nullable=False, default='[]'),  # JSON as TEXT
        sa.Column('recommendations', sa.Text, default='[]'),  # JSON as TEXT
        sa.Column('validation_score', sa.DECIMAL(5, 2)),
        sa.Column('validated_by', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('validated_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('expires_at', sa.DateTime)
    )
    
    # Create indexes for compliance_validations
    op.create_index('idx_compliance_validations_project_id', 'compliance_validations', ['project_id'])
    op.create_index('idx_compliance_validations_region', 'compliance_validations', ['region'])
    op.create_index('idx_compliance_validations_status', 'compliance_validations', ['overall_status'])
    op.create_index('idx_compliance_validations_validated_at', 'compliance_validations', ['validated_at'])
    
    # Create compliance_reports table
    op.create_table(
        'compliance_reports',
        sa.Column('id', sa.String(36), primary_key=True, default=sa.text('(lower(hex(randomblob(4))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(6))))')),
        sa.Column('validation_id', sa.String(36), sa.ForeignKey('compliance_validations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('report_format', sa.String(20), nullable=False),
        sa.Column('file_path', sa.String(500)),
        sa.Column('file_size', sa.BigInteger),
        sa.Column('generated_by', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('generated_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('downloaded_at', sa.DateTime),
        sa.Column('expires_at', sa.DateTime)
    )
    
    # Enhance projects table with Phase 3 columns (only add new columns)
    # Note: budget_currency and project_type already exist
    op.add_column('projects', sa.Column('complexity_level', sa.String(20), default='medium'))
    op.add_column('projects', sa.Column('compliance_regions', sa.Text, default='["US"]'))  # JSON array as TEXT
    op.add_column('projects', sa.Column('design_requirements', sa.Text, default='{}'))  # JSON as TEXT
    op.add_column('projects', sa.Column('project_metadata', sa.Text, default='{}'))  # JSON as TEXT
    
    # Enhance users table with Phase 3 columns
    op.add_column('users', sa.Column('timezone', sa.String(50), default='UTC'))
    op.add_column('users', sa.Column('locale', sa.String(10), default='en_US'))
    op.add_column('users', sa.Column('notification_preferences', sa.Text, default='{"email": true, "sms": false, "push": true}'))  # JSON as TEXT
    op.add_column('users', sa.Column('professional_certifications', sa.Text, default='[]'))  # JSON array as TEXT
    op.add_column('users', sa.Column('compliance_permissions', sa.Text, default='{}'))  # JSON as TEXT


def downgrade() -> None:
    """Drop currency and compliance tables and enhanced columns."""
    # Drop enhanced columns from users table
    op.drop_column('users', 'compliance_permissions')
    op.drop_column('users', 'professional_certifications')
    op.drop_column('users', 'notification_preferences')
    op.drop_column('users', 'locale')
    op.drop_column('users', 'timezone')
    
    # Drop enhanced columns from projects table
    op.drop_column('projects', 'project_metadata')
    op.drop_column('projects', 'design_requirements')
    op.drop_column('projects', 'compliance_regions')
    op.drop_column('projects', 'complexity_level')
    op.drop_column('projects', 'project_type')
    op.drop_column('projects', 'budget_currency')
    
    # Drop tables
    op.drop_table('compliance_reports')
    op.drop_table('compliance_validations')
    op.drop_table('compliance_rules')
    op.drop_table('currency_preferences')
    op.drop_table('multi_currency_transactions')
    op.drop_table('exchange_rates')