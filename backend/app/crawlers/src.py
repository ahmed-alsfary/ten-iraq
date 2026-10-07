"""Crawler for South Refineries Company (SRC) tenders."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler, CrawlResult, DiscoveredItem

PAGE = "https://src.gov.iq/muaqasat-page.aspx"
LOCAL = "https://src.gov.iq/muaqasat-local.aspx"
EXTERNAL = "https://src.gov.iq/muaqasat-external.aspx"


def _parse_src_date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return value


class SrcCrawler(BaseCrawler):
    def __init__(self, timeout: float = 35.0):
        self.timeout = timeout

    def crawl(self, source_id: str, base_url: str, selectors: dict | None = None) -> CrawlResult:
        selectors = selectors or {}
        pages = selectors.get("pages") or [PAGE, LOCAL, EXTERNAL]
        result = CrawlResult(source_id=source_id, discovered=[])
        headers = {
            "User-Agent": "TenderIQ-Iraq/0.1 (+local research crawler)",
            "Accept": "text/html,*/*",
            "Accept-Language": "ar,en;q=0.9",
        }
        seen: set[str] = set()

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
                for page_url in pages:
                    response = client.get(page_url)
                    response.raise_for_status()
                    result.pages_scanned += 1
                    soup = BeautifulSoup(response.text, "html.parser")

                    if "muaqasat-page" in page_url:
                        self._parse_cards(soup, page_url, result, seen)
                    else:
                        kind = "local" if "local" in page_url else "external"
                        self._parse_table(soup, page_url, kind, result, seen)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(str(exc))
        return result

    def _parse_cards(
        self,
        soup: BeautifulSoup,
        page_url: str,
        result: CrawlResult,
        seen: set[str],
    ) -> None:
        for card in soup.select(".card-txt"):
            title_el = card.select_one("h2")
            title = title_el.get_text(" ", strip=True) if title_el else ""
            if not title:
                continue

            publish_raw = None
            number = None
            for span in card.select("span"):
                text = span.get_text(" ", strip=True)
                if text.startswith("تاريخ النشر"):
                    publish_raw = text.split(":", 1)[-1].strip()
                elif re.fullmatch(r"\d+/\d{4}", text):
                    number = text

            close_raw = None
            h4 = card.select_one("h4")
            if h4:
                close_raw = h4.get_text(" ", strip=True).split(":", 1)[-1].strip()

            publish = _parse_src_date(publish_raw)
            close = _parse_src_date(close_raw)
            number = number or "unknown"

            file_url = None
            for parent in card.parents:
                if parent.name == "body":
                    break
                link = parent.select_one('a[href*="mainfile"], a[href*="MainFile"]')
                if link and link.get("href"):
                    file_url = urljoin(page_url, link["href"])
                    break

            external_id = f"src-page-{number}-{publish or 'na'}"
            if external_id in seen:
                continue
            seen.add(external_id)

            detail = file_url or f"https://src.gov.iq/tenders/page/{number}/{publish or 'na'}"
            url_hash = hashlib.sha256(detail.encode("utf-8")).hexdigest()
            files = []
            if file_url:
                files.append(
                    {
                        "fileId": hashlib.sha256(file_url.encode()).hexdigest()[:32],
                        "fileName": file_url.split("/")[-1],
                        "url": file_url,
                        "type": "AdDocument",
                    }
                )

            result.discovered.append(
                DiscoveredItem(
                    url=detail,
                    title=title,
                    published_at=publish,
                    metadata={
                        "url_hash": url_hash,
                        "external_id": external_id,
                        "tender_number": number,
                        "organization_name": "شركة مصافي الجنوب",
                        "organization_type": "company",
                        "parent_organization_name": "وزارة النفط",
                        "publish_date": publish,
                        "close_date": close,
                        "status": "Published",
                        "status_raw": "Published",
                        "source_label": "مصفى البصرة (SRC)",
                        "governorate": "البصرة",
                        "files": files,
                    },
                )
            )

    def _parse_table(
        self,
        soup: BeautifulSoup,
        page_url: str,
        kind: str,
        result: CrawlResult,
        seen: set[str],
    ) -> None:
        for tr in soup.select("table tr")[1:]:
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(cells) < 5:
                continue
            title = cells[1]
            number = cells[2]
            publish = _parse_src_date(cells[3])
            close = _parse_src_date(cells[4])
            if not title:
                continue
            # Skip if already captured from muaqasat-page cards
            if any(s.startswith(f"src-page-{number}-") for s in seen):
                continue
            key = f"src-{kind}-{number}-{publish or 'na'}"
            if key in seen:
                continue
            seen.add(key)
            detail = f"https://src.gov.iq/tenders/{kind}/{number}"
            url_hash = hashlib.sha256(f"{detail}-{publish}".encode("utf-8")).hexdigest()
            result.discovered.append(
                DiscoveredItem(
                    url=page_url,
                    title=title,
                    published_at=publish,
                    metadata={
                        "url_hash": url_hash,
                        "external_id": key,
                        "tender_number": number,
                        "organization_name": "شركة مصافي الجنوب",
                        "organization_type": "company",
                        "parent_organization_name": "وزارة النفط",
                        "publish_date": publish,
                        "close_date": close,
                        "status": "Published",
                        "status_raw": "Published",
                        "source_label": "مصفى البصرة (SRC)",
                        "governorate": "البصرة",
                    },
                )
            )
