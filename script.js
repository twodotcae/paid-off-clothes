// ---------- EDIT THIS: your stock ----------
const CATEGORIES = ["All", "T-Shirts", "Belts", "Shoes", "Backpacks"];

// Real stock imported from PO_inventory — generic non-brand names (see chat). 3 "Cough Syrup" tee
// styles use their real (unbranded) product photos; everything else uses free-license stock photos
// (Pexels, no attribution required) shared across styles within a category as generic placeholders
// — swap in real per-item shots when you have them. Prices are placeholders too.
const PRODUCTS = [
  ...expandSizedStock("T-Shirts", "Cough Syrup Graphic Tee (Style 1)", "Heavyweight cotton tee, bold graphic front and back print.", 32, { S: 5, M: 5, L: 5, XL: 5, XXL: 0 }, "images/IMG_7806.jpeg"),
  ...expandSizedStock("T-Shirts", "Cough Syrup Graphic Tee (Style 2)", "Heavyweight cotton tee, bold graphic front and back print.", 32, { S: 5, M: 5, L: 5, XL: 5, XXL: 0 }, "images/IMG_7817.jpeg"),
  ...expandSizedStock("T-Shirts", "Cough Syrup Graphic Tee (Style 3)", "Heavyweight cotton tee, bold graphic front and back print, cartoon character detail.", 32, { S: 5, M: 5, L: 5, XL: 5, XXL: 0 }, "images/IMG_7807.jpeg"),
  ...expandSizedStock("T-Shirts", "Bold Block Letter Tee", "Oversized fit tee with large 3D-style block lettering across the chest.", 38, { S: 5, M: 5, L: 5, XL: 4, XXL: 2 }, "images/stock-tee.jpeg"),
  ...expandSizedStock("T-Shirts", "Minimal Logo Graphic Tee", "Relaxed fit tee with a clean centered wordmark graphic.", 34, { S: 4, M: 5, L: 5, XL: 4, XXL: 2 }, "images/stock-tee.jpeg"),
  ...expandSizedStock("T-Shirts", "Gothic Cross Tank Top", "Ribbed tank top with a gothic cross emblem print, front and back.", 28, { S: 20, M: 20, L: 20, XL: 5, XXL: 0 }, "images/stock-tee.jpeg"),

  ...expandSizedStock("Belts", "Black Cross Buckle Belt", "Leather belt with an oversized cross-shaped buckle.", 45, { "100cm": 3, "105cm": 0, "110cm": 2, "115cm": 0, "120cm": 0 }, "images/stock-belt.jpeg"),
  ...expandSizedStock("Belts", "White Buckle Belt (Style 1)", "Leather belt with a polished buckle.", 45, { "100cm": 2, "105cm": 0, "110cm": 2, "115cm": 0, "120cm": 0 }, "images/stock-belt.jpeg"),
  ...expandSizedStock("Belts", "White Buckle Belt (Style 2)", "Leather belt with a polished buckle.", 45, { "100cm": 6, "105cm": 0, "110cm": 0, "115cm": 0, "120cm": 0 }, "images/stock-belt.jpeg"),
  ...expandSizedStock("Belts", "White Oval Buckle Belt", "Leather belt with an oval-shaped buckle.", 45, { "100cm": 3, "105cm": 0, "110cm": 3, "115cm": 0, "120cm": 0 }, "images/stock-belt.jpeg"),
  ...expandSizedStock("Belts", "Two-Tone Monogram Belt — Black Hardware", "Woven monogram-pattern belt, dark hardware.", 55, { "100cm": 0, "105cm": 3, "110cm": 3, "115cm": 3, "120cm": 3 }, "images/stock-belt.jpeg"),
  ...expandSizedStock("Belts", "Two-Tone Monogram Belt — Silver Hardware", "Woven monogram-pattern belt, polished hardware.", 55, { "100cm": 0, "105cm": 3, "110cm": 3, "115cm": 3, "120cm": 0 }, "images/stock-belt.jpeg"),
  ...expandSizedStock("Belts", "Monogram Print Belt — Black", "Coated canvas belt, all-over monogram print.", 50, { "100cm": 0, "105cm": 3, "110cm": 3, "115cm": 3, "120cm": 2 }, "images/stock-belt.jpeg"),
  ...expandSizedStock("Belts", "Embossed Belt — Black", "Debossed leather belt with tonal pattern detailing.", 50, { "100cm": 0, "105cm": 3, "110cm": 3, "115cm": 3, "120cm": 3 }, "images/stock-belt.jpeg"),
  ...expandSizedStock("Belts", "Monogram Print Belt — White", "Coated canvas belt, all-over monogram print.", 50, { "100cm": 0, "105cm": 4, "110cm": 3, "115cm": 3, "120cm": 2 }, "images/stock-belt.jpeg"),
  ...expandSizedStock("Belts", "Multicolor Monogram Belt", "Coated canvas belt, multicolor monogram print.", 60, { "100cm": 0, "105cm": 5, "110cm": 0, "115cm": 0, "120cm": 0 }, "images/stock-belt.jpeg"),

  ...expandSizedStock("Shoes", "Silver / White Runner", "Chunky low-top sneaker, layered mesh and suede paneling.", 75, { "EU 42": 1, "EU 43": 1, "EU 44": 3, "EU 45": 2 }, "images/stock-sneaker.jpeg"),
  ...expandSizedStock("Shoes", "Black / White Runner", "Chunky low-top sneaker, layered mesh and suede paneling.", 75, { "EU 42": 1, "EU 43": 2, "EU 44": 2, "EU 45": 2 }, "images/stock-sneaker.jpeg"),

  ...oneSizeStock("Backpacks", "Woven Pattern Backpack — Green", "Coated canvas backpack, all-over woven print with leather trim.", 70, 3, "images/stock-backpack.jpeg"),
  ...oneSizeStock("Backpacks", "Woven Pattern Backpack — Black", "Coated canvas backpack, all-over woven print with leather trim.", 70, 5, "images/stock-backpack.jpeg"),
  ...oneSizeStock("Backpacks", "Woven Pattern Backpack — Brown", "Coated canvas backpack, all-over woven print with leather trim.", 70, 5, "images/stock-backpack.jpeg"),
];

