"""Create project management tables

Revision ID: create_project_management
Revises: create_3d_design_models
Create Date: 2025-01-27 10:01:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'create_project_management'
down_revision = 'create_3d_design_models'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create project management tables."""
    
    # Create project_tasks table
    op.create_table(
        'project_tasks',
        sa.Column('id', sa.String(36), primary_key=True, default=sa.text('(lower(hex(randomblob(4))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(6))))')),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=False),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('priority', sa.String(20), default='medium'),
        sa.Column('assigned_to', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('estimated_hours', sa.DECIMAL(8, 2), default=0),
        sa.Column('actual_hours', sa.DECIMAL(8, 2), default=0),
        sa.Column('completion_percentage', sa.DECIMAL(5, 2), default=0),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp())
    )
    
    # Create indexes for project_tasks
    op.create_index('idx_project_tasks_project_id', 'project_tasks', ['project_id'])
    op.create_index('idx_project_tasks_assigned_to', 'project_tasks', ['assigned_to'])
    op.create_index('idx_project_tasks_status', 'project_tasks', ['status'])
    op.create_index('idx_project_tasks_dates', 'project_tasks', ['start_date', 'end_date'])
    
    # Create task_dependencies table
    op.create_table(
        'task_dependencies',
        sa.Column('id', sa.String(36), primary_key=True, default=sa.text('(lower(hex(randomblob(4))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(6))))')),
        sa.Column('task_id', sa.String(36), sa.ForeignKey('project_tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('depends_on_task_id', sa.String(36), sa.ForeignKey('project_tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dependency_type', sa.String(50), default='finish_to_start'),
        sa.Column('lag_days', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp())
    )
    
    # Create unique constraint and indexes for task_dependencies
    op.create_index('idx_task_dependencies_unique', 'task_dependencies', ['task_id', 'depends_on_task_id'], unique=True)
    op.create_index('idx_task_dependencies_task_id', 'task_dependencies', ['task_id'])
    op.create_index('idx_task_dependencies_depends_on', 'task_dependencies', ['depends_on_task_id'])
    
    # Create project_milestones table
    op.create_table(
        'project_milestones',
        sa.Column('id', sa.String(36), primary_key=True, default=sa.text('(lower(hex(randomblob(4))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(2))) || "-" || lower(hex(randomblob(6))))')),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('target_date', sa.Date, nullable=False),
        sa.Column('completion_date', sa.Date),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('progress_percentage', sa.DECIMAL(5, 2), default=0),
        sa.Column('milestone_type', sa.String(50), default='project'),
        sa.Column('created_at', sa.DateTime, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.current_timestamp())
    )
    
    # Create indexes for project_milestones
    op.create_index('idx_project_milestones_project_id', 'project_milestones', ['project_id'])
    op.create_index('idx_project_milestones_target_date', 'project_milestones', ['target_date'])
    op.create_index('idx_project_milestones_status', 'project_milestones', ['status'])


def downgrade() -> None:
    """Drop project management tables."""
    op.drop_table('project_milestones')
    op.drop_table('task_dependencies')
    op.drop_table('project_tasks')