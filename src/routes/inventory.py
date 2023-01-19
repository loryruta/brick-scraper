from re import M
from flask import request, Blueprint, redirect, url_for, render_template, flash, g, current_app
import sqlalchemy
from components.paginator import Paginator
from db import Session
from models import Color, InventoryItem, User
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
import jwt
import os
from datetime import datetime, timezone, timedelta
from routes.auth import auth_request
import models


blueprint = Blueprint('inventory', __name__)


@blueprint.route('/inventory', methods=['GET'])
@auth_request
def show():
    with Session.begin() as session:
        colors = session.query(Color) \
            .order_by(Color.name.asc()) \
            .all()

        search_params = {
            'colors': [int(color_id) for color_id in request.args.getlist('colors')],
            'conditions': request.args.getlist('conditions'),
            'price_min': request.args.get('price_min'),
            'price_max': request.args.get('price_max'),
            'quantity_min': request.args.get('quantity_min'),
            'quantity_max': request.args.get('quantity_max'),
            'user_remarks': request.args.get('user_remarks'),
            'user_description': request.args.get('user_description'),
        }

        get_query = session.query(InventoryItem) \
            .where(InventoryItem.user_id == g.user_id)

        # TODO item type

        if search_params['colors']:
            get_query = get_query \
                .where(InventoryItem.color_id.in_(search_params['colors']))

        if search_params['conditions']:
            get_query = get_query \
                .where(InventoryItem.condition.in_(search_params['conditions']))

        if search_params['price_min']:
            get_query = get_query \
                .where(InventoryItem.unit_price >= search_params['price_min'])

        if search_params['price_max']:
            get_query = get_query \
                .where(InventoryItem.unit_price <= search_params['price_max'])
            
        if search_params['quantity_min']:
            get_query = get_query \
                .where(InventoryItem.quantity >= search_params['quantity_min'])

        if search_params['quantity_max']:
            get_query = get_query \
                .where(InventoryItem.quantity <= search_params['quantity_max'])

        if search_params['user_remarks']:
            get_query = get_query \
                .where(InventoryItem.user_remarks == search_params['user_remarks'])

        if search_params['user_description']:
            get_query = get_query \
                .where(InventoryItem.user_description == search_params['user_description'])
        
        paginator = Paginator(get_query)
        items = paginator.paginate()

        return render_template('inventory.j2',
            items=items,
            colors=colors,
            paginator=paginator,
            search_params=search_params,
        )


@blueprint.route('/orders/apply', methods=['GET'])
@auth_request
def apply_orders():
    # TODO item_manager.apply_orders(g.user_id)
    return "fatto"


