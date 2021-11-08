"""empty message

Revision ID: 52434e15a484
Revises: 
Create Date: 2021-11-07 23:38:24.245190

"""
from alembic import op
import sqlalchemy as sa


revision = '52434e15a484'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('colors',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('rgb', sa.String(length=6), nullable=False),
    sa.Column('type', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=512), nullable=False),
    sa.Column('password_hash', sa.String(length=128), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('inventory_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_user', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['id_user'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_user', sa.Integer(), nullable=False),
    sa.Column('buyer_name', sa.String(), nullable=False),
    sa.Column('buyer_email', sa.String(length=512), nullable=False),
    sa.Column('date_ordered', sa.DateTime(), nullable=False),
    sa.Column('status', sa.Enum('UNKNOWN', 'PENDING', 'PAID', 'PROCESSING', 'PROCESSED', 'SHIPPED', 'RECEIVED', name='orderstatus'), nullable=False),
    sa.Column('shipping_method', sa.String(), nullable=True),
    sa.Column('shipping_address_first_name', sa.String(), nullable=True),
    sa.Column('shipping_address_last_name', sa.String(), nullable=True),
    sa.Column('shipping_address_address_1', sa.String(), nullable=True),
    sa.Column('shipping_address_address_2', sa.String(), nullable=True),
    sa.Column('shipping_address_country_code', sa.String(), nullable=True),
    sa.Column('shipping_address_city', sa.String(), nullable=True),
    sa.Column('shipping_address_state', sa.String(), nullable=True),
    sa.Column('shipping_address_postal_code', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['id_user'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id_user', 'buyer_name', 'buyer_email', 'date_ordered')
    )
    op.create_table('parts',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('id_category', sa.Integer(), nullable=True),
    sa.Column('img_url', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['id_category'], ['categories.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sets',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('id_category', sa.Integer(), nullable=True),
    sa.Column('img_url', sa.String(), nullable=True),
    sa.Column('year', sa.Integer(), nullable=True),
    sa.Column('num_parts', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['id_category'], ['categories.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('applied_orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id'], ['inventory_history.id'], ),
    sa.ForeignKeyConstraint(['id_order'], ['orders.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('order_parts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_order', sa.Integer(), nullable=False),
    sa.Column('id_part', sa.String(), nullable=False),
    sa.Column('id_color', sa.Integer(), nullable=False),
    sa.Column('condition', sa.String(length=1), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('user_remarks', sa.String(), nullable=True),
    sa.Column('user_description', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['id_color'], ['colors.id'], ),
    sa.ForeignKeyConstraint(['id_order'], ['orders.id'], ),
    sa.ForeignKeyConstraint(['id_part'], ['parts.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id_order', 'id_part', 'id_color', 'condition', 'quantity', 'user_remarks', 'user_description')
    )
    op.create_table('parted_out_sets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_set', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['id'], ['inventory_history.id'], ),
    sa.ForeignKeyConstraint(['id_set'], ['sets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('inventory_parts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_part', sa.String(), nullable=False),
    sa.Column('id_color', sa.Integer(), nullable=False),
    sa.Column('condition', sa.String(length=1), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('id_parted_out_set', sa.Integer(), nullable=True),
    sa.Column('id_user', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id_color'], ['colors.id'], ),
    sa.ForeignKeyConstraint(['id_part'], ['parts.id'], ),
    sa.ForeignKeyConstraint(['id_parted_out_set'], ['parted_out_sets.id'], ),
    sa.ForeignKeyConstraint(['id_user'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id_part', 'id_color', 'condition', 'id_parted_out_set', 'id_user')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('inventory_parts')
    op.drop_table('parted_out_sets')
    op.drop_table('order_parts')
    op.drop_table('applied_orders')
    op.drop_table('sets')
    op.drop_table('parts')
    op.drop_table('orders')
    op.drop_table('inventory_history')
    op.drop_table('users')
    op.drop_table('colors')
    op.drop_table('categories')
    # ### end Alembic commands ###