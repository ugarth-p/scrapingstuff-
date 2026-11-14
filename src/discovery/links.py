from __future__ import annotations

import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from ..utils.urls import canonicalize_url, same_domain


PRODUCT_HINTS = ["/product", "/produit", "/boutique/", "/p/", "/item", "/shop/"]
LISTING_HINTS = ["/category", "/categorie", "/collection", "/collections", "/boutique", "/shop", "/catalog", "/c/"]
SKIP_HINTS = ["/cart", "/panier", "/checkout", "/mon-compte", "/my-account", "/login", "/wp-admin", "/contact", "/blog", "/tag/", "mailto:", "tel:", "javascript:"]


def extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if not href:
            continue
        if any(h in href for h in ["mailto:", "tel:", "javascript:"]):
            continue
        u = canonicalize_url(href, base=base_url)
        if not u:
            continue
        if same_domain(u, base_url):
            links.append(u)
    # dedupe preserve order
    seen = set()
    out = []
    for u in links:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def classify_url(url: str) -> str:
    path = urlparse(url).path.lower()
    if any(h in path for h in ["/cart", "/panier", "/checkout", "/mon-compte", "/my-account", "/wp-login", "/contact"]):
        return "skip"
    if any(h in path for h in ["/product/", "/produit/", "/boutique/"]) and not path.rstrip("/").endswith("/boutique"):
        # /boutique/slug/ likely product on woo; /boutique/ listing
        if path.count("/") >= 3:
            return "product"
        return "listing"
    if any(h in path for h in ["/product", "/produit", "/item/", "/p/"]):
        return "product"
    if any(h in path for h in ["/categorie-produit", "/category", "/collection", "/collections", "/catalog", "/shop", "/boutique"]):
        return "listing"
    if re.search(r"/page/\d+/?$", path) or "page=" in url or "paged=" in url:
        return "listing"
    return "other"


def should_skip(url: str) -> bool:
    low = url.lower()
    return any(h in low for h in ["/cart", "/panier", "/checkout", "/mon-compte", "/my-account", "wp-login", "add-to-cart", "logout", "mailto:", "tel:"])
