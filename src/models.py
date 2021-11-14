import sqlalchemy as sa
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql.schema import ForeignKey, Table
from sqlalchemy import func
from enum import Enum
from sqlalchemy.dialects.postgresql import JSONB


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = sa.Column(sa.Integer, primary_key=True)
    email = sa.Column(sa.String(512), unique=True, nullable=False)
    password_hash = sa.Column(sa.String(128), nullable=False)

    # Bricklink credentials
    bl_customer_key = sa.Column(sa.String)
    bl_customer_secret = sa.Column(sa.String)
    bl_token_value = sa.Column(sa.String)
    bl_token_secret = sa.Column(sa.String)

    bl_credentials_approved = sa.Column(sa.Boolean, nullable=False, default=False)

    # BrickOwl credentials
    bo_key = sa.Column(sa.String)

    bo_credentials_approved = sa.Column(sa.Boolean, nullable=False, default=False)

    # Rate limiter
    bl_current_hour = sa.Column(sa.Integer)
    bl_current_hour_requests_count = sa.Column(sa.Integer)

    bl_api_current_day = sa.Column(sa.Integer)
    bl_api_current_day_requests_count = sa.Column(sa.Integer)

    bo_api_current_minute_requests_count = sa.Column(sa.Integer)
    bo_api_current_minute = sa.Column(sa.Integer)

    # Syncer
    syncer_enabled = sa.Column(sa.Boolean, default=False)
    syncer_enable_timestamp = sa.Column(sa.DateTime)
    syncer_running = sa.Column(sa.Boolean, default=False)

    orders = relationship('Order')


class Op(Base):
    __tablename__ = 'op'

    id = sa.Column(sa.Integer, primary_key=True)
    id_user = sa.Column(sa.Integer, sa.ForeignKey('users.id'))
    type = sa.Column(sa.String(64), nullable=False)
    id_dependency = sa.Column(sa.Integer, sa.ForeignKey('op.id'))
    id_parent = sa.Column(sa.Integer, sa.ForeignKey('op.id'))
    params = sa.Column(JSONB, nullable=False)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=func.now())
    invoked_at = sa.Column(sa.DateTime)
    processed_at = sa.Column(sa.DateTime)

    dependency = relationship('Op', foreign_keys=[id_dependency], remote_side=[id])
    parent = relationship('Op', foreign_keys=[id_parent], remote_side=[id])
    user = relationship('User')


class Color(Base):
    __tablename__ = 'colors'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    rgb = sa.Column(sa.String(6), nullable=False)
    type = sa.Column(sa.String(64), nullable=False)

    id_bo = sa.Column(sa.Integer)


class Category(Base):
    __tablename__ = 'categories'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String, nullable=False)


class Part(Base):
    __tablename__ = 'parts'

    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    id_category = sa.Column(sa.Integer, sa.ForeignKey('categories.id'))

    id_bo = sa.Column(sa.Integer)


class Set(Base):
    __tablename__ = 'sets'

    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    id_category = sa.Column(sa.Integer, sa.ForeignKey('categories.id'))
    img_url = sa.Column(sa.String)
    year = sa.Column(sa.Integer)
    num_parts = sa.Column(sa.Integer)
    last_modified_date: sa.Column(sa.DateTime)


class OrderStatus(Enum):
    UNKNOWN = -1
    PENDING = 0
    PAID = 1
    PROCESSING = 2
    PROCESSED = 3
    SHIPPED = 4
    RECEIVED = 5


class Order(Base):
    __tablename__ = 'orders'

    id = sa.Column(sa.Integer, primary_key=True)
    id_user = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=False)
    buyer_name = sa.Column(sa.String, nullable=False)
    buyer_email = sa.Column(sa.String(512), nullable=False)
    date_ordered = sa.Column(sa.DateTime, nullable=False)
    status = sa.Column(sa.Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    shipping_method = sa.Column(sa.String)
    shipping_address_first_name = sa.Column(sa.String)
    shipping_address_last_name = sa.Column(sa.String)
    shipping_address_address_1 = sa.Column(sa.String)
    shipping_address_address_2 = sa.Column(sa.String)
    shipping_address_country_code = sa.Column(sa.String)
    shipping_address_city = sa.Column(sa.String)
    shipping_address_state = sa.Column(sa.String)
    shipping_address_postal_code = sa.Column(sa.String)

    id_bl = sa.Column(sa.Integer)
    id_bo = sa.Column(sa.Integer)

    __table_args__ = (
        sa.UniqueConstraint(id_user, buyer_name, buyer_email, date_ordered),
    )

    parts = relationship('OrderPart')


class OrderPart(Base):
    __tablename__ = 'order_parts'

    id = sa.Column(sa.Integer, primary_key=True)
    id_order = sa.Column(sa.Integer, sa.ForeignKey('orders.id'), nullable=False)
    id_part = sa.Column(sa.String, sa.ForeignKey('parts.id'), nullable=False)
    id_color = sa.Column(sa.Integer, sa.ForeignKey('colors.id'), nullable=False)
    condition = sa.Column(sa.String(1), nullable=False, default='U')
    quantity = sa.Column(sa.Integer, nullable=False, default=0)
    user_remarks = sa.Column(sa.String)
    user_description = sa.Column(sa.String)

    part = relationship('Part')
    color = relationship('Color')

    __table_args__ = (
        sa.UniqueConstraint('id_order', 'id_part', 'id_color', 'condition', 'quantity', 'user_remarks', 'user_description'),
    )


class InventoryPart(Base):
    __tablename__ = 'inventory_parts'

    id = sa.Column(sa.Integer, primary_key=True)
    id_user = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=False)
    id_part = sa.Column(sa.String, sa.ForeignKey('parts.id'), nullable=False)
    id_color = sa.Column(sa.Integer, sa.ForeignKey('colors.id'), nullable=False)
    condition = sa.Column(sa.String(1), nullable=False, default='U')
    quantity = sa.Column(sa.Integer, nullable=False, default=0)
    user_remarks = sa.Column(sa.String)
    user_description = sa.Column(sa.String)

    part = relationship("Part")
    color = relationship("Color")
    user = relationship("User")

    __table_args__ = (
        sa.UniqueConstraint('id_user', 'id_part', 'id_color', 'condition', 'user_remarks'),
    )