// Expands a style into one product card per size that's actually in stock (skips zero-qty sizes).
// No `img` — these show the "Photo Coming" placeholder until real (non-branded) photos are added.
function expandSizedStock(category, name, desc, price, sizeQty, img) {
  return Object.entries(sizeQty)
    .filter(([, qty]) => qty > 0)
    .map(([size, qty]) => ({
      name,
      category,
      meta: `Size ${size}`,
      price,
      status: "available",
      stock: qty,
      desc,
      ...(img ? { img } : {}),
    }));
}

function oneSizeStock(category, name, desc, price, qty, img) {
  if (qty <= 0) return [];
  return [{ name, category, meta: "One Size", price, status: "available", stock: qty, desc, ...(img ? { img } : {}) }];
}

const state = { category: "All", search: "", sizes: [], minPrice: null, maxPrice: null, inStockOnly: false, sort: "newest" };
const tiltBound = new WeakSet();
let currentModalProduct = null;
let checkoutItems = [];

// Most placeholder pieces are one-off (no stock field, implied qty 1); real multi-unit
// stock sets p.stock explicitly.
function stockLabel(p) {
  const qty = p.stock || 1;
  return qty > 1 ? `${qty} left` : "1 left";
}

// meta is "<size/fit> · <condition>" (e.g. "Size 10 · 9/10"), or just "<size/fit>" with no delimiter.
function sizeOf(p) {
  const [rawSize] = p.meta.split(" · ");
  return (rawSize || p.meta).replace(/^Size\s+/i, "");
}

// ---------- bid of the week ----------
let bidItem = null;

function isoWeekNumber(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
}

// Rotates automatically each week — no manual curation needed.
function getBidItem() {
  const eligible = PRODUCTS.filter((p) => p.status === "available");
  if (eligible.length === 0) return null;
  return eligible[isoWeekNumber(new Date()) % eligible.length];
}

function renderBidCard() {
  const card = document.getElementById("bid-card");
  bidItem = getBidItem();

  if (!bidItem) {
    card.innerHTML = `<p class="cart-empty-note">Nothing eligible for bidding right now — check back once new stock drops.</p>`;
    return;
  }

  card.innerHTML = `
    <div class="bid-card-media">${bidItem.img ? `<img src="${bidItem.img}" alt="${bidItem.name}">` : ""}</div>
    <div class="bid-card-info">
      <span class="tag available">Last One In Stock</span>
      <h3>${bidItem.name}</h3>
      <p class="card-meta">${bidItem.category} · ${bidItem.meta}</p>
      <p class="bid-card-desc">${bidItem.desc}</p>
      <div class="bid-current">
        <div>
          <span class="bid-current-label">Current Bid</span>
          <span class="bid-current-amount" id="bid-current-amount">$${bidItem.price}</span>
        </div>
        <span class="bid-current-name" id="bid-current-name">Starting price — no bids yet</span>
      </div>
      <form class="bid-form" id="bid-form">
        <input type="text" id="bid-name" placeholder="Your name" maxlength="40" required />
        <input type="number" id="bid-amount" placeholder="$${bidItem.price + 1}+" min="${bidItem.price + 1}" step="1" required />
        <button type="submit" class="btn btn-primary tilt" data-tilt-max="6">Place Bid</button>
      </form>
      <p class="bid-error" id="bid-error" hidden></p>
      <p class="bid-note">Ends Sunday at midnight. Highest bid wins — no snipe protection, so bid your max.</p>
    </div>
  `;

  document.getElementById("bid-form").addEventListener("submit", (e) => {
    e.preventDefault();
    submitBid();
  });
  document.querySelector(".bid-card-media").addEventListener("click", (e) => {
    if (e.target.tagName === "IMG") openLightbox(e.target.src, e.target.alt);
  });

  initTilt();
  refreshBidState();
}

