from dotenv import load_dotenv


load_dotenv()


from models import Op as SavedOp, User
from db import Session
import op as op_registry
from datetime import datetime
from sqlalchemy import and_


MAX_USERS_PER_CALL = 10
MAX_OPERATIONS_PER_CALL = 1000


class Worker:
    def process():
        with Session.begin() as session:
            users = session.query(User) \
                .limit(MAX_USERS_PER_CALL) \
                .all()

            for user in users:
                remaining_op_count = MAX_OPERATIONS_PER_CALL

                have_to_wait = []

                # TODO ADD PARENT_ID SUPPORT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                while remaining_op_count > 0:  # Every cron invocation the worker is permitted to execute a certain number of operations.
                    saved_ops = session.query(SavedOp) \
                        .filter(and_(
                            SavedOp.id_user == user.id,
                            SavedOp.id.notin_(have_to_wait), # The operation has been tried to execute but refused (probably due to rate limiter).
                            SavedOp.processed_at.is_(None),  # The operation hasn't been processed yet.
                            SavedOp.dependency.has(SavedOp.processed_at.isnot(None)), # The operation's parent has been processed.
                        )) \
                        .order_by(SavedOp.created_at.asc()) \
                        .limit(MAX_OPERATIONS_PER_CALL) \
                        .all()

                    # Either no operation found or we need to wait the next cron invocation.
                    if len(saved_ops) == 0:
                        break

                    print(f"Trying to execute ${len(saved_ops)} operations...")

                    for saved_op in saved_ops:
                        op = getattr(op_registry, saved_op.type)

                        print(f"Executing \"{saved_op.type}\" (#{saved_op.id})...")

                        # Tries to execute the current operation through the rate limiter.
                        if op.execute(session, user, saved_op):
                            saved_op.processed_at = datetime.now().isoformat()
                            session.flush([saved_op])
                        else:  # If fails, it means the rate limiter stopped the operation, so we won't consider it for this cron invocation.
                            have_to_wait.append(saved_op)
                            print(f"Rate limited \"{saved_op.type}\". Will be retryed the next loop.")

                    remaining_op_count -= len(saved_ops)


if __name__ == '__main__':
    Worker.process()
