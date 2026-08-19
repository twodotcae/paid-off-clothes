"""Serves the site and backs the click tracker, Bid of the Week, My Orders lookup, and email gate with local JSON files."""
import http.server
import json
import os
import re
import threading
import time
from urllib.parse import parse_qs, urlsplit

DIR = os.path.dirname(os.path.abspath(__file__))
CLICKS_FILE = os.path.join(DIR, "clicks.json")
BIDS_FILE = os.path.join(DIR, "bids.json")
ORDERS_FILE = os.path.join(DIR, "orders.json")
SUBSCRIBERS_FILE = os.path.join(DIR, "subscribers.json")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
lock = threading.Lock()


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def do_GET(self):
        path = urlsplit(self.path).path
        query = parse_qs(urlsplit(self.path).query)

        if path == "/api/stats":
            with lock:
                data = load_json(CLICKS_FILE, {})
            self._send_json(data)
            return

        if path == "/api/bid":
            item = (query.get("item") or [""])[0]
            with lock:
                bids = load_json(BIDS_FILE, {})
            self._send_json(bids.get(item, {}))
            return

        if path == "/api/orders":
            email = (query.get("email") or [""])[0].strip().lower()
            with lock:
                orders = load_json(ORDERS_FILE, {})
            self._send_json(orders.get(email, []))
            return

        super().do_GET()

    def do_POST(self):
        if self.path == "/api/click":
            payload = self._read_json()
            name = payload.get("name", "") if isinstance(payload, dict) else ""
            if name:
                with lock:
                    data = load_json(CLICKS_FILE, {})
                    data[name] = data.get(name, 0) + 1
                    save_json(CLICKS_FILE, data)
            self._send_json({"ok": True})
            return

        if self.path == "/api/bid":
            payload = self._read_json()
            try:
                item = str(payload.get("item", "")).strip()
                amount = float(payload.get("amount", 0))
                name = str(payload.get("name") or "Anonymous").strip()[:40] or "Anonymous"
            except (TypeError, ValueError):
                item, amount, name = "", 0, ""
            if not item or amount <= 0:
                self._send_json({"ok": False, "error": "Invalid bid."})
                return
            with lock:
                bids = load_json(BIDS_FILE, {})
                current = bids.get(item)
                if current and amount <= current.get("amount", 0):
                    self._send_json({"ok": False, "error": "Someone already bid higher.", "current": current})
                    return
                bids[item] = {"amount": amount, "name": name, "time": time.time()}
                save_json(BIDS_FILE, bids)
                current_bid = bids[item]
            self._send_json({"ok": True, "current": current_bid})
            return

        if self.path == "/api/order":
            payload = self._read_json()
            email = str(payload.get("email", "")).strip().lower() if isinstance(payload, dict) else ""
            items = payload.get("items") if isinstance(payload, dict) else None
            address = str(payload.get("address", "")).strip() if isinstance(payload, dict) else ""
            try:
                total = float(payload.get("total", 0))
            except (TypeError, ValueError):
                total = 0
            if not email or not items:
                self._send_json({"ok": False, "error": "Invalid order."})
                return
            with lock:
                orders = load_json(ORDERS_FILE, {})
                order_id = 4000 + sum(len(v) for v in orders.values())
                order = {
                    "id": order_id,
                    "items": items,
                    "total": total,
                    "address": address,
                    "time": time.time(),
                    "status": "Hold — pending shipping",
                }
                orders.setdefault(email, []).append(order)
                save_json(ORDERS_FILE, orders)
            self._send_json({"ok": True, "id": order_id})
            return

        if self.path == "/api/subscribe":
            payload = self._read_json()
            email = str(payload.get("email", "")).strip().lower() if isinstance(payload, dict) else ""
            if not EMAIL_RE.match(email):
                self._send_json({"ok": False, "error": "Invalid email."})
                return
            with lock:
                subs = load_json(SUBSCRIBERS_FILE, {})
                is_new = email not in subs
                if is_new:
                    # TODO(resend): once the Resend account/API key are set up, send the
                    # "Welcome to Paid Off Clothes" email here (or via a separate script
                    # that reads subscribers.json) — plus new-drop announcements to
                    # everyone in this file going forward. Not wired up yet.
                    subs[email] = {"time": time.time()}
                    save_json(SUBSCRIBERS_FILE, subs)
            self._send_json({"ok": True, "new": is_new})
            return

        self.send_response(404)
        self.end_headers()

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _send_json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    port = 8000
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Serving Paid Off Clothes on http://localhost:{port}")
    httpd.serve_forever()
