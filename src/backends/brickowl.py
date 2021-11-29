from typing import List, Optional
import requests
import json
import os


class InvalidRequest(Exception):
    pass


class BrickOwl:
    def __init__(self, key: str):
        self.key = key


    def _make_request(self, method, path, **params):
        endpoint = os.environ['BRICKOWL_ENDPOINT']
        url = f"{endpoint}/{path}"
        r = requests.request(method, url, **params)

        if r.status_code != 200:
            raise InvalidRequest(f"`{method} {r.request.url}` failed with status code: {r.status_code}")

        return json.loads(r.content)


    def get_colors(self):
        return self._make_request("GET", "catalog/color_list", params={
            'key': self.key,
        })


    def get_orders(self):
        return self._make_request("GET", "order/list", params={
            'key': self.key,
        })


    def get_order_view(self, order_id: str):
        return self._make_request("GET", "order/view", params={
            'key': self.key,
            'order_id': order_id,
        })


    def get_order_items(self, order_id: str):
        return self._make_request("GET", "order/items", params={
            'key': self.key,
            'order_id': order_id,
        })


    def catalog_bulk_lookup(self, boids: List[str]):
        if len(boids) > 100:
            raise InvalidRequest(f"Couldn't catalog/bulk_lookup more than 100 BOIDs, given: ${len(boids)}")

        return self._make_request("GET", "catalog/bulk_lookup", params={
            'key': self.key,
            'boids': ",".join(boids),
        })


    def catalog_id_lookup(self, id: str, type: str, id_type: Optional[str] = None):
        return self._make_request("GET", "catalog/id_lookup", params={
            'key': self.key,
            'id': id,
            'type': type,
            'id_type': id_type,
        })

    
    def get_inventory_list(self):
        return self._make_request("GET", "inventory/list", params={
            'key': self.key,
        })


    def create_inventory(self, **args):
        return self._make_request("POST", "inventory/create", data={
            'key': self.key,
            **args,
        })


    def update_inventory(self, lot_id, **args):
        return self._make_request("POST", "inventory/update", data={
            'key': self.key,
            'lot_id': lot_id,
            **args,
        })

    
    def delete_inventory(self, lot_id):
        return self._make_request("POST", "inventory/delete", data={
            'key': self.key,
            'lot_id': lot_id,
        }) 

