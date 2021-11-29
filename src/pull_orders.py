from typing import Dict
from enum import Enum
from dotenv import load_dotenv


load_dotenv()


from db import Session
from models import Color, User, Order, OrderItem, OrderStatus, Item
import asyncio
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import and_
from backends.bricklink import Bricklink as BricklinkAPI
from backends.brickowl import BrickOwl as BrickOwlAPI


def _norm_bl_item_type(type: str):
    return {
        'PART': 'part',
        'MINIFIG': 'minifig',
        'SET': 'set',
    }[type]


def _norm_bo_item_type(item_type: str):
    return {
        'Part': 'part',
        'Minifigure': 'minifig',
        'Set': 'set',
    }[item_type]  # TODO FIX-ME What if type is not found?


def _norm_bl_condition(condition: str):
    return condition


def _norm_bo_condition(condition: str):
    return condition.upper()[0]


def _norm_bl_order_status(status: str):
    _map = {
        'pending': OrderStatus.PENDING,
        'updated': OrderStatus.PENDING,
        'processing': OrderStatus.PROCESSING,
        "ready": OrderStatus.PROCESSING,
        'paid': OrderStatus.PAID,
        'packed': OrderStatus.PACKED,
        "shipped": OrderStatus.SHIPPED,
        "received": OrderStatus.RECEIVED,
        "completed": OrderStatus.RECEIVED,
        "purged": OrderStatus.PURGED,
        "cancelled": OrderStatus.CANCELLED,
    }

    status = status.lower()
    ret = _map[status] if status in _map else OrderStatus.UNKNOWN
    return ret


def _norm_bo_order_status(status: str):
    _map = {
        'Pending': OrderStatus.PENDING,
        'Payment Submitted': OrderStatus.PAID,
        'Payment Received': OrderStatus.PAID,
        'Processing': OrderStatus.PAID,
        "Processed": OrderStatus.PAID,
        "Shipped": OrderStatus.SHIPPED,
        "Received": OrderStatus.RECEIVED,
        "On Hold": OrderStatus.ON_HOLD,
        "Cancelled": OrderStatus.CANCELLED,
    }
    return _map[status] if status in _map else OrderStatus.UNKNOWN