function updateBidDisplay(current) {
  const amountEl = document.getElementById("bid-current-amount");
  if (!bidItem || !amountEl) return;
  const amountInput = document.getElementById("bid-amount");
  const nameEl = document.getElementById("bid-current-name");
  const minNext = (current && current.amount ? current.amount : bidItem.price) + 1;

  amountEl.textContent = current && current.amount ? `$${current.amount}` : `$${bidItem.price}`;
  nameEl.textContent = current && current.name ? `by ${current.name}` : "Starting price — no bids yet";
  amountInput.min = minNext;
  amountInput.placeholder = `$${minNext}+`;
}

async function refreshBidState() {
  if (!bidItem) return;
  try {
    const res = await fetch(`/api/bid?item=${encodeURIComponent(bidItem.name)}`);
    if (res.ok) {
      const current = await res.json();
      updateBidDisplay(current && current.amount ? current : null);
    }
  } catch (e) {
    // offline / static hosting — leave starting price shown
  }
}

async function submitBid() {
  const errorEl = document.getElementById("bid-error");
  const nameInput = document.getElementById("bid-name");
  const amountInput = document.getElementById("bid-amount");
  errorEl.hidden = true;

  const name = nameInput.value.trim();
  const amount = Number(amountInput.value);
  const minBid = Number(amountInput.min);

  if (!name || !amount || amount < minBid) {
    errorEl.textContent = `Enter a name and a bid of at least $${minBid}.`;
    errorEl.hidden = false;
    return;
  }

  try {
    const res = await fetch("/api/bid", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item: bidItem.name, amount, name }),
    });
    const data = await res.json();
    if (data.ok) {
      updateBidDisplay(data.current);
      amountInput.value = "";
    } else {
      updateBidDisplay(data.current || null);
      errorEl.textContent = data.error || "Someone already bid higher — try a higher amount.";
      errorEl.hidden = false;
    }
  } catch (e) {
    errorEl.textContent = "Couldn't reach the server — try again in a moment.";
    errorEl.hidden = false;
  }
}

// ---------- featured picks (card stack) — ranked by visitor clicks ----------
// Used as the tiebreak/starting order until real click counts overtake it.
const DEFAULT_FEATURED_ORDER = [
  "Bold Block Letter Tee",
  "Two-Tone Monogram Belt — Black Hardware",
  "Silver / White Runner",
  "Woven Pattern Backpack — Green",
];

let clickCounts = {};
let FEATURED = [];

async function loadClickCounts() {
  try {
    const res = await fetch("/api/stats");
    if (res.ok) clickCounts = await res.json();
  } catch (e) {
    // no backend available (e.g. static hosting) — fall back to default order
  }
}

// Recomputed on page load only, not mid-session, so cards don't shuffle under a browsing visitor.
function trackClick(name) {
  clickCounts[name] = (clickCounts[name] || 0) + 1;
  fetch("/api/click", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  }).catch(() => {});
}

function computeFeatured(n = 4) {
  return PRODUCTS.slice()
    .sort((a, b) => {
      const byClicks = (clickCounts[b.name] || 0) - (clickCounts[a.name] || 0);
      if (byClicks !== 0) return byClicks;
      const da = DEFAULT_FEATURED_ORDER.indexOf(a.name);
      const db = DEFAULT_FEATURED_ORDER.indexOf(b.name);
      return (da === -1 ? 999 : da) - (db === -1 ? 999 : db);
    })
    .slice(0, n);
}

function featuredStatsFor(p) {
  const [, rawCondition] = p.meta.split(" · ");
  return [
    ["Size", sizeOf(p)],
    ["Condition", rawCondition || "—"],
    ["Price", `$${p.price}`],
    ["Status", p.status === "sold" ? "Sold Out" : "Available"],
  ];
}

const STACK_CARD_WIDTH = 320;
const STACK_CARD_OVERLAP = 240;
let stackExpanded = false;
let stackHoveredIndex = null;

function stackPose(index, total, expanded) {
  if (!expanded) {
    const centerOffset = (total - 1) * 5;
    return {
      x: index * 10 - centerOffset,
      y: index * 2,
      rot: index * 1.5,
    };
  }
  const totalExpandedWidth = STACK_CARD_WIDTH + (total - 1) * (STACK_CARD_WIDTH - STACK_CARD_OVERLAP);
  const expandedCenterOffset = totalExpandedWidth / 2;
  return {
    x: index * (STACK_CARD_WIDTH - STACK_CARD_OVERLAP) - expandedCenterOffset + STACK_CARD_WIDTH / 2,
    y: 0,
    rot: index * 5 - (total - 1) * 2.5,
  };
}

