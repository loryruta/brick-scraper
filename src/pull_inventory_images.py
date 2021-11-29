from dotenv import load_dotenv


load_dotenv()


from typing import List
import image_storage
from db import Session
from models import Item, InventoryItem as LocalInventoryItem
import os
from sqlalchemy import or_
from urllib.request import urlretrieve
from urllib.error import HTTPError


def pull_inventory_images():
    while True:
        with Session.begin() as session:
            items: List[LocalInventoryItem] = \
                session.query(LocalInventoryItem) \
                    .filter(
                        or_(
                            LocalInventoryItem.image_pulled.is_(None),
                            LocalInventoryItem.image_pulled == 0,
                        )
                    ) \
                    .limit(100) \
                    .all()

            if len(items) == 0:
                break

            for item in items:
                image_url = image_storage.get_item_storage_url(item.item_type, item.color_id, item.item_id)
                image_path = image_storage.get_item_storage_path(item.item_type, item.color_id, item.item_id)

                if os.path.exists(image_path):
                    item.image_pulled = 1
                    continue

                try:
                    os.makedirs(os.path.dirname(image_path))
                except OSError as e:
                    pass

                bl_item_type = {
                    'part': 'PN',
                    'minifig': 'MN',
                    'set': 'SN',
                }[item.item_type]

                try:
                    bl_image_url = f"https://img.bricklink.com/ItemImage/{bl_item_type}/{item.color_id}/{item.item_id}.png"
                    urlretrieve(bl_image_url, image_path)
                except HTTPError:
                    item.image_pulled = 2
                    continue

                item.image_pulled = 1


if __name__ == "__main__":
    pull_inventory_images()
