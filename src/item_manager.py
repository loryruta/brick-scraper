import requests
from requests_oauthlib import OAuth1
import json
import os
import sqlalchemy
from models import AppliedOrder, Order, Part, InventoryPart, PartedOutSet, Set, User
from db import Session
from stores import bricklink
from sqlalchemy.dialects.postgresql import insert
import asyncio


class InvalidOperation(Exception):
    pass


def part_out_set_to_inventory(user_id: int, set_id: str, condition: str):
    matches = bricklink.get_subsets('SET', set_id)

    with Session.begin() as session:
        inventory_log = PartedOutSet(
            id_user=user_id,
            id_set=set_id
            )
        session.add(inventory_log)
        session.flush()

        session.refresh(inventory_log)  # Now I can use inventory_log.id

        print(f"inventory log id: {inventory_log.id}")

        for match in matches:
            for subset_entry in match['entries']:
                if subset_entry['item']['type'] != "PART":
                    continue

                item_no = subset_entry['item']['no']
                item_name = subset_entry['item']['name']
                color_id = subset_entry['color_id']

                values={
                    'id_part': item_no,
                    'id_color': color_id,
                    'condition': condition,
                    'quantity': subset_entry['quantity'],
                    'id_parted_out_set': inventory_log.id,
                    'id_user': user_id
                }

                # TODO handle Integrity error if a part/color isn't found

                session.execute(
                    insert(InventoryPart)
                        .values(**values)
                        .on_conflict_do_update(
                            index_elements=['id_part', 'id_color', 'condition', 'id_parted_out_set', 'id_user'],
                            set_={'quantity': InventoryPart.quantity + subset_entry['quantity']}
                        )
                    )
                #print(f"WARNING: Part \"{item_name}\" (#{item_no}) - Color: #{subset_entry['color_id']}")


def apply_order(session, user_id: int, order: Order):
    for order_part in order.parts:
        print(order_part.id_part, order_part.id_color, order_part.condition)

        inventory_parts = session.query(InventoryPart) \
            .join(PartedOutSet, PartedOutSet.id == InventoryPart.id_parted_out_set) \
            .join(Set, Set.id == PartedOutSet.id_set) \
            .filter(
                InventoryPart.id_user == user_id and
                InventoryPart.id_part == order_part.id_part and
                InventoryPart.id_color == order_part.id_color and
                InventoryPart.condition == order_part.condition# and
                #Set.id == order_part.user_remarks
            ) \
            .all()

        print(inventory_parts)
        break


def apply_orders(user_id: int):
    with Session.begin() as session:
        orders = session.query(Order) \
            .order_by(Order.date_ordered.asc()) \
            .all()
        for order in orders:
            apply_order(session, user_id, order)