function renderFeatured() {
  const wrap = document.getElementById("stack-wrap");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  FEATURED = computeFeatured();

  wrap.innerHTML = FEATURED.map((p, index) => `
    <div class="stack-card" style="z-index:${FEATURED.length - index}" data-index="${index}" tabindex="0">
      <dl class="stack-specs">
        ${featuredStatsFor(p).map(([label, value]) => `<div class="stack-spec"><dd class="stack-spec-value">${value}</dd><dt class="stack-spec-label">${label}</dt></div>`).join("")}
      </dl>
      <div class="stack-image">${p.img ? `<img src="${p.img}" alt="${p.name}" loading="lazy">` : `<span>Photo Coming</span>`}</div>
      <span class="stack-title">${p.name}</span>
      <span class="stack-subtitle">${p.category}</span>
      <p class="stack-desc">${p.desc}</p>
    </div>
  `).join("");

  applyStackPoses(reduced);

  wrap.querySelectorAll(".stack-card").forEach((card) => {
    const index = Number(card.dataset.index);

    card.addEventListener("mouseenter", () => {
      stackHoveredIndex = index;
      applyStackPoses(reduced);
    });
    card.addEventListener("mouseleave", () => {
      stackHoveredIndex = null;
      applyStackPoses(reduced);
    });
    card.addEventListener("focus", () => {
      stackHoveredIndex = index;
      applyStackPoses(reduced);
    });
    card.addEventListener("blur", () => {
      stackHoveredIndex = null;
      applyStackPoses(reduced);
    });
  });
}

function applyStackPoses(reduced) {
  const wrap = document.getElementById("stack-wrap");
  wrap.querySelectorAll(".stack-card").forEach((card, index) => {
    const pose = stackPose(index, FEATURED.length, stackExpanded);
    const isHovered = stackExpanded && stackHoveredIndex === index;
    const isDimmed = stackExpanded && stackHoveredIndex !== null && stackHoveredIndex !== index;

    card.style.transitionDelay = stackExpanded && !reduced ? `${index * 40}ms` : "0ms";
    card.style.setProperty("--sx", `${pose.x}px`);
    card.style.setProperty("--sy", `${isHovered ? pose.y - 18 : pose.y}px`);
    card.style.setProperty("--srot", reduced ? "0deg" : `${pose.rot}deg`);
    card.style.setProperty("--sscale", isHovered ? "1.14" : isDimmed ? "0.94" : "1");
    card.style.setProperty("--sopacity", isDimmed ? "0.75" : "1");
    card.style.zIndex = isHovered ? String(FEATURED.length + 10) : String(FEATURED.length - index);
  });
}

// Spreads the stack on hover; whichever card is hovered scales up and becomes the focal point.
// Click still expands/opens on touch devices, which don't fire hover events.
function initStack() {
  const wrap = document.getElementById("stack-wrap");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const expand = () => {
    if (stackExpanded) return;
    stackExpanded = true;
    wrap.setAttribute("aria-expanded", "true");
    applyStackPoses(reduced);
  };
  const collapse = () => {
    if (!stackExpanded) return;
    stackExpanded = false;
    stackHoveredIndex = null;
    wrap.setAttribute("aria-expanded", "false");
    applyStackPoses(reduced);
  };

  wrap.addEventListener("mouseenter", expand);
  wrap.addEventListener("mouseleave", collapse);
  wrap.addEventListener("focusin", expand);
  wrap.addEventListener("focusout", (e) => {
    if (!wrap.contains(e.relatedTarget)) collapse();
  });

  wrap.addEventListener("click", (e) => {
    if (!stackExpanded) {
      expand();
      return;
    }
    const card = e.target.closest(".stack-card");
    if (card) openModal(FEATURED[Number(card.dataset.index)]);
  });
  wrap.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (!stackExpanded) expand();
      else if (stackHoveredIndex !== null) openModal(FEATURED[stackHoveredIndex]);
    }
  });
}

function renderCategoryTiles() {
  const wrap = document.getElementById("category-tiles");

  wrap.innerHTML = CATEGORIES.map((c) => {
    const count = c === "All" ? PRODUCTS.length : PRODUCTS.filter((p) => p.category === c).length;
    const thumb = (PRODUCTS.find((p) => p.img && (c === "All" || p.category === c)) || {}).img;
    return `
      <button type="button" class="category-tile tilt ${c === state.category ? "active" : ""}" data-tilt-max="5" data-category="${c}">
        ${thumb ? `<img src="${thumb}" alt="" loading="lazy">` : ""}
        <div class="category-tile-overlay">
          <span class="category-tile-name">${c}</span>
          <span class="category-tile-count">${count} item${count === 1 ? "" : "s"}</span>
        </div>
      </button>
    `;
  }).join("");

  wrap.querySelectorAll(".category-tile").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.category = btn.dataset.category;
      document.getElementById("catalog-title").textContent =
        state.category === "All" ? "All Stock" : state.category;
      renderCategoryTiles();
      renderProducts();
      document.getElementById("catalog-head").scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  initTilt();
}

function renderSizeFilter() {
  const wrap = document.getElementById("size-filter");
  const sizes = [...new Set(PRODUCTS.map(sizeOf))].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));

  wrap.innerHTML = sizes.map((s) => `
    <button type="button" class="size-chip ${state.sizes.includes(s) ? "active" : ""}" data-size="${s}">${s}</button>
  `).join("");

  wrap.querySelectorAll(".size-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const size = btn.dataset.size;
      state.sizes = state.sizes.includes(size)
        ? state.sizes.filter((s) => s !== size)
        : [...state.sizes, size];
      renderSizeFilter();
      renderProducts();
    });
  });
}

