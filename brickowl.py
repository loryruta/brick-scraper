import requests
import json
import os

import lego_reseller


from dotenv import load_dotenv
load_dotenv()


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


def _parse_order_view(order_view):
    return {
        'order_id': order_view['order_id'],
        'date_ordered': order_view['iso_order_time'],
        'buyer_name': order_view['buyer_name']
    }


# ------------------------------------------------------------------------------------------------


class OrderItem(lego_reseller.OrderItem):
    platform = "BRICKOWL"

    @staticmethod
    def _find_valid_item_ids(item_ids):
        result = []
        for _id in item_ids:
            if _id['type'] == 'design_id':
                result.append(_id['id'])

        if len(result) == 0:  # TODO MINIFIGS!
            # print(f"Couldn't find item_no for: {order_item['name']} ({order_item['type']})")
            return None

        return result

    @staticmethod
    def _item_type_to_bl(item_type):
        return item_type.upper()  # TODO

    def __init__(self, data):
        self.item_ids = self._find_valid_item_ids(data['ids'])
        self.item_type = self._item_type_to_bl(data['type'])
        self.color_bl_id = int(colors[data['color_id']]['bl_ids'][0]),
        self.condition = data['condition'][0]
        self.personal_note = data['personal_note']
        self.quantity = int(data['ordered_quantity'])

    def get_item(self):
        import bricklink

        for item_id in self.item_ids:
            return bricklink.get_item(self.item_type, item_id)


class Order(lego_reseller.Order):
    platform = "BRICKOWL"

    def __init__(self, order_id):
        self.order_id = order_id
        self.view = _parse_order_view(_get_order_view(order_id))

        self.buyer_name = self.view['buyer_name']
        #self.buyer_email = self.view['customer_email']
        self.date_ordered = self.view['date_ordered']

    def get_items(self):
        return [
            OrderItem(item)
            for item in _get_order_items(self.order_id)
        ]


def get_orders():
    return [
        Order(order['order_id'])
        for order in _get_orders()
    ]


if __name__ == "__main__":
    print(get_orders())
