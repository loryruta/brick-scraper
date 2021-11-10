import requests
from requests_oauthlib import OAuth1
import json
import os
import sqlalchemy
from models import AppliedOrder, Order, OrderPart, Part, InventoryPart, PartedOutSet, Set, User
from db import Session
from sqlalchemy import update, delete
from sqlalchemy.dialects.postgresql import insert
import asyncio


class InvalidOperation(Exception):
    pass


def apply_order(user_id: int, order: Order):
    with Session.begin() as session:
        for order_part in order.parts:
            # Checks whether an ordered part isn't in the user's inventory.
            missing_order_parts = session.query(OrderPart) \
                .filter(
                    ~session.query(InventoryPart) \
                        .filter_by(
                            id_user=user_id,
                            id_part=InventoryPart.id_part,
                            id_color=InventoryPart.id_color,
                            condition=InventoryPart.condition,
                            # TODO remarks
                        )
                ) \
                .all()

            if missing_order_parts:
                print(f"WARNING: Found {len(missing_order_parts)} missing order parts:")
                for missing_order_part in missing_order_parts:
                    print(f"- Part: {missing_order_part.id_part} - Color: #{missing_order_part.id_color} - Condition: {missing_order_part.condition}")
                
                # TODO signal that the order has a part that the inventory doesn't have!
                # Go on...

            # Deducts the matching order part quantities from inventory items.
            session.execute(
                update(InventoryPart) \
                    .join(PartedOutSet, PartedOutSet.id == InventoryPart.id_parted_out_set) \
                    .join(Set, Set.id == PartedOutSet.id_set) \
                    .where(
                        InventoryPart.id_user == user_id and
                        InventoryPart.id_part == order_part.id_part and
                        InventoryPart.id_color == order_part.id_color and
                        InventoryPart.condition == order_part.condition# and
                        #Set.id == order_part.user_remarks
                    ) \
                    .values(quantity=InventoryPart.quantity + order_part['quantity'])
            )

            # Removes items that are left to 0.
            session.execute(
                delete(InventoryPart) \
                    .where(
                        InventoryPart.id_user == user_id and
                        InventoryPart.quantity == 0
                    )
                )


def apply_orders(user_id: int):
    with Session.begin() as session:
        orders = session.query(Order) \
            .order_by(Order.date_ordered.asc()) \
            .all()
        for order in orders:
            apply_order(session, user_id, order)