function getFilteredProducts() {
  let items = PRODUCTS.filter((p) => {
    const matchesCategory = state.category === "All" || p.category === state.category;
    const matchesSearch = p.name.toLowerCase().includes(state.search.toLowerCase());
    const matchesStock = !state.inStockOnly || p.status === "available";
    const matchesSize = state.sizes.length === 0 || state.sizes.includes(sizeOf(p));
    const matchesMin = state.minPrice == null || p.price >= state.minPrice;
    const matchesMax = state.maxPrice == null || p.price <= state.maxPrice;
    return matchesCategory && matchesSearch && matchesStock && matchesSize && matchesMin && matchesMax;
  });

  if (state.sort === "price-asc") items = items.slice().sort((a, b) => a.price - b.price);
  if (state.sort === "price-desc") items = items.slice().sort((a, b) => b.price - a.price);

  return items;
}

function renderProducts() {
  const grid = document.getElementById("product-grid");
  const emptyState = document.getElementById("empty-state");
  const items = getFilteredProducts();

  emptyState.hidden = items.length > 0;
  grid.hidden = items.length === 0;

  grid.innerHTML = items.map((p, i) => `
    <div class="card tilt" data-tilt-max="6" data-index="${PRODUCTS.indexOf(p)}">
      <div class="card-media">
        ${p.img ? `<img src="${p.img}" alt="${p.name}" loading="lazy">` : `<span>Photo Coming</span>`}
        <div class="tilt-glow"></div>
        <span class="tag ${p.status}">${p.status === "sold" ? "Sold Out" : "Available"}</span>
      </div>
      <div class="card-body">
        <p class="card-title">${p.name}</p>
        <p class="card-meta">${p.meta}</p>
        <div class="card-foot">
          <div class="price-block">
            <span class="price">$${p.price}</span>
            ${p.status === "sold" ? "" : `<span class="stock-note">${stockLabel(p)}</span>`}
          </div>
          <button type="button" class="card-cta" data-index="${PRODUCTS.indexOf(p)}">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><circle cx="12" cy="8" r="0.5" fill="currentColor"/></svg>
            Details
          </button>
        </div>
      </div>
    </div>
  `).join("");

  grid.querySelectorAll(".card").forEach((el) => {
    el.addEventListener("click", () => {
      const index = Number(el.dataset.index);
      if (!Number.isNaN(index)) openModal(PRODUCTS[index]);
    });
  });

  initTilt();
}

// ---------- item detail modal ----------
function openModal(p) {
  trackClick(p.name);
  currentModalProduct = p;
  document.getElementById("modal-media").innerHTML = p.img
    ? `<img src="${p.img}" alt="${p.name}">`
    : `<span id="modal-media-label">Photo Coming</span>`;
  const tag = document.getElementById("modal-tag");
  tag.textContent = p.status === "sold" ? "Sold Out" : "Available";
  tag.className = `tag ${p.status}`;
  document.getElementById("modal-title").textContent = p.name;
  document.getElementById("modal-meta").textContent = `${p.category} · ${p.meta}`;
  document.getElementById("modal-desc").textContent = p.desc;
  document.getElementById("modal-price").textContent = `$${p.price}`;
  document.getElementById("modal-stock-note").textContent = p.status === "sold" ? "" : stockLabel(p);
  const buyBtn = document.getElementById("buy-now-btn");
  buyBtn.disabled = p.status === "sold";
  buyBtn.textContent = p.status === "sold" ? "Sold Out" : "Buy Now";
  const cartBtn = document.getElementById("add-to-cart-btn");
  cartBtn.disabled = p.status === "sold";
  cartBtn.textContent = "Add to Cart";
  document.getElementById("modal-overlay").hidden = false;
  syncBodyScroll();
}

function closeModal() {
  document.getElementById("modal-overlay").hidden = true;
  syncBodyScroll();
}

function initModal() {
  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("modal-overlay").addEventListener("click", (e) => {
    if (e.target.id === "modal-overlay") closeModal();
  });
  document.getElementById("modal-media").addEventListener("click", (e) => {
    if (e.target.tagName === "IMG") openLightbox(e.target.src, e.target.alt);
  });
  document.getElementById("buy-now-btn").addEventListener("click", () => {
    if (!currentModalProduct || currentModalProduct.status === "sold") return;
    closeModal();
    openCheckout([currentModalProduct]);
  });
  document.getElementById("add-to-cart-btn").addEventListener("click", (e) => {
    if (!currentModalProduct || currentModalProduct.status === "sold") return;
    const added = addToCart(currentModalProduct);
    const btn = e.currentTarget;
    btn.textContent = added ? "Added ✓" : "Already in Cart";
    setTimeout(() => { btn.textContent = "Add to Cart"; }, 1500);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeLightbox();
      closeModal();
      closeCheckout();
      closeCart();
      closeOrders();
    }
  });
}

// ---------- image lightbox (click product photo to zoom) ----------
function openLightbox(src, alt) {
  document.getElementById("lightbox-img").src = src;
  document.getElementById("lightbox-img").alt = alt;
  document.getElementById("lightbox-overlay").hidden = false;
}

