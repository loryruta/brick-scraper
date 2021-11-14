from models import Color, Op as SavedOp, Part, User, InventoryPart
from typing import Callable, Dict, Optional, Type
from backends.bricklink import Bricklink
from backends.brickowl import BrickOwl
import rate_limiter
from db import Session
from sqlalchemy import and_, func
from sqlalchemy.dialects.postgresql import insert
import image_handler
import os
import urllib.request
from urllib.error import HTTPError
from functools import wraps


class Registry:
    _by_name = {}

    def register(operation_class):
        required_params = operation_class.params \
            if hasattr(operation_class, 'params') else []

        rate_limiter_ = operation_class.rate_limiter \
            if hasattr(operation_class, 'rate_limiter') else rate_limiter.none

        class DecoredOperation(Op):
            def __init__(self, user_id, **params):
                operation_name = operation_class.__name__
                self.__class__.__name__ = operation_name

                missing_params = \
                    [key for key in required_params if key not in params.keys()]
                if missing_params:
                    raise TypeError(f"Operation {operation_class.__name__} misses required parameters:", missing_params)

                super().__init__(user_id, **params)

            @staticmethod
            def create_executor(session, saved_op: SavedOp):
                return Op.Executor(session, saved_op, operation_class, rate_limiter_)
        
        Registry._by_name[operation_class.__name__] = DecoredOperation
        #print(f"Registered operation #{len(Registry._list)}: {operation_class.__name__}")

        return DecoredOperation


class Op:
    def __init__(self, user_id: int, **params):
        self.user_id = user_id
        self.params = params

    def save(self, session, parent_id: Optional[int] = None, dependency_id: Optional[int] = None):
        saved_op = SavedOp(
            id_user=self.user_id,
            type=self.__class__.__name__,
            id_parent=parent_id,
            id_dependency=dependency_id,
            params=self.params,
        )
        session.add(saved_op)
        session.flush([saved_op])
        session.refresh(saved_op)
        return saved_op

    class Executor:
        def __init__(self, session, saved_op: SavedOp, operation_class, rate_limiter):
            self.session = session
            self.saved_op = saved_op
            self.operation_class = operation_class
            self.rate_limiter = rate_limiter
            
            self.params = saved_op.params
            self.user = saved_op.user

            self.generated_children = []


        def add_child(self, generator):
            def save(op: Op, dependency_id: Optional[int]):
                return op.save(self.session, self.saved_op.id, dependency_id)

            self.generated_children = []
            params = next(generator)
            try:
                while True:
                    saved_op = save(**params)
                    self.generated_children.append(saved_op)

                    params = generator.send(saved_op)
            except StopIteration:
                pass

            return self.generated_children


        def execute(self):
            user = self.user
            rate_limiter = self.rate_limiter
            if rate_limiter.get_wait_time(user) == 0:
                rate_limiter.issue(user, lambda: self.operation_class.execute(self))
                return True
            else:
                return False


def run_(operation: Op):
    """Enqueues a single operation.
    """ 
    return sync_(operation)


def sync_(*operations: Op, dependency_id: Optional[int] = None):
    last_dependency_id = dependency_id
    for operation in operations:
        saved_op = (yield { 'op': operation, 'dependency_id': last_dependency_id, })
        last_dependency_id = saved_op.id


def async_(*operations: Op):
    """Enqwueues a list of operations that will be called in parallel.
    """ 
    for operation in operations:
        saved_op = yield { 'op': operation }


def schedule(session, generator):
    def save(op: Op, dependency_id: int):
        return op.save(session, None, dependency_id)

    params = next(generator)
    try:
        while True:
            saved_op = save(**params)
            params = generator.send(saved_op)
    except StopIteration:
        pass


# ------------------------------------------------------------------------------------------------
# Bricklink (website)
# ------------------------------------------------------------------------------------------------


@Registry.register
class bl_retrieve_part_image:
    params = [
        'color_id',
        'part_id'
    ]

    rate_limiter = rate_limiter.bricklink

    def execute(self):
        color_id = self.saved_op.params['color_id']
        part_id = self.saved_op.params['part_id']

        img_path = image_handler.get_part_image_storage_path(color_id, part_id)
        img_url = image_handler.get_part_image_url(color_id, part_id)

        if os.path.exists(img_path):
            return

        try:
            os.makedirs(os.path.dirname(img_path))
        except OSError:
            pass

        try:
            bricklink_img_url = f"https://img.bricklink.com/ItemImage/PN/{color_id}/{part_id}.png"
            urllib.request.urlretrieve(bricklink_img_url, img_path)
            return img_url
        except HTTPError:
            pass

        # TODO still not found


@Registry.register
class bl_retrieve_inventory_images:
    params = []
    rate_limiter = rate_limiter.bricklink

    def execute(self):
        session = self.session
        bricklink = Bricklink.from_user(self.user)
        for item in bricklink.get_inventories():
            session.add(
                InventoryPart(
                    id_user=self.user.id,
                    id_part=item['item']['no'],
                    id_color=item['color_id'],
                    condition=item['condition'],
                    quantity=item['quantity'],
                    user_remarks=item['remarks'],
                    user_description=item['description'],
                )
            )


