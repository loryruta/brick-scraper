from flask import request, Blueprint, render_template, g, redirect, url_for
from db import Session
from models import User, InventoryItem
from routes.auth import auth_request
from backends.bricklink import Bricklink, parse_bricklink_item_type
import json


blueprint = Blueprint('partout', __name__)


def partout(set_no: str):
    with Session() as session:
        user = session.query(User) \
            .filter_by(id=g.user_id) \
            .first()

        bricklink = Bricklink(
            user.bl_customer_key,
            user.bl_customer_secret,
            user.bl_token_value,
            user.bl_token_secret
        )

        subsets = bricklink.get_subsets(item_type='set', item_no=set_no)

        result = []
        for subset in subsets:
            result += subset['entries']

        return result


@blueprint.route('/partout', methods=['GET'])
@auth_request
def show():
    set_no = request.args.get('set_no')

    result = None
    if set_no:
        result = partout(set_no)
    
    return render_template('partout.j2',
        result=result
    )


@blueprint.route('/partout/inventory', methods=['POST'])
@auth_request
def add_to_inventory():
    set_no = request.form.get('set_no')
    condition = 'N' if 'new' in request.form else 'U'

    if not set_no:
        raise Exception("set_no is required")

    set_entries = partout(set_no)

    with Session() as session:
        inventory_items = [
            InventoryItem(
                user_id=g.user_id,
                item_id=entry['item']['no'],
                item_type=parse_bricklink_item_type(entry['item']['type']),
                color_id=entry['color_id'],
                condition=condition,
                unit_price=None,
                quantity=entry['quantity'],
                user_remarks=set_no,
                user_description=''
            )
            for entry in set_entries
        ]
        session.bulk_save_objects(inventory_items)
        session.commit()

    return redirect(url_for('inventory.show'))
