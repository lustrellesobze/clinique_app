"""motif_consultation VARCHAR(2000) — compatibilité MariaDB / WAMP (TEXT + DEFAULT problématique)

Revision ID: 004_passages_motif_varchar
Revises: 003_passages_accueil
Create Date: 2026-04-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_passages_motif_varchar"
down_revision: Union[str, None] = "003_passages_accueil"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return
    op.alter_column(
        "passages_accueil",
        "motif_consultation",
        existing_type=sa.Text(),
        type_=sa.String(length=2000),
        existing_nullable=False,
        nullable=False,
        server_default=sa.text("''"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return
    op.alter_column(
        "passages_accueil",
        "motif_consultation",
        existing_type=sa.String(length=2000),
        type_=sa.Text(),
        existing_nullable=False,
        nullable=False,
        server_default=sa.text("''"),
    )
