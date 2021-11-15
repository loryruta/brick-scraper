from dotenv import load_dotenv


load_dotenv()


from models import Part, Set, Color, Category, User
from db import Session
from sqlalchemy.dialects.postgresql import insert
import time
from typing import TextIO, List
from backends.brickowl import BrickOwl
import os


def _read_bricklink_catalog_file(file: TextIO, headers: List[str]):
    file.readline()

    elements_count = 0

    def log():
        print(f"Processed {elements_count} elements...")

    last_logged_at = 0

    for line in file:
        fields = line.split("\t")
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
    with open('tmp/colors.txt', 'rt') as f:
        for data in _read_bricklink_catalog_file(f, ['id', 'name', 'rgb', 'type']):
            session.execute(
                insert(Color)
                    .values(**data)
                    .on_conflict_do_update(index_elements=['id'], set_=data)
                )


def add_bo_colors(session):
    super_admin = session.query(User) \
        .filter(
            User.email == os.environ['SUPER_ADMIN_USER_EMAIL'],
        ) \
        .first()

    if not super_admin.has_bo_credentials():
        raise RuntimeError("This operation requires super-admin user to be present.")

    bo = BrickOwl.from_user(super_admin)
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

        bl_color.id_bo = bo_id


def add_categories(session):
    with open('tmp/categories.txt', 'rt') as f:
        for data in _read_bricklink_catalog_file(f, ['id', 'name']):
            session.execute(
                insert(Category)
                    .values(**data)
                    .on_conflict_do_update(index_elements=['id'], set_=data)
            )


def add_parts(session):
    with open('tmp/parts.txt', 'rt') as f:
        for data in _read_bricklink_catalog_file(f, ['id_category', 'category_name', 'id', 'name']):

            del data['category_name']

            session.execute(
                insert(Part)
                    .values(**data)
                    .on_conflict_do_update(index_elements=['id'], set_=data)
            )


def add_sets(session):
    with open('tmp/sets.txt', 'rt') as f:
        for data in _read_bricklink_catalog_file(f, ['id_category', 'category_name', 'id', 'name']):

            del data['category_name']

            session.execute(
                insert(Set)
                    .values(**data)
                    .on_conflict_do_update(index_elements=['id'], set_=data)
            )


if __name__ == "__main__":
    #print("Adding colors...")
    #with Session.begin() as session:
    #   add_colors(session)

    print("Adding BO colors...")
    with Session.begin() as session:
        add_bo_colors(session)

    #print("Adding categories...")
    #with Session.begin() as session:
    #   add_categories(session)

    #print("Adding parts...")
    #with Session.begin() as session:
    #    add_parts(session)

    #print("Adding sets...")
    #with Session.begin() as session:
    #    add_sets(session)
