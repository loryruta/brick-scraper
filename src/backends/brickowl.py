from typing import Optional
import requests
import json
import os

from models import User


class InvalidRequest(Exception):
    pass


class BrickOwl:
    def __init__(self, key: str):
        self.key = key


    def _make_request(self, method, path, params):
        params['key'] = self.key

        endpoint = os.environ['BRICKOWL_ENDPOINT']
        url = f"{endpoint}/{path}"
        r = requests.request(method, url, params=params)

        if r.status_code != 200:
            raise InvalidRequest(f"`{method} {r.request.url}` failed with status code: {r.status_code}")

        return json.loads(r.content)


    def get_colors(self):
        return self._make_request("GET", "catalog/color_list", {})


    def get_orders(self):
        return self._make_request("GET", "order/list", {})


    def get_order_view(self, order_id: str):
        return self._make_request("GET", "order/view", {'order_id': order_id})


    def get_order_items(self, order_id: str):
        return self._make_request("GET", "order/items", {'order_id': order_id})


    def catalog_id_lookup(self, id: str, type: str, id_type: Optional[str] = None):
        return self._make_request("GET", "catalog/id_lookup", {
            'id': id,
            'type': type,
            'id_type': id_type
        })

    
    def get_inventory_list(self):
        return self._make_request("GET", "inventory/list", {})
        

    @staticmethod
    def from_user(user: User):
        return BrickOwl(user.bo_key)

