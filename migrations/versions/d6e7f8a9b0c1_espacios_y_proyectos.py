"""espacios y proyectos: tablas y columnas

Revision ID: d6e7f8a9b0c1
Revises: c5e6f7a8b9c0
Create Date: 2026-11-04 14:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6e7f8a9b0c1'
down_revision: Union[str, Sequence[str], None] = 'c5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Ampliación de tabla users
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_space', sa.String(length=20), server_default='personal', nullable=True))
        batch_op.add_column(sa.Column('last_project_id', sa.Integer(), nullable=True))

    # 2. Tabla projects
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('icon', sa.String(length=20), nullable=True),
        sa.Column('is_archived', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_projects_id', 'projects', ['id'])
    op.create_index('ix_projects_owner_id', 'projects', ['owner_id'])

    # 3. Tabla project_roles
    op.create_table(
        'project_roles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('color', sa.String(length=20), server_default='#C9B49A', nullable=False),
        sa.Column('position', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('project_id', 'name', name='uq_project_role_project_name'),
    )
    op.create_index('ix_project_roles_id', 'project_roles', ['id'])
    op.create_index('ix_project_roles_project_id', 'project_roles', ['project_id'])

    # 4. Tabla project_members
    op.create_table(
        'project_members',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('permission', sa.String(length=20), server_default='member', nullable=False),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('project_roles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('weekly_hours', sa.Integer(), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('project_id', 'user_id', name='uq_project_member_project_user'),
    )
    op.create_index('ix_project_members_id', 'project_members', ['id'])
    op.create_index('ix_project_members_project_id', 'project_members', ['project_id'])
    op.create_index('ix_project_members_user_id', 'project_members', ['user_id'])
    op.create_index('ix_project_members_role_id', 'project_members', ['role_id'])

    # 5. Tabla project_columns
    op.create_table(
        'project_columns',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('position', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_done', sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index('ix_project_columns_id', 'project_columns', ['id'])
    op.create_index('ix_project_columns_project_id', 'project_columns', ['project_id'])
    op.create_index('ix_project_columns_project_pos', 'project_columns', ['project_id', 'position'])

    # 6. Tabla project_tasks
    op.create_table(
        'project_tasks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('column_id', sa.Integer(), sa.ForeignKey('project_columns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(length=20), server_default='medium', nullable=False),
        sa.Column('position', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('start_time', sa.Time(), nullable=True),
        sa.Column('end_time', sa.Time(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('estimated_minutes', sa.Integer(), nullable=True),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('project_roles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_project_tasks_id', 'project_tasks', ['id'])
    op.create_index('ix_project_tasks_project_id', 'project_tasks', ['project_id'])
    op.create_index('ix_project_tasks_column_id', 'project_tasks', ['column_id'])
    op.create_index('ix_project_tasks_date', 'project_tasks', ['date'])
    op.create_index('ix_project_tasks_pos', 'project_tasks', ['project_id', 'column_id', 'position'])
    op.create_index('ix_project_tasks_sched', 'project_tasks', ['project_id', 'date', 'start_time'])

    # 7. Tabla project_task_assignees (N:M)
    op.create_table(
        'project_task_assignees',
        sa.Column('task_id', sa.Integer(), sa.ForeignKey('project_tasks.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('project_task_assignees')
    op.drop_table('project_tasks')
    op.drop_table('project_columns')
    op.drop_table('project_members')
    op.drop_table('project_roles')
    op.drop_table('projects')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('last_project_id')
        batch_op.drop_column('last_space')

