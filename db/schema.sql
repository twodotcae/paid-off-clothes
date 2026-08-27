-- Paid Off Clothes — relational schema.
--
-- SQLite, because it is a real database (ACID transactions, foreign keys, indexes, SQL) that ships
-- inside Python's standard library. The project's zero-dependency property survives, it behaves
-- identically on the Mac and the Windows PC, and the whole database is one file that can be copied,
-- diffed and restored. Moving to Postgres later is a dialect change, not a redesign.
--
-- Money is stored in CENTS as INTEGER. Floats cannot represent 24.99 exactly, and a catalogue that
-- reprices itself through repeated float round-trips is a real hazard once orders reference it.
-- The JSON projection converts back to decimal on the way out.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
  name             TEXT PRIMARY KEY,
  position         INTEGER NOT NULL,   -- order in products.json, which drives the filter tiles
  bulk_noun        TEXT,
  pricing_position INTEGER             -- order in pricing.json, kept so the projection is faithful
);

CREATE TABLE IF NOT EXISTS products (
  id           TEXT PRIMARY KEY,              -- permanent slug; never reused
  name         TEXT NOT NULL UNIQUE,          -- the cart and pricing still key on this
  brand        TEXT NOT NULL DEFAULT '[brand?]',
  category     TEXT NOT NULL REFERENCES categories(name) ON UPDATE CASCADE,
  description  TEXT NOT NULL DEFAULT '',
  image        TEXT,
  retail_cents INTEGER NOT NULL CHECK (retail_cents >= 0),
  bulk_cents   INTEGER CHECK (bulk_cents IS NULL OR bulk_cents >= 0),
  bulk_min_qty INTEGER CHECK (bulk_min_qty IS NULL OR bulk_min_qty > 0),
  status       TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available','sold')),
  featured     INTEGER NOT NULL DEFAULT 0 CHECK (featured IN (0,1)),
  position     INTEGER NOT NULL,             -- catalogue order, from products.json
  pricing_position INTEGER                    -- order in pricing.json, kept for a faithful export
);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

-- Zero-qty rows are KEPT: they are how a sold-out size is restocked without retyping the size list.
CREATE TABLE IF NOT EXISTS product_sizes (
  product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  size       TEXT NOT NULL,
  qty        INTEGER NOT NULL CHECK (qty >= 0),
  position   INTEGER NOT NULL,
  PRIMARY KEY (product_id, size)
);

CREATE TABLE IF NOT EXISTS product_images (
  product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  url        TEXT NOT NULL,
  position   INTEGER NOT NULL,
  PRIMARY KEY (product_id, url)
);

-- The quantity ladder. Scope is either a category ('cat:T-Shirts'), a product ('prod:<id>') or the
-- global default ('default'), mirroring pricing.json's three levels exactly.
CREATE TABLE IF NOT EXISTS pricing_tiers (
  scope     TEXT NOT NULL,
  tier_id   TEXT NOT NULL,
  label     TEXT,
  min_qty   INTEGER NOT NULL CHECK (min_qty >= 1),
  position  INTEGER NOT NULL,
  PRIMARY KEY (scope, tier_id)
);

CREATE TABLE IF NOT EXISTS product_prices (
  product_id  TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  tier_id     TEXT NOT NULL,
  price_cents INTEGER CHECK (price_cents IS NULL OR price_cents >= 0),
  position    INTEGER NOT NULL DEFAULT 0,   -- ladder order: retail, smallBulk, bulk, largeBulk
  PRIMARY KEY (product_id, tier_id)
);

-- PRIVATE. Never projected into products.json and never served.
CREATE TABLE IF NOT EXISTS product_costs (
  product_id             TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
  item_cost_cents        INTEGER CHECK (item_cost_cents IS NULL OR item_cost_cents >= 0),
  shipping_method        TEXT CHECK (shipping_method IS NULL OR shipping_method IN ('air','sea','other')),
  shipping_per_unit_cents INTEGER CHECK (shipping_per_unit_cents IS NULL OR shipping_per_unit_cents >= 0),
  extra_fees_per_unit_cents INTEGER CHECK (extra_fees_per_unit_cents IS NULL OR extra_fees_per_unit_cents >= 0)
  -- landed cost is DERIVED, never stored: see the landed_cost view below.
);

