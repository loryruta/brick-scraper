from op import Registry
from models import InventoryPart
import rate_limiter


@Registry.register
class clear_inventory:
    params = []
    rate_limiter = rate_limiter.none

    def execute(self):
        session = self.session
        user = self.user

        session.query(InventoryPart) \
            .filter_by(id_user=user.id) \
            .delete()

