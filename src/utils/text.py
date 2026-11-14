from __future__ import annotations

import re
from bs4 import BeautifulSoup


def clean_text(text: str | None) -> str | None:
    if text is None:
        return None
    text = BeautifulSoup(text, "lxml").get_text(" ", strip=True) if "<" in text and ">" in text else text
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def parse_price(text: str | None) -> tuple[float | None, str | None]:
    if not text:
        return None, None
    t = text.replace("\xa0", " ").strip()
    # currency detection
    currency = None
    tu = t.upper()
    if "DA" in tu or "DZD" in tu:
        currency = "DZD"
    elif "€" in t or "EUR" in tu:
        currency = "EUR"
    elif "$" in t or "USD" in tu:
        currency = "USD"
    elif "£" in t or "GBP" in tu:
        currency = "GBP"
    # extract first plausible number (handle ranges by taking first/current)
    # normalize decimal separators: 1 200,00 or 1,200.00 or 5000
    nums = re.findall(r"[0-9][0-9\s.,]*[0-9]|[0-9]", t)
    if not nums:
        return None, currency
    n = nums[0].strip().replace(" ", "")
    # decide decimal separator
    if "," in n and "." in n:
        # assume last separator is decimal
        if n.rfind(",") > n.rfind("."):
            n = n.replace(".", "").replace(",", ".")
        else:
            n = n.replace(",", "")
    elif "," in n:
        # could be thousands or decimal; if ends with ,dd treat as decimal
        if re.search(r",\d{1,2}$", n):
            n = n.replace(".", "").replace(",", ".")
        else:
            n = n.replace(",", "")
    else:
        n = n.replace(",", "")
    try:
        val = float(n)
        return val, currency
    except Exception:
        return None, currency


def extract_add_to_cart_id(html: str | None, url: str | None = None) -> str | None:
    if not html:
        return None
    m = re.search(r"add-to-cart=(\d+)", html)
    if m:
        return m.group(1)
    m = re.search(r'data-product_id=["\'](\d+)["\']', html)
    if m:
        return m.group(1)
    m = re.search(r'"product_id"\s*:\s*"?(\d+)"?', html)
    if m:
        return m.group(1)
    return None
