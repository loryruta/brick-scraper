from typing import List
from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select


load_dotenv()


from models import Color, InventoryItem as LocalInventoryItem, Item, User, Op as SavedOp
from sqlalchemy import and_, or_, null
from db import Session
from backends.bricklink import Bricklink as BricklinkAPI
from backends.brickowl import BrickOwl as BrickOwlAPI


class CantIdentifyInventoryItem(RuntimeError):
    pass


def _norm_bl_item_type(type: str):
    return {
        'PART': 'part',
        'MINIFIG': 'minifig',
        'SET': 'set',
    }[type]  # TODO FIX-ME What if type is not found?


def _norm_bl_condition(condition: str):
    return condition


def _norm_bo_item_type(item_type: str):
    return {
        'Part': 'part',
        'Minifigure': 'minifig',
        'Set': 'set',
    }[item_type]  # TODO FIX-ME What if type is not found?


def _norm_bo_condition(condition: str):
    return {
        'new': 'N',
        'news': 'N',
        'newc': 'N',
        'newi': 'N',
        'used': 'U',
        'usedc': 'U',
        'usedi': 'U',
        'usedn': 'U',
        'usedg': 'U',
        'useda': 'U',
        # other
    }[condition]


def _spec_item_type_to_bo(item_type: str):
    return {
        'part': 'Part',
        'minifig': 'Minifigure',
        'set': 'Set',
    }[item_type]


def _spec_condition_to_bo(condition: str):
    return {
        'N': 'new',
        'U': 'usedn',
    }[condition]


