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

