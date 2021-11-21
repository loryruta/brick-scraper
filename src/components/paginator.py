from flask.helpers import url_for
from db import Session
from sqlalchemy.sql.expression import func
from math import ceil, floor
from flask import request
import urllib.parse


class Paginator:
    def __init__(self, src_query, per_page=100, page=None):
        self.per_page = per_page
        self.src_query = src_query
        self.items_count = src_query.count()
        self.pages_count = int(ceil(self.items_count / per_page))
        self.page = page or self.get_current_page()

    def paginate(self):
        return self.src_query \
            .offset(self.page * self.per_page) \
            .limit(self.per_page)

    def is_first_page(self, page: int):
        return page == 0

    def is_last_page(self, page: int):
        return page == self.pages_count - 1

    def get_current_page(self):
        return int(request.args.get('page') or 0)
        
    def get_previous_page(self):
        return self.get_current_page() - 1

    def get_next_page(self):
        return self.get_current_page() + 1

    def get_view_pages(self):
        middle_rad = 3
        pages = []
        cur_page = self.get_current_page()
        last_page = self.pages_count - 1
        start_page = max(cur_page - middle_rad, 0)
        end_page = min(cur_page + middle_rad, last_page)

        if start_page > 0:
            pages.append(0)

        if start_page > 1:
            pages.append(-1)

        for page in range(max(cur_page - middle_rad, 0), min(cur_page + middle_rad, last_page) + 1):
            pages.append(page)

        if end_page < last_page - 1:
            pages.append(-1)

        if end_page < last_page:
            pages.append(last_page)

        return pages

    def build_page_url(self, page: int):
        args = request.args.to_dict()
        args['page'] = page
        return request.path + "?" + urllib.parse.urlencode(args)
