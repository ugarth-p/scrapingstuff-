CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_name TEXT NOT NULL,
    product_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    price REAL,
    currency TEXT,
    quantity INTEGER,
    stock_status TEXT,
    product_url TEXT,
    raw_json TEXT,
    scraped_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE(shop_name, product_id)
);

CREATE INDEX IF NOT EXISTS idx_products_shop_url ON products(shop_name, product_url);
CREATE INDEX IF NOT EXISTS idx_products_shop_name ON products(shop_name);
