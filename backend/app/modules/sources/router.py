from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.domain.models import Source
from app.schemas.sources import SourceCreate, SourceOut
from app.worker.tasks import crawl_source_task

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)) -> list[Source]:
    return list(db.scalars(select(Source).order_by(Source.created_at.desc())).all())


@router.post("", response_model=SourceOut, status_code=201)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)) -> Source:
    source = Source(
        name=payload.name,
        base_url=str(payload.base_url),
        organization_id=payload.organization_id,
        source_type=payload.source_type,
        crawler_type=payload.crawler_type,
        crawl_frequency_minutes=payload.crawl_frequency_minutes,
        selectors=payload.selectors,
        is_active=payload.is_active,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.post("/{source_id}/crawl", status_code=202)
def trigger_crawl(source_id: str, db: Session = Depends(get_db)) -> dict:
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if not source.is_active:
        raise HTTPException(status_code=400, detail="Source is inactive")

    settings = get_settings()
    # Without Docker/Redis: run crawl synchronously for local development.
    if settings.database_url.startswith("sqlite"):
        result = crawl_source_task.run(source_id)
        return {"source_id": source_id, "status": "completed", "result": result}

    task = crawl_source_task.delay(source_id)
    return {"task_id": task.id, "source_id": source_id, "status": "queued"}
