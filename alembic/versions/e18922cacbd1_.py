"""empty message

Revision ID: e18922cacbd1
Revises: 42fb82a7cbc4
Create Date: 2021-11-29 13:24:02.883516

"""
from alembic import op
import sqlalchemy as sa


revision = 'e18922cacbd1'
down_revision = '42fb82a7cbc4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('inventory_items', 'user_remarks',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('inventory_items', 'user_description',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.add_column('items', sa.Column('image_pulled', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('items', 'image_pulled')
    op.alter_column('inventory_items', 'user_description',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('inventory_items', 'user_remarks',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###
