from flask import request, Blueprint, render_template
from components.paginator import Paginator
from db import Session
from models import Color, Item
from routes.auth import auth_request


blueprint = Blueprint('catalog', __name__)


@blueprint.route('/colors', methods=['GET'])
@auth_request
def colors():
    with Session() as session:
        query = session.query(Color)
        
        paginator = Paginator(query)
        colors = paginator.paginate() \
            .all()
        
        return render_template(f'catalog/colors.j2', \
            paginator=paginator,
            colors=colors
        )


@blueprint.route('/catalog', methods=['GET'])
@auth_request
def catalog():
    _type = request.args.get('type')

    with Session() as session:
        query = session.query(Item)
        if _type:
            query.filter_by(type=_type)

        paginator = Paginator(query)
        items = paginator.paginate() \
            .all()
        
        return render_template(f'catalog/catalog.j2', \
            paginator=paginator,
            items=items,
            search_params=[]
        )
