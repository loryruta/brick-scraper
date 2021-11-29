from dotenv import load_dotenv


load_dotenv()


from models import Item, Color, Category, User
from db import Session
from sqlalchemy import and_
from sqlalchemy.dialects.postgresql import insert
import time
from typing import TextIO, List
from backends.brickowl import BrickOwl
import os


STORAGE_FOLDER = "storage"


def _spec_item_type_to_bo(item_type: str):  # TODO centralize
    return {
        'part': 'Part',
        'minifig': 'Minifigure',
        'set': 'Set',
    }[item_type]


def _read_bricklink_catalog_file(file: TextIO, headers: List[str]):
    file.readline()

    elements_count = 0

    def log():
        print(f"Processed {elements_count} elements...")

    last_logged_at = 0

    for line in file:
        fields = line.rstrip().split("\t")
        if len(fields) < len(headers):
            continue
        
        element = {}
        for i in range(len(headers)):
            element[headers[i]] = fields[i]
        yield element
        elements_count += 1

        now = time.time()
        if now - last_logged_at > 3.0:
            log()
            last_logged_at = now

    log()
    print("Done")


def add_colors(session):
    with open(f"{STORAGE_FOLDER}/bl_catalog/colors.txt", 'rt') as f:
        for data in _read_bricklink_catalog_file(f, ['id', 'name', 'rgb', 'type']):
            session.execute(
                insert(Color)
                    .values(**data)
                    .on_conflict_do_update(index_elements=['id'], set_=data)
                )


def lookup_colors_bo_ids(session):
    bo = BrickOwl(key=os.environ['BRICKOWL_KEY'])
    colors = bo.get_colors()
    for bo_id, color in colors.items():
        bl_ids = color['bl_ids']
        if len(bl_ids) != 1:
            print(f"WARNING: Unexpected bl_ids array, empty or with more than one element.")

        bl_id = bl_ids[0]
        bl_name = color['bl_names'][0]
        bl_color = session.query(Color) \
            .filter_by(id=bl_id) \
            .first()

        if not bl_color:
            print(f"WARNING: Unknown BL color ID \"{bl_name}\" (#{bl_id}) for BO color: \"{color['name']}\" (#{bo_id})")
            continue

        bl_color.bo_id = bo_id
        session.flush([bl_color])

    session.query(Color) \
        .filter(Color.bo_id.is_(None)) \
        .update({
            'bo_id': -1,
        })


def add_categories(session):
    with open(f"{STORAGE_FOLDER}/bl_catalog/categories.txt", 'rt') as f:
        for data in _read_bricklink_catalog_file(f, ['id', 'name']):
            session.execute(
                insert(Category)
                    .values(**data)
                    .on_conflict_do_update(index_elements=['id'], set_=data)
            )


def add_parts(session):
    with open(f"{STORAGE_FOLDER}/bl_catalog/parts.txt", 'rt') as f:
        for data in _read_bricklink_catalog_file(f, ['id_category', 'category_name', 'id', 'name']):

            del data['category_name']

            session.execute(
                insert(Item)
                    .values(**({'type': 'part'} | data))
                    .on_conflict_do_update(index_elements=['id', 'type'], set_=data)
            )


def add_minifigs(session):
    with open(f"{STORAGE_FOLDER}/bl_catalog/minifigs.txt", 'rt') as f:
        for data in _read_bricklink_catalog_file(f, ['id_category', 'category_name', 'id', 'name']):

            del data['category_name']

            session.execute(
                insert(Item)
                    .values(**({'type': 'minifig'} | data))
                    .on_conflict_do_update(index_elements=['id', 'type'], set_=data)
            )


def add_sets(session):
    with open(f"{STORAGE_FOLDER}/bl_catalog/sets.txt", 'rt') as f:
        for data in _read_bricklink_catalog_file(f, ['id_category', 'category_name', 'id', 'name']):

            del data['category_name']

            session.execute(
                insert(Item)
                    .values(**({'type': 'set'} | data))
                    .on_conflict_do_update(index_elements=['id', 'type'], set_=data)
            )


def lookup_items_bo_id():
    while True:
        with Session.begin() as session:
            get_query = session.query(Item) \
                .filter(and_(
                    Item.bo_id.is_(None),
                ))

            remaining_count = get_query.count()
            items = get_query \
                .limit(100) \
                .all()

            if len(items) == 0:
                break
                
            print(f"Remaining {remaining_count} items to update...")

            solved_counter = 0
            bo = BrickOwl(key=os.environ['BRICKOWL_KEY'])
            for item in items:
                boids = bo.catalog_id_lookup(
                    id=item.id,
                    type=_spec_item_type_to_bo(item.type),
                )['boids']

                if len(boids) == 0:
                    print(f"WARNING: Couldn't find BO ID for item ({item.id}): {item.name} ({item.type})")
                    item.bo_id = -1
                else:
                    boid: str = boids[0]
                    boid = boid.split('-')[0]

                    item.bo_id = boid

                    solved_counter += 1

            print(f"Found BO ID for {solved_counter} items")

    print("Done")


def main():
    print("Adding colors...")
    with Session.begin() as session:
       add_colors(session)

    print("Looking up colors BO ID...")
    with Session.begin() as session:
        lookup_colors_bo_ids(session)

    print("Adding categories...")
    with Session.begin() as session:
       add_categories(session)

    print("Adding parts...")
    with Session.begin() as session:
        add_parts(session)

    print("Adding minifigs...")
    with Session.begin() as session:
        add_minifigs(session)

    print("Adding sets...")
    with Session.begin() as session:
        add_sets(session)

    print("Looking up items BO ID...")
    lookup_items_bo_id()


if __name__ == "__main__":
    lookup_items_bo_id()
    
