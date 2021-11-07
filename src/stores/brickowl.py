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


def _get_colors():
    return _make_request("get", "catalog/color_list", {})


def _get_order_items(order_id: str):
    return _make_request("get", "order/items", {'order_id': order_id})


def _get_order_view(order_id: str):
    return _make_request("get", "order/view", {'order_id': order_id})


def _get_orders(list_type=None):
    return _make_request("get", "order/list", {})


colors = _get_colors()


def _parse_order_view(order_view):
    return {
        'order_id': order_view['order_id'],
        'date_ordered': order_view['iso_order_time'],
        'buyer_name': order_view['buyer_name']
    }


def does_part_exist(part_num):
    # todo
    return True
