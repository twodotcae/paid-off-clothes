-- Order lifecycle and inventory reservation.
--
-- The central idea: physical stock (product_sizes.qty) is NOT decremented when an order is placed.
-- A pending order RESERVES stock instead. Available = physical - reserved. Stock is only actually
-- deducted when payment is confirmed. That way an abandoned or failed checkout cannot silently eat
-- inventory, and a refund can hand it back.
--
--   pending    order placed, stock reserved, nothing charged
--   paid       payment confirmed, stock deducted from product_sizes
--   fulfilled  shipped
--   cancelled  released before payment; reservation dropped, stock never touched
--   failed     payment failed; same as cancelled
--   refunded   money returned and stock added back

ALTER TABLE orders ADD COLUMN order_ref TEXT;          -- public, unguessable reference
ALTER TABLE orders ADD COLUMN updated_at REAL;
ALTER TABLE orders ADD COLUMN currency TEXT NOT NULL DEFAULT 'USD';
ALTER TABLE orders ADD COLUMN inventory_state TEXT NOT NULL DEFAULT 'none';
       -- none | reserved | deducted | released | restored

-- order_items gains product_id so inventory can be moved. product_name stays as the historical
-- record: an order must still read correctly after a product is renamed or deleted, so this is
-- deliberately NOT a foreign key.
ALTER TABLE order_items ADD COLUMN product_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_ref ON orders(order_ref);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

-- What a pending order is holding. Rows are deleted when the order leaves 'pending' — either
-- converted into a real deduction on payment, or simply dropped on cancellation.
CREATE TABLE IF NOT EXISTS inventory_reservations (
  order_id   INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id TEXT NOT NULL,
  size       TEXT NOT NULL,
  qty        INTEGER NOT NULL CHECK (qty > 0),
  created_at REAL NOT NULL,
  PRIMARY KEY (order_id, product_id, size)
);
CREATE INDEX IF NOT EXISTS idx_res_product ON inventory_reservations(product_id, size);

-- Every payment-provider event, recorded once. The UNIQUE primary key is the whole mechanism that
-- stops a replayed or duplicated webhook from creating a second order or deducting stock twice:
-- the second insert fails, and the handler treats that as "already processed".
CREATE TABLE IF NOT EXISTS payment_events (
  event_id    TEXT PRIMARY KEY,
  provider    TEXT NOT NULL DEFAULT 'manual',
  event_type  TEXT NOT NULL,
  order_id    INTEGER REFERENCES orders(id) ON DELETE SET NULL,
  received_at REAL NOT NULL,
  payload     TEXT
);

-- An audit trail of every status move, so "why is this order cancelled" has an answer.
CREATE TABLE IF NOT EXISTS order_events (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  at          REAL NOT NULL,
  from_status TEXT,
  to_status   TEXT NOT NULL,
  note        TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_order_events ON order_events(order_id);

-- Live availability: physical stock minus whatever pending orders are holding.
DROP VIEW IF EXISTS size_availability;
CREATE VIEW size_availability AS
SELECT
  s.product_id,
  s.size,
  s.qty AS physical_qty,
  COALESCE(r.reserved, 0) AS reserved_qty,
  s.qty - COALESCE(r.reserved, 0) AS available_qty
FROM product_sizes s
LEFT JOIN (
  SELECT product_id, size, SUM(qty) AS reserved
  FROM inventory_reservations GROUP BY product_id, size
) r ON r.product_id = s.product_id AND r.size = s.size;
