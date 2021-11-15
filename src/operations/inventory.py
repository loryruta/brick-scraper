from op import Registry, async_, run_
from models import InventoryPart, Part
import rate_limiter
from backends.bricklink import Bricklink
from operations.local_storage import lookup_part_bo_id, retrieve_bl_part_image


@Registry.register
class clear_inventory:
    params = []
    rate_limiter = rate_limiter.none

    def execute(self):
        session = self.session
        user = self.user

        session.query(InventoryPart) \
            .filter_by(id_user=user.id) \
            .delete()


@Registry.register
class download_bl_inventory:
    params = []
    rate_limiter = rate_limiter.bricklink_api

    def execute(self):
        session = self.session

        bl = Bricklink.from_user(self.user)
        bl_inventories = bl.get_inventories()

        for item in bl_inventories:
            item_no = item['item']['no']
            item_type = item['item']['type']
            if item_type != 'PART':
                print(f"WARNING: {item_type} will be ignored: {item_no}")
                continue

            session.add(
                InventoryPart(
                    id_user=self.user.id,
                    id_part=item_no,
                    id_color=item['color_id'],
                    condition=item['new_or_used'],
                    quantity=item['quantity'],
                    user_remarks=item['remarks'],
                    user_description=item['description'],
                )
            )


@Registry.register
class lookup_inventory_bo_ids:
    params = []
    rate_limiter = rate_limiter.none

    def execute(self):
        session = self.session

        inv_parts = session.query(InventoryPart) \
            .filter_by(id_user=self.user.id) \
            .all()
        
        self.schedule_child(session, *[
            run_(lookup_part_bo_id(part_id=inv_part.part.id))
            for inv_part in inv_parts
        ])


@Registry.register
class retrieve_inventory_bl_images:
    params = []
    rate_limiter = rate_limiter.none

    def execute(self):
        session = self.session
        user = self.user

        inv_parts = session.query(InventoryPart) \
            .filter(
                InventoryPart.id_user == user.id,
            ) \
            .all()

        self.schedule_child(session, *[
            run_(retrieve_bl_part_image(
                part_id=inv_part.part.id,
                color_id=inv_part.color.id,
            ))
            for inv_part in inv_parts
        ])
