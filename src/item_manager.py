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
        inventory_log = PartedOutSet(id_user=user_id, id_set=set_id)
        session.add(inventory_log)

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


def apply_order(user: User, order: Order):
    pass
