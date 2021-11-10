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
from routes.auth import auth_request
from models import Op as SavedOp


blueprint = Blueprint('admin', __name__)


@blueprint.route('/admin/op', methods=['GET'])
@auth_request
async def parts():
    with Session.begin() as session:
        op_list = session.query(SavedOp) \
            .filter_by(
                id_user=g.user_id
            ) \
            .order_by(
                SavedOp.created_at.desc(),
                SavedOp.id.desc()
            ) \
            .all()
        return render_template('op.html.j2', op_list=op_list)

