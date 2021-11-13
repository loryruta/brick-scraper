from dotenv import load_dotenv


load_dotenv()


from models import Op as SavedOp
from db import Session
import op as op_registry
from datetime import datetime
from sqlalchemy import and_, func


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
            for user_id in user_ids:
                remaining_op_count = 100

                have_to_wait = []

                while remaining_op_count > 0:
                    saved_ops = session.query(SavedOp) \
                        .filter(and_(
                            SavedOp.id_user == user_id,
                            SavedOp.id.notin_(have_to_wait), # The operation has been tried to execute but refused (probably due to rate limiter).
                            SavedOp.invoked_at.is_(None),    # The operation hasn't been processed yet.
                            SavedOp.dependency.has(SavedOp.processed_at.isnot(None)), # The operation's parent has been processed.
                        )) \
                        .order_by(SavedOp.created_at.asc()) \
                        .limit(remaining_op_count) \
                        .all()

                    # Either no operation found or we need to wait the next cron invocation.
                    if len(saved_ops) == 0:
                        break

                    print(f"Trying to execute ${len(saved_ops)} operations...")

                    for saved_op in saved_ops:
                        operation_definition = getattr(op_registry, saved_op.type)
                        
                        print(f"Executing \"{saved_op.type}\" (#{saved_op.id})...")

                        executor = operation_definition.executor(session, saved_op)

                        executed = executor.execute()

                        if executed:
                            saved_op.invoked_at = datetime.now().isoformat()
                            session.flush([saved_op])

                            # If the operation hasn't added children operations, we can directly set the processed_at field.
                            if not executor.children:
                                saved_op.processed_at = datetime.now().isoformat()
                                session.flush([saved_op])
                                
                                # We climb every parent and if all of its children are processed,
                                # sets the processed_at field also for it.
                                parent = saved_op.parent
                                while parent:
                                    unprocessed_children = session.query(func.count(SavedOp)) \
                                        .filter(and_(
                                            SavedOp.id_parent == parent.id,
                                            SavedOp.processed_at.is_(None),
                                        ))

                                    if unprocessed_children > 0: # If the current parent has some unprocessed operations stop.
                                        break

                                    parent.processed_at = datetime.now().isoformat()
                                    session.flush([parent])
                        else:
                            # The operation can't be executed now (because of rate limiter).
                            # It will wait until the next cron invocation.
                            have_to_wait.append(saved_op.id)

                    remaining_op_count -= len(saved_ops)


if __name__ == '__main__':
    Worker.process()