function closeLightbox() {
  document.getElementById("lightbox-overlay").hidden = true;
}

function initLightbox() {
  document.getElementById("lightbox-close").addEventListener("click", closeLightbox);
  document.getElementById("lightbox-overlay").addEventListener("click", (e) => {
    if (e.target.id === "lightbox-overlay") closeLightbox();
  });
}

function syncBodyScroll() {
  const anyOpen = ["modal-overlay", "checkout-overlay", "cart-overlay", "orders-overlay"]
    .some((id) => !document.getElementById(id).hidden);
  document.body.style.overflow = anyOpen ? "hidden" : "";
}

function checkoutItemRow(p, removable) {
  return `
    <div class="checkout-item">
      <div class="checkout-item-media">${p.img ? `<img src="${p.img}" alt="${p.name}">` : ""}</div>
      <div class="checkout-item-info">
        <span class="checkout-item-name">${p.name}</span>
        <span class="checkout-item-meta">${p.category} · ${p.meta}</span>
      </div>
      <span class="price">$${p.price}</span>
      ${removable ? `<button type="button" class="checkout-item-remove" data-name="${p.name}" aria-label="Remove">&times;</button>` : ""}
    </div>
  `;
}

// ---------- checkout (front-end mock — no payment processor wired up yet) ----------
function formatCardNumber(value) {
  return value.replace(/\D/g, "").slice(0, 16).replace(/(.{4})/g, "$1 ").trim();
}

function formatExpiry(value) {
  const digits = value.replace(/\D/g, "").slice(0, 4);
  if (digits.length <= 2) return digits;
  return `${digits.slice(0, 2)} / ${digits.slice(2)}`;
}

// items is always an array — a lone "Buy Now" is a one-item array, cart checkout is the whole cart.
function openCheckout(items) {
  checkoutItems = items;
  const total = items.reduce((sum, p) => sum + p.price, 0);

  document.getElementById("checkout-items").innerHTML = items.map((p) => checkoutItemRow(p, false)).join("");
  document.getElementById("checkout-total-price").textContent = `$${total}`;
  document.getElementById("checkout-form").reset();
  document.getElementById("checkout-form-view").hidden = false;
  document.getElementById("checkout-success-view").hidden = true;

  const payBtn = document.getElementById("checkout-pay-btn");
  payBtn.disabled = false;
  document.getElementById("checkout-pay-label").innerHTML = `Pay <span id="checkout-pay-amount">$${total}</span>`;

  const applePayBtn = document.getElementById("apple-pay-btn");
  applePayBtn.disabled = false;
  document.getElementById("apple-pay-label").textContent = "Pay";

  document.getElementById("checkout-overlay").hidden = false;
  syncBodyScroll();
}

function closeCheckout() {
  document.getElementById("checkout-overlay").hidden = true;
  syncBodyScroll();
}

// Shared success step for both the card form and the Apple Pay button —
// both are front-end previews only, nothing is actually charged. Still records
// a real order (server-side) so My Orders has something to look up.
function completeCheckout(triggerLabelEl, method, successMessage, email) {
  triggerLabelEl.textContent = "Processing...";
  const items = checkoutItems;
  const total = items.reduce((sum, p) => sum + p.price, 0);

  const address = document.getElementById("co-address").value;
  fetch("/api/order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      total,
      address,
      items: items.map((p) => ({ name: p.name, price: p.price })),
    }),
  }).catch(() => {});

  items.forEach((p) => removeFromCart(p.name));

  setTimeout(() => {
    document.getElementById("checkout-form-view").hidden = true;
    document.getElementById("checkout-success-view").hidden = false;
    document.getElementById("payment-alert-title").textContent = `Payment successful — via ${method}`;
    document.getElementById("payment-alert-desc").textContent = successMessage;
  }, 1100);
}

function initCheckout() {
  document.getElementById("checkout-close").addEventListener("click", closeCheckout);
  document.getElementById("checkout-done-btn").addEventListener("click", closeCheckout);
  document.getElementById("checkout-overlay").addEventListener("click", (e) => {
    if (e.target.id === "checkout-overlay") closeCheckout();
  });

  document.getElementById("co-card").addEventListener("input", (e) => {
    e.target.value = formatCardNumber(e.target.value);
  });
  document.getElementById("co-exp").addEventListener("input", (e) => {
    e.target.value = formatExpiry(e.target.value);
  });

  document.getElementById("checkout-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const payBtn = document.getElementById("checkout-pay-btn");
    const email = document.getElementById("co-email").value;
    payBtn.disabled = true;
    const label = checkoutItems.length > 1 ? `Your ${checkoutItems.length} items are` : `${checkoutItems[0].name} is`;
    completeCheckout(
      document.getElementById("checkout-pay-label"),
      "Card",
      `${label} on hold. A confirmation will go to ${email} once shipping is arranged.`,
      email
    );
  });

  document.getElementById("apple-pay-btn").addEventListener("click", () => {
    const btn = document.getElementById("apple-pay-btn");
    btn.disabled = true;
    const email = document.getElementById("co-email").value || "no-email-provided@applepay";
    const label = checkoutItems.length > 1 ? `Your ${checkoutItems.length} items are` : `${checkoutItems[0].name} is`;
    completeCheckout(
      document.getElementById("apple-pay-label"),
      "Apple Pay",
      `${label} on hold. A confirmation will go to ${email} once shipping is arranged.`,
      email
    );
  });
}

