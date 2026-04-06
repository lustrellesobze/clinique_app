"""passages_accueil — carnet électronique accueil

Revision ID: 003_passages_accueil
Revises: 002_patients_factures
Create Date: 2026-04-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_passages_accueil"
down_revision: Union[str, None] = "002_patients_factures"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "passages_accueil",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("enregistre_par_id", sa.String(length=36), nullable=False),
        sa.Column("medecin_id", sa.String(length=36), nullable=True),
        sa.Column("poids_kg", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("taille_cm", sa.Numeric(precision=5, scale=1), nullable=True),
        sa.Column("temperature_c", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("tension", sa.String(length=30), nullable=True),
        sa.Column(
            "motif_consultation",
            sa.Text(),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column(
            "type_consultation",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'generale'"),
        ),
        sa.Column("derniere_date_regles", sa.Date(), nullable=True),
        sa.Column(
            "est_assure",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("compagnie_assurance", sa.String(length=150), nullable=True),
        sa.Column("date_validite_assurance", sa.Date(), nullable=True),
        sa.Column("numero_assure", sa.String(length=80), nullable=True),
        sa.Column(
            "montant_consultation_fcfa",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="5000",
        ),
        sa.Column(
            "remise_fcfa",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "statut",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'enregistre'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["enregistre_par_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["medecin_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        op.f("ix_passages_accueil_patient_id"),
        "passages_accueil",
        ["patient_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_passages_accueil_patient_id"), table_name="passages_accueil")
    op.drop_table("passages_accueil")
