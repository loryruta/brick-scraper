from time import time
from models import User
from typing import Callable
from db import Session


class none:
    def get_wait_time(user: User) -> int:
        return 0

    def issue(user: User, f: Callable) -> None:
        f()


class bricklink:
    MAX_REQUESTS_PER_HOUR = 10000

    def get_wait_time(user: User) -> int:
        if (user.bl_current_hour_requests_count or 0) < bricklink.MAX_REQUESTS_PER_HOUR:
            return 0

        hour_sec = 60 * 60
        cur_sec = int(time())
        cur_hour = int(cur_sec / (hour_sec))
        if cur_hour != user.bl_current_hour:
            return 0
        
        return cur_sec - cur_sec % hour_sec

    def issue(user: User, f: Callable) -> None:
        cur_hour = int(time() / (60 * 60))
        if cur_hour != user.bl_current_hour:
            user.bl_current_hour = cur_hour
            user.bl_current_hour_requests_count = 0
        f()
        user.bl_current_hour_requests_count += 1
        Session.object_session(user).flush([user])


class bricklink_api:
    MAX_REQUESTS_PER_DAY = 5000

    def get_wait_time(user: User) -> int:
        if (user.bl_api_current_day_requests_count or 0) < bricklink_api.MAX_REQUESTS_PER_DAY:
            return 0

        day_sec = (24 * 60 * 60)

        cur_sec = int(time())
        cur_day = int(cur_sec / day_sec)
        if cur_day != user.bl_api_current_day:
            return 0

        return day_sec - cur_sec % day_sec
        
    def issue(user: User, f: Callable) -> None:
        cur_day = int(time() / (24 * 60 * 60))
        if cur_day != user.bl_api_current_day:
            user.bl_api_current_day = cur_day
            user.bl_api_current_day_requests_count = 0
        f()
        user.bl_api_current_day_requests_count += 1
        Session.object_session(user).flush([user])


class brickowl_api:
    MAX_REQUESTS_PER_MINUTE = 600

    def get_wait_time(user: User) -> int:
        if (user.bo_api_current_minute_requests_count or 0) < brickowl_api.MAX_REQUESTS_PER_MINUTE:
            return 0
    
        cur_sec = int(time())
        cur_min = int(cur_sec / 60)
        if cur_min != user.bo_api_current_minute:
            return 0

        return 60

    def issue(user: User, f: Callable) -> None:
        cur_min = int(time() / 60)
        if cur_min != user.bo_api_current_minute:
            user.bo_api_current_minute = cur_min
            user.bo_api_current_minute_requests_count = 0
        f()
        user.bo_api_current_minute_requests_count += 1
        Session.object_session(user).flush([user])  # TODO UPDATE THE USER FIELDS IMMEDIATELY! (begin a new session + transaction)


