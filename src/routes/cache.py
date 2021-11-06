from flask import request, Blueprint, redirect, url_for, render_template, flash, g
from db import Session
from models import Color
from routes.auth import auth_request


blueprint = Blueprint('cache', __name__)


@blueprint.route('/colors', methods=['GET'])
@auth_request
async def colors():
    with Session() as session:
        colors = session.query(Color) \
            .order_by(Color.id.asc()) \
            .all()
        return render_template('colors.html', colors=colors)
        
