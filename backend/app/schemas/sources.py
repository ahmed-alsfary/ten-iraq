from typing import Optional

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.common import ORMModel


class SourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    base_url: HttpUrl
    organization_id: Optional[str] = None
    source_type: str = "website"
    crawler_type: str = "generic_html"
    crawl_frequency_minutes: int = 60
    selectors: dict = Field(default_factory=dict)
    is_active: bool = True


class SourceOut(ORMModel):
    id: str
    name: str
    base_url: str
    organization_id: Optional[str]
    source_type: str
    crawler_type: str
    crawl_frequency_minutes: int
    selectors: dict
    is_active: bool
    last_error: Optional[str]
