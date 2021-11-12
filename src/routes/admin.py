from flask import Blueprint, redirect, url_for, render_template, flash, g, current_app, request
from db import Session
from routes.auth import auth_request
from models import Op as SavedOp, User
from components.paginator import Paginator
from sqlalchemy import update


blueprint = Blueprint('account', __name__)


@blueprint.route('/settings', methods=['GET', 'POST'])
@auth_request
def settings():
    if request.method == "GET":
        with Session.begin() as session:
            user = session.query(User) \
                .filter_by(id=g.user_id) \
                .first()
            return render_template('settings.j2', user=user)

    elif request.method == "POST":
        with Session.begin() as session:
            session.execute(
                update(User) \
                    .values(id=g.user_id, **request.form.to_dict())
            )
            return redirect(url_for('account.settings'))


@blueprint.route('/admin/op', methods=['GET'])
@auth_request
def op():
    with Session.begin() as session:
        paginator = Paginator(SavedOp)
        op_list = paginator.paginate(
            session.query(SavedOp) \
                .filter_by(
                    id_user=g.user_id
                ) \
                .order_by(
                    SavedOp.created_at.desc(),
                    SavedOp.id.desc()
                )
            ) \
            .all()
        return render_template('op.j2', op_list=op_list, paginator=paginator)

