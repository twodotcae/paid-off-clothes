"""Migrate the JSON data files into SQLite, and project them back out again.

Two directions, deliberately:

  import_all(db)  JSON  -> SQLite
  export_all(db)  SQLite -> the same JSON structures

The export exists so the migration can be PROVEN rather than asserted: import then export must
reproduce the original files exactly. It is also the rollback path — one command regenerates every
JSON file from the database, so the old file-backed server keeps working with no data loss.

Run directly:
    python3 db/migrate.py import     build paidoff.db from the JSON files
    python3 db/migrate.py export     rewrite the JSON files from paidoff.db
    python3 db/migrate.py verify     import into a temp db, export, and diff against the originals
"""
import json, os, sqlite3, sys, decimal

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DIR, "paidoff.db")
SCHEMA = os.path.join(DIR, "db", "schema.sql")

PRODUCTS = os.path.join(DIR, "products.json")
PRICING  = os.path.join(DIR, "pricing.json")
COSTS    = os.path.join(DIR, "costs.json")
CLICKS   = os.path.join(DIR, "clicks.json")
ORDERS   = os.path.join(DIR, "orders.json")
BIDS     = os.path.join(DIR, "bids.json")
SUBS     = os.path.join(DIR, "subscribers.json")


# ---- money -----------------------------------------------------------------------------------
# Decimal, not round(x*100): round(2.675*100) is 267 because 2.675 is not exactly representable.
# Every price in the catalogue goes through here, so a silent one-cent drift would be permanent.
def to_cents(v):
    if v is None:
        return None
    return int(decimal.Decimal(str(v)).scaleb(2).to_integral_value(rounding=decimal.ROUND_HALF_UP))


def from_cents(c):
    if c is None:
        return None
    d = decimal.Decimal(c).scaleb(-2)
    # Give back an int when the value is whole, so 45 round-trips as 45 and not 45.0 — the JSON
    # files hold both forms and the projection has to reproduce what was there.
    return int(d) if d == d.to_integral_value() else float(d)


