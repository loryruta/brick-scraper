import bricklink
import brickowl


def get_orders(direction=None, status=None, filed=None):
    return [
        *bricklink.get_orders(direction),  # todo direction `in`
        *brickowl.get_orders()
    ]
