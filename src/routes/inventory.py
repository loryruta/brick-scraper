from flask import request, Blueprint, redirect, url_for, render_template, flash, g, current_app
import sqlalchemy
from components.paginator import Paginator
from db import Session
from models import InventoryPart, User, Part
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
import bcrypt
import jwt
import os
from datetime import datetime, timezone, timedelta
from routes.auth import auth_request
import models


blueprint = Blueprint('inventory', __name__)


@blueprint.route('/inventory/parts', methods=['GET'])
@auth_request
async def parts():
    with Session.begin() as session:
        paginator = Paginator(InventoryPart)
        inventory_parts = paginator.paginate(
            session.query(InventoryPart)
                .where(InventoryPart.id_user == g.user_id)
            ) \
            .all()
        return render_template('inventory/parts.j2', inv_parts=inventory_parts, paginator=paginator)


@blueprint.route('/orders/apply', methods=['GET'])
@auth_request
def apply_orders():
    # TODO item_manager.apply_orders(g.user_id)
    return "fatto"


