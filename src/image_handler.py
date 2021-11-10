

def get_part_image_storage_path(color_id: str, part_id: str):
    return f'storage/parts/img/{color_id}/{part_id}.png'


def get_part_image_url(color_id: str, part_id: str):
    return f'/public/' + get_part_image_storage_path(color_id, part_id)


def get_set_image_url(set_id: int):
    set_img = f'storage/parts/img/'

    return None

