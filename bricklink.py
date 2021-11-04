import requests
from requests_oauthlib import OAuth1
import json
import os

import lego_reseller


from dotenv import load_dotenv
load_dotenv()


def _make_request(method, path, params):
    auth = OAuth1(
        os.environ['BRICKLINK_CONSUMER_KEY'],
        os.environ['BRICKLINK_CONSUMER_SECRET'],
        os.environ['BRICKLINK_TOKEN_VALUE'],
        os.environ['BRICKLINK_TOKEN_SECRET']
    )
    r = requests.request(method, f"{os.environ['BRICKLINK_ENDPOINT']}/{path}", auth=auth, params=params)

    if r.status_code != 200:
        raise Exception("HTTP request failed with status code: " + str(r.status_code))

    r = json.loads(r.content)
    if r['meta']['code'] != 200:
        raise Exception("Bricklink request failed (%d): \"%s\"" % (r['meta']['code'], r['meta']['description']))

    return r['data']


# ------------------------------------------------------------------------------------------------


def get_colors():
    return _make_request("get", "colors", {})


def get_item(item_type, item_no):
    return _make_request("get", f"items/{item_type.lower()}/{item_no}", {})


def get_subsets(item_type, item_no):
    return _make_request("get", f"items/{item_type}/{item_no}/subsets", {})


def _get_order_items(order_id):
    return _make_request("get", f"orders/{order_id}/items", {})


def _parse_order_item(order_item):
    return order_item | {
        'item': {
            'ids': [order_item['item']['no']],
        },
        'condition': order_item['new_or_used']
    }


# ------------------------------------------------------------------------------------------------


class Item(lego_reseller.Item):
    platform = "BRICKLINK"

    def __init__(self, data):
        self.bl_id = data['no']
        self.bl_alt_id = data['alternate_no']
        self.name = data['name']
        self.type = data['type']
        self.category_id = data['category_id']
        self.image_url = data['image_url']
        self.thumbnail_url = data['thumbnail_url']
        self.weight = data['weight']
        self.dim_x = data['dim_x']
        self.dim_y = data['dim_y']
        self.dim_z = data['dim_z']
        self.description = data['description']
        self.year_released = data['year_released']


class OrderItem(lego_reseller.OrderItem):
    platform = "BRICKLINK"

    def __init__(self, data):
        self.item_ids = [data['item']['no']]
        self.item_type = data['item']['type']
        self.color_bl_id = data['color_bl_id']
        self.condition = data['new_or_used']
        self.personal_note = data['remarks']
        self.quantity = data['quantity']

    def get_item(self):
        return Item(
            get_item(self.item_type, self.item_ids[0])
        )


class Order(lego_reseller.Order):
    platform = "BRICKLINK"

    def __init__(self, data):
        self.order_id = data['order_id']
        self.buyer_name = data['buyer_name']
        #self.buyer_email = data['buyer_email']
        self.date_ordered = data['date_ordered']

    def get_items(self):
        return [
            _parse_order_item(order_item)
            for order_item in _get_order_items(self.order_id)[0]
        ]


def get_orders(direction=None, status=None, filed=None):
    params = {
        'direction': direction,
        'status': status,
        'filed': filed
    }
    orders = _make_request("get", "orders", params)
    return [
        Order(order)
        for order in orders
    ]
