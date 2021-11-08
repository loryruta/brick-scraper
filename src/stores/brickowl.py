import requests
import json
import os


def _make_request(method, path, params):
    params['key'] = os.environ['BRICKOWL_KEY']

    url = os.environ['BRICKOWL_ENDPOINT'] + "/" + path
    r = requests.request(method, url, params=params)

    if r.status_code != 200:
        raise Exception(f"`{method} {r.request.url}` failed with status code: {r.status_code}")

    return json.loads(r.content)


def get_colors():
    return _make_request("get", "catalog/color_list", {})


def get_orders():
    return _make_request("get", "order/list", {})


def get_order_view(order_id: str):
    return _make_request("get", "order/view", {'order_id': order_id})


def get_order_items(order_id: str):
    return _make_request("get", "order/items", {'order_id': order_id})

