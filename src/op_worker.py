from dotenv import load_dotenv


load_dotenv()


from models import Op as SavedOp, OpGroup, OpView, op_dependencies_table 
from db import Session
from operations import *
from op import Registry as OperationRegistry, schedule
from datetime import datetime
from sqlalchemy import and_, func, or_
from sqlalchemy.sql.operators import exists
from sqlalchemy.dialects.postgresql import INTERVAL
import random
import argparse


def get_users_with_pending_operations(session):
    return [
        user_id
        for (user_id,) in session.query(OpGroup.id_user) \
            .join(SavedOp, SavedOp.id_group == OpGroup.id) \
            .filter(
                SavedOp.invoked_at.is_(None),
            ) \
            .order_by(
                OpGroup.id_user.asc(),
                OpGroup.created_at.asc(),
            ) \
            .distinct(OpGroup.id_user) \
            .limit(10) \
            .all()
    ]


def get_user_pending_groups(session, user_id: int):
    return [
        group_id
        for (group_id,) in session.query(OpGroup.id) \
                .join(SavedOp, SavedOp.id_group == OpGroup.id) \
                .filter(and_(
                    OpGroup.id_user == user_id,
                    SavedOp.invoked_at.is_(None),
                )) \
                .order_by(
                    OpGroup.id.asc(),
                    OpGroup.created_at.asc(),
                ) \
                .distinct(OpGroup.id) \
                .limit(10) \
                .all()
    ]


def step():
    with Session.begin() as session:
        user_ids = get_users_with_pending_operations(session)

        # For every user processes a certain number of operations.
        for user_id in user_ids:
            remaining_op_count = 1000

            group_ids = get_user_pending_groups(session, user_id)
            for group_id in group_ids:

                print(f"Processing operations for user: {user_id}")

                while remaining_op_count > 0:
                    query = session.query(SavedOp) \
                        .filter(and_(
                            SavedOp.id_group == group_id,
                            SavedOp.invoked_at.is_(None),        # The operation hasn't been processed yet.
                            ~SavedOp.dependencies.any(
                                SavedOp.processed_at == None
                            ),
                            or_(
                                SavedOp.id_parent.is_(None),
                                SavedOp.parent.has( # If the parent is set, it should be invoked before child operations can run.
                                    SavedOp.invoked_at.isnot(None),
                                ),
                            ),
                            or_( # The rate limit time, if any, must be expired.
                                SavedOp.rate_limited_at.is_(None),
                                SavedOp.rate_limited_at + SavedOp.rate_limited_for * func.cast("1 second", INTERVAL) <= func.now(),
                            )
                        )) \
                        .order_by(SavedOp.created_at.asc()) \
                        .limit(remaining_op_count)
                    saved_ops = query.all()

                    # Either no operation found or we need to wait the next cron invocation.
                    if len(saved_ops) == 0:
                        break
                    
                    print(f"Queried {len(saved_ops)} operation(s) waiting to be executed...")

                    for saved_op in saved_ops:
                        operation_class = OperationRegistry._by_name[saved_op.type]
                        
                        print(f"Executing: \"{saved_op.type}\" (#{saved_op.id})")

                        executor = operation_class.create_executor(session, saved_op)

                        execute_result = executor.execute()

                        if execute_result == 0:
                            saved_op.invoked_at = datetime.now().isoformat()

                            saved_op.rate_limited_at = None # The operation has been executed, remove the rate limiter fields.
                            saved_op.rate_limited_for = None 

                            session.flush([saved_op])

                            children_ops = session.query(func.count(SavedOp.id)) \
                                .filter(and_(
                                    SavedOp.id_parent == saved_op.id,
                                    SavedOp.processed_at.is_(None),
                                )) \
                                .scalar()

                            if children_ops == 0:
                                # If the operation hasn't any children operation (generated during execution or not),
                                # we can set the processed_at field directly.
                                saved_op.processed_at = datetime.now().isoformat()
                                session.flush([saved_op])

                                # We climb every parent and if all of its children are processed, set the processed_at field also for it.
                                parent = saved_op.parent
                                while parent:
                                    unprocessed_children = session.query(func.count(SavedOp.id)) \
                                        .filter(and_(
                                            SavedOp.id_parent == parent.id,
                                            SavedOp.processed_at.is_(None),
                                        )) \
                                        .scalar()

                                    if unprocessed_children > 0: # If the current parent has some unprocessed operations stops.
                                        break

                                    parent.processed_at = datetime.now().isoformat()
                                    session.flush([parent])

                                    parent = parent.parent

                                left_ops = session.query(func.count(SavedOp.id)) \
                                    .filter(and_(
                                        SavedOp.id_group == saved_op.id_group,
                                        SavedOp.processed_at.is_(None),
                                    )) \
                                    .scalar()
                                if left_ops == 0:  # If all the operations for the current group has been processed, sets the group as processed.
                                    group = saved_op.group
                                    group.processed_at = datetime.now().isoformat()
                                    session.flush([group])
                        else:
                            # The operation couldn't be executed because of rate limiter. It will
                            # be skipped the next iterations according to the time to wait.
                            saved_op.rate_limited_at = datetime.now().isoformat()
                            saved_op.rate_limited_for = execute_result
                            session.flush([saved_op])

                    remaining_op_count -= len(saved_ops)


def delete_processed_op_groups():
    with Session.begin() as session:
        session.query(OpGroup) \
                .filter(and_(
                    OpGroup.processed_at.isnot(None),
                    OpGroup.processed_at + func.cast("3 DAYS", INTERVAL) <= func.now(),
                )) \
                .delete()


def screenshot():
    with Session.begin() as session:
        # Takes every group, for every user, still registered.
        # This is safe because completed groups older than a certain amount of time will be deleted.
        groups = session.query(OpGroup.id) \
            .all()
    
        for (group_id,) in groups:
            op_count = session.query(SavedOp) \
                .filter(and_(
                    SavedOp.id_group == group_id,
                    SavedOp.processed_at.is_(None),
                )) \
                .count()  # Counts how many operations does it have.

            screenshot = OpView(
                id_group=group_id,
                op_count=op_count,
            )
            session.add(screenshot)


def schedule_dummy_group(): # TODO TEST FUNCTION
    with Session.begin() as session:
        super_admin = User.get_super_admin(session)

        ops = [
            run_(Dummy())
            for _ in range(0, random.randrange(10, 20))
        ]
        schedule(session, super_admin.id, "Dummy", async_(*ops))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub_parsers = parser.add_subparsers()
    sub_parsers.required = True

    sub_cmds = [step, screenshot, schedule_dummy_group, delete_processed_op_groups]
    for sub_cmd in sub_cmds:
        sub_parser = sub_parsers.add_parser(sub_cmd.__name__)
        sub_parser.set_defaults(func=sub_cmd)

    args = parser.parse_args()
    args.func()

