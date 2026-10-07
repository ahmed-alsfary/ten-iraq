from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.crawlers.factory import get_crawler
from app.crawlers.itp_iq import map_itp_status, parse_dt
from app.domain.enums import TenderStatus
from app.domain.models import Document, Organization, Source, Tender
from app.utils.tender_display import effective_status
from app.worker.celery_app import celery_app


def _to_decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _ensure_organization(
    db,
    name: str | None,
    external_id: str | None = None,
    org_type: str | None = None,
) -> str | None:
    if not name:
        return None
    existing = db.scalar(select(Organization).where(Organization.name_ar == name))
    if existing:
        if org_type and not existing.organization_type:
            existing.organization_type = org_type
        return existing.id
    org = Organization(
        name_ar=name,
        name_en=None,
        organization_type=org_type or ("government" if external_id else None),
    )
    db.add(org)
    db.flush()
    return org.id


def _sync_documents(db, tender: Tender, files: list[dict]) -> int:
    synced = 0
    for file_info in files or []:
        file_id = str(file_info.get("fileId") or "")
        url = file_info.get("url") or ""
        filename = file_info.get("fileName") or "document.pdf"
        if not url and not file_id:
            continue

        existing = None
        if file_id:
            existing = db.scalar(
                select(Document).where(
                    Document.tender_id == tender.id,
                    Document.content_hash == file_id,
                )
            )
        if not existing and url:
            existing = db.scalar(
                select(Document).where(
                    Document.tender_id == tender.id,
                    Document.storage_key == url,
                )
            )

        file_type = file_info.get("type") or "application/octet-stream"
        if existing:
            existing.filename = filename
            existing.storage_key = url or existing.storage_key
            existing.mime_type = str(file_type)
            existing.content_hash = file_id or existing.content_hash
        else:
            db.add(
                Document(
                    tender_id=tender.id,
                    filename=filename,
                    mime_type=str(file_type),
                    content_hash=file_id or None,
                    storage_key=url or f"itp:{file_id}",
                    version=1,
                )
            )
            synced += 1
    return synced


@celery_app.task(name="crawl_source")
def crawl_source_task(source_id: str) -> dict:
    db = SessionLocal()
    try:
        source = db.get(Source, source_id)
        if not source:
            return {"ok": False, "error": "source_not_found"}

        crawler = get_crawler(source.crawler_type, source.base_url)
        result = crawler.crawl(source.id, source.base_url, source.selectors or {})

        created = 0
        updated = 0
        docs_synced = 0
        for item in result.discovered:
            meta = item.metadata or {}
            url_hash = meta.get("url_hash")
            external_id = meta.get("external_id")

            existing = None
            if url_hash:
                existing = db.scalar(
                    select(Tender)
                    .options(selectinload(Tender.documents))
                    .where(Tender.url_hash == url_hash)
                )
            if not existing and external_id:
                existing = db.scalar(
                    select(Tender)
                    .options(selectinload(Tender.documents))
                    .where(
                        Tender.reference_number == external_id,
                        Tender.source_id == source.id,
                    )
                )

            org_id = _ensure_organization(
                db,
                meta.get("organization_name"),
                meta.get("organization_external_id"),
                meta.get("organization_type"),
            )

            publish_dt = parse_dt(meta.get("publish_date") or item.published_at)
            close_dt = parse_dt(meta.get("close_date"))
            mapped_status = (
                map_itp_status(meta.get("status"))
                if meta.get("status")
                else TenderStatus.DISCOVERED.value
            )
            status = effective_status(mapped_status, close_dt)

            # Skip expired / closed tenders — keep the catalog active-only
            if status in {
                TenderStatus.CLOSED.value,
                TenderStatus.CANCELLED.value,
                TenderStatus.ARCHIVED.value,
            }:
                if existing:
                    for doc in list(existing.documents or []):
                        db.delete(doc)
                    db.delete(existing)
                continue

            source_label = (
                meta.get("source_label")
                or (source.selectors or {}).get("source_label")
                or source.name
            )
            source_slug = (source.selectors or {}).get("slug") or source.crawler_type or "src"
            fields = {
                "source_id": source.id,
                "organization_id": org_id or source.organization_id,
                "title": item.title or item.url,
                "description": meta.get("notes"),
                "tender_number": meta.get("tender_number"),
                "reference_number": external_id,
                "tender_type": meta.get("tender_type") or meta.get("subject"),
                "publication_date": publish_dt.date() if isinstance(publish_dt, datetime) else None,
                "submission_deadline": close_dt,
                "estimated_value": _to_decimal(meta.get("estimated_value")),
                "currency": meta.get("currency") or "IQD",
                "status": status,
                "location": meta.get("document_purchase_place"),
                "governorate": meta.get("governorate"),
                "original_url": item.url,
                "url_hash": url_hash,
                "extracted_fields": {
                    "source": source_label,
                    "source_name": source.name,
                    "source_base_url": source.base_url,
                    "subject": meta.get("subject"),
                    "status_raw": meta.get("status_raw") or meta.get("status"),
                    "duration": meta.get("duration"),
                    "document_price": meta.get("document_price"),
                    "document_price_currency": meta.get("document_price_currency"),
                    "document_purchase_place": meta.get("document_purchase_place"),
                    "organization_name": meta.get("organization_name"),
                    "organization_type": meta.get("organization_type"),
                    "parent_organization_name": meta.get("parent_organization_name"),
                    "tags": meta.get("tags"),
                    "files": meta.get("files"),
                    "owned_by": meta.get("owned_by"),
                    "republish_count": meta.get("republish_count"),
                    "extension_count": meta.get("extension_count"),
                    "raw": meta.get("raw"),
                },
                "slug": f"{source_slug}-{external_id}" if external_id else None,
            }

            if existing:
                for key, value in fields.items():
                    if value is not None:
                        setattr(existing, key, value)
                tender = existing
                updated += 1
            else:
                tender = Tender(**fields)
                db.add(tender)
                db.flush()
                created += 1

            docs_synced += _sync_documents(db, tender, meta.get("files") or [])

        source.last_crawled_at = datetime.now(UTC)
        if result.errors:
            source.last_error = "; ".join(result.errors)[:2000]
        else:
            source.last_success_at = datetime.now(UTC)
            source.last_error = None

        db.commit()
        return {
            "ok": True,
            "source_id": source_id,
            "pages_scanned": result.pages_scanned,
            "discovered": len(result.discovered),
            "created": created,
            "updated": updated,
            "documents_synced": docs_synced,
            "errors": result.errors,
        }
    finally:
        db.close()


def crawl_all_active_sources() -> dict:
    """Crawl every active source sequentially (safe for local SQLite)."""
    db = SessionLocal()
    try:
        sources = db.scalars(select(Source).where(Source.is_active.is_(True))).all()
        source_ids = [s.id for s in sources]
    finally:
        db.close()

    results = []
    for source_id in source_ids:
        try:
            results.append(crawl_source_task(source_id))
        except Exception as exc:  # noqa: BLE001
            results.append({"ok": False, "source_id": source_id, "error": str(exc)})

    return {
        "ok": True,
        "sources": len(source_ids),
        "created": sum(r.get("created", 0) for r in results if isinstance(r, dict)),
        "updated": sum(r.get("updated", 0) for r in results if isinstance(r, dict)),
        "results": results,
    }


@celery_app.task(name="crawl_all_sources")
def crawl_all_sources_task() -> dict:
    return crawl_all_active_sources()


@celery_app.task(name="process_document")
def process_document_task(document_id: str) -> dict:
    return {"ok": True, "document_id": document_id, "status": "queued_for_phase_2"}
