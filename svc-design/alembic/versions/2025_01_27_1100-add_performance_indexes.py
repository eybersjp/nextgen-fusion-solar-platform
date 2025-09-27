"""Add performance indexes for frequently queried columns

Revision ID: add_performance_indexes
Revises: create_project_management
Create Date: 2025-01-27 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_performance_indexes'
down_revision = 'create_currency_compliance'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes for frequently queried columns."""
    
    # Designs table indexes
    try:
        op.create_index(
            'idx_designs_project_org',
            'designs',
            ['project_id', 'organization_id'],
            unique=False
        )
    except Exception:
        # Index might already exist
        pass
    
    try:
        op.create_index(
            'idx_designs_status_stage',
            'designs',
            ['approval_status', 'design_stage'],
            unique=False
        )
    except Exception:
        pass
    
    try:
        op.create_index(
            'idx_designs_current_version',
            'designs',
            ['is_current_version', 'created_at'],
            unique=False
        )
    except Exception:
        pass
    
    try:
        op.create_index(
            'idx_designs_client_lookup',
            'designs',
            ['client_email', 'client_company'],
            unique=False
        )
    except Exception:
        pass
    
    # Skip location index for now - columns may not exist in current schema
    # op.create_index(
    #     'idx_designs_location',
    #     'designs',
    #     ['site_latitude', 'site_longitude'],
    #     unique=False
    # )
    
    # Layouts table indexes
    try:
        op.create_index(
            'idx_layouts_design_status',
            'layouts',
            ['design_id', 'status'],
            unique=False
        )
    except Exception:
        pass
    
    try:
        op.create_index(
            'idx_layouts_optimization',
            'layouts',
            ['optimization_objective', 'optimization_status'],
            unique=False
        )
    except Exception:
        pass
    
    try:
        op.create_index(
            'idx_layouts_performance',
            'layouts',
            ['total_capacity_kw', 'performance_ratio'],
            unique=False
        )
    except Exception:
        pass
    
    # Panel arrays table indexes
    try:
        op.create_index(
            'idx_panel_arrays_layout',
            'panel_arrays',
            ['layout_id', 'array_name'],
            unique=False
        )
    except Exception:
        pass
    
    try:
        op.create_index(
            'idx_panel_arrays_config',
            'panel_arrays',
            ['module_type', 'orientation'],
            unique=False
        )
    except Exception:
        pass
    
    # Skip solar designs indexes for now - table structure may vary
    # Solar designs table indexes (if exists)
    # try:
    #     op.create_index(
    #         'idx_solar_designs_project_status',
    #         'solar_designs',
    #         ['project_id', 'status'],
    #         unique=False
    #     )
    # except Exception:
    #     pass
    
    # Design versions table indexes (if exists)
    try:
        op.create_index(
            'idx_design_versions_design_created',
            'design_versions',
            ['design_id', 'created_at'],
            unique=False
        )
    except Exception:
        pass
    
    # Design approvals table indexes (if exists)
    try:
        op.create_index(
            'idx_design_approvals_design_status',
            'design_approvals',
            ['design_id', 'approval_status'],
            unique=False
        )
        
        op.create_index(
            'idx_design_approvals_user_date',
            'design_approvals',
            ['approved_by', 'approved_at'],
            unique=False
        )
    except Exception:
        pass
    
    # Design comments table indexes (if exists)
    try:
        op.create_index(
            'idx_design_comments_design_created',
            'design_comments',
            ['design_id', 'created_at'],
            unique=False
        )
    except Exception:
        pass
    
    # Users table indexes for authentication
    try:
        op.create_index(
            'idx_users_email_active',
            'users',
            ['email', 'is_active'],
            unique=False
        )
        
        op.create_index(
            'idx_users_org_role',
            'users',
            ['organization_id', 'role'],
            unique=False
        )
    except Exception:
        pass
    
    # Projects table indexes
    try:
        op.create_index(
            'idx_projects_org_status',
            'projects',
            ['organization_id', 'status'],
            unique=False
        )
        
        op.create_index(
            'idx_projects_created_updated',
            'projects',
            ['created_at', 'updated_at'],
            unique=False
        )
    except Exception:
        pass


def downgrade():
    """Remove performance indexes."""
    
    # Drop indexes in reverse order
    indexes_to_drop = [
        'idx_projects_created_updated',
        'idx_projects_org_status',
        'idx_users_org_role',
        'idx_users_email_active',
        'idx_design_comments_design_created',
        'idx_design_approvals_user_date',
        'idx_design_approvals_design_status',
        'idx_design_versions_design_created',
        'idx_solar_designs_performance',
        'idx_solar_designs_capacity',
        'idx_solar_designs_active_version',
        'idx_solar_designs_project_status',
        'idx_panel_arrays_layout',
        'idx_layouts_validation',
        'idx_layouts_capacity',
        'idx_layouts_optimization',
        'idx_layouts_design_type',
        'idx_designs_location',
        'idx_designs_client_lookup',
        'idx_designs_current_version',
        'idx_designs_status_stage',
        'idx_designs_project_org'
    ]
    
    for index_name in indexes_to_drop:
        try:
            op.drop_index(index_name)
        except Exception:
            # Index might not exist
            pass