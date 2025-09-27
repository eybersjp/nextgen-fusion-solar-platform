"""Create 3D design models tables

Revision ID: create_3d_design_models
Revises: create_core_tables
Create Date: 2025-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'create_3d_design_models'
down_revision = 'create_core_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create 3D design models tables."""
    
    # Create design_3d_models table
    op.create_table(
        'design_3d_models',
        sa.Column('id', sa.String(36), primary_key=True, default=sa.text('(lower(hex(randomblob(4))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(6))))')),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('building_geometry', sa.Text, nullable=False),  # JSON as TEXT in SQLite
        sa.Column('panel_layout', sa.Text, nullable=False, default='[]'),  # JSON as TEXT
        sa.Column('simulation_parameters', sa.Text, default='{}'),  # JSON as TEXT
        sa.Column('total_capacity', sa.DECIMAL(10, 2)),
        sa.Column('estimated_output', sa.DECIMAL(12, 2)),
        sa.Column('validation_status', sa.String(50), default='pending'),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp())
    )
    
    # Create indexes for design_3d_models
    op.create_index('idx_design_3d_models_project_id', 'design_3d_models', ['project_id'])
    op.create_index('idx_design_3d_models_status', 'design_3d_models', ['validation_status'])
    op.create_index('idx_design_3d_models_created_at', 'design_3d_models', ['created_at'])
    
    # Create solar_panels table
    op.create_table(
        'solar_panels',
        sa.Column('id', sa.String(36), primary_key=True, default=sa.text('(lower(hex(randomblob(4))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(6))))')),
        sa.Column('design_id', sa.String(36), sa.ForeignKey('design_3d_models.id', ondelete='CASCADE'), nullable=False),
        sa.Column('panel_type', sa.String(100), nullable=False),
        sa.Column('power_rating', sa.DECIMAL(8, 2), nullable=False),
        sa.Column('position_coordinates', sa.Text, nullable=False),  # JSON as TEXT
        sa.Column('rotation_angles', sa.Text, nullable=False),  # JSON as TEXT
        sa.Column('mounting_type', sa.String(50), default='roof_mounted'),
        sa.Column('efficiency', sa.DECIMAL(5, 2)),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp())
    )
    
    # Create indexes for solar_panels
    op.create_index('idx_solar_panels_design_id', 'solar_panels', ['design_id'])
    op.create_index('idx_solar_panels_type', 'solar_panels', ['panel_type'])
    
    # Create panel_specifications table
    op.create_table(
        'panel_specifications',
        sa.Column('id', sa.String(36), primary_key=True, default=sa.text('(lower(hex(randomblob(4))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(6))))')),
        sa.Column('manufacturer', sa.String(100), nullable=False),
        sa.Column('model_number', sa.String(100), nullable=False),
        sa.Column('power_rating', sa.DECIMAL(8, 2), nullable=False),
        sa.Column('efficiency', sa.DECIMAL(5, 2), nullable=False),
        sa.Column('dimensions', sa.Text, nullable=False),  # JSON as TEXT
        sa.Column('technology_type', sa.String(50), nullable=False),
        sa.Column('temperature_coefficient', sa.DECIMAL(6, 4)),
        sa.Column('warranty_years', sa.Integer, default=25),
        sa.Column('certification_standards', sa.Text, default='[]'),  # JSON as TEXT
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp())
    )
    
    # Create unique constraint for panel_specifications
    op.create_index('idx_panel_specs_unique', 'panel_specifications', ['manufacturer', 'model_number'], unique=True)
    
    # Create irradiance_calculations table
    op.create_table(
        'irradiance_calculations',
        sa.Column('id', sa.String(36), primary_key=True, default=sa.text('(lower(hex(randomblob(4))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(6))))')),
        sa.Column('design_id', sa.String(36), sa.ForeignKey('design_3d_models.id', ondelete='CASCADE'), nullable=False),
        sa.Column('annual_irradiance', sa.DECIMAL(8, 2)),
        sa.Column('monthly_data', sa.Text),  # JSON as TEXT
        sa.Column('shading_analysis', sa.Text),  # JSON as TEXT
        sa.Column('performance_ratio', sa.DECIMAL(5, 2)),
        sa.Column('calculation_method', sa.String(50), default='pvlib'),
        sa.Column('weather_data_source', sa.String(100)),
        sa.Column('calculated_at', sa.DateTime, default=sa.func.current_timestamp())
    )
    
    # Create indexes for irradiance_calculations
    op.create_index('idx_irradiance_calculations_design_id', 'irradiance_calculations', ['design_id'])
    op.create_index('idx_irradiance_calculations_calculated_at', 'irradiance_calculations', ['calculated_at'])


def downgrade() -> None:
    """Drop 3D design models tables."""
    op.drop_table('irradiance_calculations')
    op.drop_table('panel_specifications')
    op.drop_table('solar_panels')
    op.drop_table('design_3d_models')