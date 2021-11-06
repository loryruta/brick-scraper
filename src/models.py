import sqlalchemy as sa
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql.schema import ForeignKey, Table


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = sa.Column(sa.Integer, primary_key=True)
    email = sa.Column(sa.String(512), unique=True, nullable=False)
    password_hash = sa.Column(sa.String(128), nullable=False)

    parted_out_sets = relationship('PartedOutSet', back_populates='user')


class Color(Base):
    __tablename__ = 'colors'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    rgb = sa.Column(sa.String(6), nullable=False)

    id_bricklink = sa.Column(sa.Integer)
    id_brickowl = sa.Column(sa.Integer)


class Part(Base):
    __tablename__ = 'parts'

    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    id_category = sa.Column(sa.Integer)
    part_url = sa.Column(sa.String)
    part_img_url = sa.Column(sa.String)
    
    id_bricklink = sa.Column(sa.String)
    id_brickowl = sa.Column(sa.String)


class Set(Base):
    __tablename__ = 'sets'

    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    year = sa.Column(sa.Integer)
    id_theme = sa.Column(sa.Integer)
    num_parts = sa.Column(sa.Integer)
    set_img_url = sa.Column(sa.String)
    set_url = sa.Column(sa.String)
    last_modified_date: sa.Column(sa.DateTime)


class PartedOutSet(Base):
    __tablename__ = 'parted_out_sets'

    id = sa.Column(sa.Integer, primary_key=True)
    id_user = sa.Column(sa.Integer, sa.ForeignKey('users.id'))
    id_set = sa.Column(sa.String, sa.ForeignKey('sets.id'))

    user = relationship("User", back_populates='parted_out_sets')
    set = relationship("Set")


class InventoryPart(Base):
    __tablename__ = 'inventory_parts'

    id = sa.Column(sa.Integer, primary_key=True)
    id_part = sa.Column(sa.String, sa.ForeignKey('parts.id'))
    id_color = sa.Column(sa.Integer, sa.ForeignKey('colors.id'))
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