// ---------- cart ----------
let cart = [];

function loadCart() {
  try {
    const names = JSON.parse(localStorage.getItem("poc_cart") || "[]");
    cart = names.map((n) => PRODUCTS.find((p) => p.name === n)).filter(Boolean);
  } catch (e) {
    cart = [];
  }
}

function saveCart() {
  localStorage.setItem("poc_cart", JSON.stringify(cart.map((p) => p.name)));
}

function updateCartBadge() {
  const badge = document.getElementById("cart-badge");
  badge.textContent = String(cart.length);
  badge.hidden = cart.length === 0;
}

function addToCart(p) {
  if (cart.some((item) => item.name === p.name)) return false;
  cart.push(p);
  saveCart();
  updateCartBadge();
  return true;
}

function removeFromCart(name) {
  if (!cart.some((p) => p.name === name)) return;
  cart = cart.filter((p) => p.name !== name);
  saveCart();
  updateCartBadge();
  if (!document.getElementById("cart-overlay").hidden) renderCartItems();
}

function renderCartItems() {
  const wrap = document.getElementById("cart-items");
  const emptyNote = document.getElementById("cart-empty-note");
  const totalRow = document.getElementById("cart-total-row");
  const checkoutBtn = document.getElementById("cart-checkout-btn");

  emptyNote.hidden = cart.length > 0;
  totalRow.hidden = cart.length === 0;
  checkoutBtn.hidden = cart.length === 0;

  wrap.innerHTML = cart.map((p) => checkoutItemRow(p, true)).join("");
  document.getElementById("cart-total-price").textContent = `$${cart.reduce((sum, p) => sum + p.price, 0)}`;

  wrap.querySelectorAll(".checkout-item-remove").forEach((btn) => {
    btn.addEventListener("click", () => removeFromCart(btn.dataset.name));
  });
}

function openCart() {
  renderCartItems();
  document.getElementById("cart-overlay").hidden = false;
  syncBodyScroll();
}

function closeCart() {
  document.getElementById("cart-overlay").hidden = true;
  syncBodyScroll();
}

function initCart() {
  document.getElementById("cart-btn").addEventListener("click", openCart);
  document.getElementById("cart-close").addEventListener("click", closeCart);
  document.getElementById("cart-overlay").addEventListener("click", (e) => {
    if (e.target.id === "cart-overlay") closeCart();
  });
  document.getElementById("cart-checkout-btn").addEventListener("click", () => {
    if (cart.length === 0) return;
    closeCart();
    openCheckout(cart.slice());
  });
}

// ---------- my orders (email lookup — no accounts) ----------
function orderRow(order) {
  const date = new Date(order.time * 1000).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  const itemsSummary = order.items.map((it) => `1x ${it.name}`).join(", ");
  return `
    <div class="order-card">
      <div class="order-card-head">
        <h4>Order #${order.id}</h4>
        <button type="button" class="order-toggle-btn" aria-label="Toggle details" aria-expanded="false">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m7 15 5 5 5-5"/><path d="m7 9 5-5 5 5"/></svg>
        </button>
      </div>
      <div class="order-field-row">
        <span class="order-field-label">Status</span>
        <span class="order-field-value">${order.status}</span>
      </div>
      <div class="order-details" hidden>
        <div class="order-field-row order-field-block">
          <p class="order-field-label">Placed</p>
          <p class="order-field-value">${date} · $${order.total}</p>
        </div>
        <div class="order-field-row order-field-block">
          <p class="order-field-label">Shipping address</p>
          <p class="order-field-value">${order.address || "Not provided"}</p>
        </div>
        <div class="order-field-row order-field-block">
          <p class="order-field-label">Items</p>
          <p class="order-field-value">${itemsSummary}</p>
        </div>
      </div>
    </div>
  `;
}

function initOrders() {
  document.getElementById("orders-btn").addEventListener("click", () => {
    document.getElementById("orders-overlay").hidden = false;
    syncBodyScroll();
  });
  document.getElementById("orders-close").addEventListener("click", closeOrders);
  document.getElementById("orders-overlay").addEventListener("click", (e) => {
    if (e.target.id === "orders-overlay") closeOrders();
  });

  document.getElementById("orders-list").addEventListener("click", (e) => {
    const btn = e.target.closest(".order-toggle-btn");
    if (!btn) return;
    const details = btn.closest(".order-card").querySelector(".order-details");
    const open = details.hidden;
    details.hidden = !open;
    btn.setAttribute("aria-expanded", String(open));
    btn.classList.toggle("open", open);
  });

  document.getElementById("orders-lookup-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("orders-email").value.trim();
    const list = document.getElementById("orders-list");
    const emptyNote = document.getElementById("orders-empty-note");
    list.innerHTML = "";
    emptyNote.hidden = true;

    try {
      const res = await fetch(`/api/orders?email=${encodeURIComponent(email)}`);
      const orders = res.ok ? await res.json() : [];
      if (orders.length === 0) {
        emptyNote.hidden = false;
      } else {
        list.innerHTML = orders.slice().reverse().map(orderRow).join("");
      }
    } catch (err) {
      emptyNote.textContent = "Couldn't reach the server — try again in a moment.";
      emptyNote.hidden = false;
    }
  });
}

