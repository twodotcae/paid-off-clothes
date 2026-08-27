# Paid Off Clothes

Storefront for a one-person resale business selling high-end designer clothing and accessories
(tees, belts, shoes, backpacks). The goal is a site that reads as a real, curated boutique — not a
generic e-commerce template — where visitors browse rotating stock, bid on a weekly one-off, and
either check out on-site or DM on Instagram to buy.

## Stack

Static site, no build step, no dependencies. Four files at the repo root:

- [index.html](index.html) — full page markup; every dynamic region is an empty container filled by JS
- [script.js](script.js) — inventory data + all rendering and behavior (~1000 lines, single global scope, no modules)
- [styles.css](styles.css) — all styling, dark theme, CSS custom properties in `:root`
- [server.py](server.py) — stdlib-only dev server + tiny JSON API

## Running it

```bash
python3 server.py
```

Serves on http://localhost:8000. Opening `index.html` directly via `file://` works for browsing but
breaks the API-backed features (bids, orders, click stats, email gate submit).

The server sends `Cache-Control: no-store` on everything. Separately, `index.html` links assets with
a manual cache-busting query (`styles.css?v=2`, `script.js?v=2`) for deployed hosts — **bump both
`v=` numbers when you change CSS or JS**, or returning visitors get stale files.

## Inventory

`PRODUCTS` at the top of [script.js](script.js:8) is the source of truth. It's built from two helpers:

- `sizedStock(brand, category, name, desc, price, {size: qty}, img)` — **one card per style**, not
  per size. Zero-qty sizes are dropped and a style with nothing left drops out entirely.
- `oneSizeStock(brand, category, name, desc, price, qty, img)` — single card, `meta: "One Size"`.

Each product carries `sizes: [{size, qty}]` (in-stock sizes only) and `stock` (their total, shown as
"N left" on the card). `sizesOf(p)` lists the size names; the modal renders the per-size breakdown as
pills ("S ×5"), and the size filter matches a style if *any* of its sizes match.

Source of the data is `PO inventory.xlsm` (currently in ~/Downloads, not in the repo). Its sheets —
Summary / Shirts / Belts / Shoes / Backpacks — carry the real brand names and per-size counts;
`PRODUCTS` currently reproduces all 275 units exactly. Re-check against that workbook when restocking.

Conventions that other code depends on:

- `p.meta` is the available sizes joined with `" · "` (or `"One Size"`), used as the card's sub-line.
- `p.brand` is the designer name, rendered above the title on every card, in the modal, the featured
  stack, the bid card, and cart/checkout lines. `fullName(p)` joins brand + name; search matches it.
- Unknown brands use the `NEEDS_BRAND` sentinel (`"[brand?]"`), which renders in warning orange via
  `.card-brand-missing` so an unlabelled piece can't pass as a finished listing. `hasBrand(p)` tests
  it. **`NEEDS_BRAND` is a `const` and must stay declared above `PRODUCTS`** — it's referenced during
  that array's initialization, so moving it below reintroduces a temporal-dead-zone crash.
- `p.status` is `"available"` or `"sold"`; `"sold"` disables Buy/Add-to-Cart and hides stock count.
- `p.stock` is optional; absent means one-off (qty 1).
- Names are now unique per card (one card per style), which retired the old collision bug where the
  cart, click tracking, and the featured stack all keyed on a `name` repeated across sizes.
- The item modal's size chips double as the availability breakdown and the picker: each shows its
  units ("M ×5"), clicking one selects it, and Buy Now / Add to Cart stay disabled reading
  "Select a Size" until one is. A single-size style auto-selects. A quantity stepper appears once a
  size is chosen and is capped at that size's units.
- **Everything quantity-related goes through `clampQty(p, size, n)`**, which floors at 1 and ceilings
  at `unitsFor(p, size)`. It runs on the modal stepper, on cart steppers, on top-ups, and again in
  `loadCart`, so a hand-edited `localStorage` can't push a line past available stock.
