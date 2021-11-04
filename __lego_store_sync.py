import sqlite3
import sys
import datetime
from dateutil import parser


class bcolors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    WHITE = "\u001b[37m"
    UNDERLINE = '\033[4m'


# -----


from dotenv import load_dotenv
load_dotenv()


import api_layer
import bricklink


con = sqlite3.connect("my.db", isolation_level=None)  # autocommit


def init_db():
    with open("dbsetup.sql") as f:
        con.executescript(f.read())


def clear_inventory(inv_id=0):
    con.execute('''
        delete from "inventory_entries" where "id_inventory" = ?
    ''', (inv_id,))


def clear_orders(inv_id=0):
    con.execute('''
        delete from "orders" where "id_inventory"=:inv_id
    ''', (inv_id,))


def upload_colors():
    colors = (
        (color['color_id'], color['color_name'], color['color_code'], color['color_type'])
        for color in bricklink.get_colors()
    )
    r = con.executemany('''
        insert or ignore into "colors" ("id", "name", "hex_code", "type") values (?, ?, ?, ?)
    ''', colors)
    if r.rowcount > 0:
        print(f"{r.rowcount} colors has been added.")


def upload_item_subsets(item_type, item_no, inv_id=0, set_condition='N', set_keyword=''):
    print("=================================================================")
    print(f"Uploading subsets of {item_no} ({item_type}) on inventory #{inv_id}")
    print("=================================================================")

    subsets = bricklink.get_subsets(item_type, item_no)

    # ----------------------------------------------------------------
    # Inserts the inventory entry if it wasn't present before.
    # ----------------------------------------------------------------

    params = (
        (
            inv_id,
            entry['item']['no'],
            entry['color_id'],
            set_condition,
            set_keyword
        )
        for subset in subsets for entry in subset['entries']
    )
    r = con.executemany('''
         insert or ignore into "inventory_entries" (
             "id_inventory",
             "item_bl_id", 
             "color_bl_id",
             "condition",
             "keyword",
             
             "available_quantity"
         ) values (?, ?, ?, ?, ?, 0)
     ''', params)

    print(f"Inserted {r.rowcount} entries inserted into the inventory #{inv_id}.")

    # ----------------------------------------------------------------
    # Updates the quantity of the entry.
    # ----------------------------------------------------------------

    params = [
        {
            "quantity": item['quantity'],
            "id_inventory": inv_id,
            "item_bl_id": item['item']['no'],
            "color_bl_id":  item['color_id'],
            "condition": set_condition,
            "keyword": set_keyword
        }
        for subset in subsets
        for item in subset['entries']
    ]
    r = con.executemany('''
        update "inventory_entries"
        set "available_quantity" = "available_quantity" + :quantity
        where
            "id_inventory" = :id_inventory and
            "item_bl_id" = :item_bl_id and 
            "color_bl_id" = :color_bl_id and 
            "condition" = :condition and 
            "keyword" = :keyword
        ''', params)

    print(f"Updated {r.rowcount} entries in the inventory #{inv_id}.")


def pull_shipped_orders(inv_id=0):
    con.execute("begin transaction;")

    orders = api_layer.get_orders()

    for order in orders:
        cur = con.execute('''
            insert or ignore into "orders" (
                "buyer_name",
                "date_ordered",
                "platform"
            ) values (
                :buyer_name,
                :date_ordered,
                :platform
            )
        ''', {
            "buyer_name": order.buyer_name,
            "date_ordered": order.date_ordered,
            "platform": order.platform,
        })

        if cur.rowcount > 0:
            item_group_id = 0
            for order_item in order.get_items():
                for item_id in order_item['item']['ids']:
                    con.execute('''
                        insert or ignore into "order_items" (
                            "id_order",
                            "item_group_id",
                            "item_id",
                            "color_bl_id",
                            "condition",
                            "keyword",
                            "purchased_quantity"
                        ) values (
                            :id_order,
                            :item_group_id,
                            :item_id,
                            :color_bl_id,
                            :condition,
                            :keyword,
                            :purchased_quantity
                        )
                    ''', {
                        "id_order": cur.lastrowid,
                        "item_group_id": item_group_id,
                        "item_id": item_id,
                        "color_bl_id": order_item['color_id'],
                        "condition": order_item['condition'],
                        "keyword": order_item['remarks'],
                        "purchased_quantity": order_item['quantity']
                    })
                item_group_id += 1

            print(f"Order #{cur.lastrowid} of {order.buyer_name} ({order.date_ordered}) added succesfully.")

    con.commit()


def clear_applied_orders(inv_id=0):
    cur = con.execute('''
        delete from "inventory_applied_orders" where "inventory_applied_orders"."id_inventory"=:inv_id
    ''', (inv_id,))


