from re import M
from flask import request, Blueprint, redirect, url_for, render_template, flash, g, current_app
import sqlalchemy
from components.paginator import Paginator
from db import Session
from models import Color, InventoryPart, User, Part
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
import jwt
import os
from datetime import datetime, timezone, timedelta
from routes.auth import auth_request
import models
from math import inf


blueprint = Blueprint('inventory', __name__)


@blueprint.route('/inventory/parts', methods=['GET'])
@auth_request
def parts():
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

        inv_parts_query = session.query(InventoryPart) \
            .where(InventoryPart.id_user == g.user_id)

        if search_params['colors']:
            inv_parts_query = inv_parts_query \
                .where(InventoryPart.id_color.in_(search_params['colors']))

        if search_params['conditions']:
            inv_parts_query = inv_parts_query \
                .where(InventoryPart.condition.in_(search_params['conditions']))

        if search_params['price_min']:
            inv_parts_query = inv_parts_query \
                .where(InventoryPart.unit_price >= search_params['price_min'])

        if search_params['price_max']:
            inv_parts_query = inv_parts_query \
                .where(InventoryPart.unit_price <= search_params['price_max'])
            
        if search_params['quantity_min']:
            inv_parts_query = inv_parts_query \
                .where(InventoryPart.quantity <= search_params['quantity_min'])

        if search_params['quantity_max']:
            inv_parts_query = inv_parts_query \
                .where(InventoryPart.quantity <= search_params['quantity_max'])

        if search_params['user_remarks']:
            inv_parts_query = inv_parts_query \
                .where(InventoryPart.user_remarks == search_params['user_remarks'])

        if search_params['user_description']:
            inv_parts_query = inv_parts_query \
                .where(InventoryPart.user_description == search_params['user_description'])
        
        paginator = Paginator(inv_parts_query)
        inv_parts = paginator.paginate()

        return render_template('inventory/parts.j2',
            inv_parts=inv_parts,
            colors=colors,
            paginator=paginator,
            search_params=search_params,
        )


@blueprint.route('/orders/apply', methods=['GET'])
@auth_request
def apply_orders():
    # TODO item_manager.apply_orders(g.user_id)
    return "fatto"


