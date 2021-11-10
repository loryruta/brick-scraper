from db import Session
from sqlalchemy.sql.expression import func
from math import ceil
from flask import request


class Paginator:
    def __init__(self, table, per_page=100, page=None):
        with Session() as session:
            self.per_page = per_page
            self.items_count = session.query(func.count(table.id)).scalar()
            self.pages_count = int(ceil(self.items_count / per_page))
            self.page = page or self.get_current_page()

    def paginate(self, query):
        return query \
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
