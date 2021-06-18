import sqlite3
from dotenv import load_dotenv


load_dotenv()


import lego_reseller_manager
import bricklink


con = sqlite3.connect("my.db", isolation_level=None)  # autocommit


def init_db():
    with open("dbsetup.sql") as f:
        con.executescript(f.read())


def clear_inv(inv_id=0):
    con.execute('''
        delete from "inventory_entries" where "id_inventory" = ?
    ''', (inv_id,))

    con.execute('''
        delete from "inventory_pulled_orders" where "id_inventory" = ?
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


def upload_item_subsets(item_type, item_no, inv_id=0):

    print("=================================================================")
    print(f"Uploading subsets of {item_no} ({item_type}) on inventory #{inv_id}")
    print("=================================================================")

    subsets = bricklink.get_subsets(item_type, item_no)

    # ----------------------------------------------------------------
    # Adds the item types to the internal database.
    # ----------------------------------------------------------------

    params = (
        (entry['item']['no'], entry['item']['type'], entry['item']['name'], entry['item']['category_id'])
        for subset in subsets for entry in subset['entries']
    )
    r = con.executemany('''
        insert or ignore into "items" ("no", "type", "name", "id_category") values (?, ?, ?, ?)
    ''', params)

    print(f"Inserted {r.rowcount} new items in the DB.")

    # ----------------------------------------------------------------
    # Inserts the inventory entry if it wasn't present before.
    # ----------------------------------------------------------------

    params = (
        (inv_id, entry['item']['type'], entry['item']['no'], entry['color_id'])
        for subset in subsets for entry in subset['entries']
    )
    r = con.executemany('''
         insert or ignore into "inventory_entries" ("id_inventory", "item_type", "item_no",  "id_color", "quantity")
             values (?, ?, ?, ?, 0)
     ''', params)

    print(f"Inserted {r.rowcount} entries inserted into the inventory #{inv_id}.")

    # ----------------------------------------------------------------
    # Updates the quantity of the entry.
    # ----------------------------------------------------------------

    params = (
        (entry['quantity'], inv_id, entry['item']['type'], entry['item']['no'], entry['color_id'])
        for subset in subsets for entry in subset['entries']
    )
    r = con.executemany('''
        update "inventory_entries" set "quantity" = "quantity" + ?
            where
                "id_inventory" = ? and
                "item_type" = ? and 
                "item_no" = ? and 
                "id_color" = ?
        ''', params)

    print(f"Updated {r.rowcount} entries in the inventory #{inv_id}.")


def pull_shipped_orders(inv_id=0):

    print("=================================================================")
    print(f"Pulling shipped orders on inventory #{inv_id}")
    print("=================================================================")

    orders = lego_reseller_manager.get_orders()
    orders.sort(key=lambda _order: _order.date_ordered)

    for order in orders:
        cur = con.execute('''
            insert or ignore into "inventory_pulled_orders" ("id_inventory", "buyer_name", "date_ordered") values (?, ?, ?)
        ''', (inv_id, order.buyer_name, order.date_ordered))
        if cur.rowcount == 0:
            continue

        print(f"Pulling order: {order.buyer_name} ({order.date_ordered})...")

        order_items = order.get_items()

        # ----------------------------------------------------------------
        # Removes the ordered quantity from the entries in the inventory.
        # ----------------------------------------------------------------

        params = (
            (order_item['quantity'], inv_id, order_item['item']['no'], order_item['item']['type'], order_item['color_id'])
            for order_item in order_items
        )
        cur = con.executemany('''
            update "inventory_entries"
            set "quantity" = "quantity" - ?
            where
                "id_inventory" = ? and
                "item_no" = ? and
                "item_type" = ? and 
                "id_color" = ?
        ''', params)

        print(f"- {cur.rowcount} items affected by this order.")

        # ----------------------------------------------------------------
        # Removes the entries that have 0 quantity (or less).
        # ----------------------------------------------------------------

        cur = con.execute('''
            delete from "inventory_entries"
            where "id_inventory" = ? and "quantity" <= 0
        ''', (inv_id,))

        print(f"- {cur.rowcount} items removed because of this order.")


def main():

    try:
        init_db()

        clear_inv()

        upload_colors()

        upload_item_subsets("SET", "10278-1")  # Police Station
        upload_item_subsets("SET", "8070-1")  # Supercar
        upload_item_subsets("SET", "8069-1")  # Backhoe Loader

        pull_shipped_orders()

    finally:
        con.close()


if __name__ == '__main__':
    main()
