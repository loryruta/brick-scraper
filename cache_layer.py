from peewee import *

db = SqliteDatabase("cache.db")


class BaseModel(Model):
    class Meta:
        database = db


class Order(BaseModel):
    id = AutoField()
    buyer_name = TextField()
    buyer_email = TextField()
    date_ordered = DateField()

    def get_order_items(self):
        return OrderItem.select().where(OrderItem.order_id == self.id).get()

    class Meta:
        table_name = "orders"
        indexes = (
            (('buyer_name', 'date_ordered'), True),
        )


class OrderItem(BaseModel):
    id = AutoField()
    order_id = ForeignKeyField(Order, backref="id", on_delete="CASCADE")

    # item_ids
    item_type = TextField()
    color_bl_id = IntegerField()
    condition = CharField()
    personal_note = TextField()
    quantity = IntegerField()

    def get_item(self):
        item_ids = self.get_item_ids()
        return Item.select().where(
            ((Item.item_bl_id << item_ids) | (Item.item_bl_alt_id << item_ids)) & (OrderItem.item_type == Item.type)
        ).get()

    def get_item_ids(self):
        return [
            order_item.item_id
            for order_item in OrderItemId.select().where(OrderItem.order_item_id == self.id).get()
        ]

    class Meta:
        table_name = "order_items"


class OrderItemId(BaseModel):
    order_item_id = ForeignKeyField(OrderItem, backref="id", on_delete="CASCADE")
    item_id = TextField()

    class Meta:
        table_name = "order_item_ids"
        primary_key = CompositeKey('order_item_id', 'item_id')


class Item(BaseModel):
    item_bl_id = TextField()
    item_bl_alt_id = TextField()
    type = TextField()
    name = TextField()
    category_id = IntegerField()
    image_url = TextField()
    thumbnail_url = TextField()
    weight = DoubleField()
    dim_x = DoubleField()
    dim_y = DoubleField()
    dim_z = DoubleField()
    description = DoubleField()
    year_released = IntegerField()

    class Meta:
        table_name = "items"
        primary_key = CompositeKey('item_bl_id', 'type')


class Inventory(BaseModel):
    id = AutoField()
    description = TextField()

    class Meta:
        table_name = "inventories"


class InventoryEntry(BaseModel):
    id = AutoField()
    inventory_id = ForeignKeyField(Inventory, backref="id", on_delete="CASCADE")

    item_bl_id = TextField()
    item_type = TextField()
    color_bl_id = IntegerField()
    condition = CharField()
    personal_note = TextField()
    quantity = IntegerField()

    class Meta:
        table_name = "inventory_entries"
        indexes = (
            (('inventory_id', 'item_bl_id', 'item_type', 'color_bl_id', 'condition', 'personal_note'), True),
        )


class AppliedOrder(BaseModel):
    order_id = ForeignKeyField(Order, backref="id")
    inventory_id = ForeignKeyField(Inventory, backref="id")

    class Meta:
        table_name = "applied_orders"
        primary_key = CompositeKey('order_id', 'inventory_id')


print("before creating tables")

db.create_tables([
    Order
])

print("after creating tables")
