from dotenv import load_dotenv


load_dotenv()


from stores import bricklink
from db import Session
from models import Color, User, Order, OrderStatus, OrderPart, Part
import asyncio
from sqlalchemy.dialects.postgresql import insert


async def add_bricklink_order_item(session, order_id: int, order_item):
    item_type = order_item['item']['type']
    if item_type != 'PART':
        print(f"WARNING: Order #{order_id} - Unsupported item type: {item_type}")
        return

    item_no = order_item['item']['no']
    item_name = order_item['item']['name']

    # Searches the part in the local storage.
    part = session.query(Part) \
        .filter_by(id=item_no) \
        .first()

    if part is None:
        print(f"WARNING: Order #{order_id} - Part not found: {item_name} ({item_no})")
        return
    
    # Searches the color in the local storage.
    color = session.query(Color) \
        .filter_by(id=order_item['color_id']) \
        .first()

    if color == None:
        print(f"WARNING: Order #{order_id} - Unsupported color: {order_item['color_name']} (#{order_item['color_id']})")
        return

    values={
        'id_order': order_id,
        'id_part': part.id,
        'id_color': color.id,
        'condition': order_item['new_or_used'],
        'quantity': order_item['quantity'],
        'user_remarks': order_item['remarks'],
        'user_description': order_item['description']
    }

    session.execute(
        insert(OrderPart)
            .values(**values)
            .on_conflict_do_nothing()
        )


async def add_bricklink_order(session, user_id: int, bricklink_order_id: int):
    already_inserted = session.query(Order) \
            .filter_by(id_bricklink=bricklink_order_id) \
            .first()

    if already_inserted != None:
        print(f"Order #{already_inserted.id} (Bricklink: {already_inserted.id_bricklink}) already pulled")
        return
        
    order = bricklink.get_order(bricklink_order_id)
    shipping_address = order['shipping']['address']

    buyer_name = order['buyer_name']
    buyer_email = order['buyer_email']
    date_ordered = order['date_ordered']

    index={
        'id_user': user_id,
        'buyer_email': buyer_email,
        'buyer_name': buyer_name,
        'date_ordered': date_ordered
    }

    values={
        'status': OrderStatus.PENDING,
        'shipping_address_first_name': shipping_address['name']['first'],
        'shipping_address_last_name': shipping_address['name']['last'],
        'shipping_address_address_1': shipping_address['address1'],
        'shipping_address_address_2': shipping_address['address2'],
        'shipping_address_country_code': shipping_address['country_code'],
        'shipping_address_city': shipping_address['city'],
        'shipping_address_state': shipping_address['state'],
        'shipping_address_postal_code': shipping_address['postal_code'],
        'id_bricklink': bricklink_order_id,
        'id_brickowl': None
    }
    
    order_id = session.execute(
        insert(Order)
            .values(**index, **values)
            .on_conflict_do_update(index_elements=index.keys(), set_=values)
            .returning(Order.id)
        ).first()[0]

    print(f"Found order #{order_id} (Bricklink: #{bricklink_order_id}) {date_ordered}: {buyer_name} ({buyer_email})")

    await asyncio.gather(*[
        add_bricklink_order_item(session, order_id, order_item)
        for result in bricklink.get_order_items(bricklink_order_id)
        for order_item in result
    ])


async def add_bricklink_orders(session, user_id: int):
    print(f"Pulling bricklink orders...")
    await asyncio.gather(*[
        add_bricklink_order(session, user_id, order['order_id'])
        for order in bricklink.get_orders()
    ])


if __name__ == "__main__":
    with Session.begin() as session:
        users = session.query(User).all()
        for user in users:
            print(f"Pulling orders for user (#{user.id}): {user.email}...")
            asyncio.run(
                add_bricklink_orders(session, user.id)
            )

