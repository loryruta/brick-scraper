import requests
from requests_oauthlib import OAuth1
import json
import os

import lego_reseller


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


def get_subsets(item_type, item_no):
    return _make_request("get", f"items/{item_type}/{item_no}/subsets", {})


def get_order_items(order_id):
    return _make_request("get", f"orders/{order_id}/items", {})


class Order(lego_reseller.Order):
    def __init__(self, data):
        self.order_id = data['order_id']
        self.buyer_name = data['buyer_name']
        self.date_ordered = data['date_ordered']

    def get_items(self):
        return get_order_items(self.order_id)[0]


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
