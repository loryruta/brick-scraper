from dotenv import load_dotenv


load_dotenv()


from models import Op as SavedOp, op_dependencies_table 
from db import Session
from operations import *
from op import Registry as OperationRegistry
from datetime import datetime
from sqlalchemy import and_, func, or_
from sqlalchemy.dialects.postgresql import INTERVAL


class Worker:
    def process():
        with Session.begin() as session:
            # Gets users that have pending operations (operations that haven't been invoked).
            user_ids = session.query(SavedOp.id_user) \
                .filter(
                    SavedOp.invoked_at.is_(None),
                ) \
                .order_by(SavedOp.created_at.asc()) \
                .distinct() \
                .limit(10) \
                .all()

            # For every user processes a certain number of operations.
            for (user_id,) in user_ids:
                remaining_op_count = 1000

                print(f"Processing operations for user: {user_id}")

                while remaining_op_count > 0:
                    query = session.query(SavedOp) \
                        .filter(and_(
                            SavedOp.id_user == user_id,
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
                        else:
                            # The operation couldn't be executed because of rate limiter. It will
                            # be skipped the next iterations according to the time to wait.
                            saved_op.rate_limited_at = datetime.now().isoformat()
                            saved_op.rate_limited_for = execute_result
                            session.flush([saved_op])

                    remaining_op_count -= len(saved_ops)


if __name__ == '__main__':
    Worker.process()
