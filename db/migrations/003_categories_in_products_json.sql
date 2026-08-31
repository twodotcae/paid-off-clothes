-- export_products() used to decide which categories belong in products.json by checking whether
-- any product currently sits in that category. That conflates two different things: a category
-- with zero CURRENT products (legitimate — "a category with no products still renders its tile...
-- it is how a new category gets seeded", per products.json's own README) and a category that only
-- exists because pricing.json pre-seeded a ladder for it before any product uses it (Bags, Shorts).
-- The first belongs in products.json even at zero products; the second never has, until an admin
-- actually adds it. Without a stored answer to "which one is this", the export can't tell them
-- apart, and the old proxy dropped every currently-empty category — including real ones — which is
-- what made the admin "Add Product" category dropdown show "No Options".
ALTER TABLE categories ADD COLUMN in_products_json INTEGER NOT NULL DEFAULT 1;
