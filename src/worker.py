from dotenv import load_dotenv


load_dotenv()


from models import Op as SavedOp, User
from db import Session
import op as op_registry
from datetime import datetime
from sqlalchemy import inspect, and_


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

                while remaining_op_count > 0:
                    saved_op_list = session.query(SavedOp) \
                        .filter(and_(
                            SavedOp.id_user == user.id,
                            SavedOp.processed_at.is_(None)
                        )) \
                        .order_by(SavedOp.created_at.asc()) \
                        .limit(MAX_OPERATIONS_PER_CALL) \
                        .all()

                    print(f"{len(saved_op_list)} operations found...")

                    for saved_op in saved_op_list:
                        op = getattr(op_registry, saved_op.type)

                        print(f"Operation #{saved_op.id} \"{saved_op.type}\" - scheduled at: {saved_op.created_at}")

                        if op.execute(session, user, saved_op):
                            saved_op.processed_at = datetime.now().isoformat()
                            session.flush([saved_op])

                            print(f"Operation #{saved_op.id} processed at: {saved_op.processed_at}")

                            #saved_op.expire()
                            #session.commit()
                            #t = inspect(saved_op)
                            #print(t.transient, t.pending, t.persistent, t.deleted, t.detached)
                        else:
                            print(f"Operation #{saved_op} skipped")

                    if len(saved_op_list) == 0:
                        break

                    remaining_op_count -= len(saved_op_list)


if __name__ == '__main__':
    Worker.process()
