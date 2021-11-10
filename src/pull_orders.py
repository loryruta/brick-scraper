from dotenv import load_dotenv


load_dotenv()


from backends import bricklink, brickowl
from db import Session
from models import BOColor, Color, User, Order, OrderStatus, OrderPart, Part
import asyncio
from sqlalchemy.dialects.postgresql import insert


# ------------------------------------------------------------------------------------------------
# Bricklink
# ------------------------------------------------------------------------------------------------


def add_bricklink_order_item(session, order: Order, order_item):
    item_type = order_item['item']['type']
    if item_type != 'PART':
        print(f"WARNING: Order #{order.id} - Unsupported item type: {item_type}")
        return

    item_no = order_item['item']['no']
    item_name = order_item['item']['name']

    # Color mapping
    color = session.query(Color) \
        .filter_by(id=order_item['color_id']) \
        .first()

    if color == None:
        print(f"WARNING: Order #{order.id} - Unsupported color: {order_item['color_name']} (#{order_item['color_id']})")
        return

    # Part mapping (currently taking ldraw ID)
    part = session.query(Part) \
        .filter_by(id=item_no) \
        .first()

    if part is None:
        print(f"WARNING: Order #{order.id} - Part not found: {item_name} ({item_no})")
        return

    values={
        'id_order': order.id,
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


async def add_bricklink_order(user: User, bricklink_order_id: int):
    order_data = bricklink.get_order(bricklink_order_id)
    shipping_address = order_data['shipping']['address']

    buyer_name = order_data['buyer_name']
    buyer_email = order_data['buyer_email']
    date_ordered = order_data['date_ordered']

    index={
        'id_user': user.id,
        'buyer_email': buyer_email,
        'buyer_name': buyer_name,
        'date_ordered': date_ordered
    }

    values={
        'status': OrderStatus.PENDING,  # TODO STATUS MAPPING!
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
    
    order_exists = False

    with Session.begin() as session:
        order_exists = session.query(Order.id) \
            .filter_by(id_bricklink=bricklink_order_id) \
            .first() != None
        
        order = session.execute(
            insert(Order)
                .values(**index, **values)
                .on_conflict_do_update(index_elements=index.keys(), set_=values)
                .returning(Order)
            ).first()

    print(f"Order #{order.id} (Bricklink ID: #{bricklink_order_id}) {date_ordered}: {buyer_name} ({buyer_email})%s" % (" - already inserted" if order_exists else "",))

    if not order_exists:
        with Session.begin() as session:
            for result in bricklink.get_order_items(bricklink_order_id):
                for order_item in result:
                    add_bricklink_order_item(session, order, order_item)


async def add_bricklink_orders(user: User):
    await asyncio.gather(*[
        add_bricklink_order(user, order['order_id'])
        for order in bricklink.get_orders()
    ])


# ------------------------------------------------------------------------------------------------
# Brickowl
# ------------------------------------------------------------------------------------------------


def parse_brickowl_order_item_condition(condition: str):
    return condition.upper()[0]


def add_brickowl_order_item(session, order: Order, order_item):
    item_type = order_item['type']

    if item_type != "Part":
        print(f"WARNING: Order #{order.id} - Unsupported item type: {item_type}")
        return 

    # Color mapping
    bo_color_id = order_item['color_id']
    bo_color = session.query(BOColor) \
        .filter_by(id=bo_color_id) \
        .first()

    if not bo_color:
        print(f"WARNING: Order #{order.id} - Unsupported BO color #{bo_color_id}. The color probably didn't had a direct BL color mapping.")
        return

    # Part mapping (currently taking ldraw ID)
    def search_id(id_type: str):
        for item_id in order_item['ids']:
            if item_id['type'] == id_type:
                return item_id['id']
        return None

    part = None
    for id_type in ['ldraw', 'design_id']:
        part_id = search_id(id_type)
        if part_id != None:
            part = session.query(Part) \
                .filter_by(id=part_id) \
                .first()
            if part != None:
                break

    if part is None:
        print(f"WARNING: Order #{order.id} - Unsupported BO item \"{order_item['name']}\" (#{order_item['boid']}) - {order_item['image_small']}")
        return

    # OK
    values={
        'id_order': order.id,
        'id_part': part.id,
        'id_color': bo_color.color.id,
        'condition': parse_brickowl_order_item_condition(order_item['condition']),
        'quantity': order_item['ordered_quantity'],
        'user_remarks': order_item['personal_note'],
        'user_description': order_item['public_note']
    }

    session.execute(
        insert(OrderPart)
            .values(**values)
            .on_conflict_do_nothing()
        )


async def add_brickowl_order(user: User, brickowl_order_id: str):
    order_view = brickowl.get_order_view(brickowl_order_id)

    buyer_name = order_view['customer_username']
    buyer_email = order_view['customer_email']
    date_ordered = order_view['iso_order_time']

    index={
        'id_user': user.id,
        'buyer_email': buyer_email,
        'buyer_name': buyer_name,
        'date_ordered': date_ordered
    }

    values={
        'status': OrderStatus.PENDING,  # TODO STATUS MAPPING!
        'shipping_address_first_name': order_view['ship_first_name'],
        'shipping_address_last_name': order_view['ship_last_name'],
        'shipping_address_address_1': order_view['ship_street_1'],
        'shipping_address_address_2': order_view['ship_street_2'],
        'shipping_address_country_code': order_view['ship_country_code'],
        'shipping_address_city': order_view['ship_city'],
        'shipping_address_state': order_view['ship_region'],
        'shipping_address_postal_code': order_view['ship_post_code'],
        'id_bricklink': None,
        'id_brickowl': brickowl_order_id
    }
    
    order_exists = False

    with Session.begin() as session:
        order_exists = session.query(Order.id) \
            .filter_by(id_brickowl=brickowl_order_id) \
            .first() != None
        
        order = session.execute(
            insert(Order)
                .values(**index, **values)
                .on_conflict_do_update(index_elements=index.keys(), set_=values)
                .returning(Order)
            ).first()

    print(f"Order #{order.id} (Brickowl ID: #{brickowl_order_id}) {date_ordered}: {buyer_name} ({buyer_email})%s" % (" - already inserted" if order_exists else "",))

    if not order_exists:
        with Session.begin() as session:
            for order_item in brickowl.get_order_items(brickowl_order_id):
                add_brickowl_order_item(session, order, order_item)


async def add_brickowl_orders(user: User):
    await asyncio.gather(*[
        add_brickowl_order(user, order['order_id'])
        for order in brickowl.get_orders()
    ])


# ------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    with Session.begin() as session:
        users = session.query(User) \
            .all()
        for user in users:
            print("Pulling BL orders...")
            asyncio.run(add_bricklink_orders(user))

            print("Pulling BO orders...")
            asyncio.run(add_brickowl_orders(user))

