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


class Registry:
    op_list = []

    def register(rate_limiter = rate_limiter.none):
        def wrapper(op):
            op.executor = lambda session, saved_op: \
                op.Executor(session, saved_op, lambda: op.execute, rate_limiter)

            Registry.op_list.append(op)
            return op

        return wrapper


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
        def __init__(self, session, saved_op: SavedOp, execute_function: Callable, rate_limiter):
            self.session = session
            self.saved_op = saved_op
            self.execute_function = execute_function
            self.rate_limiter = rate_limiter
            
            self.params = saved_op.params
            self.user = saved_op.user

        def add_child(self, generator):
            def save(op: Op, dependency_id: Optional[int]):
                return op.save(self.session, self.saved_op.id, dependency_id)

            saved_ops = []
            for params in generator:
                saved_ops.append(
                    save(**params)
                )
            return saved_ops

        def execute(self):
            user = self.user
            rate_limiter = self.rate_limiter
            if rate_limiter.get_wait_time(user) == 0:
                rate_limiter.issue(user, self.execute_function)
                return True
            else:
                return False


def run_(operation: Op):
    """Enqueues a single operation.
    """ 
    return sync_(operation)


def sync_(*operations: Op, dependency_id: Optional[int] = None):
    """Enqueues a list of operations that will be called sequentially.
    """
    last_dependency_id = dependency_id
    for operation in operations:
        yield { 'op': operation, 'dependency_id': last_dependency_id, }
        last_dependency_id = dependency_id


def async_(*operations: Op):
    """Enqwueues a list of operations that will be called in parallel.
    """ 
    for operation in operations:
        yield { 'op': operation }


# ------------------------------------------------------------------------------------------------
# Bricklink (website)
# ------------------------------------------------------------------------------------------------


@Registry.register(rate_limiter=rate_limiter.bricklink)
class bl_retrieve_part_image:
    params = [
        'color_id',
        'part_id'
    ]

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


@Registry.register(rate_limiter=rate_limiter.bricklink)
class bl_retrieve_inventory_images:
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


@Registry.register(rate_limiter=rate_limiter.bricklink_api)
class download_inventory:
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


@Registry.register(rate_limiter=rate_limiter.brickowl_api)
class lookup_part_bo_id:
    params = [
        'part_id'
    ]

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


@Registry.register(rate_limiter=rate_limiter.brickowl_api)
class bo_upload_inventory:
    params = []

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


@Registry.register(rate_limiter=rate_limiter.brickowl_api)
class bo_inventory_create:
    params = [
    ]

    def execute(self):
        pass


@Registry.register(rate_limiter=rate_limiter.brickowl_api)
class bo_inventory_update:
    params = [
        'lot_id',
        'absolute_quantity',
        'price',
        'personal_note',
        'public_note',
    ]

    def execute(self):
        pass


@Registry.register(rate_limiter=rate_limiter.brickowl_api)
class bo_inventory_delete:
    params = []  # TODO

    def execute(self):
        pass


# ------------------------------------------------------------------------------------------------
# Local
# ------------------------------------------------------------------------------------------------


@Registry.register
class local_clear_inventory:
    def __init__(self, user_id: int):
        self.__init__(user_id)

    def on_execute(session, user: User, saved_op: SavedOp):
        session.query(InventoryPart) \
            .filter_by(id_user=user.id) \
            .delete()

