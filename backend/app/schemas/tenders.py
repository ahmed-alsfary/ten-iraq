from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class TenderCreate(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    description: Optional[str] = None
    tender_number: Optional[str] = None
    organization_id: Optional[str] = None
    source_id: Optional[str] = None
    publication_date: Optional[date] = None
    submission_deadline: Optional[datetime] = None
    estimated_value: Optional[Decimal] = None
    currency: str = "IQD"
    location: Optional[str] = None
    governorate: Optional[str] = None
    original_url: Optional[str] = None
    status: str = "discovered"


class DocumentOut(ORMModel):
    id: str
    filename: str
    mime_type: Optional[str] = None
    storage_key: str
    content_hash: Optional[str] = None
    version: int = 1


class TenderOut(ORMModel):
    id: str
    title: str
    description: Optional[str]
    tender_number: Optional[str]
    organization_id: Optional[str]
    organization_name: Optional[str] = None
    source_id: Optional[str]
    publication_date: Optional[date]
    submission_deadline: Optional[datetime]
    estimated_value: Optional[Decimal]
    currency: str
    status: str
    status_label: Optional[str] = None
    remaining_time: Optional[dict[str, Any]] = None
    location: Optional[str]
    governorate: Optional[str]
    original_url: Optional[str]
    ai_summary: Optional[str]
    slug: Optional[str]
    tender_type: Optional[str] = None
    document_price: Optional[str] = None
    documents: list[DocumentOut] = Field(default_factory=list)
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
