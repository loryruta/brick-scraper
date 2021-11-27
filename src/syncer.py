from dotenv import load_dotenv


load_dotenv()


from models import InventoryItem as LocalInventoryItem, Store, User, Op as SavedOp
from sqlalchemy import and_, or_
from db import Session
from stores import create_gateway_from, create_gateway_item_from, InventoryItem


def _lookup_inventory_item_ids(inv_item: InventoryItem) -> InventoryItem:
    pass  # TODO


def _process_master_store_inventory_changes(session, store: Store) -> None:
    gateway = create_gateway_from(store)

    evaluated_local_inventory_items = []

    for (_, inv_item) in gateway.get_items():
        inv_item = _lookup_inventory_item_ids(inv_item)

        key = {  # TODO configurable?
            'user_id': store.user_id,
            'item_id': inv_item.bl_id,
            'item_type': inv_item.type,
            'color_id': inv_item.bl_color_id,
            'condition': inv_item.condition,
            'user_remarks': inv_item.user_remarks,
        }

        # unit_price, quantity, user_description

        local_inv_item: LocalInventoryItem = \
            session.query(LocalInventoryItem) \
                .filter_by(**key) \
                .first()

        if not local_inv_item:
            local_inv_item = LocalInventoryItem(
                user_id=store.user_id,
                item_id=inv_item.bl_id,
                item_type=inv_item.type,
                color_id=inv_item.bl_color_id,
                condition=inv_item.condition,
                unit_price=inv_item.unit_price,
                quantity=inv_item.quantity,
                user_remarks=inv_item.user_remarks,
                user_description=inv_item.user_description,
            )

            session.add(local_inv_item)
            session.flush([local_inv_item])
            session.refresh(local_inv_item)
        else:
            local_inv_item.unit_price = inv_item.unit_price
            local_inv_item.quantity = inv_item.quantity
            local_inv_item.user_description = inv_item.user_description

        evaluated_local_inventory_items.append(local_inv_item.id)

    session.query(LocalInventoryItem) \
        .filter(and_(
            LocalInventoryItem.user_id == store.user_id,
            LocalInventoryItem.id.notin_(evaluated_local_inventory_items),
        )) \
        .delete()


def _process_slave_store_inventory_changes(session, store: Store) -> None:
    gateway = create_gateway_from(store)

    evaluated_local_inventory_items = []

    for (lot_id, inv_item) in gateway.get_items():
        inv_item = _lookup_inventory_item_ids(inv_item)

        key = {  # TODO configurable?
            'user_id': store.user_id,
            'item_id': inv_item.bl_id,
            'item_type': inv_item.type,
            'color_id': inv_item.bl_color_id,
            'condition': inv_item.condition,
            'user_remarks': inv_item.user_remarks,
        }

        # unit_price, quantity, user_description

        local_inv_item: LocalInventoryItem = \
            session.query(LocalInventoryItem) \
                .filter_by(**key) \
                .first()

        if not local_inv_item:
            gateway.delete_item(lot_id)
        else:
            changed = False
            changed |= local_inv_item.unit_price != inv_item.unit_price
            changed |= local_inv_item.quantity != inv_item.quantity
            changed |= local_inv_item.user_description != inv_item.user_description

            if changed:
                gateway.update_item(lot_id, inv_item)

        evaluated_local_inventory_items.append(local_inv_item.id)

    to_add_items = session.query(LocalInventoryItem) \
        .filter(and_(
            LocalInventoryItem.user_id == store.user_id,
            LocalInventoryItem.id.notin_(evaluated_local_inventory_items),
        )) \
        .all()
    for to_add_item in to_add_items:
        to_add_item = create_gateway_item_from(to_add_item)
        gateway.create_item(to_add_item)


def _process_inventory_changes(session, user_id: int) -> None:
    stores = session.query(Store) \
        .filter_by(id_user=user_id) \
        .all()
            
    master_store = [stores for store in stores if store.is_master][0]
    
    _process_master_store_inventory_changes(master_store)
    for slave_store in stores:
        if not slave_store.is_master:
            _process_slave_store_inventory_changes(slave_store)


def _initialize_inventory(session, user_id: int) -> None:
    session.query(LocalInventoryItem) \
        .filter_by(user_id=user_id) \
        .delete()

    _process_inventory_changes(session, user_id)


def start(session, user_id: int) -> bool:
    user = session.query(User) \
        .filter_by(user_id=user_id) \
        .first()

    if user.is_syncer_enabled:
        return False

    _initialize_inventory(session, user_id)

    return True


def run(session, user_id: int):
    return True


def stop(session, user_id: int):
    user = session.query(User) \
        .filter_by(id=user_id) \
        .first()

    if not user.is_syncer_enabled:
        return False

    session.query(SavedOp) \
        .filter(and_(
            SavedOp.id_user == user.id,
            or_(
                SavedOp.id_group == user.inventory_initialization_group_id,
                SavedOp.id_group == user.syncer_group_id,
            ),
        )) \
        .delete()

    user.inventory_initialization_group_id = None
    user.syncer_group_id = None
    user.is_inventory_initializing = False
    user.is_inventory_initialized = False
    user.is_syncer_enabled = False
    user.is_syncer_running = False
    session.flush([user])

    return True


if __name__ == "__main__":
    with Session.begin() as session:
        users = session.query(User) \
            .all()

        for user in users:
            start(session, user.id)

