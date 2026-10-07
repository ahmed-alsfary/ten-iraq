from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func, nulls_last, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.domain.models import Document, Organization, Source, Tender
from app.utils.tender_display import remaining_time, status_label

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["status_label"] = status_label
templates.env.globals["remaining_time"] = remaining_time


def _tender_time_order():
    """Newest tenders first by publication date, not scrape/source order."""
    return (
        nulls_last(desc(Tender.publication_date)),
        nulls_last(desc(Tender.submission_deadline)),
        desc(Tender.updated_at),
        desc(Tender.created_at),
    )


def _tender_view(tender: Tender) -> dict:
    fields = tender.extracted_fields or {}
    org_name = tender.organization.name_ar if tender.organization else fields.get("organization_name")
    source_name = None
    if tender.source:
        source_name = (tender.source.selectors or {}).get("source_label") or tender.source.name
    source_name = source_name or fields.get("source") or fields.get("source_name") or "—"
    return {
        "tender": tender,
        "organization_name": org_name or "—",
        "parent_organization_name": fields.get("parent_organization_name"),
        "source_name": source_name,
        "source_url": tender.source.base_url if tender.source else fields.get("source_base_url"),
        "status_label": status_label(tender.status),
        "status_raw": fields.get("status_raw") or tender.status,
        "remaining": remaining_time(tender.submission_deadline),
        "document_price": fields.get("document_price"),
        "document_price_currency": fields.get("document_price_currency") or tender.currency,
        "document_purchase_place": fields.get("document_purchase_place") or tender.location,
        "subject": fields.get("subject"),
        "documents": list(tender.documents or []),
    }


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    settings = get_settings()
    tender_count = db.scalar(select(func.count()).select_from(Tender)) or 0
    org_count = db.scalar(select(func.count()).select_from(Organization)) or 0
    source_count = db.scalar(select(func.count()).select_from(Source)) or 0
    doc_count = db.scalar(select(func.count()).select_from(Document)) or 0
    latest = db.scalars(
        select(Tender)
        .options(
            selectinload(Tender.organization),
            selectinload(Tender.documents),
            selectinload(Tender.source),
        )
        .order_by(*_tender_time_order())
        .limit(8)
    ).all()

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "app_name": settings.app_name,
            "stats": {
                "tenders": tender_count,
                "organizations": org_count,
                "sources": source_count,
                "documents": doc_count,
            },
            "latest_tenders": [_tender_view(t) for t in latest],
        },
    )


@router.get("/search", response_class=HTMLResponse)
def search_page(
    request: Request,
    q: str | None = None,
    governorate: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    settings = get_settings()
    page_size = 20
    stmt = select(Tender).options(
        selectinload(Tender.organization),
        selectinload(Tender.documents),
        selectinload(Tender.source),
    )
    count_stmt = select(func.count()).select_from(Tender)

    if q:
        pattern = f"%{q.strip()}%"
        filter_q = or_(Tender.title.ilike(pattern), Tender.description.ilike(pattern))
        stmt = stmt.where(filter_q)
        count_stmt = count_stmt.where(filter_q)
    if governorate:
        stmt = stmt.where(Tender.governorate == governorate)
        count_stmt = count_stmt.where(Tender.governorate == governorate)
    if status:
        stmt = stmt.where(Tender.status == status)
        count_stmt = count_stmt.where(Tender.status == status)

    total = db.scalar(count_stmt) or 0
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
    if page > total_pages:
        page = total_pages
    items = db.scalars(
        stmt.order_by(*_tender_time_order()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    # Compact page window around current page
    window = 2
    start_page = max(1, page - window)
    end_page = min(total_pages, page + window)
    page_numbers = list(range(start_page, end_page + 1))

    return templates.TemplateResponse(
        request,
        "search.html",
        {
            "app_name": settings.app_name,
            "q": q or "",
            "governorate": governorate or "",
            "status": status or "",
            "tenders": [_tender_view(t) for t in items],
            "total_count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "page_numbers": page_numbers,
            "showing_from": ((page - 1) * page_size + 1) if total else 0,
            "showing_to": min(page * page_size, total),
        },
    )


@router.get("/tenders/{tender_id}", response_class=HTMLResponse)
def tender_detail(request: Request, tender_id: str, db: Session = Depends(get_db)) -> HTMLResponse:
    settings = get_settings()
    tender = db.scalar(
        select(Tender)
        .options(
            selectinload(Tender.organization),
            selectinload(Tender.documents),
            selectinload(Tender.source),
        )
        .where(Tender.id == tender_id)
    )
    context = {
        "app_name": settings.app_name,
        "tender": tender,
    }
    if tender:
        context.update(_tender_view(tender))
    return templates.TemplateResponse(request, "tender_detail.html", context)
