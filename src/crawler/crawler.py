from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass

from ..render.fetch import Fetcher
from ..utils.robots import RobotsPolicy
from ..utils.urls import canonicalize_url, same_domain, get_domain
from ..discovery.links import extract_links, classify_url, should_skip
from ..extract.normalize import extract_product
from ..output.writer import OutputWriter


@dataclass
class CrawlResult:
    pages_fetched: int
    products_saved: int
    output_files: list[str]


def crawl_shop(start_url: str, config: dict) -> CrawlResult:
    start_url = canonicalize_url(start_url) or start_url
    user_agent = config.get("user_agent", "GenericShopScraper/1.0")
    timeout = int(config.get("timeout_seconds", 20))

    mp = config.get("max_pages", None)
    if mp is None or mp == "" or int(mp) <= 0:
        max_pages = float("inf")
    else:
        max_pages = int(mp)

    md = config.get("max_depth", None)
    if md is None or md == "" or int(md) <= 0:
        max_depth = float("inf")
    else:
        max_depth = int(md)

    same_domain_only = bool(config.get("same_domain_only", True))
    respect_robots = bool(config.get("respect_robots", True))
    default_delay = float(config.get("default_delay_seconds", 1.5))
    no_delay = bool(config.get("no_delay", False))
    out_dir = config.get("out_dir", "data")
    formats = config.get("formats") or ["csv", "xlsx"]

    fetcher = Fetcher(user_agent=user_agent, timeout=timeout)
    robots = RobotsPolicy(start_url, user_agent=user_agent, respect=respect_robots, default_delay=default_delay, client=fetcher.client)
    shop_name = get_domain(start_url)
    writer = OutputWriter(shop_name=shop_name, out_dir=out_dir, formats=formats)

    visited = set()
    enqueued = set([start_url])
    q = deque([(start_url, 0)])
    pages_fetched = 0

    try:
        while q and pages_fetched < max_pages:
            url, depth = q.popleft()
            if url in visited:
                continue
            if depth > max_depth:
                continue
            if same_domain_only and not same_domain(url, start_url):
                continue
            if should_skip(url):
                continue
            if not no_delay and not robots.allowed(url):
                visited.add(url)
                continue

            if not no_delay:
                delay = robots.delay()
                if pages_fetched > 0 and delay > 0:
                    time.sleep(delay)

            html, ctype, status = fetcher.get(url)
            visited.add(url)
            pages_fetched += 1
            if not html or status is None or status >= 400:
                continue

            # try extract product
            try:
                product = extract_product(html, url, base_shop_name=shop_name)
            except Exception:
                product = None
            if product:
                writer.upsert(product)

            # discover more links (even from product pages: related, categories)
            try:
                links = extract_links(html, url)
            except Exception:
                links = []

            # prioritize: product-like and listing-like
            scored = []
            for link in links:
                if link in visited or link in enqueued:
                    continue
                if same_domain_only and not same_domain(link, start_url):
                    continue
                if should_skip(link):
                    continue
                cls = classify_url(link)
                if cls == "skip":
                    continue
                prio = 1 if cls == "product" else (2 if cls == "listing" else 3)
                scored.append((prio, link, cls))
            scored.sort(key=lambda x: x[0])
            for _, link, cls in scored:
                if link not in enqueued:
                    enqueued.add(link)
                    nd = depth + 1
                    q.append((link, nd))

        output_files = writer.save()
        return CrawlResult(pages_fetched=pages_fetched, products_saved=writer.count(), output_files=output_files)
    finally:
        fetcher.close()
