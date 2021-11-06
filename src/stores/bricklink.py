import requests
from requests_oauthlib import OAuth1
import os
import json


class InvalidRequest(Exception):
    pass


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

    response_code = r['meta']['code']
    response_description = r['meta']['description']

    if response_code != 200:
        raise InvalidRequest("Bricklink request failed (%d): \"%s\"" % (
            response_code,
            response_description
        ))

    return r['data']


def get_colors():
    return _make_request("GET", "colors", {})


def get_item(item_type, item_no):
    return _make_request("GET", f"items/{item_type.lower()}/{item_no}", {})


#def get_subsets(item_type, item_no):
#    return _make_request("GET", f"items/{item_type}/{item_no}/subsets", {})


def _get_order_items(order_id):
    return _make_request("GET", f"orders/{order_id}/items", {})


def _parse_order_item(order_item):
    return order_item | {
        'item': {
            'ids': [order_item['item']['no']],
        },
        'condition': order_item['new_or_used']
    }


def does_part_exist(part_num):
    return True
