from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, nulls_last, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.domain.models import Tender
from app.schemas.common import Page
from app.schemas.tenders import DocumentOut, TenderCreate, TenderOut
from app.utils.tender_display import remaining_time, status_label

router = APIRouter(prefix="/tenders", tags=["tenders"])


def _tender_time_order():
    return (
        nulls_last(desc(Tender.publication_date)),
        nulls_last(desc(Tender.submission_deadline)),
        desc(Tender.updated_at),
        desc(Tender.created_at),
    )


def serialize_tender(tender: Tender) -> TenderOut:
    fields = tender.extracted_fields or {}
    org_name = None
    if tender.organization:
        org_name = tender.organization.name_ar
    elif fields.get("organization_name"):
        org_name = fields.get("organization_name")

    return TenderOut(
        id=tender.id,
        title=tender.title,
        description=tender.description,
        tender_number=tender.tender_number,
        organization_id=tender.organization_id,
        organization_name=org_name,
        source_id=tender.source_id,
        publication_date=tender.publication_date,
        submission_deadline=tender.submission_deadline,
        created_at=tender.created_at,
        estimated_value=tender.estimated_value,
        currency=tender.currency,
        status=tender.status,
        status_label=status_label(tender.status),
        remaining_time=remaining_time(tender.submission_deadline),
        location=tender.location,
        governorate=tender.governorate,
        original_url=tender.original_url,
        ai_summary=tender.ai_summary,
        slug=tender.slug,
        tender_type=tender.tender_type,
        document_price=str(fields.get("document_price")) if fields.get("document_price") else None,
        documents=[DocumentOut.model_validate(doc) for doc in (tender.documents or [])],
        extracted_fields=fields,
    )


@router.get("", response_model=Page[TenderOut])
def list_tenders(
    q: str | None = None,
    organization_id: str | None = None,
    governorate: str | None = None,
    status: str | None = None,
    min_value: float | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Page[TenderOut]:
    stmt = select(Tender).options(
        selectinload(Tender.organization),
        selectinload(Tender.documents),
    )
    count_stmt = select(func.count()).select_from(Tender)

    if q:
        pattern = f"%{q.strip()}%"
        filter_q = or_(Tender.title.ilike(pattern), Tender.description.ilike(pattern))
        stmt = stmt.where(filter_q)
        count_stmt = count_stmt.where(filter_q)
    if organization_id:
        stmt = stmt.where(Tender.organization_id == organization_id)
        count_stmt = count_stmt.where(Tender.organization_id == organization_id)
    if governorate:
        stmt = stmt.where(Tender.governorate == governorate)
        count_stmt = count_stmt.where(Tender.governorate == governorate)
    if status:
        stmt = stmt.where(Tender.status == status)
        count_stmt = count_stmt.where(Tender.status == status)
    if min_value is not None:
        stmt = stmt.where(Tender.estimated_value >= min_value)
        count_stmt = count_stmt.where(Tender.estimated_value >= min_value)

    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        stmt.order_by(*_tender_time_order()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    return Page(
        items=[serialize_tender(item) for item in items],
        total_count=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{tender_id}", response_model=TenderOut)
def get_tender(tender_id: str, db: Session = Depends(get_db)) -> TenderOut:
    tender = db.scalar(
        select(Tender)
        .options(selectinload(Tender.organization), selectinload(Tender.documents))
        .where(Tender.id == tender_id)
    )
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return serialize_tender(tender)


@router.post("", response_model=TenderOut, status_code=201)
def create_tender(payload: TenderCreate, db: Session = Depends(get_db)) -> TenderOut:
    tender = Tender(**payload.model_dump())
    db.add(tender)
    db.commit()
    db.refresh(tender)
    return serialize_tender(tender)
