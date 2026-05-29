"""merge heads

Revision ID: 52c1806d5173
Revises: 005_paiements_table, 32e470cd1068
Create Date: 2026-04-16 12:46:58.879741

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52c1806d5173'
down_revision: Union[str, None] = ('005_paiements_table', '32e470cd1068')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
