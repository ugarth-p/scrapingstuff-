from __future__ import annotations

import json
from typing import Any


def _iter_products(obj: Any):
    if isinstance(obj, dict):
        t = obj.get("@type")
        if t:
            types = t if isinstance(t, list) else [t]
            if any(isinstance(x, str) and x.lower() == "product" for x in types):
                yield obj
        if "@graph" in obj and isinstance(obj["@graph"], list):
            for item in obj["@graph"]:
                yield from _iter_products(item)
        for v in obj.values():
            yield from _iter_products(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_products(item)


def extract_jsonld(html: str) -> dict | None:
    try:
        import extruct
        from w3lib.html import get_base_url  # not needed but extruct ok without
    except Exception:
        extruct = None
    data = {}
    if extruct:
        try:
            data = extruct.extract(html, syntaxes=["json-ld", "microdata"], errors="ignore")
        except Exception:
            data = {}
    else:
        # minimal fallback: parse <script type="application/ld+json">
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        blobs = []
        for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                blobs.append(json.loads(s.string or ""))
            except Exception:
                pass
        data = {"json-ld": blobs}

    products = list(_iter_products(data.get("json-ld", []))) + list(_iter_products(data.get("microdata", [])))
    if not products:
        return None
    p = products[0]
    return normalize_product_node(p, raw=p)


def _as_text(v):
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return v.get("name") or v.get("@value") or v.get("value")
    if isinstance(v, list) and v:
        return _as_text(v[0])
    return str(v)


def normalize_product_node(p: dict, raw=None) -> dict:
    offers = p.get("offers") or {}
    if isinstance(offers, list) and offers:
        offers = offers[0]
    # aggregateOffer
    if isinstance(offers, dict) and offers.get("@type", "").lower() == "aggregateoffer":
        price = offers.get("lowPrice") or offers.get("highPrice") or offers.get("price")
        currency = offers.get("priceCurrency")
        availability = offers.get("availability")
        inventory = offers.get("inventoryLevel")
    else:
        price = offers.get("price") if isinstance(offers, dict) else None
        currency = offers.get("priceCurrency") if isinstance(offers, dict) else None
        availability = offers.get("availability") if isinstance(offers, dict) else None
        inventory = None
        if isinstance(offers, dict):
            inv = offers.get("inventoryLevel")
            if isinstance(inv, dict):
                inventory = inv.get("value") or inv.get("minValue")
            else:
                inventory = inv

    brand = p.get("brand")
    brand_name = _as_text(brand)

    return {
        "name": _as_text(p.get("name")),
        "description": _as_text(p.get("description")),
        "price": _as_text(price),
        "currency": _as_text(currency),
        "product_id": _as_text(p.get("sku") or p.get("productID") or p.get("mpn") or p.get("gtin13") or p.get("gtin")),
        "availability": _as_text(availability),
        "inventory": _as_text(inventory),
        "brand": brand_name,
        "image": _as_text(p.get("image")),
        "raw_json": raw or p,
    }
