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
    url = f"{os.environ['BRICKLINK_ENDPOINT']}/{path}"
    #print(f"URL: {url}")
    r = requests.request(method, url, auth=auth, params=params)

    if r.status_code != 200:
        raise Exception("HTTP request failed with status code: " + str(r.status_code))

    parsed_response = json.loads(r.content)

    response_code = parsed_response['meta']['code']

    if response_code != 200:
        raise InvalidRequest(f"Bricklink request failed ({response_code}):", parsed_response)

    return parsed_response['data']


def get_colors():
    return _make_request("GET", "colors", {})


def get_orders():
    return _make_request("GET", "orders", {})


def get_order_items(order_id: str):
    response = _make_request("GET", f"orders/{order_id}/items", {})
    return response


def get_order(order_id: str):
    return _make_request("GET", f"orders/{order_id}", {})


def get_subsets(item_type: str, item_no: str):
    return _make_request('GET', f"items/{item_type}/{item_no}/subsets", {})
