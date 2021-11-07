import requests
from requests_oauthlib import OAuth1
import json
import os
from sqlalchemy.exc import SQLAlchemyError
from models import Part, InventoryPart, PartedOutSet, Set
from db import Session
from stores import rebrickable, bricklink, brickowl
from sqlalchemy.dialects.postgresql import insert
import asyncio


class InvalidOperation(Exception):
    pass


async def add_part(session, part: rebrickable.Part) -> Part:
    part_num = part['part_num']

    external_ids = part['external_ids']

    # todo
    bricklink_id = external_ids['BrickLink'][0] if 'BrickLink' in external_ids and bricklink.does_part_exist(external_ids['BrickLink'][0]) else None
    brickowl_id  = external_ids['BrickOwl'][0] if 'BrickOwl' in external_ids and brickowl.does_part_exist(external_ids['BrickOwl'][0]) else None

    values = {
        'name': part['name'],
        'id_category': part['part_cat_id'],
        'part_url': part['part_url'],
        'part_img_url': part['part_img_url'],
        'id_bricklink': bricklink_id,
        'id_brickowl': brickowl_id
    }

    session.execute(
        insert(Part)
            .values(id=part_num, **values)
            .on_conflict_do_update(index_elements=['id'], set_=values)
    )

    return Part(id=part_num, **values)


async def add_set(session, set: rebrickable.Set) -> Set:
    set_num = set['set_num']

    values = {
        'name': set['name'],
        'year': set['year'],
        'id_theme': set['theme_id'],
        'num_parts': set['num_parts'],
        'set_img_url': set['set_img_url'],
        'set_url': set['set_url'],
        #'last_modified_date': set['last_modified_dt'] TODO
    }

    session.execute(
        insert(Set)
            .values(id=set_num, **values)
            .on_conflict_do_update(index_elements=['id'], set_=values)
    )

    return Set(id=set_num, **values)



async def add_part_to_inventory(session, user_id: int, part: rebrickable.SetPart, condition: str, parted_out_set_id: int) -> InventoryPart:
    values={
        'id_part': part['part']['part_num'],
        'id_color': part['color']['id'],
        'condition': condition,
        'quantity': 1,
        'id_parted_out_set': parted_out_set_id,
        'id_user': user_id
    }

    session.execute(
        insert(InventoryPart)
            .values(**values)
            .on_conflict_do_update(
                index_elements=['id_part', 'id_color', 'condition', 'id_parted_out_set', 'id_user'],
                set_={'quantity': InventoryPart.quantity + 1}
            )
    )
    return InventoryPart(**values)


async def part_out_to_inventory(user_id: int, set_id: str, condition: str):
    parts = list(rebrickable.get_set_parts(set_id))

    with Session.begin() as session:
        # Caches the parts found in the set.
        await asyncio.gather(*[add_part(session, part['part']) for part in parts])

        # Caches the set information.
        await add_set(session, rebrickable.get_set(set_id))

        # Registers that the user has parted out the set.
        parted_out_set_id = session \
                .execute(
                    insert(PartedOutSet)
                        .values(id_user=user_id, id_set=set_id)
                        .returning(PartedOutSet.id)
                ) \
                .first()[0]

        # Adds the parts to the user's inventory.
        await asyncio.gather(*[
            add_part_to_inventory(session, user_id, part, condition, parted_out_set_id)
            for part in parts
        ])
