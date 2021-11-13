from functools import wraps
from flask import Blueprint, redirect, url_for, render_template, flash, g, current_app, request, get_flashed_messages
from flask.helpers import get_flashed_messages
from backends.brickowl import BrickOwl
from db import Session
from routes.auth import auth_request
from models import Op as SavedOp, User
from components.paginator import Paginator
from sqlalchemy import update
from backends.bricklink import Bricklink, InvalidRequest as BricklinkInvalidRequest
from backends.brickowl import BrickOwl, InvalidRequest as BrickowlInvalidRequest
import json


blueprint = Blueprint('settings', __name__)


def require_backends_approved(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        with Session.begin() as session:
            user = session.query(User) \
                .filter_by(id=g.user_id) \
                .first()

            if user.bl_credentials_approved and user.bo_credentials_approved:
                return current_app.ensure_sync(f)(*args, **kwargs)
            else:
                flash(json.dumps({ 'backends': { 'submit': 'Backends not approved.' }}))
                return redirect(url_for('user.settings.view'))
    return wrapper


#def require_syncer_active():
#    pass


@blueprint.route('/settings', methods=['GET'])
@auth_request
def view():
    with Session.begin() as session:
        user = session.query(User) \
            .filter_by(id=g.user_id) \
            .first()
        form_feedback = json.loads(get_flashed_messages()[0]) if get_flashed_messages() else {}
        return render_template('settings/backends.j2', user=user, form_feedback=form_feedback)
  

@blueprint.route('/settings/backends/approve', methods=['POST'])
@auth_request
def approve_backends():
    with Session.begin() as session:
        user = session.query(User) \
            .filter_by(id=g.user_id) \
            .first()

        user.bl_credentials_approved = False
        user.bo_credentials_approved = False
        user.syncer_enabled = False

        user.bl_customer_key    = request.form.get('bl_customer_key')
        user.bl_customer_secret = request.form.get('bl_customer_secret')
        user.bl_token_value     = request.form.get('bl_token_value')
        user.bl_token_secret    = request.form.get('bl_token_secret')
        
        user.bo_key = request.form.get('bo_key')

        bricklink = Bricklink.from_user(user)
        try:
            bricklink.get_inventories()
            user.bl_credentials_approved = True
        except BricklinkInvalidRequest as e:
            print(f"Invalid Bricklink credentials:", e)

        brickowl = BrickOwl.from_user(user)
        try:
            brickowl.get_colors()
            user.bo_credentials_approved = True
        except BrickowlInvalidRequest as e:
            print(f"Invalid BrickOwl credentials:", e)

    return redirect(url_for("user.settings.view"))


@blueprint.route('/settings/syncer/toggle', methods=['POST'])
@auth_request
@require_backends_approved
def toggle_syncer():
    with Session.begin() as session:
        user = session.query(User) \
            .filter_by(id=g.user_id) \
            .first()
        user.syncer_enabled = not user.syncer_enabled
        # TODO avoid syncer switch flood
    return redirect(url_for("user.settings.view"))

