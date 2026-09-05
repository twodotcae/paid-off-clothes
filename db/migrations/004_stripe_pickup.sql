-- Stripe Checkout + local pickup.
--
-- fulfillment_method distinguishes how an order gets to the buyer: 'shipping' (an address, a
-- carrier, and — from here on — real card payment through Stripe Checkout) or 'pickup' (no
-- address, no shipping charge, paid in person after a DM, confirmed by hand in the admin
-- dashboard exactly like every order was before Stripe existed). Existing rows default to
-- 'shipping', which is what every order before this migration actually was.
ALTER TABLE orders ADD COLUMN fulfillment_method TEXT NOT NULL DEFAULT 'shipping';

-- Set once a Checkout Session is created for an order, so the webhook and the success page can
-- both find their way back to it. NULL for pickup orders, which never talk to Stripe.
ALTER TABLE orders ADD COLUMN stripe_session_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_stripe_session
  ON orders(stripe_session_id) WHERE stripe_session_id IS NOT NULL;
