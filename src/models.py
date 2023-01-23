from typing import List
import sqlalchemy as sa
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import func
from enum import Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.expression import func
import os


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = sa.Column(sa.Integer, primary_key=True)
    email = sa.Column(sa.String(512), unique=True, nullable=False)
    password_hash = sa.Column(sa.String(128), nullable=False)

    bl_customer_key = sa.Column(sa.String)
    bl_customer_secret = sa.Column(sa.String)
    bl_token_value = sa.Column(sa.String)
    bl_token_secret = sa.Column(sa.String)
    bl_credentials_approved = sa.Column(sa.Boolean)

    bo_key = sa.Column(sa.String)
    bo_credentials_approved = sa.Column(sa.Boolean)

    inventory_initialization_group_id = sa.Column(sa.Integer)
    syncer_group_id = sa.Column(sa.Integer)

    is_syncer_enabled = sa.Column(sa.Boolean)
    is_inventory_initialized = sa.Column(sa.Boolean)
    is_inventory_initializing = sa.Column(sa.Boolean)
    is_syncer_running = sa.Column(sa.Boolean)

    orders = relationship('Order')


    def is_super_admin(self):
        return \
            self.email == os.environ['SUPER_ADMIN_USER_EMAIL']


    @staticmethod
    def get_super_admin(session):
        return session.query(User) \
            .filter(User.email == os.environ['SUPER_ADMIN_USER_EMAIL'],) \
            .first()


    def has_bl_credentials(self):
        return \
            self.bl_customer_key != None and \
            self.bl_customer_secret != None and \
            self.bl_token_value != None and \
            self.bl_token_secret and \
            self.bl_credentials_approved


    def has_bo_credentials(self):
        return \
            self.bo_key != None and \
            self.bo_credentials_approved


op_dependencies_table = sa.Table('op_dependencies', Base.metadata,
    sa.Column('id_op', sa.Integer, sa.ForeignKey('op.id', ondelete='CASCADE')),
    sa.Column('id_dependency', sa.Integer, sa.ForeignKey('op.id', ondelete='CASCADE')),
    sa.PrimaryKeyConstraint('id_op', 'id_dependency')
)


class Op(Base):
    __tablename__ = 'op'

    id = sa.Column(sa.Integer, primary_key=True)
    id_user = sa.Column(sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    type = sa.Column(sa.String(64), nullable=False)
    id_parent = sa.Column(sa.Integer, sa.ForeignKey('op.id', ondelete='CASCADE'))
    params = sa.Column(JSONB, nullable=False)

    # The group operation of which this operation has been originated.
    # This ID must always refer to an anchestor of the current operation (and could be avoided implementing a recursive anchestor traverse).
    id_group = sa.Column(sa.Integer, sa.ForeignKey('op.id', ondelete='CASCADE'))

    # When the operation has been enqueued.
    created_at = sa.Column(
        sa.DateTime,
        nullable=False,
        server_default=func.now()
    )

    # When the operation has been invoked, same thing for processed for non-parent operations.
    # For parent operations, this field must be set before invoking children operations. 
    invoked_at = sa.Column(sa.DateTime)

    # When the operation has been fully processed, meaning it can eventually be deleted from the queued.
    processed_at = sa.Column(sa.DateTime)

    rate_limited_at = sa.Column(sa.DateTime)    # When the operation was rate limited.
    rate_limited_for = sa.Column(sa.BigInteger) # The amount of seconds for which the operation has been rate limited.

    user = relationship('User')
    parent = relationship('Op', foreign_keys=[id_parent], remote_side=[id])
    group = relationship('Op', foreign_keys=[id_group], remote_side=[id])
    dependencies = relationship('Op',
        secondary=op_dependencies_table,
        primaryjoin= id == op_dependencies_table.c.id_op,
        secondaryjoin= id == op_dependencies_table.c.id_dependency,
    )


class OpView(Base):
    __tablename__ = 'op_view'

    id_group = sa.Column(sa.Integer, sa.ForeignKey('op.id', ondelete='CASCADE'))
    when = sa.Column(sa.DateTime, server_default=func.now())
    op_count = sa.Column(sa.Integer, nullable=False)

    #group = relationship('Op', foreign_keys=[id_group], remote_side=['id'], viewonly=True)

    __table_args__ = (
        sa.PrimaryKeyConstraint('id_group', 'when'),  # id_user isn't necessair
    )


class Color(Base):
    __tablename__ = 'colors'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    rgb = sa.Column(sa.String(6), nullable=False)
    type = sa.Column(sa.String(64), nullable=False)

    bo_id = sa.Column(sa.Integer)


class Category(Base):
    __tablename__ = 'categories'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String, nullable=False)