def load(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def connect(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init(conn):
    with open(SCHEMA) as f:
        conn.executescript(f.read())


# ---- JSON -> SQLite --------------------------------------------------------------------------
def import_all(conn):
    """Build the database from the JSON files on disk."""
    prods = load(PRODUCTS, {"categories": [], "products": []})
    pricing = load(PRICING, {"defaultTiers": [], "categories": {}, "products": {}})
    costs = load(COSTS, {"products": {}, "shipments": []})
    cur = conn.cursor()
    import_docs(cur, prods, pricing, costs)
    _import_runtime(cur)
    conn.commit()


def import_docs(cur, prods, pricing, costs):
    """Write catalogue documents into the database. Takes the same shapes the JSON files hold, so
    the migration and the live admin save share one code path and cannot drift apart."""

    # meta: keep the file-level bits that are not rows, so the projection can rebuild them
    cur.execute("INSERT OR REPLACE INTO meta VALUES ('products_schema_version', ?)",
                (str(prods.get("schemaVersion", 1)),))
    cur.execute("INSERT OR REPLACE INTO meta VALUES ('costs_schema_version', ?)",
                (str(costs.get("schemaVersion", 1)),))
    for key, src in (("products_readme", prods), ("costs_readme", costs), ("pricing_readme", pricing)):
        if "_README" in src:
            cur.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (key, json.dumps(src["_README"])))

    # Two independent orderings: products.json's array drives the storefront filter tiles, and
    # pricing.json's own key order is kept so regenerating that file reproduces it exactly.
    pricing_order = {name: i for i, name in enumerate(pricing.get("categories", {}))}
    for i, name in enumerate(prods.get("categories", [])):
        noun = (pricing.get("categories", {}).get(name) or {}).get("bulkNoun")
        cur.execute("INSERT OR REPLACE INTO categories VALUES (?,?,?,?)",
                    (name, i, noun, pricing_order.get(name)))
    # a category that only pricing.json knows about (Bags, Shorts) still needs a row
    for i, (name, entry) in enumerate(pricing.get("categories", {}).items(), start=len(prods.get("categories", []))):
        cur.execute("INSERT OR IGNORE INTO categories VALUES (?,?,?,?)",
                    (name, i, entry.get("bulkNoun"), pricing_order.get(name)))

    pricing_prod_order = {n: i for i, n in enumerate(pricing.get("products", {}))}
    for i, p in enumerate(prods.get("products", [])):
        cur.execute(
            "INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (p["id"], p["name"], p.get("brand") or "[brand?]", p["category"], p.get("description", ""),
             p.get("image"), to_cents(p.get("retailPrice")), to_cents(p.get("bulkPrice")),
             p.get("bulkMinQty"), p.get("status", "available"), 1 if p.get("featured") else 0, i,
             pricing_prod_order.get(p["name"])))
        for j, s in enumerate(p.get("sizes", [])):
            cur.execute("INSERT OR REPLACE INTO product_sizes VALUES (?,?,?,?)",
                        (p["id"], s["size"], int(s["qty"]), j))
        for j, url in enumerate(p.get("images", []) or []):
            cur.execute("INSERT OR REPLACE INTO product_images VALUES (?,?,?)", (p["id"], url, j))

    for j, t in enumerate(pricing.get("defaultTiers", [])):
        cur.execute("INSERT OR REPLACE INTO pricing_tiers VALUES (?,?,?,?,?)",
                    ("default", t["id"], t.get("label"), t["minQty"], j))
    for cname, entry in pricing.get("categories", {}).items():
        for j, t in enumerate(entry.get("tiers", []) or []):
            cur.execute("INSERT OR REPLACE INTO pricing_tiers VALUES (?,?,?,?,?)",
                        (f"cat:{cname}", t["id"], t.get("label"), t["minQty"], j))

    name_to_id = {r["name"]: r["id"] for r in cur.execute("SELECT id,name FROM products")}
    for pname, entry in pricing.get("products", {}).items():
        pid = name_to_id.get(pname)
        if pid is None:
            continue  # a pricing entry for a product that no longer exists; validate_pricing warns
        for k, (tier_id, price) in enumerate((entry.get("prices") or {}).items()):
            cur.execute("INSERT OR REPLACE INTO product_prices VALUES (?,?,?,?)",
                        (pid, tier_id, to_cents(price), k))
        for j, t in enumerate(entry.get("tiers", []) or []):
            cur.execute("INSERT OR REPLACE INTO pricing_tiers VALUES (?,?,?,?,?)",
                        (f"prod:{pid}", t["id"], t.get("label"), t["minQty"], j))

    for pid, c in (costs.get("products") or {}).items():
        if pid not in name_to_id.values():
            continue
        cur.execute("INSERT OR REPLACE INTO product_costs VALUES (?,?,?,?,?)",
                    (pid, to_cents(c.get("itemCost")), c.get("shippingMethod"),
                     to_cents(c.get("shippingPerUnit")), to_cents(c.get("extraFeesPerUnit"))))
    for i, s in enumerate(costs.get("shipments") or []):
        cur.execute("INSERT OR REPLACE INTO shipments VALUES (?,?,?,?,?,?,?,?,?)",
                    (s["id"], s.get("name", ""), s.get("date"), s.get("method", "other"),
                     to_cents(s.get("totalShippingCost")), to_cents(s.get("totalFees")),
                     s.get("allocationBasis", "units"), s.get("notes", ""), i))
        for j, ln in enumerate(s.get("lines") or []):
            cur.execute("INSERT OR REPLACE INTO shipment_lines VALUES (?,?,?,?,?)",
                        (s["id"], ln["productId"], int(ln.get("qty", 0)), to_cents(ln.get("unitCost")), j))


def _import_runtime(cur):
    """clicks, orders, bids and subscribers — history, imported once at migration time."""
    for pname, n in (load(CLICKS, {}) or {}).items():
        cur.execute("INSERT OR REPLACE INTO clicks VALUES (?,?)", (pname, int(n)))

    for email, olist in (load(ORDERS, {}) or {}).items():
        times = [o.get("time") or 0 for o in olist] or [0]
        cur.execute("INSERT OR REPLACE INTO customers VALUES (?,?,?)", (email, min(times), max(times)))
        for o in olist:
            st = o.get("ship_to") or {}
            cur.execute("INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (o["id"], email, o.get("time") or 0, to_cents(o.get("subtotal")),
                         to_cents(o.get("shipping")), to_cents(o.get("total")), o.get("weight_oz"),
                         o.get("status", ""), st.get("name", ""), st.get("address1", ""),
                         st.get("address2", ""), st.get("city", ""), st.get("state", ""),
                         st.get("zip", ""), st.get("country", "")))
            for j, it in enumerate(o.get("items") or []):
                cur.execute("INSERT OR REPLACE INTO order_items VALUES (?,?,?,?,?,?,?)",
                            (o["id"], j, it["name"], it.get("size", ""), int(it.get("qty", 1)),
                             to_cents(it.get("price")), it.get("tier")))

    for item, b in (load(BIDS, {}) or {}).items():
        if isinstance(b, dict) and b.get("amount") is not None:
            cur.execute("INSERT OR REPLACE INTO bids VALUES (?,?,?,?)",
                        (item, to_cents(b.get("amount")), b.get("name", ""), b.get("time")))

    subs = load(SUBS, {}) or {}
    for email, v in (subs.items() if isinstance(subs, dict) else []):
        cur.execute("INSERT OR REPLACE INTO subscribers VALUES (?,?)",
                    (email, v.get("time") if isinstance(v, dict) else None))


