
from models import User
from op import schedule, sync_, async_, group_, run_
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
    schedule(session, user_id,
        sync_(
            run_(syncer_begin()),
            run_(clear_inventory()),
            run_(download_bl_inventory()),
            group_(
                async_(
                    run_(lookup_inventory_bo_ids()),
                    run_(retrieve_inventory_bl_images()),
                ),
            ),
            run_(upload_inventory_to_bo()),
            run_(syncer_end()),
        )
    )


def stop(user: User):
    # Stopping the syncer means that when an inventory upload should be issue it won't be issued.
    # There's nothing to be cleared.
    pass

