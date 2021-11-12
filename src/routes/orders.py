from flask import request, Blueprint, redirect, url_for, render_template, flash, g, current_app
import sqlalchemy
from db import Session
from models import InventoryPart, OrderPart, User, Part
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
import bcrypt
import jwt
import os
from datetime import datetime, timezone, timedelta
from routes.auth import auth_request
from models import Order


blueprint = Blueprint('user', __name__)


@blueprint.route('/orders', methods=['GET'])
@auth_request
def orders():
    with Session.begin() as session:
        orders = session.query(Order) \
            .filter_by(id_user=g.user_id) \
            .order_by(Order.date_ordered) \
            .all()
        return render_template('orders.html.j2', orders=orders)


@blueprint.route('/orders/<order_id>/parts', methods=['GET'])
@auth_request
def order_parts(order_id: int):
    with Session.begin() as session:
        order_parts = session.query(OrderPart) \
                .filter_by(id_order=order_id) \
                .order_by(OrderPart.id_part) \
                .all()
        return render_template('order_parts.html.j2', order_parts=order_parts)


@blueprint.route('/order_syncer/attach', methods=['POST'])
@auth_request
def attach_order_syncer():
    pass


@blueprint.route('/order_syncer/detach', methods=['POST'])
@auth_request
def detach_order_syncer():
    pass

