"""indices de escalabilidad en tasks y occurrences

Revision ID: c5e6f7a8b9c0
Revises: b4d5e6f7a8b9
Create Date: 2026-10-30 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5e6f7a8b9c0'
down_revision: Union[str, Sequence[str], None] = 'b4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        'ix_tasks_user_active_kind',
        'tasks',
        ['user_id', 'is_active', 'kind'],
        unique=False
    )
    op.create_index(
        'ix_occurrences_date_status',
        'task_occurrences',
        ['date', 'status'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_occurrences_date_status', table_name='task_occurrences')
    op.drop_index('ix_tasks_user_active_kind', table_name='tasks')
