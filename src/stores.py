from typing import Generator, Iterator, Optional
from enum import Enum
from backends.bricklink import Bricklink as BricklinkAPI
from backends.brickowl import BrickOwl as BrickOwlAPI
from models import BLStore as BLStoreCredentials, BOStore as BOStoreCredentials, Store as StoreCredentials
from models import InventoryItem as LocalInventoryItem



# TODO


registry = {}


class ItemType(Enum):
    PART = 'part'
    MINIFIG = 'minifig'
    SET = 'set'


class InventoryItem:
    bl_id: Optional[str]
    bo_id: Optional[str]
    name: str
    type: str
    bl_color_id: Optional[str]
    bo_color_id: Optional[str]
    condition: str
    unit_price: float
    quantity: int
    user_remarks: Optional[str]
    user_description: Optional[str]


class Store:
    def create_item(self):
        pass


    def update_item(self):
        pass


    def delete_item(self, inventory_item: InventoryItem) -> None:
        pass


    def get_items(self) -> Iterator[InventoryItem]:
        pass


def create_gateway_from(credentials: StoreCredentials) -> Store:
    return registry[credentials.type](credentials)


def create_gateway_item_from(local_inv_item: LocalInventoryItem) -> InventoryItem:
    pass  # TODO



class Bricklink(Store):
    def __init__(self, credentials: BLStoreCredentials):
        self.api = BricklinkAPI(
            customer_key=credentials.bl_customer_key,
            customer_secret=credentials.bl_customer_secret,
            token_value=credentials.bl_token_value,
            token_secret=credentials.bl_token_secret,
        )

    #def create_item(): TODO UNSUPPORTED
    #    pass

    #def update_item(): TODO UNSUPPORTED
    #    pass

    #def delete_item(): TODO UNSUPPORTED
    #    pass

    @staticmethod
    def _parse_inventory_item(raw_inv_item) -> InventoryItem:
        inv_item = InventoryItem()
        inv_item.bl_id      = raw_inv_item['item']['no']
        inv_item.name       = raw_inv_item['item']['name']
        inv_item.type       = raw_inv_item['item']['type']
        inv_item.unit_price = raw_inv_item['unit_price']
        inv_item.quantity   = raw_inv_item['quantity']
        inv_item.condition  = raw_inv_item['new_or_used']
        return inv_item

    def get_items(self) -> Generator[InventoryItem, None, None]:
        inv_items = self.api.get_inventories()
        for inv_item in inv_items:
            yield Bricklink._parse_inventory_item(inv_item)

registry['bl_store'] = Bricklink


class BrickOwl(Store):
    def __init__(self, credentials: BOStoreCredentials):
        self.api = BrickOwlAPI(
            key=credentials.bo_key,
        )
    
    def create_item(item: InventoryItem):
        pass

    def update_item(item: InventoryItem):
        pass

    def delete_item(item: InventoryItem):
        pass

    @staticmethod
    def _parse_inventory_item(raw_inv_item) -> InventoryItem:
        pass

    def get_items(self):
        pass


registry['bo_store'] = BrickOwl