class Syncer:
    def __init__(self, user_id: int):
        self.user_id = user_id

        with Session() as session:
            self.user = session.query(User).filter_by(id=user_id).first()
            self.bl_api = BricklinkAPI(user.bl_customer_key, user.bl_customer_secret, user.bl_token_value, user.bl_token_secret)
            self.bo_api = BrickOwlAPI(user.bo_key)


    def _process_bl_store_inventory_changes(self, session) -> None:
        evaluated_local_inventory_items = []

        items = self.bl_api.get_inventories()
        print(f"Found {len(items)} on BL...")

        processed_count = 0

        for item in items:
            item_id = item['item']['no']
            item_type = _norm_bl_item_type(item['item']['type'])
            color_id = item['color_id']
            condition = _norm_bl_condition(item['new_or_used'])
            user_remarks= item['remarks'] or ''
            unit_price = float(item['unit_price'])
            quantity = int(item['quantity'])
            user_description = item['description'] or ''

            key = [
                'user_id', 'item_id', 'item_type', 'color_id', 'condition', 'user_remarks'
            ]

            values = {
                'user_id': self.user_id,
                'item_id': item_id,
                'item_type': item_type,
                'color_id': color_id,
                'condition': condition,
                'unit_price': unit_price,
                'quantity': quantity,
                'user_remarks': user_remarks,
                'user_description': user_description,
            }

            # Tries to insert the element in the inventory, on conflict updates the variable parameters.
            inv_item_id = \
                session.execute(
                    insert(LocalInventoryItem)
                        .values(**values)
                        .on_conflict_do_update(
                            index_elements=key,
                            set_=values
                        )
                        .returning(LocalInventoryItem.id)
                ) \
                .first()[0]

            processed_count += 1
            if processed_count % 100 == 0:
                print(f"Processed {processed_count}/{len(items)}...")

            evaluated_local_inventory_items.append(inv_item_id)

        print(f"Processed {processed_count}/{len(items)}")

        # Deletes local inventory items that haven't been detected remotely.
        loc_del_count = session.query(LocalInventoryItem) \
            .filter(and_(
                LocalInventoryItem.user_id == self.user_id,
                LocalInventoryItem.id.notin_(evaluated_local_inventory_items),
            )) \
            .delete()
        print(f"Deleted {loc_del_count} local inventory items missing on BL")


    def _process_bo_store_inventory_changes(self, session) -> None:
        evaluated_local_inventory_items = []

        for inv_entry in self.bo_api.get_inventory_list():
            lot_id: str = inv_entry['lot_id']
            boid: str = inv_entry['boid']  # BOID has <ID>-<COLOR>

            item_boid = boid.split('-')[0]
            item_type = _norm_bo_item_type(inv_entry['type'])
            condition = _norm_bo_condition(inv_entry['con'])
            user_remarks = inv_entry['personal_note'] or ''
            unit_price = float(inv_entry['price'])
            quantity = int(inv_entry['qty'])
            user_description = inv_entry['public_note'] or ''

            item_ids = session.query(Item.id) \
                .filter(and_(
                    Item.type == item_type,
                    Item.bo_id == item_boid,
                )) \
                .all()

            item_ids = [_id for (_id,) in item_ids]

            if len(item_ids) == 0:
                print(f"WARNING: No BL item ID found for BOID: {boid}")
                continue

            # If the color is present, tries to retrieve the BL color ID by the BO color ID.
            bo_color_id = boid.split('-')[1] if '-' in boid else None
            color_id = 0

            if bo_color_id:
                color: Color = session.query(Color) \
                    .filter_by(bo_id=bo_color_id) \
                    .first()
                
                if color != None:
                    color_id = color.id
                else:
                    print(f"WARNING: Couldn't find a matching color ID for: {bo_color_id}")  # TODO delete on BO?
                    continue

            # Pivot key parameters (TODO configurable?):
            key = {
                'user_id': self.user_id,
                'item_type': item_type,
                'condition': condition,
                'color_id': color_id,
                'user_remarks': user_remarks,
            }

            # Variable parameters:
            # unit_price, quantity, user_description ...

            local_inv_item = session.query(LocalInventoryItem) \
                .filter_by(**key) \
                .filter(LocalInventoryItem.item_id.in_(item_ids)) \
                .first()

            # The item couldn't be found in the local inventory, deletes it remotely.
            if not local_inv_item:
                self.bo_api.delete_inventory(lot_id=lot_id)

                print(f"Pivot: {key}")
                print(f"> BOID item {boid} ({item_type}) (possible IDs: {item_ids}) isn't present locally, deleting it on BO...")
            else:
                changed = {
                    'unit_price': (local_inv_item.unit_price, unit_price),
                    'quantity': (local_inv_item.quantity, quantity),
                    'user_description': (local_inv_item.user_description, user_description),
                }

                changed = [
                    (k, (loc_val, bo_val))
                    for k, (loc_val, bo_val) in changed.items() if loc_val != bo_val
                ]

                # The item has been found, but its parameters are different, updates the remote item with currents'.
                if len(changed) > 0:
                    self.bo_api.update_inventory(lot_id, **{
                        'absolute_quantity': local_inv_item.quantity,
                        'price': local_inv_item.unit_price,
                        'public_note': local_inv_item.user_description,
                    })
                    print(f"> Item {local_inv_item.item_id} ({boid}) ({item_type}) has changed on BO: {changed}")

                evaluated_local_inventory_items.append(local_inv_item.id)

        # Gets all the local items that haven't be matched with remote items,
        # for those create an entry in the remote inventory.
        to_add_items = session.query(LocalInventoryItem) \
            .filter(and_(
                LocalInventoryItem.user_id == self.user_id,
                LocalInventoryItem.id.notin_(evaluated_local_inventory_items),
            )) \
            .all()
        for item in to_add_items:
            result = self.bo_api.create_inventory(**{
                'boid': item.item.bo_id,
                'color_id': item.color.bo_id if item.color else None,
                'quantity': item.quantity,
                'price': item.unit_price,
                'condition': _spec_condition_to_bo(item.condition),
            })

            lot_id = result['lot_id']
            self.bo_api.update_inventory(lot_id, **{
                'personal_note': item.user_remarks,
                'public_note':item.user_description,
            })

            print(f"Local item {item.item_id} ({item.item_type}) created on BO...")


    def _process_inventory_changes(self, session) -> None:
        self._process_bl_store_inventory_changes(session)  # Master store
        self._process_bo_store_inventory_changes(session)  # Slave store


    def _initialize_inventory(self, session) -> None:
        session.query(LocalInventoryItem) \
            .filter_by(user_id=self.user_id) \
            .delete()

        self._process_inventory_changes(session)


    def start(self) -> bool:
        with Session.begin() as session:
            user = session.query(User) \
                .filter_by(id=self.user_id) \
                .first()

            if user.is_syncer_enabled:
                return False

            print("Initializing inventory...")

            self._initialize_inventory(session)

            return True


    def run(self) -> bool:
        return True


    def stop(self) -> bool:
        return True


if __name__ == "__main__":
    with Session.begin() as session:
        users = session.query(User) \
            .all()

        for user in users:
            syncer = Syncer(user.id)
            syncer.start()
