import requests
from requests_oauthlib import OAuth1
import os
import json

from models import User


class InvalidRequest(Exception):
    pass


def parse_bricklink_item_type(item_type: str) -> str:
    return {
        'PART': 'part',
        'SET': 'set',
        'MINIFIG': 'minifig'
    }[item_type]


class Bricklink:
    def __init__(self, customer_key: str, customer_secret: str, token_value: str, token_secret: str):
        self.customer_key = customer_key 
        self.customer_secret = customer_secret
        self.token_value = token_value
        self.token_secret = token_secret


    def _make_request(self, method, path, params):
        endpoint = os.environ['BRICKLINK_ENDPOINT']
        auth = OAuth1(
            self.customer_key,
            self.customer_secret,
            self.token_value,
            self.token_secret
        )

        url = f"{endpoint}/{path}"

        response = requests.request(method, url, auth=auth, params=params)

        if response.status_code != 200:
            raise InvalidRequest("HTTP request failed with status code: " + str(r.status_code))

        parsed_response = json.loads(response.content)

        response_code = parsed_response['meta']['code']

        if response_code != 200:
            raise InvalidRequest(f"Bricklink request failed ({response_code}):", parsed_response)

        return parsed_response['data']


    def get_colors(self):
        return self._make_request("GET", "colors", {})


    def get_orders(self):
        return self._make_request("GET", "orders", {})


    def get_order_items(self, order_id: str):
        return self._make_request("GET", f"orders/{order_id}/items", {})


    def get_order(self, order_id: str):
        return self._make_request("GET", f"orders/{order_id}", {})


    def get_subsets(self, item_type: str, item_no: str):
        return self._make_request('GET', f"items/{item_type}/{item_no}/subsets", {})


    def get_inventories(self):
        return self._make_request('GET', f'inventories', {})


    def get_inventory(self, inventory_id: str):
        return self._make_request('GET', f'inventories/{inventory_id}', {})


    @staticmethod
    def from_user(user: User):
        return Bricklink(
            user.bl_customer_key,
            user.bl_customer_secret,
            user.bl_token_value,
            user.bl_token_secret
        )

