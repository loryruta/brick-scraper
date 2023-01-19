"""unit_price nullable in InventoryItem

Revision ID: 3d66a171f46a
Revises: 9aa7762bb8c3
Create Date: 2023-01-19 18:38:02.350825

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '3d66a171f46a'
down_revision = '9aa7762bb8c3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('inventory_items', 'unit_price',
               existing_type=postgresql.DOUBLE_PRECISION(precision=53),
               nullable=True)


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('inventory_items', 'unit_price',
               existing_type=postgresql.DOUBLE_PRECISION(precision=53),
               nullable=False)
    # ### end Alembic commands ###