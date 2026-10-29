"""agregar manual_order a occurrences

Revision ID: a3c4d5e6f7a8
Revises: 919838a2c48d
Create Date: 2026-10-29 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = '919838a2c48d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('task_occurrences', sa.Column('manual_order', sa.Boolean(), server_default='0', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('task_occurrences', 'manual_order')
