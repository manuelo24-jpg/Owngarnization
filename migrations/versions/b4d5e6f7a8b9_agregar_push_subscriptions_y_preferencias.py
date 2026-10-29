"""agregar push_subscriptions y preferencias de usuario

Revision ID: b4d5e6f7a8b9
Revises: a3c4d5e6f7a8
Create Date: 2026-10-29 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4d5e6f7a8b9'
down_revision: Union[str, Sequence[str], None] = 'a3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('timezone', sa.String(length=64), server_default='Europe/Madrid', nullable=False))
    op.add_column('users', sa.Column('reminders_enabled', sa.Boolean(), server_default='1', nullable=False))
    op.add_column('users', sa.Column('reminder_offset_min', sa.Integer(), server_default='10', nullable=False))

    op.add_column('task_occurrences', sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        'push_subscriptions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=False),
        sa.Column('p256dh', sa.String(length=255), nullable=False),
        sa.Column('auth', sa.String(length=255), nullable=False),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('endpoint')
    )
    op.create_index(op.f('ix_push_subscriptions_user_id'), 'push_subscriptions', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_push_subscriptions_user_id'), table_name='push_subscriptions')
    op.drop_table('push_subscriptions')
    op.drop_column('task_occurrences', 'reminder_sent_at')
    op.drop_column('users', 'reminder_offset_min')
    op.drop_column('users', 'reminders_enabled')
    op.drop_column('users', 'timezone')
