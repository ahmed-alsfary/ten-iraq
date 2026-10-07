"""Crawler for Iraqi ministry sites using program-tender-fetch.php AJAX."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.crawlers.base import BaseCrawler, CrawlResult, DiscoveredItem


class MinistryCmsCrawler(BaseCrawler):
    """
    Shared adapter for Nodesbox/Royal CMS tender modules:
      POST {base}/home/program/program-tender-fetch.php
      detail: {base}/?tender={id}
    """

    def __init__(self, timeout: float = 35.0):
        self.timeout = timeout

    def crawl(self, source_id: str, base_url: str, selectors: dict | None = None) -> CrawlResult:
        selectors = selectors or {}
        base = (base_url or selectors.get("base_url") or "").rstrip("/")
        org_name = selectors.get("organization_name") or base
        source_label = selectors.get("source_label") or org_name
        action = selectors.get("action", "active")
        max_pages = int(selectors.get("max_pages", 5))
        fetch_files = bool(selectors.get("fetch_files", False))
        result = CrawlResult(source_id=source_id, discovered=[])
        if not base:
            result.errors.append("missing_base_url")
            return result

        headers = {
            "User-Agent": "TenderIQ-Iraq/0.1 (+local research crawler)",
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{base}/?tender",
        }

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
                for page in range(1, max_pages + 1):
                    response = client.post(
                        f"{base}/home/program/program-tender-fetch.php",
                        data={
                            "subPage": page,
                            "subSearch": "",
                            "homeLang": "ar",
                            "actionVariable": action,
                        },
                    )
                    response.raise_for_status()
                    result.pages_scanned += 1
                    html = response.text
                    cells = [
                        re.sub(r"<[^>]+>", "", cell, flags=re.S).replace("\n", " ").strip()
                        for cell in re.findall(r"<td[^>]*>(.*?)</td>", html, flags=re.S)
                    ]
                    ids = re.findall(r"\?tender=(\d+)", html)
                    body = cells[6:]
                    row_count = 0
                    id_idx = 0
                    for i in range(0, len(body), 6):
                        chunk = body[i : i + 6]
                        if len(chunk) < 5:
                            continue
                        title = chunk[1]
                        number = chunk[2]
                        publish = chunk[3] or None
                        close = chunk[4] or None
                        tid = ids[id_idx] if id_idx < len(ids) else None
                        id_idx += 1
                        if not title:
                            continue
                        detail = f"{base}/?tender={tid}" if tid else f"{base}/?tender"
                        external_id = tid or f"{number}-{publish}"
                        url_hash = hashlib.sha256(detail.encode("utf-8")).hexdigest()

                        files = []
                        if fetch_files and tid:
                            try:
                                detail_resp = client.get(detail, headers={**headers, "Accept": "text/html"})
                                if detail_resp.status_code == 200:
                                    soup = BeautifulSoup(detail_resp.text, "html.parser")
                                    for a in soup.select("a[href]"):
                                        href = a.get("href") or ""
                                        if any(
                                            href.lower().endswith(ext)
                                            for ext in (".pdf", ".doc", ".docx", ".zip", ".rar", ".xlsx")
                                        ):
                                            full = urljoin(base + "/", href.strip())
                                            files.append(
                                                {
                                                    "fileId": hashlib.sha256(full.encode()).hexdigest()[:32],
                                                    "fileName": a.get_text(strip=True) or full.split("/")[-1],
                                                    "url": full,
                                                    "type": "AdDocument",
                                                }
                                            )
                            except Exception:  # noqa: BLE001
                                pass

                        result.discovered.append(
                            DiscoveredItem(
                                url=detail,
                                title=title,
                                published_at=publish,
                                metadata={
                                    "url_hash": url_hash,
                                    "external_id": str(external_id),
                                    "tender_number": number,
                                    "organization_name": org_name,
                                    "organization_type": "government",
                                    "publish_date": publish,
                                    "close_date": close,
                                    "status": "Published",
                                    "status_raw": "Published",
                                    "source_label": source_label,
                                    "files": files[:5],
                                },
                            )
                        )
                        row_count += 1
                    if row_count == 0:
                        break
        except Exception as exc:  # noqa: BLE001
            result.errors.append(str(exc))
        return result
