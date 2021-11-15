from re import L
from op import Registry, async_, run_
from models import InventoryPart, Part, Color
import rate_limiter
from backends.bricklink import Bricklink
from backends.brickowl import BrickOwl
from operations.local_storage import lookup_part_bo_id, retrieve_bl_part_image
from sqlalchemy import and_


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
                    unit_price=item['unit_price'],
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


def parse_condition_bo_to_local(condition):
    return condition[0].upper()


def parse_condition_local_to_bo(condition):
    return 'new' if condition == 'N' else 'usedn'


@Registry.register
class upload_inventory_to_bo:
    params = []
    rate_limiter = rate_limiter.brickowl_api

    def execute(self):
        session = self.session
        user = self.user
        
        brickowl = BrickOwl.from_user(self.user)

        items = brickowl.get_inventory_list()

        matched_inv_part_ids = []

        for item in items:
            if item['type'] != 'Part':
                print(f"WARNING: Ignoring unsupported type: \"{item['type']}\" ({item['boid']})")
                continue

            lot_id = item['lot_id']

            boid = item['boid'].split('-')[0]
            color_boid = item['boid'].split('-')[1]
            personal_note = item['personal_note']
            public_note = item['public_note']

            inv_part = session.query(InventoryPart) \
                .filter(and_(
                    InventoryPart.id_user == user.id,
                    InventoryPart.part.has(Part.id_bo == boid),
                    InventoryPart.color.has(Color.id_bo == color_boid),
                    InventoryPart.condition == parse_condition_bo_to_local(item['con']),
                    InventoryPart.user_remarks == personal_note,
                    InventoryPart.user_description == public_note,
                )) \
                .first()
            
            if inv_part == None: # The BO part hasn't been found in the local inventory, we need to remove it from BO.
                self.schedule_child(session,
                    run_(bo_inventory_delete(
                        lot_id=lot_id
                    ))
                )
                print(f"Deleting: {boid}-{color_boid} (lot: {lot_id})")
            else:
                matched_inv_part_ids.append(inv_part.id)

                # If found, updates the non-identifier data to the local inventory's value.
                # Those are like: quantity, price, etc...
                bo_item_changed = \
                    inv_part.quantity != item['qty'] or \
                    inv_part.unit_price != float(item['price'])
                
                if bo_item_changed:
                    self.schedule_child(session,
                        run_(bo_inventory_update(
                            lot_id=lot_id,
                            absolute_quantity=inv_part.quantity,
                            price=inv_part.unit_price,
                        ))
                    )

                    print(f"Updating: {boid}-{color_boid} (lot: {lot_id}) - Quantity: {item['qty']} -> {inv_part.quantity} - Price: {item['price']} -> {inv_part.unit_price}")

        # Now takes all the local parts that haven't be matched with BO items.
        missing_inv_parts = session.query(InventoryPart) \
            .filter(
                and_(
                    InventoryPart.id_user == user.id,
                    InventoryPart.id.notin_(matched_inv_part_ids),
                ),
            ) \
            .all()
        
        print(f"Missing {len(missing_inv_parts)} parts...")

        for inv_part in missing_inv_parts:
            if inv_part.part.id_bo and inv_part.color.id_bo:
                self.schedule_child(session,
                    run_(bo_inventory_create(
                        boid=inv_part.part.id_bo,
                        color_id=inv_part.color.id_bo,
                        quantity=inv_part.quantity,
                        price=inv_part.unit_price,
                        condition=parse_condition_local_to_bo(inv_part.condition)
                    )
                ))
                print(f"Create part {inv_part.part.id_bo} ({inv_part.part.name}) - color: {inv_part.color.name} ({inv_part.color.id_bo})")


@Registry.register
class bo_inventory_create:
    params = [
        'boid',
        'color_id',
        'quantity',
        'price',
        'condition',
    ]
    rate_limiter = rate_limiter.brickowl_api

    def execute(self):
        params = self.saved_op.params
        user = self.user

        BrickOwl.from_user(user) \
            .create_inventory(
                params['boid'],
                params['color_id'],
                params['quantity'],
                params['price'],
                params['condition'],
            )


@Registry.register
class bo_inventory_update:
    params = [
        'lot_id',
        'absolute_quantity',
        'price',
    ]
    rate_limiter = rate_limiter.brickowl_api

    def execute(self):
        params = self.saved_op.params
        user = self.user

        BrickOwl.from_user(user) \
            .update_inventory(
                params['lot_id'],
                params['absolute_quantity'],
                params['price'],
            )


@Registry.register
class bo_inventory_delete:
    params = [
        'lot_id'
    ]
    rate_limiter = rate_limiter.brickowl_api

    def execute(self):
        params = self.saved_op.params
        user = self.user

        BrickOwl.from_user(user) \
            .delete_inventory(params['lot_id'])

