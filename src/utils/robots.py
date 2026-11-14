from __future__ import annotations

import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx


class RobotsPolicy:
    def __init__(self, base_url: str, user_agent: str, respect: bool = True, default_delay: float = 1.0, client: httpx.Client | None = None):
        self.base_url = base_url
        self.user_agent = user_agent
        self.respect = respect
        self.default_delay = default_delay
        self.rp = RobotFileParser()
        self.crawl_delay = default_delay
        self._loaded = False
        self._client = client

    def load(self):
        if self._loaded or not self.respect:
            self._loaded = True
            return
        robots_url = urljoin(self.base_url, "/robots.txt")
        try:
            if self._client:
                r = self._client.get(robots_url, timeout=10)
                if r.status_code == 200:
                    self.rp.parse(r.text.splitlines())
                else:
                    self.rp.parse([])
            else:
                self.rp.set_url(robots_url)
                self.rp.read()
            delay = self.rp.crawl_delay(self.user_agent) or self.rp.crawl_delay("*")
            if delay:
                self.crawl_delay = max(float(delay), self.default_delay)
            else:
                self.crawl_delay = self.default_delay
        except Exception:
            self.rp.parse([])
            self.crawl_delay = self.default_delay
        self._loaded = True

    def allowed(self, url: str) -> bool:
        self.load()
        if not self.respect:
            return True
        try:
            return self.rp.can_fetch(self.user_agent, url)
        except Exception:
            return True

    def delay(self) -> float:
        self.load()
        return self.crawl_delay if self.respect else self.default_delay
