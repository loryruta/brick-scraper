import api_layer as api
import cache_layer as cache


def clear_orders():
    cache.Order.delete()


def pull_orders():
    orders = api.get_orders()
    for order in orders:
        order_id = cache.Order.create(
            buyer_name=order.buyer_name,
            buyer_email=None,
            date_ordered=order.date_ordered
        )

        print(order_id)
        exit(1)

        if order_id is not None:
            items = [
                cache.OrderItem(order_id=order_id, **item.__dict__)
                for item in order.get_items()
            ]
            cache.OrderItem.bulk_create(items)


def get_orders():
    return cache.Order.select()


if __name__ == "__main__":
    clear_orders()
    pull_orders()
