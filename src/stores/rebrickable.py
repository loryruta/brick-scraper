import os
import requests
import json
from typing import Any, Dict, TypedDict, Generator, List, Mapping, Optional
import urllib.parse


class Color:
    class ExternalIds:
        ext_ids: List[int]
        ext_descrs: List[List[str]]

    id: int
    name: str
    rgb: str
    is_trans: bool
    external_ids: Mapping[str, ExternalIds]


class Part(TypedDict):
    part_num: str
    name: str
    part_cat_id: int
    part_url: str
    part_img_url: str
    external_ids: Mapping[str, List[int]]


class Set(TypedDict):
    set_num: str
    name: str
    year: int
    theme_id: int
    num_parts: int
    set_img_url: str
    set_url: str
    last_modified_dt: str


class SetPart(TypedDict):
    id: int
    inv_part_id: int
    part: Part
    color: Color
    set_num: str
    quantity: int
    is_spare: bool
    element_id: Optional[int]
    num_sets: int


class InvalidRequest(Exception):
    pass


def _build_request_url(path: str, params: Mapping[str, str] = {}):
    endpoint = os.environ['REBRICKABLE_ENDPOINT']

    params['key'] = os.environ['REBRICKABLE_API_KEY']

    encoded_params = urllib.parse.urlencode(params)
    return f"{endpoint}/{path}?{encoded_params}"


def _send_request(method: str, url: str) -> Generator[Any, None, None]:
    response = requests.request(method, url)
    if response.status_code != 200:
        raise InvalidRequest((response.content, response.status_code))

    parsed_response = json.loads(response.content)
    return parsed_response


def _issue_request(method: str, path: str, params: Mapping[str, str]) -> Dict:
    url = _build_request_url(path, params)
    return _send_request(method, url)


def _issue_multipage_request(method: str, path: str, params: Mapping[str, str]) -> Generator[Any, None, None]:
    key = os.environ['REBRICKABLE_API_KEY']
    params['page'] = 1
    url = _build_request_url(path, params)

    while True:
        parsed_response = _send_request(method, url)
        for result in parsed_response['results']:
            yield result
        if parsed_response['next'] is None:
            break
        url = parsed_response['next']
        url += f"&key={key}"


def get_colors() -> Color:
    return _issue_multipage_request("GET", f'lego/colors', {})


def get_set(set_num: str) -> Set:
    return _issue_request("GET", f'lego/sets/{set_num}/', {})


def get_set_parts(set_num: str) -> Generator[Part, None, None]:
    return _issue_multipage_request("GET", f'lego/sets/{set_num}/parts', {})

