"""empty message

Revision ID: 1e2360a68156
Revises: 
Create Date: 2021-11-28 19:58:19.182706

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '1e2360a68156'
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
    sa.Column('bo_id', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=512), nullable=False),
    sa.Column('password_hash', sa.String(length=128), nullable=False),
    sa.Column('bl_customer_key', sa.String(), nullable=True),
    sa.Column('bl_customer_secret', sa.String(), nullable=True),
    sa.Column('bl_token_value', sa.String(), nullable=True),
    sa.Column('bl_token_secret', sa.String(), nullable=True),
    sa.Column('bo_key', sa.String(), nullable=True),
    sa.Column('inventory_initialization_group_id', sa.Integer(), nullable=True),
    sa.Column('syncer_group_id', sa.Integer(), nullable=True),
    sa.Column('is_syncer_enabled', sa.Boolean(), nullable=True),
    sa.Column('is_inventory_initialized', sa.Boolean(), nullable=True),
    sa.Column('is_inventory_initializing', sa.Boolean(), nullable=True),
    sa.Column('is_syncer_running', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('items',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('type', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('id_category', sa.Integer(), nullable=True),
    sa.Column('bo_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['id_category'], ['categories.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', 'type')
    )
    op.create_table('op',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_user', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=64), nullable=False),
    sa.Column('id_parent', sa.Integer(), nullable=True),
    sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('id_group', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('invoked_at', sa.DateTime(), nullable=True),
    sa.Column('processed_at', sa.DateTime(), nullable=True),
    sa.Column('rate_limited_at', sa.DateTime(), nullable=True),
    sa.Column('rate_limited_for', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['id_group'], ['op.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['id_parent'], ['op.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['id_user'], ['users.id'], ondelete='CASCADE'),
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
    sa.Column('id_bl', sa.Integer(), nullable=True),
    sa.Column('id_bo', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['id_user'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id_user', 'buyer_name', 'buyer_email', 'date_ordered')
    )
    op.create_table('inventory_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.String(), nullable=False),
    sa.Column('item_type', sa.String(), nullable=False),
    sa.Column('color_id', sa.Integer(), nullable=False),
    sa.Column('condition', sa.String(length=1), nullable=False),
    sa.Column('unit_price', sa.Float(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('user_remarks', sa.String(), nullable=True),
    sa.Column('user_description', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['color_id'], ['colors.id'], ),
    sa.ForeignKeyConstraint(['item_id', 'item_type'], ['items.id', 'items.type'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'item_id', 'item_type', 'color_id', 'condition', 'user_remarks')
    )
    op.create_table('op_dependencies',
    sa.Column('id_op', sa.Integer(), nullable=False),
    sa.Column('id_dependency', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id_dependency'], ['op.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['id_op'], ['op.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id_op', 'id_dependency')
    )
    op.create_table('op_view',
    sa.Column('id_group', sa.Integer(), nullable=False),
    sa.Column('when', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('op_count', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id_group'], ['op.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id_group', 'when')
    )
    op.create_table('order_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_order', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.String(), nullable=False),
    sa.Column('item_type', sa.String(), nullable=False),
    sa.Column('id_color', sa.Integer(), nullable=False),
    sa.Column('condition', sa.String(length=1), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('user_remarks', sa.String(), nullable=True),
    sa.Column('user_description', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['id_color'], ['colors.id'], ),
    sa.ForeignKeyConstraint(['id_order'], ['orders.id'], ),
    sa.ForeignKeyConstraint(['item_id', 'item_type'], ['items.id', 'items.type'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id_order', 'item_id', 'item_type', 'id_color', 'condition', 'quantity', 'user_remarks', 'user_description')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('order_items')
    op.drop_table('op_view')
    op.drop_table('op_dependencies')
    op.drop_table('inventory_items')
    op.drop_table('orders')
    op.drop_table('op')
    op.drop_table('items')
    op.drop_table('users')
    op.drop_table('colors')
    op.drop_table('categories')
    # ### end Alembic commands ###
