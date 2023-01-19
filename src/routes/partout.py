from flask import request, Blueprint, redirect, url_for, render_template, flash, g, current_app
from db import Session
from models import User
from routes.auth import auth_request
from models import Order
from backends.bricklink import Bricklink


blueprint = Blueprint('partout', __name__)


@blueprint.route('/partout', methods=['GET'])
@auth_request
def show():
    set_no = request.args.get('set_no')

    result = None

    if set_no:
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

    return render_template('partout/index.j2',
        result=result
    )


@blueprint.route('/partout/inventory', methods=['POST'])
@auth_request
def add_to_inventory():
    # TODO
    pass

