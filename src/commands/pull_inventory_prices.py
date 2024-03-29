
"""
Command that should run periodically (e.g. every 10 minutes).

Get the items of the inventory for which a price hasn't been set yet (e.g. they have just been parted out).
Search for their price in the local catalog cache, if the price isn't found, send a request to the Bricklink API. 
"""


from db import Session
from models import InventoryItem, ItemPrice
from backends.bricklink import Bricklink
from typing import List, Optional
from datetime import datetime
import time


MAX_ELAPSED_TIME = 5 * 60  # 5 minutes


bricklink = Bricklink.from_supervisor()


async def run():
    started_at = time.time()

    session = Session()
    inventory_items: List[InventoryItem] = \
        session.query(InventoryItem) \
            .where(InventoryItem.unit_price == None) \
            .all()

    for inventory_item in inventory_items:
        if (time.time() - started_at) >= MAX_ELAPSED_TIME:
            print(f"Max elapsed time reached")
            return

        if inventory_item.unit_price == None:
            print(f"Item {inventory_item.item_id} ({inventory_item.item_type}) {inventory_item.color.name}", end='')

            # Check if the price was already retrieved for the item
            cached_price_guide: Optional[ItemPrice] = session.query(ItemPrice) \
                .where(ItemPrice.item_id == inventory_item.item_id) \
                .where(ItemPrice.item_type == inventory_item.item_type) \
                .where(ItemPrice.color_id == inventory_item.color_id) \
                .where(ItemPrice.condition == inventory_item.condition) \
                .first()
            
            if cached_price_guide == None:
                # The price wasn't retrieved yet, we have to query it from the Bricklink API    
                price_guide = bricklink.get_price_guide(
                    inventory_item.item_type,
                    inventory_item.item_id,
                    params={
                        'color_id': inventory_item.color_id,
                        'new_or_used': inventory_item.condition,
                    })

                session.add(
                    ItemPrice(
                        item_id=inventory_item.item_id,
                        item_type=inventory_item.item_type,
                        color_id=inventory_item.color_id,
                        condition=inventory_item.condition,
                        min_price=price_guide['min_price'],
                        max_price=price_guide['max_price'],
                        avg_price=price_guide['avg_price'],
                        updated_at=datetime.now()
                    )
                )
                
                avg_price = price_guide['avg_price']
                inventory_item.unit_price = avg_price

                print(f" -> QUERIED PRICE {avg_price}")
            else:
                # The price was already retrieved and cached, use it
                inventory_item.unit_price = cached_price_guide.avg_price
                
                print(f" -> PRICE {avg_price}")

            session.commit()