- Sum money with `lineTotal(lines)` (price x qty), never by reducing over `price` alone.
- Adding a category means adding it to `CATEGORIES` too.

`images/logo.png` is the brand logo, 700x452 with a **transparent** background, used by the opening
reveal and safe to drop on any background. It was keyed out of the supplied black-backed original
(kept as `images/logo-original.png`) by treating luminance above a 0.16 threshold as fully opaque
and ramping only the narrow antialiasing band just above black — so the grey skyline and off-white
script stay solid rather than becoming semi-transparent, which is what a naive luminance-as-alpha
pass produces.

`images/skyline.png` (672x152, transparent) is the skyline band lifted straight out of the logo, so
the backdrop is the brand's own artwork rather than a stock photo — no licensing question and it
matches the mark exactly. Regenerate it by cropping `images/logo.png` above the first row
containing a run of near-white pixels (the top of "PAIDOFF").

Three things to keep in mind when touching the reveal:
- **Keep `.intro-sheen` a direct child of `.intro`, not of `.intro-stage`.** Nested inside the stage
  it inherits the spin and rotates with the logo instead of sweeping the screen.
- **Do not add `backface-visibility: hidden`** to the spinning element. It turns through two full
  revolutions, so hiding the back face blanks it for half of every turn — it strobes instead of
  spinning.
- Animate transform and opacity only. An earlier version animated `filter: blur()`, which drops the
  sequence off the compositor and makes the spin hitch.

Images live in `images/`. All 21 style photos were extracted from `PO inventory.xlsm` — they are
embedded drawing objects in `xl/media`, **not cell values**, so reading the sheet with
`openpyxl(values_only=True)` shows an empty IMAGE column and misses them entirely. Each was matched
to its style by the drawing anchor row in `xl/drawings/drawingN.xml`, so every shot is provably the
one sitting in that workbook row. Filenames are semantic (`belt-lv-multicolor.jpg`,
`backpack-green.jpg`). Nothing renders the "Photo Coming" tile any more.

Left on disk but no longer referenced: `stock-*.jpeg` (old Pexels placeholders) and
`IMG_7806/7807/7817.jpeg` — see the photo discrepancy under Known TODOs before deleting the latter.

**Naming:** listings name the real designer (Amiri, Chrome Hearts, Louis Vuitton, That's An Awful Lot Of
Cough Syrup). This is correct and intentional for a reseller of authentic goods — the first-sale doctrine
and nominative fair use permit using a brand's name to describe genuine items you own and are
reselling, which is why every established resale platform lists by brand. The owner states all stock
is authentic and that receipts are provided to buyers after purchase.

## Features and where they live

