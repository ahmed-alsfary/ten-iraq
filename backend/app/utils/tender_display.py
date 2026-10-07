from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

STATUS_AR = {
    "draft": "مسودة",
    "discovered": "مكتشفة",
    "processing": "قيد المعالجة",
    "published": "متاحة",
    "closing_soon": "قاربت على الإغلاق",
    "closed": "مغلقة",
    "cancelled": "ملغاة",
    "archived": "مؤرشفة",
    "Published": "متاحة",
    "Available": "متاحة",
    "Closed": "مغلقة",
    "Canceled": "ملغاة",
    "Cancelled": "ملغاة",
    "Awarded": "محالة",
    "Signed": "تم التوقيع",
}


def status_label(status: str | None) -> str:
    if not status:
        return "—"
    return STATUS_AR.get(status, status)


def remaining_time(deadline: datetime | None, now: datetime | None = None) -> dict[str, Any]:
    """Return human-readable remaining time until submission deadline."""
    if not deadline:
        return {
            "label": "غير محدد",
            "is_expired": False,
            "total_seconds": None,
            "days": None,
            "hours": None,
            "minutes": None,
        }

    current = now or datetime.now(UTC)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)

    delta = deadline - current
    total_seconds = int(delta.total_seconds())
    if total_seconds <= 0:
        return {
            "label": "منتهية",
            "is_expired": True,
            "total_seconds": total_seconds,
            "days": 0,
            "hours": 0,
            "minutes": 0,
        }

    days = delta.days
    hours = (delta.seconds // 3600)
    minutes = (delta.seconds % 3600) // 60

    if days > 0:
        label = f"{days} يوم و {hours} ساعة"
    elif hours > 0:
        label = f"{hours} ساعة و {minutes} دقيقة"
    else:
        label = f"{minutes} دقيقة"

    return {
        "label": label,
        "is_expired": False,
        "total_seconds": total_seconds,
        "days": days,
        "hours": hours,
        "minutes": minutes,
    }


def effective_status(status: str | None, deadline: datetime | None) -> str:
    """Downgrade published tenders to closing_soon when deadline is near."""
    base = status or "discovered"
    if base not in {"published", "Published", "Available"}:
        return "published" if base in {"Published", "Available"} else base

    rem = remaining_time(deadline)
    if rem["is_expired"]:
        return "closed"
    if rem["total_seconds"] is not None and rem["total_seconds"] <= int(timedelta(days=3).total_seconds()):
        return "closing_soon"
    return "published"
