"""Crawler for Baghdad Governorate tenders listing."""

from __future__ import annotations

import hashlib
import re

import httpx
from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler, CrawlResult, DiscoveredItem

DEFAULT_LIST = "https://baghdad.gov.iq/tenders/index.1.html"


class BaghdadCrawler(BaseCrawler):
    def __init__(self, timeout: float = 35.0):
        self.timeout = timeout

    def crawl(self, source_id: str, base_url: str, selectors: dict | None = None) -> CrawlResult:
        selectors = selectors or {}
        max_pages = int(selectors.get("max_pages", 15))
        result = CrawlResult(source_id=source_id, discovered=[])
        headers = {
            "User-Agent": "TenderIQ-Iraq/0.1 (+local research crawler)",
            "Accept": "text/html,*/*",
            "Accept-Language": "ar,en;q=0.9",
        }

        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers=headers,
                verify=False,
            ) as client:
                for page in range(1, max_pages + 1):
                    url = f"https://baghdad.gov.iq/tenders/index.{page}.html"
                    response = client.get(url)
                    if response.status_code != 200:
                        break
                    result.pages_scanned += 1
                    soup = BeautifulSoup(response.text, "html.parser")
                    page_items = 0
                    seen: set[str] = set()
                    for a in soup.select('a[href*="/tenders/"]'):
                        href = a.get("href") or ""
                        m = re.search(r"/tenders/(\d+)\.html", href)
                        if not m:
                            continue
                        title = a.get_text(" ", strip=True)
                        if not title or len(title) < 4 or title.isdigit():
                            continue
                        tid = m.group(1)
                        if tid in seen:
                            continue
                        seen.add(tid)
                        detail = f"https://baghdad.gov.iq/tenders/{tid}.html"
                        url_hash = hashlib.sha256(detail.encode("utf-8")).hexdigest()
                        result.discovered.append(
                            DiscoveredItem(
                                url=detail,
                                title=title,
                                metadata={
                                    "url_hash": url_hash,
                                    "external_id": tid,
                                    "tender_number": None,
                                    "organization_name": "محافظة بغداد",
                                    "organization_type": "government",
                                    "status": "Published",
                                    "status_raw": "Published",
                                    "source_label": "محافظة بغداد",
                                    "governorate": "بغداد",
                                },
                            )
                        )
                        page_items += 1
                    if page_items == 0:
                        break
        except Exception as exc:  # noqa: BLE001
            result.errors.append(str(exc))
        return result
