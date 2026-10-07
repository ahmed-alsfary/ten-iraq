"""Crawler for Ministry of Higher Education bids pages."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler, CrawlResult, DiscoveredItem

DEFAULT_LIST = "https://www.mohesr.gov.iq/ar/navbar/bids"


class MohesrCrawler(BaseCrawler):
    def __init__(self, timeout: float = 35.0):
        self.timeout = timeout

    def crawl(self, source_id: str, base_url: str, selectors: dict | None = None) -> CrawlResult:
        selectors = selectors or {}
        list_url = selectors.get("list_url") or DEFAULT_LIST
        max_pages = int(selectors.get("max_pages", 20))
        page_step = int(selectors.get("page_step", 10))
        result = CrawlResult(source_id=source_id, discovered=[])
        headers = {
            "User-Agent": "TenderIQ-Iraq/0.1 (+local research crawler)",
            "Accept": "text/html,*/*",
            "Accept-Language": "ar,en;q=0.9",
        }

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
                for page_idx in range(max_pages):
                    offset = page_idx * page_step
                    url = list_url if offset == 0 else f"{list_url.rstrip('/')}/{offset}"
                    response = client.get(url)
                    response.raise_for_status()
                    result.pages_scanned += 1
                    soup = BeautifulSoup(response.text, "html.parser")
                    rows = soup.select("tr.tender_row")
                    if not rows:
                        break
                    for tr in rows:
                        tender_id = tr.get("id")
                        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
                        # Columns: #, directorate, title, number, publish, close, extension, attachments
                        if len(cells) < 4:
                            continue
                        directorate = cells[1] if len(cells) > 1 else None
                        title = cells[2] if len(cells) > 2 else None
                        number = cells[3] if len(cells) > 3 else None
                        publish = cells[4] if len(cells) > 4 else None
                        close = cells[5] if len(cells) > 5 else None
                        if not title and len(cells) >= 3:
                            # Fallback if column shift
                            title = cells[1]
                            directorate = None
                            number = cells[2]
                            publish = cells[3] if len(cells) > 3 else None
                        if not tender_id or not title:
                            continue
                        detail = urljoin(list_url, f"/ar/tenders/tender_data/{tender_id}")
                        url_hash = hashlib.sha256(detail.encode("utf-8")).hexdigest()
                        result.discovered.append(
                            DiscoveredItem(
                                url=detail,
                                title=title,
                                published_at=publish or None,
                                metadata={
                                    "url_hash": url_hash,
                                    "external_id": str(tender_id),
                                    "tender_number": number or None,
                                    "organization_name": directorate or "وزارة التعليم العالي والبحث العلمي",
                                    "organization_type": "government",
                                    "publish_date": publish or None,
                                    "close_date": close or None,
                                    "status": "Published" if close not in (None, "", "—") else "Published",
                                    "status_raw": "Published",
                                    "source_label": "وزارة التعليم العالي",
                                },
                            )
                        )
        except Exception as exc:  # noqa: BLE001
            result.errors.append(str(exc))
        return result
