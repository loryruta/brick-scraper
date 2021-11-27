from models import InventoryItem, Store as StoreCredentials
from op import Registry, run_, async_
from stores import create_gateway_from



@Registry.register
class _SyncerGroup:
    def execute(self):
        session = self.session
        user = self.user
        group_id = self.saved_op.id

        user.syncer_group_id = group_id
        session.flush([user])


@Registry.register
class _SetSyncerRunning:
    params = ['flag']

    def execute(self):
        session = self.session
        user = self.user

        user.is_syncer_running = self.saved_op.params['flag']
        session.flush([user])


@Registry.register
class _PullAndApplyOrdersGroup:
    display_name = "Pull & apply orders"


@Registry.register
class _CheckInventoryUpdatesGroup:
    display_name = "Check inventory updates"


@Registry.register
class _EndInventoryInitialization:
    def execute(self):
        session = self.session
        user = self.user

        user.inventory_initialization_group_id = None
        user.is_inventory_initializing = False
        user.is_inventory_initialized = True
        session.flush([user])


@Registry.register
class _InitializeInventoryGroup:
    display_name = "Initialize inventory"

    def execute(self):
        session = self.session
        user = self.user
        group_id = self.saved_op.id

        user.inventory_initialization_group_id = group_id
        session.flush([user])


@Registry.register
class LookupInventoryItemBlId:
    params = ['inv_item']

    def execute(self):
        pass


@Registry.register
class LookupInventoryItemBoId:
    params = ['inv_item']

    def execute(self):
        pass


@Registry.register
class LookupInventoryItemBlColorId:
    params = ['inv_item']

    def execute(self):
        pass


@Registry.register
class LookupInventoryItemBoColorId:
    params = ['inv_item']

    def execute(self):
        pass


@Registry.register
class LookupInventoryItemIds:
    params = ['inv_item']

    def execute(self):
        session = self.session
        inv_item = self.saved_op.params['inventory_item']

        ops = []
        
        if inv_item['bl_id'] is None:       ops.append(run_(LookupInventoryItemBlId(inv_item=inv_item)))
        if inv_item['bl_color_id'] is None: ops.append(run_(LookupInventoryItemBlColorId(inv_item=inv_item)))

        if inv_item['bo_id'] is None:       ops.append(run_(LookupInventoryItemBoId(inv_item=inv_item)))
        if inv_item['bo_color_id'] is None: ops.append(run_(LookupInventoryItemBoColorId(inv_item=inv_item)))

        self.schedule_child(session, async_(*ops))


@Registry.register
class HandleMasterStoreInventoryUpdate:
    params = ['store_id']

    def execute(self):
        session = self.session
        user = self.user
        params = self.saved_op.params

        credentials = session.query(StoreCredentials) \
            .filter_by(id=params['store_id']) \
            .first()

        gateway = create_gateway_from(credentials)
        for inv_item in gateway.get_items():
            # Is the item present in local inventory?
            local_inv_item = session.query(InventoryItem) \
                .filter_by(
                    user_id=user.id,
                    item_id=inv_item.bl_id,
                    item_type=inv_item.type,
                    color_id=inv_item.bl_color_id,

                ) \
                .first()


@Registry.register
class HandleSlaveStoreInventoryUpdate:
    params = ['store_id']

    def execute(self):
        session = self.session
        params = self.saved_op.params

        credentials = session.query(StoreCredentials) \
            .filter_by(id=params['store_id']) \
            .first()

        gateway = create_gateway_from(credentials)
        for inv_item in gateway.get_items():
            pass


@Registry.register
class HandleInventoryUpdate:
    def execute(self):
        session = self.session
        user = self.user



        children = []
        children.append(HandleMasterStoreInventoryUpdate(master_store.id))
        for slave_store in slave_stores:
            children.append(HandleSlaveStoreInventoryUpdate(slave_store.id))
        self.schedule_child(session, *children)

