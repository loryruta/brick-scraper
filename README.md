# BrickScraper

The user has the possibility to have a set of LEGO stores (e.g.: Bricklink, BrickOwl, ...), all sharing
the same physical inventory and the system must be able to keep the inventory of those
updated based on orders originating from all stores.

## How to run

```
docker-compose up -d db
docker-compose up app
```

You can then connect to the web service at `localhost:5000`.

## Syncing procedure

### Initialization

In first place, the system has to have a unfied view of the global inventory. In order
to achieve it we need to visit the inventory of all stores configured, and we can have
the following scenario:

1. ITEM_1 is present in STORE_1 with some parameters (like quantity and price) that are different in STORE_2:
    
    *Do not add ITEM_1 and signal the error.*

2. ITEM_1 is present in STORE_1 but absent in STORE_2:
    
    *Add ITEM_1.*

3. ITEM_1 is present in STORE_1 and in STORE_2 with the same parameters:
    
    *Add ITEM_1 (really nice).*

In the case (1.) we can let the user decide what to do:
- keep the item as it is in STORE_1 (and thus send an update to STORE_2)
- keep the item as it is in STORE_2 (and thus send an update to STORE_1)

We can make this process more user-friendly by letting the user decide **which is the master store**.
So, if STORE_1 is the master, items of STORE_1 will always replace parameters of items of STORE_2. 
Still, it's useful to keep a log of inconsistensies (1., 2.).

### Order pulling & applying

Now, having an unified view of the inventory, we can start the syncing activity. To avoid the user
setting additional webhooks in order to "real-time" listen when an order is received, it's run a
periodical task that pulls orders from stores and detects new entries.

The orders are pulled from every store and sorted by ordered date and when a new order is received there
could be the following scenario:

1. ITEM_1 isn't present in the local inventory or present with wrong parameters (ITEM_1 quantity < ordered quantity):
     
     *Signal the error (critical error: where the item spawned at?).*

2. ITEM_1 is present and parameters fit the ordered item parameters:

     *Apply the order to the local inventory item.*

Supposing the order is coming from STORE_1, I need to update STORE_2, STORE_3 (...). The "update" consists of 
decreasing the item quantity or delete the ordered item. 

### Handling inventory updates

Inventory updates are detected by a periodical task that compare the local inventory against the remote
inventory. The behavior of inventory updates can vary whether the updated store is the master store or the slave store.

If STORE_1 is our **master store**, there could be the following cases:

1. LOCAL_INVENTORY has ITEM_1 and REMOTE_STORE_1 doesn't have ITEM_1 (ITEM_1 remotely removed).
    
    *Remove ITEM_1 locally and synchronize remote slave stores.*

2. LOCAL_INVENTORY doesn't have ITEM_1 and REMOTE_STORE_1 have ITEM_1 (ITEM_1 remotely added).
    
    *Add ITEM_1 locally and synchronize remote slave stores.*

2. LOCAL_INVENTORY has ITEM_1 w/ different parameters than REMOTE_STORE_1:
    
    *Update ITEM_1 locally and synchronize remote slave stores.*

If STORE_1 is our **slave store**, there could be the same possibilities but the behavior is different:

1. LOCAL_INVENTORY has ITEM_1 and REMOTE_STORE_1 doesn't have ITEM_1 (ITEM_1 remotely removed).
    
    *Add ITEM_1 to REMOTE_STORE_1.*

2. LOCAL_INVENTORY doesn't have ITEM_1 and REMOTE_STORE_1 have ITEM_1 (ITEM_1 remotely added).
    
    *Remove ITEM_1 from REMOTE_STORE_1.*

2. LOCAL_INVENTORY has ITEM_1 w/ different parameters than REMOTE_STORE_1:
    
    *Update ITEM_1 as it is locally.*

But what if the inventory update was triggered by an order?

E.g. An order on a slave store decreses the quantity of an item which is suddenly restored because the local inventory hasn't changed. 

To avoid this issue the sequantial procedure must go this way:
1. Order pulling & applying from different stores
*If the order comes here we have a synchronization error, but it's unavoidable and very unlucky.*
2. Inventory updates test

**The initialization operation can be trated as a inventory update where the LOCAL_INVENTORY is empty.**

**IMPORTANT NOTE:**

**IT IS FORBIDDEN TO UPDATE SLAVE STORES INVENTORIES. ALL INVENTORY OPERATIONS MUST HAPPEN ON THE MASTER STORE INVENTORY.**

### Handling items mismatchings

It could happen that an ITEM_1 of STORE_1 can't be matched with a representation of STORE_2:

1. If STORE_1 is the master store, the the item is still kept locally and synchronized with stores that provide a matching representation.
2. If STORE_1 is the slave store, this situation is impossible, because slave stores will always have at most master store's items.

All mismatchings should be visualized on a web interface.
