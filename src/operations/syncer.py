from op import Registry
from db import Session
from models import User


def set_running(user: User, running: bool):
    user.syncer_running = running
    Session.object_session(user).flush([user])


@Registry.register
class syncer_begin:
    def execute(self):
        user = self.user
        set_running(user, True)


@Registry.register
class syncer_end:
    def execute(self):
        user = self.user
        set_running(user, False)


