from dotenv import load_dotenv


load_dotenv()


from logger import logger
from models import Item
from db import Session
import time
import os
import asyncio
from sqlalchemy import and_
from backends.brickowl import BrickOwl


BATCH_SIZE = 10           # How many requests to BrickOwl to dispatch in parallel
MAX_ELAPSED_TIME = 60 * 5 # The max elapsed time reserved to the task


bo = BrickOwl(key=os.environ['SUPERVISOR_BRICKOWL_KEY'])


def _specialize_item_type_to_bo(item_type: str):
    return {
        'part': 'Part',
        'minifig': 'Minifigure',
        'set': 'Set',
    }[item_type]


async def main():
    logger.info(f"Looking for items' BO IDs...")

    task_started_at = time.time()

    while True:
        with Session.begin() as session:
            started_at = time.time()

            query = session.query(Item) \
                .filter(and_(
                    Item.bo_id.is_(None),
                ))
            remaining_count = query.count()
            items = query \
                .limit(BATCH_SIZE) \
                .all()

            if len(items) == 0:
                logger.info(f"No more items to process!")
                break

            async def lookup_item_bo_id(item: Item):
                bo_ids = bo.catalog_id_lookup(
                    id=item.id,
                    type=_specialize_item_type_to_bo(item.type),
                )['boids']

                if len(bo_ids) == 0:
                    item.bo_id = -1
                    return False

                bo_id: str = bo_ids[0]
                bo_id = bo_id.split('-')[0]
                item.bo_id = bo_id
                return True

            resolved_item_count = sum(await asyncio.gather(*[lookup_item_bo_id(item) for item in items]))
            
            task_elapsed_time = time.time() - task_started_at
            elapsed_time = time.time() - started_at

            logger.info(f"{task_elapsed_time:.1f}s - Resolved {resolved_item_count}/{BATCH_SIZE} items in {elapsed_time:.1f}s, remaining {remaining_count} items")

            if task_elapsed_time >= MAX_ELAPSED_TIME:
                logger.info(f"Max available time reached!")
                break


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
