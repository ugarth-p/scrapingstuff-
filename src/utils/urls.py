from __future__ import annotations

import hashlib
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode


TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "ref", "sessionid", "phpsessid",
}


def canonicalize_url(url: str, base: str | None = None) -> str | None:
    if not url:
        return None
    url = url.strip()
    if base:
        url = urljoin(base, url)
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None
    # normalize netloc
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    # remove fragments and tracking params
    q = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS]
    query = urlencode(q, doseq=True)
    return urlunparse((parsed.scheme, netloc, path, "", query, ""))


def same_domain(url: str, root: str) -> bool:
    try:
        return urlparse(url).netloc.lower() == urlparse(root).netloc.lower()
    except Exception:
        return False


def url_hash(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def get_domain(url: str) -> str:
    return urlparse(url).netloc.lower()
