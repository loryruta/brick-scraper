from flask import request, Blueprint, redirect, url_for, render_template, flash, g, current_app
import sqlalchemy
from db import Session
from models import InventoryPart, User, Part
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
import bcrypt
import jwt
import os
from datetime import datetime, timezone, timedelta
import item_manager
from item_manager import InvalidOperation
from routes.auth import auth_request
import models


blueprint = Blueprint('inventory', __name__)


@blueprint.route('/inventory/parts', methods=['GET'])
@auth_request
async def parts():
    if request.method == "GET":
        with Session.begin() as session:
            inv_parts = session.query(InventoryPart) \
                .where(InventoryPart.id_user == g.user_id) \
                .all()
            return render_template('inventory/parts.html', inv_parts=inv_parts)


@blueprint.route('/parted_out_sets/add', methods=['GET', 'POST'])
@auth_request
def add_parted_out_set():
    # GET
    if request.method == "GET":
        return render_template('add_parted_out_set.html')

    # POST
    elif request.method == "POST":
        set_id = request.form.get('set_id')
        condition = request.form.get('condition')
        try:
            item_manager.part_out_set_to_inventory(g.user_id, set_id, condition)
            return redirect(url_for('inventory.parted_out_sets'))
        except RuntimeError as e:
            # flash
            return redirect(url_for('inventory.add_parted_out_set'))


@blueprint.route('/parted_out_sets', methods=['GET'])
@auth_request
async def parted_out_sets():
    if request.method == "GET":
        with Session.begin() as session:
            parted_out_sets = session.query(models.PartedOutSet).filter_by(id_user=g.user_id).all()
            return render_template('parted_out_sets.html', parted_out_sets=parted_out_sets)


@blueprint.route('/orders/apply', methods=['GET'])
@auth_request
def apply_orders():
    item_manager.apply_orders(g.user_id)
    return "fatto"


