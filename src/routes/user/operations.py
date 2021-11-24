from flask import Blueprint, render_template, g
from sqlalchemy import and_
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import func
from db import Session
from routes.auth import auth_request
from models import Op as SavedOp, OpView
from components.paginator import Paginator
from sqlalchemy.dialects.postgresql import INTERVAL


blueprint = Blueprint('operations', __name__)


@blueprint.route('/operations', methods=['GET'])
@auth_request
def operations():
    with Session.begin() as session:
        op_query = session.query(SavedOp) \
                .filter_by(id_user=g.user_id) \
                .order_by(
                    SavedOp.created_at.desc(),
                    SavedOp.id.desc(),
                )

        paginator = Paginator(op_query)
        op_list =  paginator.paginate()
        
        return render_template('op.j2',
            op_list=op_list,
            paginator=paginator,
        )


@blueprint.route('/operations/chart', methods=['GET'])
@auth_request
def operations_chart():
    with Session.begin() as session:
        groups = session.query(SavedOp) \
            .join(OpView, and_(
                SavedOp.id_user == g.user_id,
                OpView.id_group == SavedOp.id,
            )) \
            .all()

        entries = []

        for group in groups:
            screenshots = session.query(OpView) \
                .filter(OpView.id_group == group.id) \
                .limit(100) \
                .all()

            entries.append({
                'group': group,
                'screenshots': screenshots,
            })

        return render_template('op_chart.j2',
            entries=entries,
        )

