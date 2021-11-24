from dotenv import load_dotenv


load_dotenv()


from models import User, Op as SavedOp
from sqlalchemy import and_, or_
from op import schedule, sync_, async_, group_, run_
from operations import Dummy
from operations.syncer import _PullAndApplyOrdersGroup, _CheckInventoryUpdatesGroup, _InitializeInventoryGroup, _EndInventoryInitialization, _SyncerGroup, _SetSyncerRunning
from db import Session


def _pull_and_apply_orders():
    return \
        group_(_PullAndApplyOrdersGroup(), True,
            sync_(
                run_(Dummy()),  # TODO
            )
        )


def _check_inventory_updates(pinned: bool):
    return \
        group_(_CheckInventoryUpdatesGroup(), pinned,
            sync_(
                run_(Dummy()),  # TODO
            )
        )


def _init_inventory(session, user: User):
    schedule(session, user.id,
        group_(_InitializeInventoryGroup(), True,
            sync_(
                _check_inventory_updates(pinned=False),
                run_(_EndInventoryInitialization()),
            ),
        )
    )
    
    user.is_inventory_initializing = True
    session.flush([user])


def start(session, user_id: int):
    user = session.query(User) \
        .filter_by(id=user_id) \
        .first()

    if user.is_syncer_enabled:
        return False

    _init_inventory(session, user)

    user.is_syncer_enabled = True
    session.flush([user])

    return True


def run(session, user_id: int):
    user = session.query(User) \
        .filter_by(id=user_id) \
        .first()
    
    if not user.is_syncer_enabled:
        print("Syncer must be enabled in order to run.")
        return False

    if not user.is_inventory_initialized:
        print("Inventory isn't initialized. Syncer couldn't run.")
        return False

    if user.is_syncer_running:
        print("Syncer is already running, avoiding possible overlap.")
        return False

    schedule(session, user_id,
        group_(_SyncerGroup(), False,
            sync_(
                _pull_and_apply_orders(),
                _check_inventory_updates(pinned=True),
                run_(_SetSyncerRunning(flag=False)),
            ),
        ),
    )

    user.is_syncer_running = True
    session.flush([user])

    return True


def stop(session, user_id: int):
    user = session.query(User) \
        .filter_by(id=user_id) \
        .first()

    if not user.is_syncer_enabled:
        return False

    session.query(SavedOp) \
        .filter(and_(
            SavedOp.id_user == user.id,
            or_(
                SavedOp.id_group == user.inventory_initialization_group_id,
                SavedOp.id_group == user.syncer_group_id,
            ),
        )) \
        .delete()

    user.inventory_initialization_group_id = None
    user.syncer_group_id = None
    user.is_inventory_initializing = False
    user.is_inventory_initialized = False
    user.is_syncer_enabled = False
    user.is_syncer_running = False
    session.flush([user])

    return True


if __name__ == "__main__":
    with Session.begin() as session:
        users = session.query(User) \
            .all()

        for user in users:
            run(session, user.id)

