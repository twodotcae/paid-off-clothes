"""Tests for the Stripe Checkout integration: the stdlib Stripe client, the pickup/shipping order
lifecycle in db/orders.py, and the actual HTTP routes in server.py.

Run with:  python3 -m unittest discover -s tests -v

Nothing here talks to the real Stripe API — every test that would (session creation, webhook
signatures) either fakes urllib.request.urlopen or builds a webhook payload/signature by hand using
the same HMAC scheme stripe_client.py implements. No STRIPE_SECRET_KEY needs to be a real key; the
tests that need "configured" just set the environment variable to a fake test-mode-shaped string,
since is_configured() only checks presence, never validity — Stripe itself is the only thing that
would ever reject a bad key, and nothing here calls Stripe for real.
"""
import glob
import hashlib
import hmac
import http.client
import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
import urllib.error

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)

import stripe_client  # noqa: E402  (module under test; sys.path is set up above)


def _load_module(name, rel_path):
    """A fresh module instance for each test's paths, mirroring how server.py itself loads
    db/store.py, db/orders.py and db/migrate.py via spec_from_file_location instead of a normal
    import — that pattern is what lets each test point at its own throwaway database."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(APP_DIR, rel_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fresh_db(path):
    """Schema + every migration, applied the same way server.py's bootstrap() applies them, plus
    one seeded product so quote()/create_order() have something real to price."""
    migrate = _load_module("_test_migrate", "db/migrate.py")
    conn = migrate.connect(path)
    migrate.init(conn)
    for fname in sorted(glob.glob(os.path.join(APP_DIR, "db", "migrations", "*.sql"))):
        raw = open(fname).read()
        body = "\n".join(l for l in raw.splitlines() if not l.strip().startswith("--"))
        for stmt in [s.strip() for s in body.split(";") if s.strip()]:
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
                    raise
    conn.execute("INSERT INTO categories(name, position, in_products_json) VALUES ('T-Shirts', 0, 1)")
    conn.execute("""INSERT INTO products
        (id, name, brand, category, description, image, retail_cents, bulk_cents, bulk_min_qty,
         status, featured, position, pricing_position)
        VALUES ('test-tee','Test Tee','TestBrand','T-Shirts','','',2500,NULL,NULL,'available',0,0,0)""")
    conn.execute("INSERT INTO product_sizes(product_id, size, qty, position) VALUES ('test-tee','M',10,0)")
    conn.execute("INSERT INTO pricing_tiers(scope, tier_id, label, min_qty, position) "
                "VALUES ('default','retail','Retail',1,0)")
    conn.execute("INSERT INTO product_prices(product_id, tier_id, price_cents, position) "
                "VALUES ('test-tee','retail',2500,0)")
    conn.commit()
    return conn, migrate


# ---------------------------------------------------------------------------------------------
class StripeClientSignatureTests(unittest.TestCase):
    """verify_webhook_event() is a hand-rolled implementation of Stripe's documented webhook
    signing scheme — these are the properties that make it actually safe to trust."""

    def setUp(self):
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret"
        self.payload = json.dumps({"id": "evt_1", "type": "checkout.session.completed"}).encode()

    def tearDown(self):
        os.environ.pop("STRIPE_WEBHOOK_SECRET", None)

    def _sign(self, payload, secret="whsec_test_secret", timestamp=None):
        ts = str(int(timestamp if timestamp is not None else time.time()))
        sig = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
        return f"t={ts},v1={sig}"

    def test_valid_signature_is_accepted_and_payload_parsed(self):
        header = self._sign(self.payload)
        event = stripe_client.verify_webhook_event(self.payload, header)
        self.assertEqual(event["id"], "evt_1")

    def test_tampered_payload_is_rejected(self):
        header = self._sign(self.payload)
        tampered = self.payload.replace(b"evt_1", b"evt_2")
        with self.assertRaises(stripe_client.SignatureError):
            stripe_client.verify_webhook_event(tampered, header)

    def test_wrong_secret_is_rejected(self):
        header = self._sign(self.payload, secret="whsec_wrong")
        with self.assertRaises(stripe_client.SignatureError):
            stripe_client.verify_webhook_event(self.payload, header)

    def test_old_timestamp_is_rejected_as_replay(self):
        header = self._sign(self.payload, timestamp=time.time() - 600)
        with self.assertRaises(stripe_client.SignatureError):
            stripe_client.verify_webhook_event(self.payload, header)

    def test_missing_header_is_rejected(self):
        with self.assertRaises(stripe_client.SignatureError):
            stripe_client.verify_webhook_event(self.payload, "")

    def test_malformed_header_is_rejected(self):
        with self.assertRaises(stripe_client.SignatureError):
            stripe_client.verify_webhook_event(self.payload, "not,a=valid,header")

    def test_no_webhook_secret_configured_refuses_everything(self):
        os.environ.pop("STRIPE_WEBHOOK_SECRET", None)
        header = self._sign(self.payload)
        with self.assertRaises(stripe_client.SignatureError):
            stripe_client.verify_webhook_event(self.payload, header)

    def test_key_rotation_multiple_v1_values_matches_any(self):
        ts = str(int(time.time()))
        good_sig = hmac.new(b"whsec_test_secret", f"{ts}.".encode() + self.payload,
                            hashlib.sha256).hexdigest()
        header = f"t={ts},v1=deadbeef,v1={good_sig}"
        event = stripe_client.verify_webhook_event(self.payload, header)
        self.assertEqual(event["id"], "evt_1")


class StripeClientConfigTests(unittest.TestCase):
    def test_is_configured_reflects_env_var(self):
        os.environ.pop("STRIPE_SECRET_KEY", None)
        self.assertFalse(stripe_client.is_configured())
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_fake"
        self.assertTrue(stripe_client.is_configured())
        os.environ.pop("STRIPE_SECRET_KEY", None)

    def test_create_checkout_session_without_key_raises(self):
        os.environ.pop("STRIPE_SECRET_KEY", None)
        with self.assertRaises(stripe_client.StripeError):
            stripe_client.create_checkout_session(
                line_items=[{"name": "x", "unit_amount_cents": 100, "qty": 1}],
                email="a@example.com", order_id=1, order_ref="PO-TEST",
                success_url="https://example.com/success", cancel_url="https://example.com/cancel")


class StripeClientRequestBuildingTests(unittest.TestCase):
    """create_checkout_session() with urlopen faked out — this checks the request this file builds
    is shaped the way Stripe's API actually expects, without a network call."""

    def setUp(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_fake"
        self._captured = {}
        self._real_urlopen = stripe_client.urllib.request.urlopen

        def fake_urlopen(req, timeout=15):
            self._captured["url"] = req.full_url
            self._captured["headers"] = dict(req.header_items())
            self._captured["body"] = req.data.decode() if req.data else None
            self._captured["method"] = req.get_method()

            class FakeResponse:
                def read(self_inner):
                    return json.dumps({"id": "cs_test_123", "url": "https://checkout.stripe.com/pay/cs_test_123"}).encode()
                def __enter__(self_inner):
                    return self_inner
                def __exit__(self_inner, *a):
                    return False
            return FakeResponse()

        stripe_client.urllib.request.urlopen = fake_urlopen

    def tearDown(self):
        stripe_client.urllib.request.urlopen = self._real_urlopen
        os.environ.pop("STRIPE_SECRET_KEY", None)

    def test_session_request_shape_and_auth_header(self):
        session = stripe_client.create_checkout_session(
            line_items=[{"name": "Test Tee (M)", "unit_amount_cents": 2500, "qty": 2},
                        {"name": "Shipping", "unit_amount_cents": 550, "qty": 1}],
            email="buyer@example.com", order_id=42, order_ref="PO-ABCD1234",
            success_url="https://example.com/success.html?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://example.com/cancel.html?ref=PO-ABCD1234",
            idempotency_key="checkout_session_42",
        )
        self.assertEqual(session["id"], "cs_test_123")
        self.assertEqual(self._captured["method"], "POST")
        self.assertTrue(self._captured["url"].endswith("/checkout/sessions"))

        auth = self._captured["headers"].get("Authorization", "")
        self.assertTrue(auth.startswith("Basic "))
        import base64
        decoded = base64.b64decode(auth[6:]).decode()
        self.assertEqual(decoded, "sk_test_fake:")
        self.assertEqual(self._captured["headers"].get("Idempotency-key"), "checkout_session_42")

        body = self._captured["body"]
        self.assertIn("mode=payment", body)
        self.assertIn("metadata%5Border_id%5D=42", body)
        self.assertIn("line_items%5B%5D%5Bquantity%5D=2", body)
        self.assertIn("unit_amount%5D=2500", body)
        self.assertIn("unit_amount%5D=550", body)

    def test_http_error_from_stripe_is_wrapped(self):
        def raising_urlopen(req, timeout=15):
            raise urllib.error.HTTPError(
                req.full_url, 402, "Payment error",
                {}, __import__("io").BytesIO(json.dumps({"error": {"message": "Your card was declined."}}).encode()))
        stripe_client.urllib.request.urlopen = raising_urlopen
        with self.assertRaises(stripe_client.StripeError) as ctx:
            stripe_client.create_checkout_session(
                line_items=[{"name": "x", "unit_amount_cents": 100, "qty": 1}],
                email="a@example.com", order_id=1, order_ref="PO-X",
                success_url="https://example.com/s", cancel_url="https://example.com/c")
        self.assertIn("declined", str(ctx.exception))


# ---------------------------------------------------------------------------------------------
class OrderLifecyclePickupTests(unittest.TestCase):
    """db/orders.py: pickup zeroes shipping and skips the address; Stripe session bookkeeping and
    mark_paid()'s idempotency, exercised directly against a throwaway database."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.conn, _ = _fresh_db(self.db_path)
        self.orders = _load_module("_test_orders", "db/orders.py")

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _basket(self, qty=1):
        return [{"id": "test-tee", "name": "Test Tee", "size": "M", "qty": qty}]

    def test_pickup_order_has_zero_shipping_and_no_address(self):
        result = self.orders.create_order(
            self.conn, "buyer@example.com", self._basket(),
            ship_to={"name": "Should Be Dropped", "address1": "123 X St"},
            fulfillment_method="pickup")
        self.assertEqual(result["subtotal_cents"], 2500)
        self.assertEqual(result["shipping_cents"], 0)
        self.assertEqual(result["total_cents"], 2500)

        row = self.conn.execute("SELECT * FROM orders WHERE id=?", (result["order_id"],)).fetchone()
        self.assertEqual(row["fulfillment_method"], "pickup")
        self.assertEqual(row["shipping_cents"], 0)
        self.assertEqual(row["ship_address1"], "")   # never persisted, even though the caller sent one
        self.assertEqual(row["status"], "pending")    # never auto-paid — only the admin can confirm this

    def test_shipping_order_charges_real_shipping(self):
        result = self.orders.create_order(
            self.conn, "buyer@example.com", self._basket(),
            ship_to={"name": "Jordan Smith", "address1": "123 Main St", "city": "Houston",
                     "state": "TX", "zip": "77001", "country": "US"},
            fulfillment_method="shipping")
        self.assertGreater(result["shipping_cents"], 0)
        row = self.conn.execute("SELECT * FROM orders WHERE id=?", (result["order_id"],)).fetchone()
        self.assertEqual(row["fulfillment_method"], "shipping")
        self.assertEqual(row["ship_address1"], "123 Main St")

    def test_unknown_fulfillment_method_is_rejected(self):
        with self.assertRaises(self.orders.OrderError):
            self.orders.create_order(self.conn, "buyer@example.com", self._basket(), {},
                                     fulfillment_method="teleport")

    def test_stripe_session_round_trip(self):
        result = self.orders.create_order(self.conn, "buyer@example.com", self._basket(),
                                          {"name": "N", "address1": "A", "city": "C", "state": "TX",
                                           "zip": "1", "country": "US"},
                                          fulfillment_method="shipping")
        self.assertIsNone(self.orders.order_by_stripe_session(self.conn, "cs_test_999"))
        self.orders.set_stripe_session(self.conn, result["order_id"], "cs_test_999")
        found = self.orders.order_by_stripe_session(self.conn, "cs_test_999")
        self.assertEqual(found["id"], result["order_id"])

    def test_mark_paid_via_stripe_deducts_stock_exactly_once_on_duplicate_webhook(self):
        result = self.orders.create_order(self.conn, "buyer@example.com", self._basket(qty=3),
                                          {"name": "N", "address1": "A", "city": "C", "state": "TX",
                                           "zip": "1", "country": "US"},
                                          fulfillment_method="shipping")
        before = self.conn.execute(
            "SELECT qty FROM product_sizes WHERE product_id='test-tee' AND size='M'").fetchone()["qty"]

        first = self.orders.mark_paid(self.conn, result["order_id"], "evt_dup_test", provider="stripe")
        self.assertFalse(first["duplicate"])
        after_first = self.conn.execute(
            "SELECT qty FROM product_sizes WHERE product_id='test-tee' AND size='M'").fetchone()["qty"]
        self.assertEqual(after_first, before - 3)

        # Stripe redelivers the identical event (it does this on principle until it gets a 2xx) —
        # the SAME event_id must be a complete no-op, not a second deduction.
        second = self.orders.mark_paid(self.conn, result["order_id"], "evt_dup_test", provider="stripe")
        self.assertTrue(second["duplicate"])
        after_second = self.conn.execute(
            "SELECT qty FROM product_sizes WHERE product_id='test-tee' AND size='M'").fetchone()["qty"]
        self.assertEqual(after_second, before - 3, "a redelivered webhook must not deduct stock twice")

        row = self.conn.execute("SELECT status FROM orders WHERE id=?", (result["order_id"],)).fetchone()
        self.assertEqual(row["status"], "paid")

    def test_pending_order_never_deducts_stock_before_payment(self):
        before = self.conn.execute(
            "SELECT qty FROM product_sizes WHERE product_id='test-tee' AND size='M'").fetchone()["qty"]
        self.orders.create_order(self.conn, "buyer@example.com", self._basket(qty=2), {},
                                 fulfillment_method="pickup")
        after = self.conn.execute(
            "SELECT qty FROM product_sizes WHERE product_id='test-tee' AND size='M'").fetchone()["qty"]
        self.assertEqual(before, after, "placing an order must only reserve stock, never deduct it")


# ---------------------------------------------------------------------------------------------
class CheckoutHttpTests(unittest.TestCase):
    """End-to-end against the real server.py routes: /api/checkout/session, /api/checkout/config,
    /api/checkout/status and /api/webhooks/stripe, each hit over real HTTP against a throwaway
    database. Stripe's network calls are faked; everything else is the genuine code path."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls._old_data_dir = os.environ.get("POC_DATA_DIR")
        os.environ["POC_DATA_DIR"] = cls.tmpdir

        # Seed the catalogue files bootstrap() will import from, BEFORE the server ever runs — this
        # is what keeps a plain `python3 server.py` unaffected: the fixture only exists in tmpdir.
        products_doc = {
            "schemaVersion": 1, "categories": ["T-Shirts"],
            "products": [{
                "id": "test-tee", "name": "Test Tee", "brand": "TestBrand", "category": "T-Shirts",
                "description": "", "image": "", "images": [], "retailPrice": 25.00,
                "bulkPrice": None, "bulkMinQty": None,
                "sizes": [{"size": "M", "qty": 10}], "status": "available", "featured": False,
            }],
        }
        pricing_doc = {
            "defaultTiers": [{"id": "retail", "label": "Retail", "minQty": 1}],
            "categories": {}, "products": {"Test Tee": {"category": "T-Shirts", "prices": {"retail": 25.00}}},
        }
        with open(os.path.join(cls.tmpdir, "products.json"), "w") as f:
            json.dump(products_doc, f)
        with open(os.path.join(cls.tmpdir, "pricing.json"), "w") as f:
            json.dump(pricing_doc, f)

        cls.server_mod = _load_module("_test_server", "server.py")
        cls.server_mod.bootstrap()

        import http.server
        cls.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), cls.server_mod.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        if cls._old_data_dir is None:
            os.environ.pop("POC_DATA_DIR", None)
        else:
            os.environ["POC_DATA_DIR"] = cls._old_data_dir
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def setUp(self):
        os.environ.pop("STRIPE_SECRET_KEY", None)
        os.environ.pop("STRIPE_WEBHOOK_SECRET", None)
        self._real_create_session = stripe_client.create_checkout_session
        self._real_retrieve_session = stripe_client.retrieve_checkout_session

    def tearDown(self):
        stripe_client.create_checkout_session = self._real_create_session
        stripe_client.retrieve_checkout_session = self._real_retrieve_session
        os.environ.pop("STRIPE_SECRET_KEY", None)
        os.environ.pop("STRIPE_WEBHOOK_SECRET", None)

    def _post(self, path, payload, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        body = json.dumps(payload).encode() if not isinstance(payload, (bytes, bytearray)) else payload
        conn.request("POST", path, body=body,
                    headers={"Content-Type": "application/json", **(headers or {})})
        resp = conn.getresponse()
        out = json.loads(resp.read().decode())
        conn.close()
        return resp.status, out

    def _get(self, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", path)
        resp = conn.getresponse()
        out = json.loads(resp.read().decode())
        conn.close()
        return resp.status, out

    def test_config_reports_stripe_disabled_by_default(self):
        status, out = self._get("/api/checkout/config")
        self.assertEqual(status, 200)
        self.assertFalse(out["stripeEnabled"])

    def test_pickup_checkout_reserves_without_touching_stripe(self):
        status, out = self._post("/api/checkout/session", {
            "email": "pickup@example.com",
            "fulfillment_method": "pickup",
            "ship_to": {},
            "idempotency_key": "test_pickup_1",
            "items": [{"id": "test-tee", "name": "Test Tee", "size": "M", "qty": 1}],
        })
        self.assertEqual(status, 200)
        self.assertTrue(out["ok"])
        self.assertEqual(out["mode"], "pickup")
        self.assertEqual(out["shipping"], 0.0)
        self.assertTrue(out["ref"].startswith("PO-"))

    def test_shipping_checkout_without_stripe_configured_is_refused_safely(self):
        status, out = self._post("/api/checkout/session", {
            "email": "buyer@example.com",
            "fulfillment_method": "shipping",
            "ship_to": {"name": "Jordan Smith", "address1": "123 Main St", "city": "Houston",
                        "state": "TX", "zip": "77001"},
            "idempotency_key": "test_shipping_noconfig",
            "items": [{"id": "test-tee", "name": "Test Tee", "size": "M", "qty": 1}],
        })
        self.assertEqual(status, 503)
        self.assertFalse(out["ok"])
        self.assertEqual(out["code"], "stripe_not_configured")

    def test_shipping_checkout_requires_a_complete_address(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_fake"
        status, out = self._post("/api/checkout/session", {
            "email": "buyer@example.com",
            "fulfillment_method": "shipping",
            "ship_to": {"name": "Jordan Smith"},  # missing address1/city/state/zip
            "idempotency_key": "test_shipping_incomplete",
            "items": [{"id": "test-tee", "name": "Test Tee", "size": "M", "qty": 1}],
        })
        self.assertEqual(status, 400)
        self.assertFalse(out["ok"])

    def test_shipping_checkout_creates_stripe_session_and_stores_it(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_fake"
        captured = {}

        def fake_create(**kwargs):
            captured.update(kwargs)
            return {"id": "cs_fake_abc", "url": "https://checkout.stripe.com/pay/cs_fake_abc"}
        stripe_client.create_checkout_session = fake_create

        status, out = self._post("/api/checkout/session", {
            "email": "buyer@example.com",
            "fulfillment_method": "shipping",
            "ship_to": {"name": "Jordan Smith", "address1": "123 Main St", "city": "Houston",
                        "state": "TX", "zip": "77001"},
            "idempotency_key": "test_shipping_ok",
            "items": [{"id": "test-tee", "name": "Test Tee", "size": "M", "qty": 1}],
        })
        self.assertEqual(status, 200)
        self.assertTrue(out["ok"])
        self.assertEqual(out["mode"], "stripe")
        self.assertEqual(out["checkout_url"], "https://checkout.stripe.com/pay/cs_fake_abc")

        # The order was priced on the server, not from anything the request claimed about money.
        self.assertGreater(sum(li["unit_amount_cents"] * li["qty"] for li in captured["line_items"]), 0)

        conn = self.server_mod.store.connect()
        try:
            row = conn.execute("SELECT * FROM orders WHERE order_ref=?", (out["ref"],)).fetchone()
        finally:
            conn.close()
        self.assertEqual(row["stripe_session_id"], "cs_fake_abc")
        self.assertEqual(row["status"], "pending")
        self.assertEqual(row["inventory_state"], "reserved")

    def test_webhook_marks_order_paid_and_duplicate_delivery_is_a_noop(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_fake"
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret"
        stripe_client.create_checkout_session = lambda **kw: {
            "id": "cs_webhook_test", "url": "https://checkout.stripe.com/pay/cs_webhook_test"}

        status, out = self._post("/api/checkout/session", {
            "email": "webhook@example.com",
            "fulfillment_method": "shipping",
            "ship_to": {"name": "Jordan Smith", "address1": "123 Main St", "city": "Houston",
                        "state": "TX", "zip": "77001"},
            "idempotency_key": "test_webhook_order",
            "items": [{"id": "test-tee", "name": "Test Tee", "size": "M", "qty": 2}],
        })
        self.assertEqual(status, 200)
        ref = out["ref"]

        conn = self.server_mod.store.connect()
        try:
            order_id = conn.execute("SELECT id FROM orders WHERE order_ref=?", (ref,)).fetchone()["id"]
            before_qty = conn.execute(
                "SELECT qty FROM product_sizes WHERE product_id='test-tee' AND size='M'").fetchone()["qty"]
        finally:
            conn.close()

        event = {
            "id": "evt_webhook_test_1", "type": "checkout.session.completed",
            "data": {"object": {"payment_status": "paid",
                               "metadata": {"order_id": str(order_id), "order_ref": ref}}},
        }
        raw = json.dumps(event).encode()
        ts = str(int(time.time()))
        sig = hmac.new(b"whsec_test_secret", f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
        header = {"Stripe-Signature": f"t={ts},v1={sig}"}

        status, out = self._post("/api/webhooks/stripe", raw, headers=header)
        self.assertEqual(status, 200)

        conn = self.server_mod.store.connect()
        try:
            row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
            after_qty = conn.execute(
                "SELECT qty FROM product_sizes WHERE product_id='test-tee' AND size='M'").fetchone()["qty"]
        finally:
            conn.close()
        self.assertEqual(row["status"], "paid")
        self.assertEqual(after_qty, before_qty - 2)

        # Stripe redelivers the same event until it sees a 2xx — replaying it must not deduct twice.
        status2, out2 = self._post("/api/webhooks/stripe", raw, headers=header)
        self.assertEqual(status2, 200)
        conn = self.server_mod.store.connect()
        try:
            after_qty2 = conn.execute(
                "SELECT qty FROM product_sizes WHERE product_id='test-tee' AND size='M'").fetchone()["qty"]
        finally:
            conn.close()
        self.assertEqual(after_qty2, before_qty - 2, "a redelivered webhook must not deduct stock twice")

    def test_webhook_with_bad_signature_is_rejected(self):
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret"
        event = {"id": "evt_bad", "type": "checkout.session.completed",
                 "data": {"object": {"payment_status": "paid", "metadata": {"order_id": "1"}}}}
        raw = json.dumps(event).encode()
        status, out = self._post("/api/webhooks/stripe", raw,
                                 headers={"Stripe-Signature": "t=123,v1=not_a_real_signature"})
        self.assertEqual(status, 400)
        self.assertFalse(out["ok"])


if __name__ == "__main__":
    unittest.main()
