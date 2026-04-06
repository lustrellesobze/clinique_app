"""patients, factures, lignes_facture

Revision ID: 002_patients_factures
Revises: 001_create_users
Create Date: 2026-04-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_patients_factures"
down_revision: Union[str, None] = "001_create_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code_patient", sa.String(length=32), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("prenom", sa.String(length=100), nullable=False),
        sa.Column("date_naissance", sa.Date(), nullable=True),
        sa.Column("sexe", sa.String(length=10), nullable=True),
        sa.Column("telephone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=150), nullable=True),
        sa.Column("contact_urgence", sa.String(length=255), nullable=True),
        sa.Column("medecin_id", sa.String(length=36), nullable=True),
        sa.Column("assureur", sa.String(length=150), nullable=True),
        sa.Column("numero_police_assurance", sa.String(length=80), nullable=True),
        sa.Column(
            "est_actif",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
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
            ["medecin_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        op.f("ix_patients_code_patient"), "patients", ["code_patient"], unique=True
    )

    op.create_table(
        "factures",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("numero_facture", sa.String(length=40), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("caissier_id", sa.String(length=36), nullable=True),
        sa.Column(
            "statut",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'brouillon'"),
        ),
        sa.Column(
            "montant_total",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "montant_regle",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "remise_globale",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("part_assurance", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("part_patient", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "devise",
            sa.String(length=3),
            nullable=False,
            server_default=sa.text("'XAF'"),
        ),
        sa.Column(
            "est_annulee",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("commentaire", sa.Text(), nullable=True),
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
            ["patient_id"],
            ["patients.id"],
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
    op.create_index(
        op.f("ix_factures_numero_facture"),
        "factures",
        ["numero_facture"],
        unique=True,
    )

    op.create_table(
        "lignes_facture",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("facture_id", sa.String(length=36), nullable=False),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("designation", sa.String(length=255), nullable=False),
        sa.Column(
            "quantite",
            sa.Numeric(precision=10, scale=3),
            nullable=False,
            server_default="1",
        ),
        sa.Column("prix_unitaire", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "remise_montant",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("montant_ligne", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["facture_id"],
            ["factures.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )


def downgrade() -> None:
    op.drop_table("lignes_facture")
    op.drop_index(op.f("ix_factures_numero_facture"), table_name="factures")
    op.drop_table("factures")
    op.drop_index(op.f("ix_patients_code_patient"), table_name="patients")
    op.drop_table("patients")
