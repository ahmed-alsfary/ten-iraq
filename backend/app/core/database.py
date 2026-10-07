from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

# backend/ directory (this file is backend/app/core/database.py)
BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_ROOT / "data"
DEFAULT_SQLITE_PATH = DATA_DIR / "tenderiq.db"


class Base(DeclarativeBase):
    pass


def _resolve_database_url(raw_url: str) -> str:
    """Pin SQLite to an absolute file so crawls always persist in one place."""
    url = (raw_url or "").strip()
    if not url.startswith("sqlite"):
        return url

    # sqlite:////abs/path or sqlite:///./relative or sqlite:///relative
    prefix = "sqlite:///"
    if url.startswith("sqlite:////"):
        return url  # already absolute (4 slashes)

    relative = url[len(prefix) :] if url.startswith(prefix) else url.replace("sqlite://", "")
    relative = relative.lstrip("./")
    if relative in {"", ":memory:"}:
        path = DEFAULT_SQLITE_PATH
    else:
        candidate = Path(relative)
        path = candidate if candidate.is_absolute() else (DATA_DIR / candidate.name)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # One-time migrate from older cwd-relative locations
    legacy_candidates = [
        BACKEND_ROOT / "tenderiq.db",
        BACKEND_ROOT / relative if relative else None,
        Path.cwd() / "tenderiq.db",
        Path.cwd() / "backend" / "tenderiq.db",
    ]
    if not path.exists():
        for legacy in legacy_candidates:
            if legacy and legacy.exists() and legacy.resolve() != path.resolve():
                path.write_bytes(legacy.read_bytes())
                break

    return f"sqlite:///{path}"


settings = get_settings()
DATABASE_URL = _resolve_database_url(settings.database_url)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
