from __future__ import annotations

import csv
import re
from pathlib import Path
from datetime import datetime, timezone


COLUMNS = [
    "product_name", "price", "stock_status", "product_id", "shop_name", "product_url",
]


def sanitize_filename(name: str) -> str:
    name = (name or "shop").strip().lower()
    name = re.sub(r"^https?://", "", name)
    name = name.split("/")[0]
    name = re.sub(r"[^a-z0-9._-]+", "_", name)
    name = name.strip("._") or "shop"
    return name


class OutputWriter:
    def __init__(self, shop_name: str, out_dir: str = "data", formats: list[str] | None = None):
        self.shop_name = shop_name
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.formats = formats or ["csv", "xlsx"]
        self.base = sanitize_filename(shop_name)
        self.products: dict[str, dict] = {}

    def _key(self, product: dict) -> str:
        shop = (product.get("shop_name") or self.shop_name or "").strip()
        pid = (product.get("product_id") or "").strip()
        if pid:
            return f"{shop}::{pid}"
        url = (product.get("product_url") or "").strip()
        return f"{shop}::url::{url}"

    def upsert(self, product: dict) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        shop_name = (product.get("shop_name") or self.shop_name or "").strip()
        pid = (product.get("product_id") or "").strip()
        name = (product.get("name") or product.get("product_name") or "").strip()
        if not (shop_name and name and (pid or product.get("product_url"))):
            return False
        key = self._key({**product, "shop_name": shop_name, "product_id": pid})
        row = {
            "product_name": name,
            "price": product.get("price"),
            "stock_status": product.get("stock_status") or "unknown",
            "product_id": pid,
            "shop_name": shop_name,
            "product_url": product.get("product_url"),
        }
        if key in self.products:
            existing = self.products[key]
            merged = dict(existing)
            for k in COLUMNS:
                if row.get(k) not in (None, ""):
                    merged[k] = row[k]
                elif existing.get(k) not in (None, ""):
                    merged[k] = existing[k]
            self.products[key] = merged
        else:
            self.products[key] = row
        return True

    def count(self) -> int:
        return len(self.products)

    def paths(self) -> list[str]:
        out = []
        for fmt in self.formats:
            out.append(str(self.out_dir / f"{self.base}.{fmt}"))
        return out

    def save(self):
        rows = list(self.products.values())
        # stable order
        rows.sort(key=lambda r: (r.get("product_name") or "", r.get("product_url") or ""))
        if "csv" in self.formats:
            path = self.out_dir / f"{self.base}.csv"
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=COLUMNS)
                w.writeheader()
                for r in rows:
                    w.writerow({c: r.get(c) for c in COLUMNS})
        if "xlsx" in self.formats:
            try:
                from openpyxl import Workbook
            except Exception as e:
                raise RuntimeError("openpyxl is required for Excel output. Install it with: pip install openpyxl") from e
            wb = Workbook()
            ws = wb.active
            ws.title = "Products"
            ws.append(COLUMNS)
            for r in rows:
                ws.append([r.get(c) for c in COLUMNS])
            path = self.out_dir / f"{self.base}.xlsx"
            wb.save(path)
        return self.paths()
