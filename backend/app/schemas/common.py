from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PageMeta(BaseModel):
    total_count: int
    page: int
    page_size: int


class Page(BaseModel, Generic[T]):
    items: list[T]
    total_count: int
    page: int
    page_size: int