class ItemPrice(Base):
    __tablename__ = 'item_prices'

    item_id = sa.Column(sa.String)
    item_type = sa.Column(sa.String)
    color_id = sa.Column(sa.Integer)
    condition = sa.Column(sa.String)

    min_price = sa.Column(sa.Numeric, nullable=True)
    avg_price = sa.Column(sa.Numeric, nullable=True)
    max_price = sa.Column(sa.Numeric, nullable=True)

    updated_at = sa.Column(sa.DateTime, nullable=True)
    
    __table_args__ = (
        sa.PrimaryKeyConstraint('item_id', 'item_type', 'color_id', 'condition'),
    )


class Item(Base):
    __tablename__ = 'items'

    id = sa.Column(sa.String)
    type = sa.Column(sa.String)
    name = sa.Column(sa.String, nullable=False)
    id_category = sa.Column(sa.Integer, sa.ForeignKey('categories.id', ondelete='CASCADE'))  # TODO category_id

    bo_id = sa.Column(sa.Integer)

    category = relationship('Category')

    __table_args__ = (
        sa.PrimaryKeyConstraint('id', 'type'),
    )
    
    prices = relationship(ItemPrice, primaryjoin="and_( \
        Item.id == foreign(ItemPrice.item_id), \
        Item.type == foreign(ItemPrice.item_type) \
    )")


class OrderStatus(Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    PAID = "Paid"
    PACKED = "Packed"
    SHIPPED = "Shipped"
    RECEIVED = "Received"
    ON_HOLD = "On Hold"
    CANCELLED = "Cancelled"
    PURGED = "Purged"
    UNKNOWN = "Unknown"


class Order(Base):
    __tablename__ = 'orders'

    id = sa.Column(sa.Integer, primary_key=True)

    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=False)
    buyer_name = sa.Column(sa.String, nullable=False)
    buyer_email = sa.Column(sa.String(512), nullable=False)
    date_ordered = sa.Column(sa.DateTime, nullable=False)

    status = sa.Column(sa.Enum(OrderStatus), nullable=False)

    shipping_method = sa.Column(sa.String)
    shipping_address_first_name = sa.Column(sa.String)
    shipping_address_last_name = sa.Column(sa.String)
    shipping_address_address_1 = sa.Column(sa.String)
    shipping_address_address_2 = sa.Column(sa.String)
    shipping_address_country_code = sa.Column(sa.String)
    shipping_address_city = sa.Column(sa.String)
    shipping_address_state = sa.Column(sa.String)
    shipping_address_postal_code = sa.Column(sa.String)

    bl_id = sa.Column(sa.Integer)
    bo_id = sa.Column(sa.Integer)

    applied = sa.Column(sa.Boolean)

    __table_args__ = (
        sa.UniqueConstraint(user_id, buyer_name, buyer_email, date_ordered),
    )

    items = relationship('OrderItem')


class OrderItem(Base):
    __tablename__ = 'order_items'

    id = sa.Column(sa.Integer, primary_key=True)
    order_id = sa.Column(sa.Integer, sa.ForeignKey('orders.id', ondelete="CASCADE"), nullable=False)
    
    item_id = sa.Column(sa.String, nullable=False)
    item_type = sa.Column(sa.String, nullable=False)
    color_id = sa.Column(sa.Integer, sa.ForeignKey('colors.id'), nullable=False)
    condition = sa.Column(sa.String(1), nullable=False, default='U')
    quantity = sa.Column(sa.Integer, nullable=False, default=0)
    user_remarks = sa.Column(sa.String)
    user_description = sa.Column(sa.String)

    image_pulled = sa.Column(sa.Integer)
    
    color = relationship('Color')
    item = relationship('Item')

    __table_args__ = (
        sa.UniqueConstraint('order_id', 'item_id', 'item_type', 'color_id', 'condition', 'quantity', 'user_remarks', 'user_description'),
        sa.ForeignKeyConstraint(['item_id', 'item_type'], ['items.id', 'items.type']),
    )


class InventoryItem(Base):
    __tablename__ = 'inventory_items'

    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    item_id = sa.Column(sa.String, nullable=False)
    item_type = sa.Column(sa.String, nullable=False)

    color_id = sa.Column(sa.Integer, sa.ForeignKey('colors.id'), nullable=False, default=0)

    condition = sa.Column(sa.String(1), nullable=False, default='U')
    unit_price = sa.Column(sa.Numeric, nullable=True)
    quantity = sa.Column(sa.Integer, nullable=False, default=0)
    user_remarks = sa.Column(sa.String, nullable=False, default='')
    user_description = sa.Column(sa.String, nullable=False, default='')

    image_pulled = sa.Column(sa.Integer)

    item = relationship('Item')
    color = relationship("Color")
    user = relationship("User")

    __table_args__ = (
        sa.ForeignKeyConstraint(['item_id', 'item_type'], ['items.id', 'items.type']),
    )

    
    def is_valid_for_bricklink(self):
        return \
            self.unit_price is not None


    def is_valid_for_brickowl(self):
        return \
            self.unit_price is not None and \
            self.item.bo_id is not None
