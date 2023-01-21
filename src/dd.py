from backends.bricklink import Bricklink
import os
import json


if __name__ == "__main__":
    bricklink = Bricklink(
        os.environ["SUPERVISOR_BRICKLINK_CONSUMER_KEY"],
        os.environ["SUPERVISOR_BRICKLINK_CONSUMER_SECRET"],
        os.environ["SUPERVISOR_BRICKLINK_TOKEN_VALUE"],
        os.environ["SUPERVISOR_BRICKLINK_TOKEN_SECRET"]
    )
    with open("test.json", "wt") as f:
        f.write(json.dumps(bricklink.get_inventories()))
