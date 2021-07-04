
-- ------------------------------------------------------------------------------------------------ colors

CREATE TABLE IF NOT EXISTS "colors"
(
    "id" INT NOT NULL,
    "name" VARCHAR(256) NOT NULL,
    "hex_code" VARCHAR(8) NOT NULL,
    "type" VARCHAR(64) NOT NULL,

    PRIMARY KEY ("id")
);

-- ------------------------------------------------------------------------------------------------ inventories

CREATE TABLE IF NOT EXISTS "inventories" (
    "id" INT AUTO_INCREMENT,

    PRIMARY KEY ("id")
);

INSERT OR IGNORE INTO "inventories"("id") VALUES (0);

-- ------------------------------------------------------------------------------------------------ inventory_entries

-- This table describes an item within a certain inventory (an inventory entry).
-- Additionally to item's fields, it has a color, a condition and a private note

create table if not exists "inventory_entries"
(
    "id_inventory" int not null,

    "item_bl_id" varchar(256) not null,
    "color_bl_id" int not null,
    "condition" character(1) not null, -- U or N
    "keyword" varchar(255) not null,

    "available_quantity" int not null default 0,

    primary key ("id_inventory", "item_bl_id", "color_bl_id", "condition", "keyword"),
    foreign key ("id_inventory") references "inventories"("id") on delete cascade
);

-- ------------------------------------------------------------------------------------------------ orders

create table if not exists "orders"
(
    "id" integer primary key,
    "buyer_name" varchar(256) not null,
    "date_ordered" timestamp not null,
    "platform" varchar(256) not null,

    unique ("buyer_name", "date_ordered")
);

-- ------------------------------------------------------------------------------------------------ order_items

create table if not exists "order_items"
(
    "id_order" int not null,

    "item_group_id" int not null,
    "item_id" varchar(256) not null,
    "color_bl_id" int not null,
    "condition" character(1) not null,
    "keyword" varchar(255) not null,

    "purchased_quantity" unsigned int not null default 0,

    primary key ("id_order", "item_group_id", "item_id", "color_bl_id", "condition", "keyword"),
    foreign key ("id_order") references "orders"("id") on delete cascade
);

create table if not exists "inventory_applied_orders"
(
    "id_inventory" int not null,
    "id_order" int not null,

    primary key ("id_inventory", "id_order"),
    foreign key ("id_inventory") references "inventories"("id"),
    foreign key ("id_order") references "orders"("id")
);
