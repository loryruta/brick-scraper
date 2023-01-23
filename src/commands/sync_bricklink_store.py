"""
Command that should be run when the SYNC activity starts.

Get the differences between the local and the remote Bricklink store and
upload the differences to the Bricklink store to ensure it has AT LEAST the local
inventory items.
"""


import asyncio
from backends.bricklink import Bricklink, parse_bricklink_item_type, to_bricklink_item_type
from backends.bricklink_types import StoreInventory
from db import Session
from models import InventoryItem
from math import ceil
from typing import List, Optional


BATCH_SIZE = 100


bricklink = Bricklink.from_supervisor()


def match_remote_inventory_item(inventory_item: InventoryItem, remote_inventory_item: StoreInventory) -> bool:
    does_match = True
    does_match &= inventory_item.item_id == remote_inventory_item['item']['no']
    does_match &= inventory_item.item_type == parse_bricklink_item_type(remote_inventory_item['item']['type'])
    does_match &= inventory_item.color_id == remote_inventory_item['color_id']
    does_match &= inventory_item.condition == remote_inventory_item['new_or_used']
    does_match &= inventory_item.user_remarks == remote_inventory_item['remarks']
    return does_match


async def search_item_in_remote_inventory_batch(inventory_item: InventoryItem, remote_inventory_batch: List[StoreInventory]) -> Optional[StoreInventory]:
    for remote_inventory_item in remote_inventory_batch:
        if match_remote_inventory_item(inventory_item, remote_inventory_item):
            return remote_inventory_item
    return None


def is_different(inventory_item: InventoryItem, remote_inventory_item: StoreInventory):
    result = False
    result |= inventory_item.unit_price != remote_inventory_item['unit_price']
    result |= inventory_item.quantity != remote_inventory_item['quantity']
    result |= inventory_item.user_description != remote_inventory_item['description']
    return result


async def create_inventory_item(inventory_item: InventoryItem):
    # https://www.bricklink.com/v3/api.page?page=create-inventory
    bricklink.create_store_inventories(store_inventory_resources=[{
        'item': {
            'no': inventory_item.item_id,
            'type': to_bricklink_item_type(inventory_item.item_type),
        },
        'color_id': inventory_item.color_id,
        'quantity': inventory_item.quantity,
        'unit_price': 1.0,#inventory_item.unit_price,
        'new_or_used': inventory_item.condition,
        'completeness': None,
        'description': inventory_item.user_description,
        'remarks': inventory_item.user_remarks,
        'bulk': None,
        'is_retain': False,
        'is_stock_room': False,
        'my_cost': None,
        'sale_rate': None,
        'tier_quantity1': None,
        'tier_quantity2': None,
        'tier_quantity3': None,
        'tier_price1': None,
        'tier_price2': None,
        'tier_price3': None,
    }])


async def update_inventory_item(inventory_item: InventoryItem, remote_item_id: int):
    # https://www.bricklink.com/v3/api.page?page=update-inventory
    bricklink.update_store_inventory(remote_item_id, store_inventory_resource={
        'quantity': inventory_item.quantity,
        'description': inventory_item.user_description,
        'remarks': inventory_item.user_remarks,
        'bulk': None,
        'is_retain': False,
        'is_stock_room': False,
        'stock_room_id': None,
        'my_cost': None,
        'sale_rate': None,
        'tier_quantity1': None,
        'tier_quantity2': None,
        'tier_quantity3': None,
        'tier_price1': None,
        'tier_price2': None,
        'tier_price3': None,
    })


async def run():
    remote_inventory = bricklink.get_store_inventories()

    session = Session()
    inventory_items: List[InventoryItem] = session.query(InventoryItem).all()

    tasks = []

    for item in inventory_items:
        print(f"Item {item.item_id} ({item.item_type}) {item.color.name}", end='')

        if not item.is_valid_for_bricklink():
            print(f" -> NOT SYNCABLE")
            continue

        matching_remote_items: List[Optional[StoreInventory]] = \
            await asyncio.gather(*[
                search_item_in_remote_inventory_batch(item, remote_inventory[i * BATCH_SIZE:(i + 1) * BATCH_SIZE])
                for i in range(0, ceil(len(remote_inventory) / BATCH_SIZE))
            ])
        
        matching_remote_items = [ item for item in matching_remote_items if item ]

        if len(matching_remote_items) == 0:
            # There's no remote item that matches local inventory item, therefore we need to CREATE IT

            print(f" -> CREATE")

            task = asyncio.create_task(create_inventory_item(item))
            tasks += [task]
        else:
            # If more than a remote item matches (e.g. different description), keep the item whose inventory_id is less
            matching_remote_items.sort(key=lambda x: x['inventory_id'])
            matching_remote_item: StoreInventory = matching_remote_items[0]

            if is_different(item, matching_remote_item):
                # If the local item is considered to be different from remote, issue an UPDATE

                print(f" -> UPDATE ("
                    f"quantity: {item.quantity}/{matching_remote_item['quantity']}, "
                    f"unit_price: {item.unit_price}/{matching_remote_item['unit_price']}, "
                    f"user_description: \"{item.user_description}\"/\"{matching_remote_item['description']}\""
                ")")

                task = asyncio.create_task(update_inventory_item(item, matching_remote_item['inventory_id']))
                tasks += [task]
            else:
                print('')  # Nothing to do!

    if tasks:
        await asyncio.wait(tasks)
