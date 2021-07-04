import requests
import json
import os

import lego_reseller


def _make_request(method, path, params):
    params['key'] = os.environ['BRICKOWL_KEY']

    url = os.environ['BRICKOWL_ENDPOINT'] + "/" + path
    r = requests.request(method, url, params=params)

    if r.status_code != 200:
        raise Exception(f"`{method} {r.request.url}` failed with status code: {r.status_code}")

    return json.loads(r.content)


def _get_colors():
    return _make_request("get", "catalog/color_list", {})


def _get_order_items(order_id):
    return _make_request("get", "order/items", {'order_id': order_id})


def _get_order_view(order_id):
    return _make_request("get", "order/view", {'order_id': order_id})


def _get_orders(list_type=None):
    return _make_request("get", "order/list", {})


# ------------------------------------------------------------------------------------------------ Brickowl -> Bricklink

colors = _get_colors()


def _parse_order_item(order_item):
    item_ids = []
    for _id in order_item['ids']:
        if _id['type'] == 'design_id':
            item_ids.append(_id['id'])

    if len(item_ids) == 0:  # TODO MINIFIGS!
        #print(f"Couldn't find item_no for: {order_item['name']} ({order_item['type']})")
        return None

    return {
        'item': {
            'ids': item_ids,
            'type': order_item['type'].upper(),
            'name': order_item['name']
        },
        'quantity': int(order_item['ordered_quantity']),
        'color_id': int(colors[order_item['color_id']]['bl_ids'][0]),
        'condition': order_item['condition'][0],  # Just get the first character (N or U)
        'remarks': order_item['personal_note']
    }


def _parse_order_view(order_view):
    return {
        'order_id': order_view['order_id'],
        'date_ordered': order_view['iso_order_time'],
        'buyer_name': order_view['buyer_name']
    }


# ------------------------------------------------------------------------------------------------


class Order(lego_reseller.Order):
    def __init__(self, order_id):
        self.platform = "brickowl"

        self.order_id = order_id
        self.data = _parse_order_view(_get_order_view(order_id))

        self.buyer_name = self.data['buyer_name']
        self.date_ordered = self.data['date_ordered']

    def get_items(self):
        return [
            parsed_item
            for parsed_item in (
                _parse_order_item(item)
                for item in _get_order_items(self.order_id)
            )
            if parsed_item is not None
        ]


def get_orders():
    return [
        Order(order['order_id'])
        for order in _get_orders()
    ]


if __name__ == "__main__":
    print(get_orders())
