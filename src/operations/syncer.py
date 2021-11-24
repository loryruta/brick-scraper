from op import Registry


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
