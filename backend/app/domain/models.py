from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums import CrawlerType, SourceType, TenderStatus, UserRole


def _uuid() -> str:
    return str(uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.CUSTOMER.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    tenant: Mapped[Optional["Tenant"]] = relationship()


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role", "permission_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    permission_id: Mapped[str] = mapped_column(String(36), ForeignKey("permissions.id"))


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(255))
    organization_type: Mapped[Optional[str]] = mapped_column(String(100))
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("organizations.id"))
    governorate: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("organizations.id")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default=SourceType.WEBSITE.value)
    crawler_type: Mapped[str] = mapped_column(String(50), default=CrawlerType.GENERIC_HTML.value)
    crawl_frequency_minutes: Mapped[int] = mapped_column(default=60)
    selectors: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[Optional[str]] = mapped_column(Text)

    organization: Mapped[Optional["Organization"]] = relationship()


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("categories.id"))
    name_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Tender(Base, TimestampMixin):
    __tablename__ = "tenders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("organizations.id")
    )
    source_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("sources.id"))
    tender_number: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    reference_number: Mapped[Optional[str]] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    tender_type: Mapped[Optional[str]] = mapped_column(String(100))
    publication_date: Mapped[Optional[date]] = mapped_column(Date)
    submission_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    opening_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    estimated_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(10), default="IQD")
    status: Mapped[str] = mapped_column(String(50), default=TenderStatus.DISCOVERED.value, index=True)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    governorate: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    original_url: Mapped[Optional[str]] = mapped_column(String(1000))
    url_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text)
    extracted_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    slug: Mapped[Optional[str]] = mapped_column(String(255), unique=True)

    organization: Mapped[Optional["Organization"]] = relationship()
    source: Mapped[Optional["Source"]] = relationship()
    documents: Mapped[list["Document"]] = relationship(back_populates="tender")


class TenderCategory(Base):
    __tablename__ = "tender_categories"
    __table_args__ = (UniqueConstraint("tender_id", "category_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenders.id"))
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("categories.id"))


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenders.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    size_bytes: Mapped[Optional[int]] = mapped_column()
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[int] = mapped_column(default=1)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)

    tender: Mapped["Tender"] = relationship(back_populates="documents")


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    categories: Mapped[list] = mapped_column(JSON, default=list)
    products: Mapped[list] = mapped_column(JSON, default=list)
    services: Mapped[list] = mapped_column(JSON, default=list)
    governorates: Mapped[list] = mapped_column(JSON, default=list)
    min_tender_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    max_tender_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(100))
    old_value: Mapped[Optional[dict]] = mapped_column(JSON)
    new_value: Mapped[Optional[dict]] = mapped_column(JSON)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
