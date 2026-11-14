# Web Scraper (Generic Shop)

Generic web scraper that crawls an online shop, discovers product pages, and stores normalized product data in SQLite.

## Stored fields
- `shop_name`
- `product_id`
- `name`
- `description`
- `price` (+ `currency`)
- `quantity` (numeric stock count when available, else NULL)
- `stock_status` (`in_stock`, `out_of_stock`, `backorder`, `unknown`)
- `product_url`, `scraped_at`, `last_seen_at`

## Setup
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix: source .venv/bin/activate
pip install -r requirements.txt
```

## Usage
```bash
python -m src.cli --url http://esp32lab.com/ --db data/products.db
```

Options:
- `--max-pages` limit number of pages to fetch
- `--max-depth` crawl depth
- `--browser-fallback` enable Playwright fallback for JS-heavy sites (requires `playwright install`)

## Notes
- Respects `robots.txt` (including `Crawl-delay`) when enabled.
- Uses structured data (JSON-LD/Microdata) first, then meta/heuristics.
- Upserts by `(shop_name, product_id)` or `(shop_name, product_url)` to avoid duplicates.
- Generic extraction may miss fields on highly custom sites; check logs for low-confidence pages.
