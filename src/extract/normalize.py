from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..utils.text import clean_text, parse_price, extract_add_to_cart_id
from ..utils.urls import canonicalize_url, get_domain, url_hash
from .structured import extract_jsonld
from .meta import extract_meta
from .stock import extract_stock


def _is_non_product_url(url: str) -> bool:
    path = urlparse(url).path.lower().rstrip("/")
    if path in ("", "/"):
        return True
    # pagination
    if re.search(r"/page/\d+$", path):
        return True
    # obvious non-product sections
    for prefix in [
        "/categorie-produit", "/product-category", "/category", "/categories",
        "/etiquette-produit", "/product-tag", "/tag",
        "/cart", "/panier", "/checkout", "/mon-compte", "/my-account",
        "/contact", "/blog", "/wp-", "/feed",
    ]:
        if path == prefix or path.startswith(prefix + "/"):
            return True
    # shop/boutique root is a listing
    if path == "/boutique" or path == "/shop":
        return True
    return False


def is_likely_product(html: str, url: str, structured: dict | None) -> bool:
    if _is_non_product_url(url):
        return False

    soup = BeautifulSoup(html, "lxml")
    # reject pages that are clearly listings of multiple products
    if soup.select_one("body.archive") or soup.select_one("body.post-type-archive-product") or soup.select_one("body.tax-product_cat") or soup.select_one("body.tax-product_tag"):
        # but allow if actually single product
        if not soup.select_one("body.single-product"):
            return False

    has_product_dom = bool(soup.select_one("body.single-product, form.cart, .single_add_to_cart_button, div.product.type-product, .woocommerce-product-gallery"))
    has_price = bool(soup.select_one(".summary .price, p.price, .product-price, [itemprop='price'], .woocommerce-Price-amount"))
    path = urlparse(url).path.lower()

    # strong structured-data signal on a plausible page
    if structured and structured.get("name") and (has_product_dom or has_price or "/boutique/" in path or "/product/" in path):
        return True

    if has_product_dom and (has_price or soup.select_one("h1")):
        return True

    # generic product-like URL
    if any(h in path for h in ["/product/", "/produit/", "/boutique/", "/p/", "/item/"]):
        # must have single-product-ish indicators, not just a grid
        if soup.select_one("h1") and (has_price or "da" in soup.get_text(" ", strip=True).lower() or "dzd" in soup.get_text(" ", strip=True).lower()):
            if soup.select_one("form.cart, .single_add_to_cart_button, .summary.entry-summary, .product_title"):
                return True
            # avoid listing pages with many products
            if len(soup.select("ul.products li.product, .products .product")) > 1:
                return False
    return False


def extract_product(html: str, url: str, base_shop_name: str | None = None) -> dict | None:
    structured = extract_jsonld(html)
    if not is_likely_product(html, url, structured):
        return None

    meta = extract_meta(html)
    soup = BeautifulSoup(html, "lxml")

    name = (structured or {}).get("name") or meta.get("name")
    if not name:
        h1 = soup.find("h1")
        name = h1.get_text(" ", strip=True) if h1 else None

    description = (structured or {}).get("description") or meta.get("description")
    if not description:
        # try common containers
        for sel in [
            "#tab-description", ".woocommerce-product-details__short-description",
            ".product-description", "[itemprop='description']", ".description", "article"
        ]:
            el = soup.select_one(sel)
            if el:
                description = el.get_text(" ", strip=True)
                if description and len(description) > 30:
                    break
    # fallback meta desc
    description = clean_text(description)

    price_raw = (structured or {}).get("price") or meta.get("price")
    currency = (structured or {}).get("currency") or meta.get("currency")
    if not price_raw:
        # try visible price (prefer summary/main)
        for sel in [".summary .price .amount", ".summary .price", "p.price .amount", "p.price", ".woocommerce-Price-amount", ".product-price", "[itemprop='price']", ".price"]:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                price_raw = el.get_text(" ", strip=True)
                break
    price_val, parsed_currency = parse_price(price_raw) if isinstance(price_raw, str) else (None, None)
    if price_val is None and isinstance(price_raw, (int, float)):
        try:
            price_val = float(price_raw)
        except Exception:
            price_val = None

    # User requested: always use DA
    currency = "DA"

    quantity, stock_status = extract_stock(html, structured)

    product_id = (structured or {}).get("product_id")
    # prefer sku in dom
    sku_el = soup.select_one(".sku, [itemprop='sku'], .product_meta .sku")
    if sku_el:
        sku_txt = sku_el.get_text(" ", strip=True)
        if sku_txt and sku_txt.lower() not in ("n/a", "na", ""):
            product_id = product_id or sku_txt
    if not product_id:
        # try add-to-cart from main product form first
        main = soup.select_one("form.cart") or soup.select_one(".summary") or soup
        product_id = extract_add_to_cart_id(str(main), url) or extract_add_to_cart_id(html, url)
    if not product_id:
        product_id = "url:" + url_hash(canonicalize_url(url) or url)

    shop_name = base_shop_name or meta.get("shop_name") or get_domain(url)

    if not name:
        return None

    # clean up: ensure not a bogus product
    name_clean = clean_text(name) or (name.strip() if name else "")
    if not name_clean:
        return None

    return {
        "shop_name": shop_name,
        "product_id": str(product_id).strip(),
        "name": name_clean,
        "description": description,
        "price": price_val,
        "currency": currency,
        "quantity": quantity,
        "stock_status": stock_status,
        "product_url": canonicalize_url(url),
        "raw_json": (structured or {}).get("raw_json") if structured else {"meta": meta},
    }
