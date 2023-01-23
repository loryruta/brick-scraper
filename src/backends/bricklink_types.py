from typing import TypedDict

class StoreInventoryItem(TypedDict):
    no: str
    name: str
    type: str
    category_id: int


class StoreInventory(TypedDict):
    inventory_id: int
    item: StoreInventoryItem
    color_id: int
    color_name: str
    quantity: int
    new_or_used: str # 'N' or 'U'
    completeness: str
    unit_price: str
    bind_id: int
    description: str
    remarks: str
    bulk: int
    is_retain: bool
    is_stock_room: bool
    stock_room_id: str
    date_created: str
    my_cost: str
    sale_rate: int
    tier_quantity1: int
    tier_quantity2: int
    tier_quantity3: int
    tier_price1: str
    tier_price2: str
    tier_price3: str
    my_weight: float

