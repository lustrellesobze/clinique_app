"""create paiements table

Revision ID: 005_paiements_table
Revises: 004_passages_motif_varchar
Create Date: 2026-04-06

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_paiements_table"
down_revision: Union[str, None] = "004_passages_motif_varchar"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "paiements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("facture_id", sa.String(length=36), nullable=False),
        sa.Column("caissier_id", sa.String(length=36), nullable=True),
        sa.Column("montant", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("mode_paiement", sa.String(length=20), nullable=False),
        sa.Column(
            "statut",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'confirme'"),
        ),
        sa.Column("reference_transaction", sa.String(length=120), nullable=True),
        sa.Column("commentaire", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["facture_id"],
            ["factures.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["caissier_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )


def downgrade() -> None:
    op.drop_table("paiements")
