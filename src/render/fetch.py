from __future__ import annotations

import httpx


class Fetcher:
    def __init__(self, user_agent: str, timeout: int = 20):
        self.client = httpx.Client(
            headers={"User-Agent": user_agent, "Accept-Language": "en,fr;q=0.9,*;q=0.8"},
            timeout=timeout,
            follow_redirects=True,
        )

    def get(self, url: str) -> tuple[str | None, str | None, int | None]:
        try:
            r = self.client.get(url)
            ctype = r.headers.get("content-type", "")
            if r.status_code >= 400:
                return None, ctype, r.status_code
            # only html/text
            if "text" in ctype or "html" in ctype or "xml" in ctype or ctype == "":
                return r.text, ctype, r.status_code
            return None, ctype, r.status_code
        except Exception:
            return None, None, None

    def close(self):
        self.client.close()
