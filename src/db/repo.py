from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ProductRepo:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        schema_path = Path(__file__).with_name("schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            self.conn.executescript(f.read())
        self.conn.commit()

    def upsert(self, product: dict):
        now = datetime.now(timezone.utc).isoformat()
        scraped_at = product.get("scraped_at") or now
        last_seen_at = now
        raw_json = json.dumps(product.get("raw_json")) if product.get("raw_json") is not None else None
        # ensure required
        shop_name = (product.get("shop_name") or "").strip()
        product_id = (product.get("product_id") or "").strip()
        name = (product.get("name") or "").strip()
        if not (shop_name and product_id and name):
            return False
        # Try upsert by (shop_name, product_id)
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO products (shop_name, product_id, name, description, price, currency, quantity, stock_status, product_url, raw_json, scraped_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(shop_name, product_id) DO UPDATE SET
                name=excluded.name,
                description=COALESCE(excluded.description, products.description),
                price=excluded.price,
                currency=COALESCE(excluded.currency, products.currency),
                quantity=excluded.quantity,
                stock_status=excluded.stock_status,
                product_url=COALESCE(excluded.product_url, products.product_url),
                raw_json=COALESCE(excluded.raw_json, products.raw_json),
                last_seen_at=excluded.last_seen_at
            """,
            (
                shop_name,
                product_id,
                name,
                product.get("description"),
                product.get("price"),
                product.get("currency"),
                product.get("quantity"),
                product.get("stock_status"),
                product.get("product_url"),
                raw_json,
                scraped_at,
                last_seen_at,
            ),
        )
        self.conn.commit()
        return True

    def count(self) -> int:
        cur = self.conn.execute("SELECT COUNT(*) as c FROM products")
        return int(cur.fetchone()["c"])

    def close(self):
        self.conn.close()