class OrderPuller:
    def __init__(self, user_id: int):
        self.user_id = user_id

        with Session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            self.bl_api = BricklinkAPI(user.bl_customer_key, user.bl_customer_secret, user.bl_token_value, user.bl_token_secret)
            self.bo_api = BrickOwlAPI(user.bo_key)


    def _add_bl_order_item(self, session, order_id: int, order_item: Dict):
        item_type = _norm_bl_item_type(order_item['item']['type'])
        item_id = order_item['item']['no']
        item_name = order_item['item']['name']
        condition = _norm_bl_condition(order_item['new_or_used'])
        quantity = int(order_item['quantity'])
        user_remarks = order_item['remarks'] or ''
        user_description = order_item['description'] or ''

        # Color mapping
        color = session.query(Color) \
            .filter_by(id=order_item['color_id']) \
            .first()

        if color == None:
            print(f"WARNING: Order #{order_id} - Unsupported color: {order_item['color_name']} (#{order_item['color_id']})")
            return  # TODO maybe throw an exception?

        # Item mapping (currently taking ldraw ID)
        item = session.query(Item) \
            .filter_by(
                type=item_type,
                id=item_id
            ) \
            .first()

        if item is None:
            print(f"WARNING: Order #{order_id} - Unsupported item: {item_id} ({item_type})")
            return

        values={
            'order_id': order_id,
            'item_id': item_id,
            'item_type': item_type,
            'color_id': color.id,
            'condition': condition,
            'quantity': quantity,
            'user_remarks': user_remarks,
            'user_description': user_description
        }

        session.execute(
            insert(OrderItem)
                .values(**values)
                .on_conflict_do_nothing()
            )


    def _add_bl_order(self, session, bl_order_id: int):
        order_data = self.bl_api.get_order(bl_order_id)
        shipping_address = order_data['shipping']['address']

        buyer_name = order_data['buyer_name']
        buyer_email = order_data['buyer_email']
        date_ordered = order_data['date_ordered']

        index={
            'user_id': self.user_id,
            'buyer_email': buyer_email,
            'buyer_name': buyer_name,
            'date_ordered': date_ordered
        }

        values={
            'status': _norm_bl_order_status(order_data['status']),
            'shipping_address_first_name': shipping_address['name']['first'],
            'shipping_address_last_name': shipping_address['name']['last'],
            'shipping_address_address_1': shipping_address['address1'],
            'shipping_address_address_2': shipping_address['address2'],
            'shipping_address_country_code': shipping_address['country_code'],
            'shipping_address_city': shipping_address['city'],
            'shipping_address_state': shipping_address['state'],
            'shipping_address_postal_code': shipping_address['postal_code'],
            'bl_id': bl_order_id,
            'bo_id': None
        }
        
        does_order_exist = \
            session.query(Order.id) \
                .filter_by(bl_id=bl_order_id) \
                .first() != None
        
        order = session.execute(
            insert(Order)
                .values(**index, **values)
                .on_conflict_do_update(index_elements=index.keys(), set_=values)
                .returning(Order)
            ).first()

        print(f"Order #{order.id} (BL ID: #{bl_order_id}) {date_ordered}: {buyer_name} ({buyer_email})%s" % (" - already inserted" if does_order_exist else "",))

        if not does_order_exist:
            for result in self.bl_api.get_order_items(bl_order_id):
                for order_item in result:
                    self._add_bl_order_item(session, order.id, order_item)


    def pull_bl_orders(self):
        for order in self.bl_api.get_orders():
            with Session.begin() as session:
                self._add_bl_order(session, order['order_id'])


    def _add_bo_order_item(self, session, order_id: int, order_item: Dict):
        item_type = _norm_bo_item_type(order_item['type'])
        item_name = order_item['name']
        boid: str = order_item['boid']
        item_boid = boid.split('-')[0]
        condition = _norm_bo_condition(order_item['condition']) 
        quantity = order_item['ordered_quantity']
        user_remarks = order_item['personal_note'] or ''
        user_description = order_item['public_note'] or ''

        # Color mapping
        bo_color_id = order_item['color_id']
        color = session.query(Color) \
            .filter_by(bo_id=bo_color_id) \
            .first()

        if not color:
            print(f"WARNING: Order #{order_id} - Color not found from BO ID: {bo_color_id}")
            return  # TODO throw an exception? 

        item = session.query(Item) \
            .filter(and_(
                Item.bo_id == item_boid,
                Item.type == item_type,
            )) \
            .first()

        if item is None:
            print(f"WARNING: Order #{order_id} - Item not found from BO ID: {boid} ({item_type})")
            return

        item_id = item.id

        values={
            'order_id': order_id,
            'item_id': item_id,
            'item_type': item_type,
            'color_id': color.id,
            'condition': condition,
            'quantity': quantity,
            'user_remarks': user_remarks,
            'user_description': user_description
        }

        session.execute(
            insert(OrderItem)
                .values(**values)
                .on_conflict_do_nothing()
            )


    def _add_bo_order(self, session, bo_order_id: str):
        order_view = self.bo_api.get_order_view(bo_order_id)

        buyer_name = order_view['customer_username']
        buyer_email = order_view['customer_email']
        date_ordered = order_view['iso_order_time']

        index={
            'user_id': self.user_id,
            'buyer_email': buyer_email,
            'buyer_name': buyer_name,
            'date_ordered': date_ordered
        }

        values={
            'status': _norm_bo_order_status(order_view['status']),
            'shipping_address_first_name': order_view['ship_first_name'],
            'shipping_address_last_name': order_view['ship_last_name'],
            'shipping_address_address_1': order_view['ship_street_1'],
            'shipping_address_address_2': order_view['ship_street_2'],
            'shipping_address_country_code': order_view['ship_country_code'],
            'shipping_address_city': order_view['ship_city'],
            'shipping_address_state': order_view['ship_region'],
            'shipping_address_postal_code': order_view['ship_post_code'],
            'bl_id': None,
            'bo_id': bo_order_id
        }
    
        does_order_exist = \
            session.query(Order.id) \
                .filter_by(bo_id=bo_order_id) \
                .first() != None
        
        order = session.execute(
            insert(Order)
                .values(**index, **values)
                .on_conflict_do_update(index_elements=index.keys(), set_=values)
                .returning(Order)
            ).first()

        print(f"Order #{order.id} (BO ID: #{bo_order_id}) {date_ordered}: {buyer_name} ({buyer_email})%s" % (" - already inserted" if does_order_exist else "",))

        if not does_order_exist:
            for order_item in self.bo_api.get_order_items(bo_order_id):
                self._add_bo_order_item(session, order.id, order_item)


    def pull_bo_orders(self):
        for order in self.bo_api.get_orders():
            with Session.begin() as session:
                self._add_bo_order(session, order['order_id'])


    def pull_orders(self):
        asyncio.run
        self.pull_bl_orders()
        self.pull_bo_orders()


if __name__ == "__main__":
    with Session.begin() as session:
        users = session.query(User).all()

        for user in users:
            order_puller = OrderPuller(user.id)
            order_puller.pull_orders()

