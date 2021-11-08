from models import InventoryPart, Set
import os
from urllib.error import HTTPError
import urllib.request
from os import OSError


def get_part_image_url(inventory_part: InventoryPart):
    part_img = f'storage/parts/img/{inventory_part.id_color}/{inventory_part.id_part}.png'
    part_img_url = f"/{part_img}"

    try:
        os.makedirs(os.path.dirname(part_img))
    except OSError:
        pass

    # Checks if the image has already been cached locally.
    if os.path.exists(part_img):
        return part_img_url

    # Tries to guess the image URL from Bricklink website.
    try:
        bricklink_img_url = f"https://img.bricklink.com/ItemImage/PN/{inventory_part.id_color}/{inventory_part.id_part}.png"
        urllib.request.urlretrieve(bricklink_img_url, part_img)
        return part_img_url
    except HTTPError:
        pass

    # Still not found? Asks the image to the Bricklink API.
    # TODO

    return None


def get_set_image_url(set: Set):
    return None