# ------------------------------------------------------------------------------------------------
# Bricklink API
# ------------------------------------------------------------------------------------------------


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


# ------------------------------------------------------------------------------------------------
# BrickOwl API
# ------------------------------------------------------------------------------------------------


@Registry.register
class lookup_inventory_bo_ids:
    params = []

    def execute(self):
        parts = self.session.query(Part) \
            .filter_by(id_user=self.user.id) \
            .all()
        
        self.add_child(
            async_(*[
                lookup_part_bo_id(part_id=part.id)
                for part in parts
            ])
        )


@Registry.register
class lookup_part_bo_id:
    params = [
        'part_id'
    ]
    rate_limiter = rate_limiter.brickowl_api

    def execute(self):
        saved_op = self.saved_op

        part_id = saved_op.params['part_id']
        part = self.session.query(Part) \
            .filter_by(id=part_id) \
            .first()

        brickowl = BrickOwl.from_user(self.user)
        boids = brickowl.catalog_id_lookup(part_id, 'Part')['boids']
        if len(boids) == 0:
            print(f"WARNING: Part \"{part.name}\" ({part.id}) couldn't be matched with BO.")
            return
        
        boid = boids[0].split('-')[0]  # Trims color (after - on BOIDs)
        part.id_bo = boid


@Registry.register
class upload_inventory_to_bo:
    params = []
    rate_limiter = rate_limiter.brickowl_api

    def execute(self):
        session = self.session
        user = self.user
        
        brickowl = BrickOwl.from_user(self.user)

        items = brickowl.get_inventory_list()
        items = {
            (item['boid'], item)
            for item in items
            if items['type'] == 'Part'
        }

        for item in items:
            lot_id = item['lot_id']
            bo_id = item['boid'].split('-')[0]
            color_id = item['boid'].split('-')[1]
            condition = item['condition']
            personal_note = item['personal_note']

            inventory_part = session.query(InventoryPart) \
                .filter(and_(
                    InventoryPart.id_user == user.id,
                    InventoryPart.part.id_bo == bo_id,
                    InventoryPart.color.id_bo == color_id,
                    InventoryPart.condition == condition[0].uppercase(),
                    InventoryPart.user_remarks == personal_note
                )) \
                .first()

            # The BO part hasn't been found in the local inventory, we need to remove it.
            if inventory_part is None:
                self.add_child(run_(
                    bo_inventory_delete(lot_id=lot_id)
                ))
                print(f"Delete part {item['boid']}")
            
            # If found, updates the non-identifier data to the local inventory's value.
            # Those are like: quantity, price, description...
            else:
                remote_changed = \
                    inventory_part.quantity != item['quantity'] or \
                    inventory_part.description != item['public_note'] #or \
                    # TODO inventory_part.price != item['price']
                
                if remote_changed:
                    self.add_child(run_(
                        bo_inventory_update(
                            lot_id=lot_id,
                            absolute_quantity=inventory_part.quantity,
                            #price=1.00, TODO
                            personal_note=inventory_part.user_remarks,
                            public_note=inventory_part.user_description,
                        )
                    ))
                    print(f"Update quantity of part {item['boid']}: {inventory_part.quantity} -> {item['quantity']}")

        # Now takes all the parts that haven't been matched with remotes' and creates them.
        missing_inventory_parts = session.query(InventoryPart) \
            .filter(and_(
                InventoryPart.id_user == user.id,
                func.concat(InventoryPart.part.id_bo, '-', InventoryPart.color.id_bo) \
                    .notin(items.keys())
            )) \
            .all()
        
        print(f"Missing {len(missing_inventory_parts)} parts...")

        for inventory_part in missing_inventory_parts:
            if inventory_part.id_bo and inventory_part.color.id_bo:
                self.add_child(run_(
                    bo_inventory_create(
                        boid=inventory_part.part.id_bo,
                        color_id=inventory_part.color.id_bo,
                        quantity=inventory_part.quantity,
                        price=1.00,#inventory_part.price,
                        condition=inventory_part.condition
                    )
                ))
                print(f"Create part {inventory_part.id_bo} ({inventory_part.part.name}) - color: {inventory_part.color.name} ({inventory_part.color.id_bo})")


@Registry.register
class bo_inventory_create:
    params = []
    rate_limiter = rate_limiter.brickowl_api

    def execute(self):
        pass


@Registry.register
class bo_inventory_update:
    params = [
        'lot_id',
        'absolute_quantity',
        'price',
        'personal_note',
        'public_note',
    ]
    rate_limiter = rate_limiter.brickowl_api

    def execute(self):
        pass


@Registry.register
class bo_inventory_delete:
    params = []  # TODO
    rate_limiter = rate_limiter.brickowl_api

    def execute(self):
        pass


# ------------------------------------------------------------------------------------------------
# Local
# ------------------------------------------------------------------------------------------------

