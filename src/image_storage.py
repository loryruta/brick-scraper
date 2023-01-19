import os
from urllib.request import urlretrieve
from urllib.error import HTTPError


def retrieve_image(item_type: str, color_id: int, item_id: int) -> bool:
    image_path = get_item_image_path(item_type, color_id, item_id)

    if os.path.exists(image_path):
        return True

    try:
        os.makedirs(os.path.dirname(image_path))
    except OSError as _:
        pass

    bl_item_type = {
        'part': 'PN',
        'minifig': 'MN',
        'set': 'SN',
    }[item_type]

    try:
        bl_image_url = f"https://img.bricklink.com/ItemImage/{bl_item_type}/{color_id}/{item_id}.png"
        urlretrieve(bl_image_url, image_path)
    except HTTPError:
        return False

    return True


def get_item_image_path(item_type: str, color_id: str, item_id: str, **kwargs):
    path = f"storage/{item_type}/img/{color_id}/{item_id}.png"

    if 'force_download' in kwargs and not os.path.isfile(path):
        retrieve_image(item_type, color_id, item_id)

    return path


def get_item_image_url(item_type: str, color_id: str, item_id: str):
    bl_item_type = { 'part': 'PN', 'minifig': 'MN', 'set': 'SN', }[item_type]
    return f"https://img.bricklink.com/ItemImage/{bl_item_type}/{color_id}/{item_id}.png"

