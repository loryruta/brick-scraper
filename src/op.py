from models import Op as SavedOp, op_dependencies_table
from typing import Optional, List
import rate_limiter


class Registry:
    _by_name = {}

    def register(operation_class):
        required_params = operation_class.params \
            if hasattr(operation_class, 'params') else []

        rate_limiter_ = operation_class.rate_limiter \
            if hasattr(operation_class, 'rate_limiter') else rate_limiter.none

        display_name = operation_class.display_name \
            if hasattr(operation_class, 'display_name') else None

        class DecoratedOperation(Op):
            def __init__(self, **params):
                operation_name = operation_class.__name__
                self.__class__.__name__ = operation_name
                self.display_name = display_name

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


    def save(self, session, user_id: int, dependencies: List[int], parent_id: Optional[int], group_id: int):
        saved_op = SavedOp(
            type=self.__class__.__name__,
            id_user=user_id,
            id_parent=parent_id,
            params=self.params,
            id_group=group_id,
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
                parent_id = self.saved_op.id_parent
                group_id = self.saved_op.id_group
                f(session, dependencies, parent_id, group_id)

        
        def execute(self):
            user = self.user
            rate_limiter = self.rate_limiter

            wait_time = rate_limiter.get_wait_time(user)

            execute_func = \
                    lambda: self.operation_class.execute(self) if hasattr(self.operation_class, 'execute') else lambda: None

            if wait_time == 0:
                rate_limiter.issue(user, execute_func)

            return wait_time


@Registry.register
class Group:
    display_name = None
    params = []
    rate_limiter = rate_limiter.none

    def execute(self):
        pass


def run_(op: Op):
    def save(session, user_id: int, dependencies: List[int], parent_id: Optional[int], group_id: int):
        subject = op.save(session, user_id, dependencies, parent_id, group_id)
        return [subject]
    return save


def group_(group_operation, pinned: bool, *tree):
    def save(session, user_id: int, dependencies: List[int], parent_id: Optional[int], group_id: int):
        subject = \
            run_(group_operation)(session, user_id, dependencies, parent_id, group_id)[0]
        for f in tree:
            f(session, user_id, dependencies, subject.id, subject.id if pinned else group_id)

        return [subject]
    return save


def sync_(*tree):
    def save(session, user_id: int, dependencies: List[int], parent_id: Optional[int], group_id: int):
        last_deps = dependencies
        for f in tree:
            subjects = f(session, user_id, last_deps, parent_id, group_id)
            last_deps = [subject.id for subject in subjects]
    return save


def async_(*tree):
    def save(session, user_id: int, dependencies: List[int], parent_id: Optional[int], group_id: int):
        subjects = tree
        for f in tree:
            f(session, user_id, dependencies, parent_id, group_id)
        return subjects
    return save


def schedule(session, user_id: int, *tree):
    for f in tree:
        f(session, user_id, [], None, None)

