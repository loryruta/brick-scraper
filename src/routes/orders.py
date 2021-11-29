from flask import request, Blueprint, redirect, url_for, render_template, flash, g, current_app
from db import Session
from models import OrderItem, OrderStatus
from routes.auth import auth_request
from models import Order


blueprint = Blueprint('orders', __name__)


@blueprint.route('/orders', methods=['GET'])
@auth_request
def show():
    with Session.begin() as session:
        orders = session.query(Order) \
            .filter_by(user_id=g.user_id) \
            .order_by(Order.date_ordered.desc()) \
            .all()
        return render_template('orders.j2', orders=orders)


@blueprint.route('/orders/<order_id>/items', methods=['GET'])
@auth_request
def show_items(order_id: int):
    with Session.begin() as session:
        order = session.query(Order) \
            .filter_by(id=order_id) \
            .first()

        items = session.query(OrderItem) \
                .filter_by(order_id=order_id) \
                .order_by(OrderItem.item_id) \
                .all()

        return render_template('order_items.j2',
            order=order,
            items=items
        )


@blueprint.context_processor
def is_order_satisfied():
      def f(order_status: OrderStatus):
            return \
                order_status == OrderStatus.RECEIVED or \
                order_status == OrderStatus.SHIPPED or \
                order_status == OrderStatus.PURGED
      return dict(is_order_satisfied=f)