| Feature | JS | Notes |
|---|---|---|
| Opening logo reveal | `initIntro` | Full-screen `#intro` at z-index 2000, above the gate's 1000, so it plays before anything is reachable. ~3.3s: the logo spins two full turns on Y while scaling up (2100ms), a viewport-wide shine sweeps across at 950ms, the overlay fades at 2600ms. Behind it sits a city backdrop — two `images/skyline.png` bands tiled `repeat-x` at different scales, opacities and drift speeds for parallax depth, over a blue-lifted night gradient with a horizon glow. Dismissed by the Skip button, a click anywhere, or Esc/Space/Enter. `animationend` unmounts it, with a 4200ms `setTimeout` guard because a backgrounded tab never fires it. Set `INTRO_ONCE_PER_SESSION = true` to play only once per session instead of every load. |
| Email gate | `initGate` | Full-screen overlay blocking the site until an email is captured; `localStorage["poc_gate_passed"]` |
| Featured picks stack | `renderFeatured` / `initStack` | Top 4 items ranked by real visitor clicks, falling back to `DEFAULT_FEATURED_ORDER` |
| Bid of the Week | `renderBidCard` / `refreshBidState` | Auto-rotates weekly via ISO week number — no manual curation; polls `/api/bid` every 6s |
| Catalog | `renderProducts` / `getFilteredProducts` | Category tiles, search, price range, size chips, in-stock toggle, sort |
| Footer / vouches | `initVouchFooter` | The site has exactly **one** footer, fixed to the bottom of the viewport, and it *is* the vouch rotator: one buyer quote at a time, swapped every `VOUCH_ROTATE_MS` (4s), with the brand/copyright line beneath. Quotes come verbatim from the Instagram reference post (`VOUCH_POST_URL`) — **never reword one**, since they are other people's words and editing turns a real quote into a fabricated one. Handles are stored **already masked** in `VOUCHES`: masking only at render would still ship the real usernames in the page source, which is not anonymity. The originals are on the public post. Rotation pauses on hover and while the tab is hidden; `body` carries a `padding-bottom` matching the footer height so content never runs underneath it. |
| Cart | `loadCart` / `saveCart` | `localStorage["poc_cart"]` stores `[{name, size, qty}]`; a *line* is a product + chosen size + quantity, keyed by `lineId` (`name__size`), so two sizes of one style are two lines. `addToCart` tops up an existing line rather than refusing it, returning `"added"` / `"topped-up"` / `"maxed"`. The badge counts units, not lines. `loadCart` drops lines whose style or size has since left `PRODUCTS`. |
| Checkout | `initCheckout` | **Front-end mock — no payment processor.** Card fields are cosmetic; only email/items/total/address are POSTed |
| My Orders | `initOrders` | Email lookup, no accounts |
| 3D tilt | `initTilt` | Any element with `class="tilt"` and optional `data-tilt-max` |

`initTilt()` must be re-called after injecting new `.tilt` markup (`renderProducts` already does).
Everything is wired up from a single `DOMContentLoaded` handler at the bottom of the file.

## Shipping

Rates are weight-based, configured in the "EDIT THIS: shipping" block at the top of
[script.js](script.js). Three pieces:

- `CATEGORY_WEIGHT_OZ` — per-category shipping weight. **These are estimates**, since the workbook
  carries no weights; a product can override with its own `weightOz`. Postage bills on real weight,
  so put the stock on a scale before going live.
- `PACKAGING_OZ` — mailer/padding, added once per order.
- `SHIPPING_TIERS` — cheapest-first bands; the first one the order's total weight fits under wins,
  falling back to `SHIPPING_OVER_MAX`. The first band is flat for everything under 1 lb because the
  12 July 2026 USPS change made all sub-1lb Ground Advantage the same price within a zone.

**The tier prices are national-average placeholders, not real quotes.** Ground Advantage is
zone-priced, so a flat table overcharges nearby buyers and undercharges distant ones. Replace them
with quotes from Pirate Ship's calculator for the zones actually shipped to.

`shippingFor(lines)` and `orderWeightOz(lines)` drive the cart, the checkout panel, and the stored
order. Format money with `money(n)` so everything reads as two decimals.

## Shipping labels (Pirate Ship)

**Pirate Ship has no API** — that is a deliberate product decision on their end, not a missing
credential, so labels cannot be bought programmatically. Their supported bulk path is spreadsheet
upload with a field-mapping step, and `GET /api/labels.csv` emits exactly that: one row per order
with Name / Email / Address 1 / Address 2 / City / State / Zip / Country / Weight (oz) / Items.
Add `?unshipped=1` to skip orders whose status starts with "Shipped". Orders placed before the
address split are skipped, since they have no label-ready address.

Never ask for or handle the owner's Pirate Ship credentials — they download the CSV and upload it
themselves.

## Serving private files

`server.py` uses `SimpleHTTPRequestHandler`, which serves the whole project directory. `PRIVATE_FILES`
blocks the data files (and any dotfile) with a 404 before the static handler ever sees the request —
without it, `orders.json` hands customer names, emails and shipping addresses to anyone who guesses
the URL. **Any new file holding customer data must be added to that set.** Reach order data through
`/api/orders` (scoped to one email) or `/api/labels.csv`.

## API (server.py)

