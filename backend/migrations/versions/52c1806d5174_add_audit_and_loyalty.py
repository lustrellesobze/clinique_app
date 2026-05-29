"""Add audit_logs and loyalty_points tables

Revision ID: 52c1806d5174
Revises: 52c1806d5173
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "52c1806d5174"
down_revision = "52c1806d5173"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("action", sa.String(length=80), nullable=False, index=True),
        sa.Column("entity_type", sa.String(length=80), nullable=True, index=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, index=True),
    )

    op.create_table(
        "loyalty_points",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("patient_id", sa.String(length=36), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("points_balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("points_earned_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("patient_id", name="uq_loyalty_points_patient_id"),
    )
    op.create_index("ix_loyalty_points_patient_id", "loyalty_points", ["patient_id"])


def downgrade() -> None:
    op.drop_index("ix_loyalty_points_patient_id", table_name="loyalty_points")
    op.drop_table("loyalty_points")
    op.drop_table("audit_logs")

