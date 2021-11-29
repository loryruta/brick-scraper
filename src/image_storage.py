

def get_item_storage_path(item_type: str, color_id: str, item_id: str):
    return f"storage/{item_type}/img/{color_id}/{item_id}.png"


def get_item_storage_url(item_type: str, color_id: str, item_id: str):
    return f"/public/" + get_item_storage_path(item_type, color_id, item_id)


def get_set_image_url(set_id: int):
    set_img = f'storage/parts/img/'

    return None