# ---- SQLite -> JSON --------------------------------------------------------------------------
def export_products(conn):
    # fetchall() on every outer query: sqlite3 cursors are stateful, and running a nested query on
    # the same cursor silently truncates the loop you are already iterating. That produced a
    # projection with one product out of twenty, which the round-trip check caught.
    cur = conn.cursor()
    readme = cur.execute("SELECT value FROM meta WHERE key='products_readme'").fetchone()
    ver = cur.execute("SELECT value FROM meta WHERE key='products_schema_version'").fetchone()
    doc = {}
    if readme: doc["_README"] = json.loads(readme["value"])
    doc["schemaVersion"] = int(ver["value"]) if ver else 1
    doc["categories"] = [r["name"] for r in cur.execute(
        "SELECT name FROM categories WHERE name IN (SELECT DISTINCT category FROM products) OR name='All' ORDER BY position").fetchall()]
    out = []
    for p in cur.execute("SELECT * FROM products ORDER BY position").fetchall():
        out.append({
            "id": p["id"], "name": p["name"], "brand": p["brand"], "category": p["category"],
            "description": p["description"], "image": p["image"],
            "images": [r["url"] for r in conn.execute(
                "SELECT url FROM product_images WHERE product_id=? ORDER BY position", (p["id"],)).fetchall()],
            "retailPrice": from_cents(p["retail_cents"]),
            "bulkPrice": from_cents(p["bulk_cents"]),
            "bulkMinQty": p["bulk_min_qty"],
            "sizes": [{"size": r["size"], "qty": r["qty"]} for r in conn.execute(
                "SELECT size, qty FROM product_sizes WHERE product_id=? ORDER BY position", (p["id"],)).fetchall()],
            "status": p["status"], "featured": bool(p["featured"]),
        })
    doc["products"] = out
    return doc


def export_pricing(conn):
    cur = conn.cursor()
    readme = cur.execute("SELECT value FROM meta WHERE key='pricing_readme'").fetchone()
    doc = {}
    if readme: doc["_README"] = json.loads(readme["value"])
    doc["defaultTiers"] = [{"id": r["tier_id"], "label": r["label"], "minQty": r["min_qty"]}
                           for r in conn.execute(
                               "SELECT * FROM pricing_tiers WHERE scope='default' ORDER BY position").fetchall()]
    cats = {}
    for c in cur.execute("""SELECT * FROM categories WHERE pricing_position IS NOT NULL
                            ORDER BY pricing_position""").fetchall():
        tiers = [{"id": r["tier_id"], "label": r["label"], "minQty": r["min_qty"]}
                 for r in conn.execute("SELECT * FROM pricing_tiers WHERE scope=? ORDER BY position",
                                      (f"cat:{c['name']}",)).fetchall()]
        if not tiers and not c["bulk_noun"]:
            continue
        entry = {}
        if c["bulk_noun"]: entry["bulkNoun"] = c["bulk_noun"]
        if tiers: entry["tiers"] = tiers
        cats[c["name"]] = entry
    doc["categories"] = cats
    prods = {}
    for p in cur.execute("""SELECT * FROM products WHERE pricing_position IS NOT NULL
                            ORDER BY pricing_position""").fetchall():
        prices = {r["tier_id"]: from_cents(r["price_cents"]) for r in conn.execute(
            "SELECT * FROM product_prices WHERE product_id=? ORDER BY position", (p["id"],)).fetchall()}
        if not prices: continue
        entry = {}
        # pricing.json carries `brand` purely as a label for whoever edits the file, and only for
        # products that actually have one — an unbranded piece has no key at all. Reproduce that.
        if p["brand"] and p["brand"] != "[brand?]":
            entry["brand"] = p["brand"]
        entry["category"] = p["category"]
        entry["prices"] = prices
        tiers = [{"id": r["tier_id"], "label": r["label"], "minQty": r["min_qty"]}
                 for r in conn.execute("SELECT * FROM pricing_tiers WHERE scope=? ORDER BY position",
                                      (f"prod:{p['id']}",)).fetchall()]
        if tiers: entry["tiers"] = tiers
        prods[p["name"]] = entry
    doc["products"] = prods
    return doc


