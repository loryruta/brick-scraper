from flask import request, Blueprint, redirect, url_for, render_template, flash, g, abort
from db import Session
from models import Color, Category, Base
from components.paginator import Paginator
from routes.auth import auth_request


blueprint = Blueprint('cache', __name__)


def _show_cache_table(cached_element):
    cached_element_filter = [
        'colors',
        'categories',
        'parts',
        'sets',
    ]

    if cached_element not in cached_element_filter:
        return abort(404)

    table = Base.metadata.tables[cached_element]
    paginator = Paginator(table.c)
    with Session() as session:
        cached_elements = paginator.paginate(
                session.query(table)
                    #.order_by(table.c.id.desc())
            ) \
            .all()
        return render_template(f'cache/{cached_element}.j2',
            **{
                'paginator': paginator,
                cached_element: cached_elements
            }
        )


@blueprint.route('/cache/<cached_element>', methods=['GET'])
@auth_request
def show_cache_table(cached_element):
    print(request.endpoint, request.path)
    return _show_cache_table(cached_element)