CREATE TABLE IF NOT EXISTS shipments (
  id                   TEXT PRIMARY KEY,
  name                 TEXT NOT NULL,
  ship_date            TEXT,
  method               TEXT NOT NULL CHECK (method IN ('air','sea','other')),
  total_shipping_cents INTEGER CHECK (total_shipping_cents IS NULL OR total_shipping_cents >= 0),
  total_fees_cents     INTEGER CHECK (total_fees_cents IS NULL OR total_fees_cents >= 0),
  allocation_basis     TEXT NOT NULL DEFAULT 'units' CHECK (allocation_basis IN ('units','value','weight')),
  notes                TEXT NOT NULL DEFAULT '',
  position             INTEGER NOT NULL
);

-- ON DELETE CASCADE is what makes deleting a product safe: the orphaned shipment line that the
-- JSON version had to clean by hand in the dashboard is now removed by the database itself.
CREATE TABLE IF NOT EXISTS shipment_lines (
  shipment_id     TEXT NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
  product_id      TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  qty             INTEGER NOT NULL CHECK (qty >= 0),
  unit_cost_cents INTEGER CHECK (unit_cost_cents IS NULL OR unit_cost_cents >= 0),
  position        INTEGER NOT NULL,
  PRIMARY KEY (shipment_id, product_id)
);

-- Customers are their own row rather than an email string repeated on every order, which is what
-- makes "how many orders has this person placed" a query instead of a scan.
CREATE TABLE IF NOT EXISTS customers (
  email      TEXT PRIMARY KEY,
  first_seen REAL,
  last_seen  REAL
);

CREATE TABLE IF NOT EXISTS orders (
  id             INTEGER PRIMARY KEY,
  email          TEXT NOT NULL REFERENCES customers(email) ON UPDATE CASCADE,
  placed_at      REAL NOT NULL,
  subtotal_cents INTEGER NOT NULL,
  shipping_cents INTEGER NOT NULL,
  total_cents    INTEGER NOT NULL,
  weight_oz      REAL,
  status         TEXT NOT NULL DEFAULT '',
  ship_name      TEXT NOT NULL DEFAULT '',
  ship_address1  TEXT NOT NULL DEFAULT '',
  ship_address2  TEXT NOT NULL DEFAULT '',
  ship_city      TEXT NOT NULL DEFAULT '',
  ship_state     TEXT NOT NULL DEFAULT '',
  ship_zip       TEXT NOT NULL DEFAULT '',
  ship_country   TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_orders_email ON orders(email);

-- Product NAME, not id: an order is a historical record of what was sold, and it must survive the
-- product being renamed or deleted. This is deliberately not a foreign key.
CREATE TABLE IF NOT EXISTS order_items (
  order_id     INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  position     INTEGER NOT NULL,
  product_name TEXT NOT NULL,
  size         TEXT NOT NULL,
  qty          INTEGER NOT NULL CHECK (qty > 0),
  price_cents  INTEGER NOT NULL,
  tier         TEXT,
  PRIMARY KEY (order_id, position)
);

CREATE TABLE IF NOT EXISTS clicks (
  product_name TEXT PRIMARY KEY,
  count        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS bids (
  item      TEXT PRIMARY KEY,
  amount_cents INTEGER NOT NULL,
  bidder    TEXT NOT NULL DEFAULT '',
  placed_at REAL
);

CREATE TABLE IF NOT EXISTS subscribers (
  email      TEXT PRIMARY KEY,
  created_at REAL
);

CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Landed cost as a VIEW, so it cannot drift from its inputs and cannot be hand-edited.
-- NULL in any input yields NULL, never a total that reads misleadingly low.
CREATE VIEW IF NOT EXISTS landed_cost AS
SELECT
  p.id AS product_id,
  p.name AS product_name,
  c.item_cost_cents,
  c.shipping_per_unit_cents,
  c.extra_fees_per_unit_cents,
  CASE WHEN c.item_cost_cents IS NULL OR c.shipping_per_unit_cents IS NULL
            OR c.extra_fees_per_unit_cents IS NULL
       THEN NULL
       ELSE c.item_cost_cents + c.shipping_per_unit_cents + c.extra_fees_per_unit_cents
  END AS landed_cents
FROM products p LEFT JOIN product_costs c ON c.product_id = p.id;
