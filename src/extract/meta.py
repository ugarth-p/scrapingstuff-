from __future__ import annotations

from bs4 import BeautifulSoup


def extract_meta(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    def meta(prop=None, name=None):
        if prop:
            tag = soup.find("meta", attrs={"property": prop})
            if tag and tag.get("content"):
                return tag["content"].strip()
        if name:
            tag = soup.find("meta", attrs={"name": name})
            if tag and tag.get("content"):
                return tag["content"].strip()
        return None

    title = meta(prop="og:title") or meta(name="twitter:title")
    if not title and soup.title:
        title = soup.title.get_text(strip=True)
    desc = meta(prop="og:description") or meta(name="description") or meta(name="twitter:description")
    price = meta(prop="product:price:amount") or meta(prop="og:price:amount")
    currency = meta(prop="product:price:currency") or meta(prop="og:price:currency")
    site = meta(prop="og:site_name")
    image = meta(prop="og:image")
    return {
        "name": title,
        "description": desc,
        "price": price,
        "currency": currency,
        "shop_name": site,
        "image": image,
    }