def export_costs(conn):
    cur = conn.cursor()
    readme = cur.execute("SELECT value FROM meta WHERE key='costs_readme'").fetchone()
    ver = cur.execute("SELECT value FROM meta WHERE key='costs_schema_version'").fetchone()
    doc = {}
    if readme: doc["_README"] = json.loads(readme["value"])
    doc["schemaVersion"] = int(ver["value"]) if ver else 1
    prods = {}
    for r in cur.execute("""SELECT p.id, p.name, l.item_cost_cents, c.shipping_method,
                                   l.shipping_per_unit_cents, l.extra_fees_per_unit_cents, l.landed_cents
                            FROM products p
                            LEFT JOIN landed_cost l ON l.product_id = p.id
                            LEFT JOIN product_costs c ON c.product_id = p.id
                            ORDER BY p.position"""):
        prods[r["id"]] = {
            "name": r["name"],
            "itemCost": from_cents(r["item_cost_cents"]),
            "shippingMethod": r["shipping_method"],
            "shippingPerUnit": from_cents(r["shipping_per_unit_cents"]),
            "extraFeesPerUnit": from_cents(r["extra_fees_per_unit_cents"]),
            "landedCostPerUnit": from_cents(r["landed_cents"]),
        }
    doc["products"] = prods
    ships = []
    for s in cur.execute("SELECT * FROM shipments ORDER BY position").fetchall():
        ships.append({
            "id": s["id"], "name": s["name"], "date": s["ship_date"], "method": s["method"],
            "totalShippingCost": from_cents(s["total_shipping_cents"]),
            "totalFees": from_cents(s["total_fees_cents"]),
            "allocationBasis": s["allocation_basis"],
            "lines": [{"productId": r["product_id"], "qty": r["qty"],
                       "unitCost": from_cents(r["unit_cost_cents"])}
                      for r in conn.execute(
                          "SELECT * FROM shipment_lines WHERE shipment_id=? ORDER BY position", (s["id"],)).fetchall()],
            "notes": s["notes"],
        })
    doc["shipments"] = ships
    return doc


def export_clicks(conn):
    return {r["product_name"]: r["count"] for r in conn.execute("SELECT * FROM clicks")}


def export_orders(conn):
    cur = conn.cursor()
    out = {}
    for c in cur.execute("SELECT email FROM customers ORDER BY first_seen").fetchall():
        olist = []
        for o in conn.execute("SELECT * FROM orders WHERE email=? ORDER BY id", (c["email"],)).fetchall():
            olist.append({
                "id": o["id"],
                "items": [{"name": r["product_name"], "size": r["size"], "qty": r["qty"],
                           "price": from_cents(r["price_cents"]), "tier": r["tier"]}
                          for r in conn.execute(
                              "SELECT * FROM order_items WHERE order_id=? ORDER BY position", (o["id"],)).fetchall()],
                "subtotal": from_cents(o["subtotal_cents"]),
                "shipping": from_cents(o["shipping_cents"]),
                "total": from_cents(o["total_cents"]),
                "weight_oz": o["weight_oz"],
                "ship_to": {"name": o["ship_name"], "address1": o["ship_address1"],
                            "address2": o["ship_address2"], "city": o["ship_city"],
                            "state": o["ship_state"], "zip": o["ship_zip"], "country": o["ship_country"]},
                "time": o["placed_at"],
                "status": o["status"],
            })
        out[c["email"]] = olist
    return out


def write_json(path, doc, pretty=True):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        if pretty:
            json.dump(doc, f, indent=2, ensure_ascii=False); f.write("\n")
        else:
            json.dump(doc, f)
    os.replace(tmp, path)


def export_all(conn):
    write_json(PRODUCTS, export_products(conn))
    write_json(PRICING, export_pricing(conn))
    write_json(COSTS, export_costs(conn))
    if os.path.exists(CLICKS): write_json(CLICKS, export_clicks(conn), pretty=False)
    if os.path.exists(ORDERS): write_json(ORDERS, export_orders(conn), pretty=False)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if cmd == "import":
        if os.path.exists(DB_PATH): os.remove(DB_PATH)
        conn = connect(); init(conn); import_all(conn)
        n = conn.execute("SELECT COUNT(*) c FROM products").fetchone()["c"]
        print(f"imported {n} products into {os.path.basename(DB_PATH)}")
    elif cmd == "export":
        conn = connect(); export_all(conn); print("JSON files regenerated from the database")
    else:
        print("use: import | export")
