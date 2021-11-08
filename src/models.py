import sqlalchemy as sa
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql.schema import ForeignKey, Table
from sqlalchemy import func
from enum import Enum


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = sa.Column(sa.Integer, primary_key=True)
    email = sa.Column(sa.String(512), unique=True, nullable=False)
    password_hash = sa.Column(sa.String(128), nullable=False)

    orders = relationship('Order')
    inventory_history = relationship('InventoryLog', back_populates='user')


class Color(Base):
    __tablename__ = 'colors'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    rgb = sa.Column(sa.String(6), nullable=False)
    type = sa.Column(sa.String(64), nullable=False)


class BOColor(Base):
    __tablename__ = 'bo_colors'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=False)
    name = sa.Column(sa.String(64), nullable=False)
    id_bricklink = sa.Column(sa.Integer, sa.ForeignKey('colors.id'))

    color = relationship('Color')


class Category(Base):
    __tablename__ = 'categories'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String, nullable=False)


class Part(Base):
    __tablename__ = 'parts'

    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    id_category = sa.Column(sa.Integer, sa.ForeignKey('categories.id'))
    img_url = sa.Column(sa.String)


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

    id_bricklink = sa.Column(sa.Integer)
    id_brickowl = sa.Column(sa.Integer)

    __table_args__ = (
        sa.UniqueConstraint(id_user, buyer_name, buyer_email, date_ordered),
    )

    applied_order = relationship('AppliedOrder')
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


class InventoryLog(Base):
    __tablename__ = 'inventory_history'

    id = sa.Column(sa.Integer, primary_key=True)
    id_user = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=False)
    type = sa.Column(sa.String(64), nullable=False)
    created_at = sa.Column(sa.DateTime, server_default=func.now())

    user = relationship("User", back_populates='inventory_history')

    __mapper_args__ = {
        'polymorphic_identity': 'inventory_history',  # TODO rename inventory_log
        'polymorphic_on': type
    }


class PartedOutSet(InventoryLog):
    __tablename__ = 'parted_out_sets'

    id = sa.Column(sa.Integer, sa.ForeignKey('inventory_history.id'), primary_key=True)
    id_set = sa.Column(sa.String, sa.ForeignKey('sets.id'), nullable=False)

    set = relationship("Set")

    __mapper_args__ = {
        'polymorphic_identity': 'parted_out_sets'  # TODO rename parted_out_set
    }


class AppliedOrder(InventoryLog):
    __tablename__ = 'applied_orders'

    id = sa.Column(sa.Integer, sa.ForeignKey('inventory_history.id'), primary_key=True)
    id_order = sa.Column(sa.Integer,  sa.ForeignKey('orders.id'), unique=True, nullable=False)

    order = relationship('Order', viewonly=True)

    __mapper_args__ = {
        'polymorphic_identity': 'applied_orders'  # TODO rename applied_order
    }


class InventoryPart(Base):
    __tablename__ = 'inventory_parts'

    id = sa.Column(sa.Integer, primary_key=True)
    id_part = sa.Column(sa.String, sa.ForeignKey('parts.id'), nullable=False)
    id_color = sa.Column(sa.Integer, sa.ForeignKey('colors.id'), nullable=False)
    condition = sa.Column(sa.String(1), nullable=False, default='U')
    quantity = sa.Column(sa.Integer, nullable=False, default=0)
    id_parted_out_set = sa.Column(sa.Integer, sa.ForeignKey('parted_out_sets.id'), nullable=True)
    id_user = sa.Column(sa.Integer, sa.ForeignKey('users.id'), nullable=False)  # todo if id_parted_out_set is valorized, id_user must be the same of parted_out_sets.id_user

    part = relationship("Part")
    color = relationship("Color")
    parted_out_set = relationship("PartedOutSet")
    user = relationship("User")

    __table_args__ = (
        sa.UniqueConstraint('id_part', 'id_color', 'condition', 'id_parted_out_set', 'id_user'),
    )
