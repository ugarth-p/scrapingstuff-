from __future__ import annotations

import re
from bs4 import BeautifulSoup


def _to_int(v) -> int | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        try:
            return int(v)
        except Exception:
            return None
    s = str(v).strip()
    m = re.search(r"-?\d+", s.replace(" ", ""))
    if not m:
        return None
    try:
        return int(m.group(0))
    except Exception:
        return None


def normalize_availability(avail: str | None) -> str | None:
    if not avail:
        return None
    a = avail.lower()
    if "instock" in a or "in_stock" in a or "in stock" in a:
        return "in_stock"
    if "outofstock" in a or "out_of_stock" in a or "out of stock" in a or "soldout" in a or "sold_out" in a:
        return "out_of_stock"
    if "backorder" in a or "preorder" in a or "pre_order" in a:
        return "backorder"
    if "discontinued" in a:
        return "out_of_stock"
    return None


def extract_stock(html: str, structured: dict | None = None) -> tuple[int | None, str]:
    quantity = None
    status = "unknown"

    # 1) structured
    if structured:
        inv = structured.get("inventory")
        quantity = _to_int(inv)
        av = normalize_availability(structured.get("availability"))
        if av:
            status = av

    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)

    # 2) explicit stock attributes in main product context (avoid related/cart elements)
    main = soup.select_one("form.cart, div.product, .summary.entry-summary") or soup
    for attr in ["data-stock", "data-instock", "data-stock_quantity", "data-product_stock"]:
        # prefer elements that look like stock holders, not add-to-cart buttons with purchase qty
        for tag in main.select(f"[{attr}]"):
            classes = " ".join(tag.get("class", [])).lower()
            if "add_to_cart" in classes or "ajax_add_to_cart" in classes:
                continue
            q = _to_int(tag.get(attr))
            if q is not None and quantity is None:
                quantity = q
                break
        if quantity is not None:
            break

    # Explicit stock text in common elements
    for sel in [".stock", "p.stock", "span.stock", ".availability", ".product-stock"]:
        el = soup.select_one(sel)
        if el:
            t = el.get_text(" ", strip=True)
            # try to get numeric count only if phrased as stock/available quantity
            m = re.search(r"(\d+)\s*(?:in stock|en stock|available|disponible|left|restant)", t, re.I)
            if m and quantity is None:
                quantity = _to_int(m.group(1))
            av = normalize_availability(t)
            if av and status == "unknown":
                status = av

    # do NOT use quantity input "value" (default purchase qty) or generic "max" as stock.

    # 3) text heuristics (multilingual hints: en/fr)
    patterns_qty = [
        r"(\d+)\s*(?:in stock|available|en stock|disponible|pi[eè]ces?|pcs?)",
        r"(?:stock|available|disponibilit[eé])\s*[:\-]?\s*(\d+)",
        r"only\s*(\d+)\s*left",
        r"plus que\s*(\d+)",
    ]
    for pat in patterns_qty:
        m = re.search(pat, text, re.I)
        if m:
            q = _to_int(m.group(1))
            if q is not None:
                quantity = q
                break

    # status phrases
    if status == "unknown":
        low = text.lower()
        out_phrases = ["out of stock", "rupture de stock", "sold out", "épuisé", "epuise", "indisponible", "unavailable"]
        in_phrases = ["in stock", "en stock", "disponible", "available"]
        back_phrases = ["backorder", "preorder", "précommande", "precommande", "sur commande"]
        if any(p in low for p in out_phrases):
            status = "out_of_stock"
        elif any(p in low for p in back_phrases):
            status = "backorder"
        elif any(p in low for p in in_phrases):
            status = "in_stock"

    # 4) infer
    if quantity is not None:
        if quantity <= 0:
            status = "out_of_stock" if status == "unknown" else status
            if status == "in_stock":
                status = "out_of_stock"
        else:
            if status == "unknown":
                status = "in_stock"
    if status == "out_of_stock" and quantity is None:
        quantity = 0
    if status == "in_stock" and quantity == 0:
        # conflicting; prefer status text? keep 0 but status in_stock unlikely
        pass

    return quantity, status
