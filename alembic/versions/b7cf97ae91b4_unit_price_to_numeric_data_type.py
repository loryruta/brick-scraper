"""unit_price to Numeric data type

Revision ID: b7cf97ae91b4
Revises: ef9107e3afae
Create Date: 2023-01-23 14:11:06.111809

"""
from alembic import op
import sqlalchemy as sa


revision = 'b7cf97ae91b4'
down_revision = 'ef9107e3afae'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('inventory_items', 'unit_price',
        type_=sa.Numeric,
        existing_type=sa.Float,
        nullable=True)


def downgrade():
    op.alter_column('inventory_items', 'unit_price',
        type_=sa.Float,
        existing_type=sa.Numeric,
        nullable=True)

