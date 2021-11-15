from re import M
from models import Color, Op as SavedOp, op_dependencies_table, Part, User, InventoryPart
from typing import Callable, Dict, Optional, Type, List
from backends.bricklink import Bricklink
from backends.brickowl import BrickOwl
import rate_limiter
from sqlalchemy import and_, func, any_


class Registry:
    _by_name = {}

    def register(operation_class):
        required_params = operation_class.params \
            if hasattr(operation_class, 'params') else []

        rate_limiter_ = operation_class.rate_limiter \
            if hasattr(operation_class, 'rate_limiter') else rate_limiter.none

        class DecoratedOperation(Op):
            def __init__(self, **params):
                operation_name = operation_class.__name__
                self.__class__.__name__ = operation_name

                missing_params = \
                    [key for key in required_params if key not in params.keys()]
                if missing_params:
                    raise TypeError(f"Operation {operation_class.__name__} misses required parameters:", missing_params)

                super().__init__(**params)

            @staticmethod
            def create_executor(session, saved_op: SavedOp):
                return Op.Executor(session, saved_op, operation_class, rate_limiter_)
        
        Registry._by_name[operation_class.__name__] = DecoratedOperation
        #print(f"Registered operation #{len(Registry._list)}: {operation_class.__name__}")

        return DecoratedOperation


class Op:
    def __init__(self, **params):
        self.params = params


    def save(self, session, user_id: int, dependencies: List[int], parent_id: Optional[int]):
        saved_op = SavedOp(
            id_user=user_id,
            type=self.__class__.__name__,
            id_parent=parent_id,
            params=self.params,
        )
        
        session.add(saved_op)
        session.flush([saved_op])
        session.refresh(saved_op)

        if dependencies:
            session.execute(
                op_dependencies_table.insert() \
                    .values([
                        { 'id_op': saved_op.id, 'id_dependency': id_dep, }
                        for id_dep in dependencies
                    ])
            )

        return saved_op


    class Executor:
        def __init__(self, session, saved_op: SavedOp, operation_class, rate_limiter):
            self.session = session
            self.saved_op = saved_op
            self.operation_class = operation_class
            self.rate_limiter = rate_limiter
            
            self.params = saved_op.params
            self.user = saved_op.user


        def schedule_child(self, session, *tree, dependencies: List[int] = []):
            for f in tree:
                f(session, self.user.id, dependencies, self.saved_op.id)

        
        def execute(self):
            user = self.user
            rate_limiter = self.rate_limiter

            wait_time = rate_limiter.get_wait_time(user)

            if wait_time == 0:
                rate_limiter.issue(
                    user,
                    lambda: self.operation_class.execute(self)
                )

            return wait_time


@Registry.register
class group:
    params = []
    rate_limiter = rate_limiter.none

    def execute(self):
        pass


def run_(op: Op):
    def save(session, user_id: int, dependencies: List[int], parent_id: Optional[int]):
        subject = op.save(session, user_id, dependencies, parent_id)
        return [subject]
    return save


def group_(*tree):
    def save(session, user_id: int, dependencies: List[int], parent_id: Optional[int]):
        subject = \
            run_(group())(session, user_id, dependencies, parent_id)[0]
        for f in tree:
            f(session, user_id, dependencies, subject.id)

        return [subject]
    return save


def sync_(*tree):
    def save(session, user_id: int, dependencies: List[int], parent_id: Optional[int]):
        last_deps = dependencies
        for f in tree:
            subjects = f(session, user_id, last_deps, parent_id)
            last_deps = [subject.id for subject in subjects]
    return save


def async_(*tree):
    def save(session, user_id: int, dependencies: List[int], parent_id: Optional[int]):
        subjects = tree
        for f in tree:
            f(session, user_id, dependencies, parent_id)
        return subjects
    return save


def schedule(session, user_id: int, *tree, dependencies: List[int] = [], parent_id: Optional[int] = None):
    for f in tree:
        f(session, user_id, dependencies, parent_id)


# ------------------------------------------------------------------------------------------------
# BrickOwl API
# ------------------------------------------------------------------------------------------------


@Registry.register
class upload_inventory_to_bo:
    params = []
    rate_limiter = rate_limiter.brickowl_api

    def execute(self):
        session = self.session
        user = self.user
        
        brickowl = BrickOwl.from_user(self.user)

        items = brickowl.get_inventory_list()

        items_by_boid = {}
        for item in items:
            boid = item['boid']

            if item['type'] != 'Part':
                print(f"WARNING: Ignored unsupported type: \"{item['type']}\" ({boid})")
                continue

            if boid in items_by_boid:
                print(f"WARNING: Duplicated item: {boid}")  # TODO HANDLE!
                continue
                
            items_by_boid[boid] = item

        for item in items:
            lot_id = item['lot_id']
            bo_id = item['boid'].split('-')[0]
            color_id = item['boid'].split('-')[1]
            condition = item['con']
            personal_note = item['personal_note'],

            inventory_part = session.query(InventoryPart) \
                .filter(and_(
                    InventoryPart.id_user == user.id,
                    InventoryPart.part.has(Part.id_bo == bo_id),
                    InventoryPart.color.has(Color.id_bo == color_id),
                    InventoryPart.condition == condition[0].upper(),
                    InventoryPart.user_remarks == personal_note,
                )) \
                .first()

            # The BO part hasn't been found in the local inventory, we need to remove it.
            if inventory_part is None:
                self.schedule_child(
                    run_(bo_inventory_delete(lot_id=lot_id))
                )
                print(f"Delete part {item['boid']}")  # TODO DELETING WRONG PARTS!
            
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
            .join(Part) \
            .join(Color) \
            .filter(and_(
                InventoryPart.id_user == user.id,
                func.concat(Part.id_bo, '-', Color.id_bo) == any_(list(items_by_boid.keys())),
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