def apply_shipped_orders(inv_id=0):

    # Takes the orders that haven't been applied to the inventory and orders them chronologically (from older to newer).
    cur = con.execute('''
        select "orders".* from "orders"
        where
            "orders"."id" not in (
                select "inventory_applied_orders"."id_order" from "inventory_applied_orders"
                where
                    "inventory_applied_orders"."id_inventory"=:id_inventory
            )
        order by "orders"."date_ordered" asc
    ''', {
        "id_inventory": inv_id
    })

    orders = cur.fetchall()

    print("Found %d orders yet to be applied" % len(orders))

    order_ordinal = 0

    for (id_order, buyer_name, date_ordered, platform) in orders:

        print(
            f"{bcolors.YELLOW}================================================================\n"
            f"Order #{bcolors.CYAN}{order_ordinal}{bcolors.YELLOW}\n"
            f"Platform: {platform.upper()}\n"
            f"Buyer: {buyer_name}\n"
            f"Date ordered: {parser.parse(date_ordered).strftime('%d-%m-%Y %H:%M:%S')}\n"
            f"================================================================{bcolors.RESET}"
        )

        # ------------------------------------------------------------------------------------------------
        # Validation
        # ------------------------------------------------------------------------------------------------

        # Takes the purchased items that are missing in the inventory.

        cur = con.execute('''
            select *
            from order_items as purchase
            where
                purchase.id_order=:id_order and
                not exists ( -- The purchased items for which doesn't exist an entry in the inventory.
                    select *
                    from inventory_entries
                    where
                        inventory_entries.id_inventory=:id_inventory and 
                        inventory_entries.item_bl_id in ( -- The BL ID is equal to one of the IDs stored for the order item.
                            select order_items.item_id
                            from order_items
                            where
                                order_items.id_order = purchase.id_order and
                                order_items.item_group_id = purchase.item_group_id
                        )
                )
        ''', {
            'id_order': id_order,
            'id_inventory': inv_id
        })

        for missing_item in cur.fetchall():
            print(f"{bcolors.RED}Purchased item missing: {missing_item}{bcolors.RESET}")

        # Takes the purchased items whose quantity isn't sufficient in the inventory.

        cur = con.execute('''
            select *
            from order_items as purchase
            where
                purchase.id_order=:id_order and
                exists (
                    select *
                    from inventory_entries
                    where
                        inventory_entries.id_inventory=:id_inventory and 
                        inventory_entries.item_bl_id in (
                            select order_items.item_id
                            from order_items
                            where
                                order_items.id_order = purchase.id_order and
                                order_items.item_group_id = purchase.item_group_id
                        ) and
                        inventory_entries.color_bl_id=purchase.color_bl_id and
                        inventory_entries.condition=purchase.condition and
                        inventory_entries.keyword=purchase.keyword and
                        purchase.purchased_quantity > inventory_entries.available_quantity
                )
        ''', {
            'id_order': id_order,
            'id_inventory': inv_id
        })

        for not_enough_item in cur.fetchall():
            print(f"{bcolors.RED}Purchased item not enough quantity: {not_enough_item}{bcolors.RESET}")

        # ------------------------------------------------------------------------------------------------
        # Applying
        # ------------------------------------------------------------------------------------------------

        # Subtracts the purchased quantity to the available quantity in the inventory.
        con.execute("begin transaction;")

        # Creates a table that combines the items in the inventory with the order.
        con.execute('''
            create temporary table purchased_inventory as
                select
                    inventory_entries.rowid as id_entry,
                    inventory_entries.item_bl_id,
                    order_items.color_bl_id,
                    order_items.condition,
                    order_items.keyword,
                    inventory_entries.available_quantity,
                    order_items.purchased_quantity
                from inventory_entries
                join order_items on
                    inventory_entries.item_bl_id = order_items.item_id and
                    inventory_entries.color_bl_id = order_items.color_bl_id and
                    inventory_entries.condition = order_items.condition and
                    inventory_entries.keyword = order_items.keyword
                where
                    order_items.id_order=:id_order and
                    inventory_entries.id_inventory=:id_inventory;
        ''', {
            'id_inventory': inv_id,
            'id_order': id_order
        })

        # Debugs the operation.
        cur = con.execute('''
            select * from "purchased_inventory"
        ''')
        for purchased_item in cur.fetchall():
            print(f"{purchased_item[1:4]} - You have {purchased_item[5]} and {purchased_item[6]} have been purchased.")

        # sadf
        cur = con.execute('''
            update inventory_entries
            set available_quantity = available_quantity - (
                select purchased_quantity
                from purchased_inventory
                where
                    purchased_inventory.id_entry=inventory_entries.rowid
            )
            where
                inventory_entries.rowid in (
                    select id_entry from purchased_inventory
                )
        ''')
        con.execute('drop table purchased_inventory;')
        con.commit()

        print("Updated quantity for %d items" % cur.rowcount)

        # Remove items that have a 0 (or negative) quantity (shouldn't be negative).

        cur = con.execute('''
            delete from "inventory_entries"
            where
                "inventory_entries"."id_inventory"=:inv_id and 
                "inventory_entries"."available_quantity" <= 0
        ''', (inv_id,))

        print("Deleted %d items from the inventory" % cur.rowcount)

        order_ordinal += 1


def main():

    try:
        init_db()

        upload_colors()

        clear_orders(0)
        pull_shipped_orders(0)

        clear_inventory()
        clear_applied_orders()

        # Pulls down the items back from the beginning.

        upload_item_subsets("SET", "10278-1", set_condition="N", set_keyword="")  # Police Station
        upload_item_subsets("SET", "8070-1", set_condition="U", set_keyword="8070")  # Supercar
        upload_item_subsets("SET", "8069-1", set_condition="U", set_keyword="")  # Backhoe Loader

        apply_shipped_orders()

    finally:
        con.close()


if __name__ == '__main__':
    main()
