from dotenv import load_dotenv


load_dotenv()


from models import Part, Set, Color, Category
from db import Session
from sqlalchemy.dialects.postgresql import insert
import time
from typing import TextIO, List


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
    print("Adding colors...")
    with Session.begin() as session:
        add_colors(session)

    print("Adding categories...")
    with Session.begin() as session:
        add_categories(session)

    print("Adding parts...")
    with Session.begin() as session:
        add_parts(session)

    print("Adding sets...")
    with Session.begin() as session:
        add_sets(session)
