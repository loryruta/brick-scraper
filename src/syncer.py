
from models import User
from op import download_bl_inventory, upload_inventory_to_bo, schedule, sync_
from operations.syncer import * 
from operations.inventory import *
from db import Session


def is_running(user: User):
    return user.syncer_running


def is_enabled(user: User):
    return user.syncer_enabled


def set_enabled(user: User, enabled: bool):
    user.syncer_enabled = enabled
    Session.object_session(user).flush([user])


def start(session, user_id: int):
    schedule(session,
        sync_( 
            syncer_begin(user_id),
            clear_inventory(user_id),
            download_bl_inventory(user_id),
            #upload_inventory_to_bo(user_id),
            syncer_end(user_id)
        )
    )


def stop(user: User):
    # Stopping the syncer means that when an inventory upload should be issue it won't be issued.
    # There's nothing to be cleared.
    pass

