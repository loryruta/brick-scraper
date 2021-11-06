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


async def init_colors(session):
    print("Pulling colors...")

    for color in rebrickable.get_colors():
        color_id = color['id']
        color_name = color['name']
        external_ids = color['external_ids']

        bricklink_id = None
        if 'BrickLink' in external_ids:
            bricklink_id = external_ids['BrickLink']['ext_ids'][0]

        brickowl_id = None
        if 'BrickOwl' in external_ids:
            brickowl_id = external_ids['BrickOwl']['ext_ids'][0]

        values = {
            'name': color_name,
            'rgb': color['rgb'],
            'id_bricklink': bricklink_id,
            'id_brickowl': brickowl_id,
        }

        session.execute(
            insert(Color)
                .values(id=color_id, **values)
                .on_conflict_do_update(index_elements=['id'], set_=values)
        )
        
        print(f"Color #{color_id}: {color_name} (Bricklink: {bricklink_id}, Brickowl: {brickowl_id})")


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
        # Cache the parts found in the set
        await asyncio.gather(*[add_part(session, part['part']) for part in parts])

        # Cache the set information
        await add_set(session, rebrickable.get_set(set_id))

        # Register the parted out set for the user
        parted_out_set_id = session \
                .execute(
                    insert(PartedOutSet)
                        .values(id_user=user_id, id_set=set_id)
                        .returning(PartedOutSet.id)
                ) \
                .first()[0]

        # Add the parts to the user's inventory
        await asyncio.gather(*[
            add_part_to_inventory(session, user_id, part, condition, parted_out_set_id)
            for part in parts
        ])

    session.commit()


# Main

if 'PULL_COLORS' in os.environ and os.environ['PULL_COLORS']:
    with Session.begin() as session:
        asyncio.run(init_colors(session))