All responses are JSON; all writes are guarded by one global lock and persisted to gitignored JSON
files in the repo root (`clicks.json`, `bids.json`, `orders.json`, `subscribers.json`).

- `GET  /api/stats` — click counts by product name
- `POST /api/click` — `{name}`, increments
- `GET  /api/bid?item=` / `POST /api/bid` — `{item, amount, name}`, rejects bids at or below current
- `GET  /api/orders?email=` / `POST /api/order` — `{email, items, subtotal, shipping, total, weight_oz, ship_to}`, where `ship_to` is `{name, address1, address2, city, state, zip, country}` split into separate fields so the label CSV can map them
- `GET  /api/labels.csv[?unshipped=1]` — Pirate Ship bulk-upload spreadsheet
- `POST /api/subscribe` — `{email}`, email-gate signups

This is a dev-grade backend: flat files, no auth, no validation beyond the basics, single process.
Anything real (payments, an admin view, sending mail) needs a proper backend behind it.

## Known TODOs

- Payments: checkout is a mock. Card data should never actually be collected until a real processor
  (Stripe or similar) handles it — don't build a homegrown card-handling path.
- Resend: `/api/subscribe` has a TODO for the welcome email and drop announcements; account/API key
  not set up yet.
- **Photo quality and provenance.** The workbook shots max out at ~420px, which is soft for a
  storefront card. They are also clearly supplier/wholesale images rather than own photography:
  `shoe-silver-white.jpg` has size quantities ("42*1 43*1 44*3 45*2") burned into the frame and
  another brand's box visible behind the shoes, and `backpack-green.jpg` carries resale-listing
  zoom-icon chrome in its corners. Own photography would fix the resolution, the overlay text, and
  any third-party copyright question in one pass.
- **Photo discrepancy on the Cough Syrup tees.** `IMG_7806/7807/7817.jpeg` (higher res, ~1200px,
  committed earlier) show a *different* graphic — plain block text — than the workbook photos
  anchored to those same three rows, which show the "PERSONA" graphic. One set is wrong for those
  listings. The workbook photos are wired up because they are row-anchored; needs the owner to say
  which is correct.
- **Brands for Shoes and Backpacks** — the workbook lists only colorway/color for those 11 cards, so
  they render `[brand?]`. Needs the owner to supply them. The green backpack photo shows a Goyard
  chevron pattern and the sneaker photo has a Bottega Veneta box in frame, but neither is confirmed
  — do not write a brand into a listing off a photo without the owner saying so.
- **Pricing** — stock is priced $28–$75, but the stated positioning is designer at plain-tee prices.
  Repricing pass still outstanding.
- **Authenticity proof is post-purchase only.** At these prices buyers will assume counterfeit, so
  the site should explain the subsidy and the receipt guarantee up front; nothing on the page does
  that yet.

## Style

- Dark, editorial, high-contrast. Space Grotesk + JetBrains Mono, loaded from Google Fonts.
- Colors come from the `:root` custom properties in [styles.css](styles.css:3) — use the tokens,
  don't hardcode hex values.
- Copy voice is lowercase, terse, streetwear ("second hand. first pick.", "gone when it's gone").
- Both CSS and JS honor `prefers-reduced-motion` — keep new animation behind those checks.
- **Responsive header.** The header is one flex row (logo + nav + cart/orders + follow) needing
  ~676px. Under 820px it becomes two rows — identity and actions on top, the section nav on its own
  horizontally scrollable strip — and under 420px the "Follow" wordmark collapses to its icon.
  Before this, a phone viewport pushed the cart and orders buttons off-screen entirely, so they were
  unreachable. Re-check those two buttons stay on-screen after any header change.
- The featured stack positions cards with fixed 320px pose math in JS, so `.stack-wrap` is clipped
  under 820px to stop the spread widening the document. Changing `STACK_CARD_WIDTH` means
  re-checking narrow viewports.
- Match the existing idiom: template literals for rendering, `document.getElementById`, section
  banner comments (`// ---------- name ----------`), comments that explain *why*, not *what*.