function closeOrders() {
  document.getElementById("orders-overlay").hidden = true;
  syncBodyScroll();
}

// ---------- email gate (blocks the site until an email is captured) ----------
// Welcome + new-drop emails go out via Resend later — not wired up yet, this just
// persists the signup server-side and remembers the visitor locally so they aren't
// re-gated on their next visit.
function initGate() {
  const overlay = document.getElementById("gate-overlay");

  if (localStorage.getItem("poc_gate_passed") === "1") {
    overlay.hidden = true;
    return;
  }

  document.body.style.overflow = "hidden";

  document.getElementById("gate-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("gate-email").value.trim();
    const errorEl = document.getElementById("gate-error");
    const btn = document.getElementById("gate-submit-btn");
    errorEl.hidden = true;
    btn.disabled = true;
    btn.textContent = "One sec...";

    try {
      const res = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (!data.ok) {
        errorEl.textContent = data.error || "That email didn't work — try again.";
        errorEl.hidden = false;
        btn.disabled = false;
        btn.textContent = "Get Access";
        return;
      }
    } catch (err) {
      // Server unreachable (e.g. static hosting) — don't hard-lock out a real visitor.
    }

    localStorage.setItem("poc_gate_passed", "1");
    overlay.hidden = true;
    document.body.style.overflow = "";
  });
}

// ---------- search / filter / sort controls ----------
function initControls() {
  document.getElementById("search-input").addEventListener("input", (e) => {
    state.search = e.target.value;
    renderProducts();
  });
  document.getElementById("price-min").addEventListener("input", (e) => {
    state.minPrice = e.target.value === "" ? null : Number(e.target.value);
    renderProducts();
  });
  document.getElementById("price-max").addEventListener("input", (e) => {
    state.maxPrice = e.target.value === "" ? null : Number(e.target.value);
    renderProducts();
  });
  document.getElementById("instock-checkbox").addEventListener("change", (e) => {
    state.inStockOnly = e.target.checked;
    renderProducts();
  });
  document.getElementById("sort-select").addEventListener("change", (e) => {
    state.sort = e.target.value;
    renderProducts();
  });
}

// ---------- social follow pill (tap-to-expand for touch devices) ----------
function initSocialToggle() {
  const toggle = document.getElementById("social-toggle");
  const btn = document.getElementById("social-toggle-btn");
  if (!toggle || !btn) return;
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    toggle.classList.toggle("open");
  });
  document.addEventListener("click", (e) => {
    if (!toggle.contains(e.target)) toggle.classList.remove("open");
  });
}

// ---------- 3D tilt hover, ported from the sniper-school TiltCard ----------
function initTilt() {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced) return;

  document.querySelectorAll(".tilt").forEach((el) => {
    if (tiltBound.has(el)) return;
    tiltBound.add(el);

    if (!el.querySelector(":scope > .tilt-glow")) {
      const glow = document.createElement("div");
      glow.className = "tilt-glow";
      el.appendChild(glow);
    }

    const maxTilt = Number(el.dataset.tiltMax || 7);
    let raf = null;

    el.addEventListener("mousemove", (e) => {
      const rect = el.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = (e.clientY - rect.top) / rect.height;

      if (raf) cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const rx = (0.5 - y) * maxTilt * 2;
        const ry = (x - 0.5) * maxTilt * 2;
        el.style.setProperty("--rx", `${rx}deg`);
        el.style.setProperty("--ry", `${ry}deg`);
        el.style.setProperty("--spot-x", `${x * 100}%`);
        el.style.setProperty("--spot-y", `${y * 100}%`);
        el.style.setProperty("--spot-o", "0.55");
        el.style.setProperty("--scale", "1.02");
      });
    });

    el.addEventListener("mouseleave", () => {
      if (raf) {
        cancelAnimationFrame(raf);
        raf = null;
      }
      el.style.setProperty("--rx", "0deg");
      el.style.setProperty("--ry", "0deg");
      el.style.setProperty("--spot-o", "0");
      el.style.setProperty("--scale", "1");
    });
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  initGate();
  await loadClickCounts();
  renderFeatured();
  initStack();
  renderBidCard();
  setInterval(refreshBidState, 6000);
  renderCategoryTiles();
  renderSizeFilter();
  renderProducts();
  loadCart();
  updateCartBadge();
  initModal();
  initLightbox();
  initCheckout();
  initCart();
  initOrders();
  initControls();
  initSocialToggle();
  initTilt();
});
