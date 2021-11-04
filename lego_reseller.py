

class Item:
    def __init__(self):
        self.bl_id = None
        self.bl_alt_id = None
        self.name = None
        self.type = None
        self.category_id = None
        self.image_url = None
        self.thumbnail_url = None
        self.weight = None
        self.dim_x = None
        self.dim_y = None
        self.dim_z = None
        self.description = None
        self.year_released = None


class OrderItem:
    def __init__(self):
        self.item_ids = None
        self.item_type = None
        self.color_bl_id = None
        self.condition = None
        self.personal_note = None
        self.quantity = None

    def get_item(self):
        pass


class Order:
    def __init__(self):
        self.buyer_name = None
        self.buyer_email = None
        self.date_ordered = None

    def get_items(self):
        pass
