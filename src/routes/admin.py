from flask import Blueprint, redirect, url_for, render_template, flash, g, current_app
from db import Session
from routes.auth import auth_request
from models import Op as SavedOp
from components.paginator import Paginator


blueprint = Blueprint('admin', __name__)


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

