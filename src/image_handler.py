from models import InventoryPart, Set
import os
from urllib.error import HTTPError
import urllib.request


def get_part_image_url(color_id: str, part_id: str):
    part_img = f'storage/parts/img/{color_id}/{part_id}.png'
    part_img_url = f"/public/{part_img}"

    try:
        os.makedirs(os.path.dirname(part_img))
    except OSError:
        pass

    # Checks if the image has already been cached locally.
    if os.path.exists(part_img):
        return part_img_url

    # Tries to guess the image URL from Bricklink website.
    try:
        bricklink_img_url = f"https://img.bricklink.com/ItemImage/PN/{color_id}/{part_id}.png"
        urllib.request.urlretrieve(bricklink_img_url, part_img)
        return part_img_url
    except HTTPError:
        pass

    # Still not found? Asks the image to the Bricklink API.
    # TODO

    return None


def get_set_image_url(set: Set):
    set_img = f'storage/parts/img/'

    return None

