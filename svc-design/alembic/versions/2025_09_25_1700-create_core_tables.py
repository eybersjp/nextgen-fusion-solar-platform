"""Create core tables for authentication, projects, and solar design

Revision ID: create_core_tables
Revises: de8dcb612834
Create Date: 2025-09-25 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'create_core_tables'
down_revision = 'de8dcb612834'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all core tables for the application."""
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(), nullable=True),
        sa.Column('verification_token', sa.String(length=255), nullable=True),
        sa.Column('reset_token', sa.String(length=255), nullable=True),
        sa.Column('reset_token_expires', sa.DateTime(), nullable=True),
        # Base model columns
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_users_email')
    )
    
    # Create indexes for users table
    op.create_index('idx_users_email_active', 'users', ['email', 'is_active'])
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_users_company', 'users', ['company'])
    
    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('device_info', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_by', sa.String(36), nullable=True),
        # Base model columns
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    
    # Create indexes for user_sessions table
    op.create_index('idx_sessions_user_active', 'user_sessions', ['user_id', 'is_active'])
    op.create_index('idx_sessions_expires', 'user_sessions', ['expires_at'])
    op.create_index('idx_sessions_token', 'user_sessions', ['token_hash'])
    op.create_index('idx_sessions_ip', 'user_sessions', ['ip_address'])
    
    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('project_type', sa.String(length=50), nullable=False, server_default='commercial'),
        sa.Column('site_address', sa.Text(), nullable=True),
        sa.Column('site_city', sa.String(length=100), nullable=True),
        sa.Column('site_state', sa.String(length=50), nullable=True),
        sa.Column('site_country', sa.String(length=50), nullable=False, server_default='ZA'),
        sa.Column('site_postal_code', sa.String(length=20), nullable=True),
        sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('elevation', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('target_capacity_kw', sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column('estimated_annual_production_kwh', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('budget_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('budget_currency', sa.String(length=3), nullable=False, server_default='ZAR'),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('target_completion_date', sa.DateTime(), nullable=True),
        sa.Column('actual_completion_date', sa.DateTime(), nullable=True),
        sa.Column('regulatory_requirements', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('permits_required', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('tags', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('custom_fields', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('design_preferences', sa.Text(), nullable=True),  # JSON as TEXT
        # Base model columns
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        # Audit columns
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for projects table
    op.create_index('idx_projects_owner', 'projects', ['owner_id'])
    op.create_index('idx_projects_status', 'projects', ['status'])
    op.create_index('idx_projects_type', 'projects', ['project_type'])
    op.create_index('idx_projects_country', 'projects', ['site_country'])
    op.create_index('idx_projects_location', 'projects', ['latitude', 'longitude'])
    op.create_index('idx_projects_dates', 'projects', ['start_date', 'target_completion_date'])
    
    # Create solar_designs table
    op.create_table(
        'solar_designs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=False, server_default='1.0'),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('system_capacity_kw', sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column('panel_count', sa.Integer(), nullable=True),
        sa.Column('inverter_count', sa.Integer(), nullable=True),
        sa.Column('array_configuration', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('panel_layout', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('electrical_design', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('estimated_annual_production_kwh', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('capacity_factor', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('performance_ratio', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('shading_analysis', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('irradiance_data', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('weather_data', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('estimated_cost', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('cost_per_watt', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('compliance_standards', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('design_validation', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('design_parameters', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('optimization_results', sa.Text(), nullable=True),  # JSON as TEXT
        # Base model columns
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        # Audit columns
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for solar_designs table
    op.create_index('idx_designs_project', 'solar_designs', ['project_id'])
    op.create_index('idx_designs_status', 'solar_designs', ['status'])
    op.create_index('idx_designs_active', 'solar_designs', ['is_active'])
    op.create_index('idx_designs_version', 'solar_designs', ['version'])
    op.create_index('idx_designs_capacity', 'solar_designs', ['system_capacity_kw'])
    
    # Create solar_components table
    op.create_table(
        'solar_components',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('design_id', sa.String(36), nullable=False),
        sa.Column('component_type', sa.String(length=50), nullable=False),
        sa.Column('manufacturer', sa.String(length=100), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('specifications', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('rated_power_w', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('efficiency', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('dimensions', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('weight_kg', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('unit_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='ZAR'),
        sa.Column('position_data', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('installation_notes', sa.Text(), nullable=True),
        sa.Column('warranty_years', sa.Integer(), nullable=True),
        sa.Column('expected_life_years', sa.Integer(), nullable=True),
        sa.Column('certifications', sa.Text(), nullable=True),  # JSON as TEXT
        # Base model columns
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['design_id'], ['solar_designs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for solar_components table
    op.create_index('idx_components_design', 'solar_components', ['design_id'])
    op.create_index('idx_components_type', 'solar_components', ['component_type'])
    op.create_index('idx_components_manufacturer', 'solar_components', ['manufacturer'])
    op.create_index('idx_components_model', 'solar_components', ['model'])
    
    # Create design_calculations table
    op.create_table(
        'design_calculations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('design_id', sa.String(36), nullable=True),
        sa.Column('calculation_type', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('input_parameters', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('results', sa.Text(), nullable=True),  # JSON as TEXT
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('calculation_version', sa.String(length=50), nullable=True),
        sa.Column('calculation_metadata', sa.Text(), nullable=True),  # JSON as TEXT
        # Base model columns
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['design_id'], ['solar_designs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for design_calculations table
    op.create_index('idx_calculations_project', 'design_calculations', ['project_id'])
    op.create_index('idx_calculations_design', 'design_calculations', ['design_id'])
    op.create_index('idx_calculations_type', 'design_calculations', ['calculation_type'])
    op.create_index('idx_calculations_status', 'design_calculations', ['status'])
    op.create_index('idx_calculations_active', 'design_calculations', ['is_active'])
    op.create_index('idx_calculations_completed', 'design_calculations', ['completed_at'])


def downgrade() -> None:
    """Drop all core tables."""
    
    # Drop tables in reverse order of creation (due to foreign key constraints)
    op.drop_table('design_calculations')
    op.drop_table('solar_components')
    op.drop_table('solar_designs')
    op.drop_table('projects')
    op.drop_table('user_sessions')
    op.drop_table('users')