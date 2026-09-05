"""Minimal Stripe REST client — stdlib only, no `stripe` package.

Two things live here: creating a Checkout Session (Stripe's hosted payment page) and verifying a
webhook's signature. Both are plain HTTPS and HMAC, which the standard library already does, so
pulling in the Stripe SDK would break this project's zero-dependency rule for no real benefit.

Credentials come ONLY from environment variables — STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET — read
fresh on every call rather than cached at import time, so a key set after the process started (or
changed between test cases) is picked up without a restart. Nothing here logs, prints, or returns
either value; is_configured()/webhook_configured() are the only things allowed to react to whether
they're set, and callers should use those rather than reaching into os.environ themselves.
"""
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.stripe.com/v1"
# Pinned so Stripe changing their default API version can't silently reshape the responses this
# file parses. Bump deliberately, not by accident.
API_VERSION = "2024-06-20"

# Stripe's own tolerance for webhook replay is 5 minutes; matching it means a delayed-but-legitimate
# delivery (a retry after your server was briefly down) isn't rejected any more strictly than
# Stripe's own dashboard would flag it.
DEFAULT_TOLERANCE_SECONDS = 300


class StripeError(Exception):
    """Talking to Stripe failed — no network, bad auth, or the API rejected the request."""


class SignatureError(Exception):
    """A webhook payload failed verification: wrong signature, wrong secret, or too old."""


def _secret_key():
    return os.environ.get("STRIPE_SECRET_KEY", "").strip()


def _webhook_secret():
    return os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()


def is_configured():
    """True once a secret key is present. Checkout Session creation needs nothing else."""
    return bool(_secret_key())


def webhook_configured():
    return bool(_webhook_secret())


def _form_encode(params, prefix=""):
    """Stripe's API takes application/x-www-form-urlencoded with PHP-style bracket nesting for
    arrays and objects — line_items[][price_data][unit_amount]=500 rather than JSON. This flattens
    nested dicts/lists into that shape. Order doesn't matter to Stripe, so plain dict iteration
    order (insertion order) is fine."""
    pairs = []
    for key, value in params.items():
        full_key = f"{prefix}[{key}]" if prefix else str(key)
        if isinstance(value, dict):
            pairs.extend(_form_encode(value, full_key))
        elif isinstance(value, (list, tuple)):
            for item in value:
                item_key = f"{full_key}[]"
                if isinstance(item, dict):
                    pairs.extend(_form_encode(item, item_key))
                else:
                    pairs.append((item_key, item))
        elif value is not None:
            pairs.append((full_key, value))
    return pairs


def _request(method, path, params=None, idempotency_key=None, timeout=15):
    key = _secret_key()
    if not key:
        raise StripeError("STRIPE_SECRET_KEY is not set.")
    url = f"{API_BASE}{path}"
    data = None
    if params is not None:
        data = urllib.parse.urlencode(_form_encode(params)).encode()
    if method == "GET" and data:
        url = f"{url}?{data.decode()}"
        data = None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{key}:".encode()).decode())
    req.add_header("Stripe-Version", API_VERSION)
    if data is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    if idempotency_key:
        req.add_header("Idempotency-Key", idempotency_key)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            msg = json.loads(body).get("error", {}).get("message", body)
        except json.JSONDecodeError:
            msg = body
        raise StripeError(f"Stripe rejected the request: {msg}") from e
    except urllib.error.URLError as e:
        raise StripeError(f"Could not reach Stripe: {e.reason}") from e


def create_checkout_session(*, line_items, email, order_id, order_ref, success_url, cancel_url,
                             idempotency_key=None):
    """One Checkout Session per order.

    line_items: [{"name": str, "unit_amount_cents": int, "qty": int}] — already-priced units, in
    cents, exactly as the server quoted them. This file never computes a price; it only forwards
    numbers db/orders.py already validated against the catalogue.

    metadata.order_id is how the webhook finds its way back to the order it should mark paid.
    client_reference_id carries the same value in Stripe's own dedicated field, which shows up
    directly in the Stripe dashboard next to the payment.
    """
    params = {
        "mode": "payment",
        "payment_method_types": ["card"],
        "customer_email": email,
        "client_reference_id": str(order_id),
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"order_id": str(order_id), "order_ref": order_ref},
        "line_items": [
            {
                "quantity": li["qty"],
                "price_data": {
                    "currency": "usd",
                    "unit_amount": li["unit_amount_cents"],
                    "product_data": {"name": li["name"]},
                },
            }
            for li in line_items
        ],
    }
    return _request("POST", "/checkout/sessions", params, idempotency_key=idempotency_key)


def retrieve_checkout_session(session_id):
    return _request("GET", f"/checkout/sessions/{urllib.parse.quote(session_id)}")


def verify_webhook_event(payload, sig_header, tolerance=DEFAULT_TOLERANCE_SECONDS):
    """Verify a Stripe webhook and return the parsed event dict, or raise SignatureError.

    payload: the RAW request body, exactly as received — as bytes. Verification HMACs those exact
    bytes; parsing JSON first and re-serializing before checking would break on any whitespace or
    key-order difference between what Stripe sent and what json.dumps() would produce.

    Implements Stripe's documented scheme by hand (see their webhook signing docs): the header is
    `t=<unix ts>,v1=<hex hmac-sha256>[,v1=<hex>...]`, and the signed message is `"{t}.{payload}"`
    keyed with the webhook signing secret. Multiple v1 values can appear during a secret rotation;
    matching any one of them is enough.
    """
    secret = _webhook_secret()
    if not secret:
        raise SignatureError("STRIPE_WEBHOOK_SECRET is not set.")
    if not sig_header:
        raise SignatureError("Missing Stripe-Signature header.")

    parts = {}
    for chunk in sig_header.split(","):
        if "=" not in chunk:
            continue
        k, _, v = chunk.partition("=")
        parts.setdefault(k.strip(), []).append(v.strip())

    timestamps, signatures = parts.get("t"), parts.get("v1")
    if not timestamps or not signatures:
        raise SignatureError("Malformed Stripe-Signature header.")
    timestamp = timestamps[0]

    signed_payload = f"{timestamp}.".encode() + payload
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        raise SignatureError("Signature does not match payload.")

    try:
        age = time.time() - int(timestamp)
    except ValueError:
        raise SignatureError("Malformed timestamp.")
    if age > tolerance:
        raise SignatureError("Webhook timestamp is too old — possible replay.")

    try:
        return json.loads(payload.decode())
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise SignatureError(f"Payload is not valid JSON: {e}")
