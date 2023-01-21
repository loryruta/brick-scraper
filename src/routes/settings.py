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
from typing import Optional
import syncer
from datetime import datetime


blueprint = Blueprint('settings', __name__)


def require_remote_keys(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        with Session.begin() as session:
            user = session.query(User) \
                .filter_by(id=g.user_id) \
                .first()

            if user.bl_credentials_approved and user.bo_credentials_approved:
                return current_app.ensure_sync(f)(*args, **kwargs)
            else:
                return redirect(url_for('settings.view'))
    return wrapper


@blueprint.route('/settings', methods=['GET'])
@auth_request
def view():
    with Session.begin() as session:
        user = session.query(User) \
            .filter_by(id=g.user_id) \
            .first()
        form_feedback = json.loads(get_flashed_messages()[0]) if get_flashed_messages() else {}
        return render_template('settings/index.j2', user=user, form_feedback=form_feedback)


@blueprint.route('/settings/stores', methods=['POST'])
@auth_request
def set_stores():
    with Session.begin() as session:
        user = session.query(User) \
            .filter_by(id=g.user_id) \
            .first()
        
        bl_customer_key = request.form.get('bl_customer_key')
        bl_customer_secret = request.form.get('bl_customer_secret')
        bl_token_value = request.form.get('bl_token_value')
        bl_token_secret = request.form.get('bl_token_secret')

        bo_key = request.form.get('bo_key')
        
        user.bl_customer_key = bl_customer_key
        user.bl_customer_secret = bl_customer_secret
        user.bl_token_value = bl_token_value
        user.bl_token_secret = bl_token_secret

        user.bo_key = bo_key

        user.bl_credentials_approved = False
        user.bo_credentials_approved = False

        bl = Bricklink(
            customer_key=bl_customer_key,
            customer_secret=bl_customer_secret,
            token_value=bl_token_value,
            token_secret=bl_token_secret,
        )
        try:
            bl.get_colors()
            user.bl_credentials_approved = True
        except BricklinkInvalidRequest as _:
            pass

        bo = BrickOwl(
            key=bo_key
        )
        try:
            bo.get_colors()
            user.bo_credentials_approved = True
        except BrickowlInvalidRequest as _:
            pass

    return redirect(url_for("settings.view"))


@blueprint.route('/settings/syncer/toggle', methods=['POST'])
@auth_request
def toggle_syncer():
    with Session.begin() as session:
        user = session.query(User) \
            .filter_by(id=g.user_id) \
            .first()

        if not (user.bl_credentials_approved and user.bo_credentials_approved):
            flash(json.dumps({ 'backends': { 'submit': 'Backends not approved.' }}))
            return redirect(url_for('settings.view'))

        should_enable = not user.syncer_enabled
        antiflood_interval = 2  # In seconds

        if should_enable:
            if user.syncer_enable_timestamp is None or \
                (datetime.now() - user.syncer_enable_timestamp).seconds >= antiflood_interval:
                syncer.start(session, user.id)

                user.syncer_enabled = True
                user.syncer_enable_timestamp = datetime.now().isoformat()
            else:
                # TODO flash error message
                pass
        else:
            user.syncer_enabled = False
            syncer.stop(user)

    return redirect(url_for("settings.view"))


@blueprint.route('/settings/syncer/start', methods=['POST'])
@auth_request
def start_syncer():
    with Session.begin() as session:
        
        syncer.start(session, g.user_id)

        return redirect(url_for('settings.view'))


@blueprint.route('/settings/syncer/stop', methods=['POST'])
@auth_request
def stop_syncer():
    with Session.begin() as session:

        syncer.stop(session, g.user_id)

        return redirect(url_for('settings.view'))




