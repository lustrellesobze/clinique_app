"""add_assurance_id_to_patients

Revision ID: 32e470cd1068
Revises: c4a3f67e0695
Create Date: 2026-04-06 10:13:37.193825

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32e470cd1068'
down_revision: Union[str, None] = 'c4a3f67e0695'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ajouter la colonne assurance_id à la table patients
    op.add_column('patients', sa.Column('assurance_id', sa.String(36), nullable=True))
    # Créer un index sur la colonne
    op.create_index('ix_patients_assurance_id', 'patients', ['assurance_id'])
    # Ajouter la foreign key
    op.create_foreign_key(
        'fk_patients_assurance_id',
        'patients',
        'insurances',
        ['assurance_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Supprimer la foreign key, l'index et la colonne
    op.drop_constraint('fk_patients_assurance_id', 'patients', type_='foreignkey')
    op.drop_index('ix_patients_assurance_id', 'patients')
    op.drop_column('patients', 'assurance_id')
