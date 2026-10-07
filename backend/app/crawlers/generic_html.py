import hashlib
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler, CrawlResult, DiscoveredItem


class GenericHtmlCrawler(BaseCrawler):
    """Selector-driven HTML listing crawler for government tender pages."""

    def crawl(self, source_id: str, base_url: str, selectors: dict | None = None) -> CrawlResult:
        selectors = selectors or {}
        item_selector = selectors.get("item", "a")
        title_selector = selectors.get("title")
        link_selector = selectors.get("link", "a")
        result = CrawlResult(source_id=source_id, discovered=[])

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(base_url)
                response.raise_for_status()
                result.pages_scanned = 1
                soup = BeautifulSoup(response.text, "lxml")

                for node in soup.select(item_selector):
                    link_node = node.select_one(link_selector) if link_selector != "a" else node
                    if link_node is None:
                        continue
                    href = link_node.get("href")
                    if not href:
                        continue

                    url = urljoin(base_url, href)
                    title = None
                    if title_selector:
                        title_node = node.select_one(title_selector)
                        title = title_node.get_text(strip=True) if title_node else None
                    if not title:
                        title = link_node.get_text(strip=True) or url

                    result.discovered.append(
                        DiscoveredItem(
                            url=url,
                            title=title,
                            metadata={
                                "url_hash": hashlib.sha256(url.encode("utf-8")).hexdigest(),
                            },
                        )
                    )
        except Exception as exc:  # noqa: BLE001 - capture crawl errors for admin dashboard
            result.errors.append(str(exc))

        return result
