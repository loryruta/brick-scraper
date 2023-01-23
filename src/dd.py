from backends.bricklink import Bricklink
import json
import asyncio
from commands import sync_bricklink_store


def bricklink_dump():
    bricklink = Bricklink.from_supervisor()
    with open("test.json", "wt") as f:
        f.write(json.dumps(bricklink.get_store_inventories()))


def run_command():
    asyncio.run(sync_bricklink_store.run())


if __name__ == "__main__":
    run_command()
