from __future__ import annotations

import argparse
import json
from pathlib import Path

from .crawler.crawler import crawl_shop


def load_config(path: str | None) -> dict:
    base = Path(__file__).resolve().parents[1]
    cfg_path = Path(path) if path else base / "config" / "default.json"
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def main():
    parser = argparse.ArgumentParser(description="Generic shop web scraper")
    parser.add_argument("--url", required=True, help="Shop URL to crawl")
    parser.add_argument("--out-dir", default="data", help="Output directory (default: data)")
    parser.add_argument("--format", choices=["csv", "xlsx", "both"], default="both", help="Output format (default: both)")
    parser.add_argument("--max-pages", type=int, default=0, help="Max pages to fetch (0 or omit for unlimited)")
    parser.add_argument("--max-depth", type=int, default=0, help="Max crawl depth (0 or omit for unlimited)")
    parser.add_argument("--no-delay", action="store_true", help="Disable crawl delay and ignore robots Crawl-delay")
    parser.add_argument("--config", help="Path to config JSON")
    parser.add_argument("--browser-fallback", action="store_true", help="Enable browser fallback (placeholder)")
    args = parser.parse_args()

    config = load_config(args.config)
    config["start_url"] = args.url
    config["out_dir"] = args.out_dir
    config["formats"] = ["csv", "xlsx"] if args.format == "both" else [args.format]
    config["max_pages"] = args.max_pages if args.max_pages and args.max_pages > 0 else 0
    config["max_depth"] = args.max_depth if args.max_depth and args.max_depth > 0 else 0
    if args.no_delay:
        config["no_delay"] = True
        config["default_delay_seconds"] = 0
    if args.browser_fallback:
        config["browser_fallback"] = True

    print(f"Starting crawl: {args.url}")
    result = crawl_shop(args.url, config)
    print(f"Done. Pages fetched: {result.pages_fetched}, products saved: {result.products_saved}")
    for p in result.output_files:
        print(f"Output: {p}")


if __name__ == "__main__":
    main()
