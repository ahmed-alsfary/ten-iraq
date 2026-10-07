from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import Base, engine
from app.domain import models  # noqa: F401
from app.modules.identity.router import router as identity_router
from app.modules.sources.router import router as sources_router
from app.modules.tenders.router import router as tenders_router
from app.modules.web.router import router as web_router
from app.worker.scheduler import start_crawl_scheduler, stop_crawl_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_crawl_scheduler()
    try:
        yield
    finally:
        await stop_crawl_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    app.include_router(web_router)
    app.include_router(identity_router, prefix="/api/v1")
    app.include_router(tenders_router, prefix="/api/v1")
    app.include_router(sources_router, prefix="/api/v1")

    @app.get("/api/v1/health")
    def health() -> dict:
        return {"status": "ok", "app": settings.app_name, "env": settings.app_env}

    return app


app = create_app()
