#!/usr/bin/env python3
"""Seed all known scrapable sources and run an initial crawl for each."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.domain import models  # noqa: F401
from app.domain.enums import CrawlerType, SourceType
from app.domain.models import Source
from app.worker.tasks import crawl_source_task

SOURCES = [
    {
        "name": "المنصة الإلكترونية الموحدة للإعلانات والمناقصات (ITP)",
        "base_url": "https://itp.iq",
        "crawler_type": CrawlerType.ITP_IQ.value,
        "source_type": SourceType.TENDER_PORTAL.value,
        "selectors": {
            "adapter": "itp_iq",
            "slug": "itp",
            "source_label": "المنصة الموحدة (ITP)",
            "page_size": 50,
            "max_pages": 100,
            "status": "Published",
        },
    },
    {
        "name": "وزارة التعليم العالي والبحث العلمي — المناقصات والمزايدات",
        "base_url": "https://www.mohesr.gov.iq",
        "crawler_type": CrawlerType.MOHESR.value,
        "source_type": SourceType.WEBSITE.value,
        "selectors": {
            "slug": "mohesr",
            "source_label": "وزارة التعليم العالي",
            "list_url": "https://www.mohesr.gov.iq/ar/navbar/bids",
            "max_pages": 10,
            "page_step": 10,
        },
    },
    {
        "name": "محافظة بغداد — الإعلانات والمناقصات",
        "base_url": "https://baghdad.gov.iq",
        "crawler_type": CrawlerType.BAGHDAD.value,
        "source_type": SourceType.WEBSITE.value,
        "selectors": {
            "slug": "baghdad",
            "source_label": "محافظة بغداد",
            "max_pages": 8,
        },
    },
    {
        "name": "شركة مصافي الجنوب (SRC)",
        "base_url": "https://src.gov.iq",
        "crawler_type": CrawlerType.SRC.value,
        "source_type": SourceType.WEBSITE.value,
        "selectors": {
            "slug": "src",
            "source_label": "مصفى البصرة (SRC)",
            "pages": [
                "https://src.gov.iq/muaqasat-page.aspx",
                "https://src.gov.iq/muaqasat-local.aspx",
                "https://src.gov.iq/muaqasat-external.aspx",
            ],
        },
    },
    {
        "name": "وزارة الكهرباء — المناقصات",
        "base_url": "https://moelc.gov.iq",
        "crawler_type": CrawlerType.MINISTRY_CMS.value,
        "source_type": SourceType.WEBSITE.value,
        "selectors": {
            "slug": "moelc",
            "source_label": "وزارة الكهرباء",
            "organization_name": "وزارة الكهرباء",
            "action": "active",
            "max_pages": 3,
        },
    },
    {
        "name": "شركة نفط البصرة — المناقصات",
        "base_url": "https://boc.oil.gov.iq",
        "crawler_type": CrawlerType.MINISTRY_CMS.value,
        "source_type": SourceType.WEBSITE.value,
        "selectors": {
            "slug": "boc",
            "source_label": "نفط البصرة (BOC)",
            "organization_name": "شركة نفط البصرة",
            "action": "",
            "max_pages": 10,
        },
    },
    {
        "name": "شركة نفط الوسط — المناقصات",
        "base_url": "https://mdoc.oil.gov.iq",
        "crawler_type": CrawlerType.MINISTRY_CMS.value,
        "source_type": SourceType.WEBSITE.value,
        "selectors": {
            "slug": "mdoc",
            "source_label": "نفط الوسط (MDOC)",
            "organization_name": "شركة نفط الوسط",
            "action": "active",
            "max_pages": 5,
        },
    },
    {
        "name": "ديوان الرقابة المالية الاتحادي — المناقصات",
        "base_url": "https://fbsa.gov.iq",
        "crawler_type": CrawlerType.MINISTRY_CMS.value,
        "source_type": SourceType.WEBSITE.value,
        "selectors": {
            "slug": "fbsa",
            "source_label": "ديوان الرقابة المالية",
            "organization_name": "ديوان الرقابة المالية الاتحادي",
            "action": "",
            "max_pages": 5,
        },
    },
    {
        "name": "وزارة النقل — المناقصات",
        "base_url": "https://www.mot.gov.iq",
        "crawler_type": CrawlerType.MINISTRY_CMS.value,
        "source_type": SourceType.WEBSITE.value,
        "selectors": {
            "slug": "mot",
            "source_label": "وزارة النقل",
            "organization_name": "وزارة النقل",
            "action": "",
            "max_pages": 50,
        },
    },
    {
        "name": "وزارة الصحة — المناقصات",
        "base_url": "https://moh.gov.iq",
        "crawler_type": CrawlerType.MINISTRY_CMS.value,
        "source_type": SourceType.WEBSITE.value,
        "selectors": {
            "slug": "moh",
            "source_label": "وزارة الصحة",
            "organization_name": "وزارة الصحة",
            "action": "",
            "max_pages": 3,
        },
    },
]


def upsert_source(db, spec: dict) -> Source:
    source = db.scalar(select(Source).where(Source.base_url == spec["base_url"]))
    if not source:
        source = Source(
            name=spec["name"],
            base_url=spec["base_url"],
            source_type=spec["source_type"],
            crawler_type=spec["crawler_type"],
            crawl_frequency_minutes=60,
            selectors=spec["selectors"],
            is_active=True,
        )
        db.add(source)
    else:
        source.name = spec["name"]
        source.crawler_type = spec["crawler_type"]
        source.source_type = spec["source_type"]
        source.selectors = spec["selectors"]
        source.is_active = True
    db.commit()
    db.refresh(source)
    return source


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    source_ids: list[str] = []
    try:
        for spec in SOURCES:
            source = upsert_source(db, spec)
            source_ids.append(source.id)
            print(f"Source ready: {source.selectors.get('source_label')} ({source.id})")
    finally:
        db.close()

    results = []
    for source_id in source_ids:
        result = crawl_source_task.run(source_id)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False))

    print("\nDONE", len(results), "sources crawled")


if __name__ == "__main__":
    main()
