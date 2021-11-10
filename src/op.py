from models import Op as SavedOp, User, PartedOutSet, InventoryPart
from typing import Dict, Type
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
            Registry.op_list.append(op)

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

            return op

        return wrapper


def _save_op(session, user_id: int, _class: Type, params: Dict):
    session.add(
        SavedOp(
            id_user=user_id,
            type=_class.__name__,
            params=params
        )
    )


@Registry.register(rate_limiter=rate_limiter.bricklink_api)
class bl_api_part_out_set:
    def append(session, user_id: int, set_id: int, condition: str):
        _save_op(session, user_id, __class__, {
            'set_id': set_id,
            'condition': condition
        })

    def on_execute(session, user: User, saved_op: SavedOp):
        set_id = saved_op.params['set_id']
        condition = saved_op.params['condition']

        matches = bricklink.get_subsets('SET', set_id)

        inventory_log = PartedOutSet(
            id_user=user.id,
            id_set=set_id
            )
        session.add(inventory_log)
        session.flush(objects=[inventory_log])
        session.refresh(inventory_log)

        for match in matches:
            for subset_entry in match['entries']:
                if subset_entry['item']['type'] != "PART":
                    continue

                item_no = subset_entry['item']['no']
                #item_name = subset_entry['item']['name']
                color_id = subset_entry['color_id']

                values={
                    'id_part': item_no,
                    'id_color': color_id,
                    'condition': condition,
                    'quantity': subset_entry['quantity'],
                    'id_parted_out_set': inventory_log.id,
                    'id_user': user.id
                }

                # TODO handle Integrity error if a part/color isn't found

                session.execute(
                    insert(InventoryPart)
                        .values(**values)
                        .on_conflict_do_update(
                            index_elements=['id_part', 'id_color', 'condition', 'id_parted_out_set', 'id_user'],
                            set_={'quantity': InventoryPart.quantity + subset_entry['quantity']}
                        )
                    )

                bl_retrieve_part_image.append(session, user.id, color_id, item_no)


@Registry.register(rate_limiter=rate_limiter.bricklink)
class bl_retrieve_part_image:
    def append(session, user_id: int, color_id: int, part_id: str):
        _save_op(session, user_id, __class__, {
            'color_id': color_id,
            'part_id': part_id,
        })

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
class BL_API_PullOrders:
    def append(session, user_id: int):
        _save_op(session, user_id, __class__, {})

    def on_execute(session, user: User, saved_op: SavedOp):
        pass


@Registry.register(rate_limiter=rate_limiter.brickowl_api)
class BO_API_PullOrders:
    def append(session, user_id: int):
        _save_op(session, user_id, __class__, {})

    def on_execute(session, user: User, saved_op: SavedOp):
        pass


@Registry.register(rate_limiter=rate_limiter.brickowl_api)
class BO_API_IdLookup:
    def append(session, user_id: int, boid: str):
        _save_op(session, user_id, __class__, {
            'boid': boid
        })

    def on_execute(session, user: User, saved_op: SavedOp):
        pass

