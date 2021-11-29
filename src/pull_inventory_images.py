from dotenv import load_dotenv


load_dotenv()


from typing import List
import image_storage
from db import Session
from models import Item, InventoryItem as LocalInventoryItem, OrderItem
import os
from sqlalchemy import or_
from urllib.request import urlretrieve
from urllib.error import HTTPError


def retrieve_image(item_type: str, color_id: int, item_id: int) -> bool:
    image_url = image_storage.get_item_storage_url(item_type, color_id, item_id)
    image_path = image_storage.get_item_storage_path(item_type, color_id, item_id)

    if os.path.exists(image_path):
        return True

    try:
        os.makedirs(os.path.dirname(image_path))
    except OSError as e:
        pass

    bl_item_type = {
        'part': 'PN',
        'minifig': 'MN',
        'set': 'SN',
    }[item_type]

    try:
        bl_image_url = f"https://img.bricklink.com/ItemImage/{bl_item_type}/{color_id}/{item_id}.png"
        urlretrieve(bl_image_url, image_path)
    except HTTPError:
        return False

    return True


def _pull_item_images_for_inventory_items():
    while True:
        with Session.begin() as session:
            inventory_items: List[LocalInventoryItem] = \
                session.query(LocalInventoryItem) \
                    .filter(
                        or_(
                            LocalInventoryItem.image_pulled.is_(None),
                            LocalInventoryItem.image_pulled == 0,
                        )
                    ) \
                    .limit(100) \
                    .all()
                
            if len(inventory_items) == 0:
                break

            for item in inventory_items:
                item.image_pulled = 1 if retrieve_image(item.item_type, item.color_id, item.item_id) else -1


def _pull_item_images_for_order_items():
    while True:
        with Session.begin() as session:
            order_items: List[OrderItem] = \
                session.query(OrderItem) \
                    .filter(
                        or_(
                            OrderItem.image_pulled.is_(None),
                            OrderItem.image_pulled == 0,
                        )
                    ) \
                    .limit(100) \
                    .all()

            if len(order_items) == 0:
                break

            for item in order_items:
                item.image_pulled = 1 if retrieve_image(item.item_type, item.color_id, item.item_id) else -1


def pull_inventory_images():
    _pull_item_images_for_inventory_items()
    _pull_item_images_for_order_items()


if __name__ == "__main__":
    pull_inventory_images()
