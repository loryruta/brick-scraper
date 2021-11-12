from models import Op as SavedOp, Part, User, InventoryPart
from typing import Dict, Optional, Type
from backends import bricklink, brickowl
import rate_limiter
from db import Session
from sqlalchemy.dialects.postgresql import insert
import image_handler
import os
import urllib.request
from urllib.error import HTTPError


class Registry:
    op_list = []

    def register(rate_limiter = rate_limiter.none):
        def wrapper(op):
            op.rate_limiter = rate_limiter

            def execute(session, user: User, saved_op: SavedOp):
                if rate_limiter.get_wait_time(user) == 0:
                    rate_limiter.issue(
                        user,
                        lambda: op.on_execute(session, user, saved_op)
                    )
                    return True
                else:
                    return False
            
            op.execute = execute

            Registry.op_list.append(op)

            return op

        return wrapper


class Op:
    def __init__(self, user_id: int, **params):
        self.user_id = user_id
        self.params = params

    def save(self, session, dependency_id: Optional[int] = None):
        saved_op = SavedOp(
            id_user=self.user_id,
            type=self.__class__.__name__,
            id_dependency=dependency_id,
            params=self.params,
        )
        session.add(saved_op)
        session.flush([saved_op])
        session.refresh(saved_op)
        return saved_op


@Registry.register(rate_limiter=rate_limiter.bricklink)
class bl_retrieve_part_image(Op):
    def __init__(user_id: int, color_id: int, part_id: str):
        super().__init__(user_id, color_id=color_id, part_id=part_id)

    def on_execute(session, user: User, saved_op: SavedOp):
        color_id = saved_op.params['color_id']
        part_id = saved_op.params['part_id']

        img_path = image_handler.get_part_image_storage_path(color_id, part_id)
        img_url = image_handler.get_part_image_url(color_id, part_id)

        if os.path.exists(img_path):
            return

        try:
            os.makedirs(os.path.dirname(img_path))
        except OSError:
            pass

        try:
            bricklink_img_url = f"https://img.bricklink.com/ItemImage/PN/{color_id}/{part_id}.png"
            urllib.request.urlretrieve(bricklink_img_url, img_path)
            return img_url
        except HTTPError:
            pass

        # TODO still not found


@Registry.register(rate_limiter=rate_limiter.bricklink_api)
class bl_api_download_inventory:
    def __init__(user_id: int, inventory_id: int):
        super().__init__(user_id, inventory_id=inventory_id)

    def on_execute(session, user: User, saved_op: SavedOp):
        pass


@Registry.register(rate_limiter=rate_limiter.brickowl_api)
class bo_api_part_id_lookup:
    def __init__(user_id: int, part_id: int):
        super().__init__(user_id, part_id=part_id)

    def on_execute(session, user: User, saved_op: SavedOp):
        part_id = saved_op.params['part_id']
        part = session.query(Part).filter_by(id=part_id).first()

        boids = brickowl.catalog_id_lookup(part_id, 'Part')['boids']
        if len(boids) == 0:
            print(f"WARNING: Part \"{part.name}\" ({part.id}) couldn't be matched with BO.")
            return
        
        boid = boids[0].split('-')[0]  # Trims color (after - on BOIDs)
        part.id_bo = boid


def save(session, op: Op):
    op.save(session)


def save_sync(session, *ops: Op):
    last_op_id = None
    for op in ops:
        saved_op = op.save(session, last_op_id)
        last_op_id = saved_op.id


def save_async(session, *ops: Op):
    for op in ops:
        op.save(session)

