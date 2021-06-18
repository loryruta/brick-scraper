
-- ------------------------------------------------------------------------------------------------ colors

CREATE TABLE IF NOT EXISTS "colors"
(
    "id" INT NOT NULL,
    "name" VARCHAR(256) NOT NULL,
    "hex_code" VARCHAR(8) NOT NULL,
    "type" VARCHAR(64) NOT NULL,

    PRIMARY KEY ("id")
);

-- ------------------------------------------------------------------------------------------------ items

CREATE TABLE IF NOT EXISTS "items"
(
    "no"            VARCHAR(256) NOT NULL,
    "type"          VARCHAR(32) NOT NULL,
    "name"          VARCHAR(2048),
    "id_category"   INT NOT NULL,

    PRIMARY KEY ("no", "type")
);

-- ------------------------------------------------------------------------------------------------ inventories

CREATE TABLE IF NOT EXISTS "inventories" (
    "id" INT AUTO_INCREMENT,

    PRIMARY KEY ("id")
);

INSERT OR IGNORE INTO "inventories"("id") VALUES (0);

-- ------------------------------------------------------------------------------------------------ inventory_entries

CREATE TABLE IF NOT EXISTS "inventory_entries"
(
    "id_inventory" INT NOT NULL,
    "item_type" VARCHAR(32) NOT NULL, -- Item
    "item_no" VARCHAR(256) NOT NULL,
    "id_color" INT NOT NULL,
    "quantity" INT NOT NULL,

    PRIMARY KEY ("id_inventory", "item_type", "item_no", "id_color"),
    FOREIGN KEY ("id_inventory") REFERENCES "inventories"("id"),
    FOREIGN KEY ("item_no", "item_type") REFERENCES "items"("no", "type"),
    FOREIGN KEY ("id_color") REFERENCES "colors"("id")
);

-- ------------------------------------------------------------------------------------------------ inventory_pulled_orders

CREATE TABLE IF NOT EXISTS "inventory_pulled_orders"
(
    "id_inventory" int not null,
    "buyer_name" varchar(256) not null,
    "date_ordered" timestamp not null,

    primary key ("id_inventory", "buyer_name", "date_ordered"),
    foreign key ("id_inventory") references "inventories"("id")
)

