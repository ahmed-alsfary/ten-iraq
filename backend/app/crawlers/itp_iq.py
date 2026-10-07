"""Crawler for Iraq Unified Tender Platform (https://itp.iq)."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

import httpx

from app.crawlers.base import BaseCrawler, CrawlResult, DiscoveredItem

API_BASE = "https://api.itp.iq/api"
PUBLIC_SITE = "https://itp.iq"


class ItpIqCrawler(BaseCrawler):
    """
    Uses the public listing API used by the ITP web app:
      POST https://api.itp.iq/api/bus/tenders/get
      body: {"page": 0, "count": 50}
    """

    def __init__(self, page_size: int = 50, max_pages: int = 100, timeout: float = 30.0):
        self.page_size = page_size
        self.max_pages = max_pages
        self.timeout = timeout

    def crawl(self, source_id: str, base_url: str, selectors: dict | None = None) -> CrawlResult:
        selectors = selectors or {}
        page_size = int(selectors.get("page_size", self.page_size))
        max_pages = int(selectors.get("max_pages", self.max_pages))
        status_filter = selectors.get("status")  # e.g. "Published"
        # Optional API-side type filter, e.g. "مناقصة"
        type_filter = selectors.get("type")

        result = CrawlResult(source_id=source_id, discovered=[])
        headers = {
            "User-Agent": "TenderIQ-Iraq/0.1 (+local research crawler)",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": PUBLIC_SITE,
            "Referer": f"{PUBLIC_SITE}/BUSINESS/tenders",
        }

        try:
            with httpx.Client(timeout=self.timeout, headers=headers) as client:
                for page in range(max_pages):
                    body: dict[str, Any] = {"page": page, "count": page_size}
                    if type_filter:
                        body["type"] = type_filter
                    response = client.post(
                        f"{API_BASE}/bus/tenders/get",
                        json=body,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    result.pages_scanned += 1

                    items = payload.get("data") or []
                    if not items:
                        break

                    for raw in items:
                        if status_filter and raw.get("status") != status_filter:
                            continue
                        item = self._map_item(raw)
                        result.discovered.append(item)

                    total_pages = int(payload.get("totalPages") or 0)
                    if total_pages and page + 1 >= total_pages:
                        break
        except Exception as exc:  # noqa: BLE001
            result.errors.append(str(exc))

        return result

    def fetch_details(self, tender_id: str) -> dict[str, Any] | None:
        headers = {
            "User-Agent": "TenderIQ-Iraq/0.1 (+local research crawler)",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": PUBLIC_SITE,
            "Referer": f"{PUBLIC_SITE}/BUSINESS/tenders",
        }
        with httpx.Client(timeout=self.timeout, headers=headers) as client:
            response = client.post(
                f"{API_BASE}/bus/tender/details/get",
                json={"tenderId": tender_id},
            )
            if response.status_code != 200:
                return None
            return response.json()

    def _map_item(self, raw: dict[str, Any]) -> DiscoveredItem:
        tender_id = str(raw.get("tenderId") or "")
        # Canonical public detail URL used by ITP web app
        url = f"{PUBLIC_SITE}/BUSINESS/tenders/{tender_id}"
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
        organization = raw.get("organization") or {}
        parent = organization.get("parentOrganization") or {}

        return DiscoveredItem(
            url=url,
            title=raw.get("title") or url,
            published_at=raw.get("publishDate"),
            metadata={
                "url_hash": url_hash,
                "external_id": tender_id,
                "tender_version_id": raw.get("tenderVersionId"),
                "tender_number": raw.get("number"),
                "tender_type": raw.get("type"),
                "subject": raw.get("subject"),
                "status": raw.get("status"),
                "status_raw": raw.get("status"),
                "publish_date": raw.get("publishDate"),
                "close_date": raw.get("closeDate"),
                "duration": raw.get("duration"),
                "estimated_value": raw.get("estimatedCost"),
                "currency": raw.get("currencyCode") or "IQD",
                "notes": raw.get("notes"),
                "organization_name": organization.get("name"),
                "organization_external_id": organization.get("id"),
                "organization_type": organization.get("typeName"),
                "parent_organization_name": parent.get("name") if isinstance(parent, dict) else None,
                "document_price": raw.get("documentPrice"),
                "document_price_currency": raw.get("documentPriceCurrencyCode") or "IQD",
                "document_purchase_place": raw.get("documentPurchasePlace"),
                "tags": raw.get("tags") or [],
                "files": raw.get("tenderFiles") or [],
                "owned_by": raw.get("ownedBy"),
                "republish_count": raw.get("republishCount") or 0,
                "extension_count": raw.get("extensionCount") or 0,
                "source_label": "المنصة الموحدة (ITP)",
                "raw": {
                    "tenderId": tender_id,
                    "number": raw.get("number"),
                    "status": raw.get("status"),
                    "type": raw.get("type"),
                    "subject": raw.get("subject"),
                },
            },
        )


def map_itp_status(status: str | None) -> str:
    mapping = {
        "Published": "published",
        "Available": "published",
        "Closed": "closed",
        "Canceled": "cancelled",
        "Cancelled": "cancelled",
        "Awarded": "closed",
        "Signed": "archived",
    }
    if not status:
        return "discovered"
    return mapping.get(status, "discovered")


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
