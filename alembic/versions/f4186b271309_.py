"""empty message

Revision ID: f4186b271309
Revises: e18922cacbd1
Create Date: 2021-11-29 13:26:43.560129

"""
from alembic import op
import sqlalchemy as sa


revision = 'f4186b271309'
down_revision = 'e18922cacbd1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('inventory_items', sa.Column('image_pulled', sa.Integer(), nullable=True))
    op.drop_column('items', 'image_pulled')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('items', sa.Column('image_pulled', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_column('inventory_items', 'image_pulled')
    # ### end Alembic commands ###
