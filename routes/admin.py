from datetime import datetime, timedelta

from fastapi import APIRouter, Query
from sqlmodel import func, select

from config.database import SessionDep
from models.request_metrics import RequestMetrics

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/metrics/response-time")
def get_response_time_metrics(
    period_hours: int = Query(default=24, ge=1, le=168),
    session: SessionDep = None,
):
    """Статистика часу відповіді за період"""
    time_threshold = datetime.utcnow() - timedelta(hours=period_hours)

    # Загальна кількість запитів
    total_requests = session.exec(
        select(func.count(RequestMetrics.id)).where(
            RequestMetrics.timestamp >= time_threshold
        )
    ).one()

    # Середній час
    avg_response_time = (
        session.exec(
            select(func.avg(RequestMetrics.response_time_ms)).where(
                RequestMetrics.timestamp >= time_threshold
            )
        ).one()
        or 0
    )

    # Максимальний час
    max_response_time = (
        session.exec(
            select(func.max(RequestMetrics.response_time_ms)).where(
                RequestMetrics.timestamp >= time_threshold
            )
        ).one()
        or 0
    )

    # Мінімальний час
    min_response_time = (
        session.exec(
            select(func.min(RequestMetrics.response_time_ms)).where(
                RequestMetrics.timestamp >= time_threshold
            )
        ).one()
        or 0
    )

    # Кількість помилок
    error_count = session.exec(
        select(func.count(RequestMetrics.id)).where(
            RequestMetrics.timestamp >= time_threshold,
            RequestMetrics.status_code >= 400,
        )
    ).one()

    success_rate = (
        ((total_requests - error_count) / total_requests * 100)
        if total_requests > 0
        else 100
    )

    return {
        "period_hours": period_hours,
        "total_requests": total_requests,
        "average_response_time_ms": round(avg_response_time, 2),
        "min_response_time_ms": round(min_response_time, 2),
        "max_response_time_ms": round(max_response_time, 2),
        "error_count": error_count,
        "success_rate_percent": round(success_rate, 2),
    }


@admin_router.get("/metrics/response-time/timeline")
def get_response_time_timeline(
    period_hours: int = Query(default=24, ge=1, le=168),
    interval_minutes: int = Query(default=60, ge=5, le=1440),
    session: SessionDep = None,
):
    """Метрики в часовому розрізі"""
    time_threshold = datetime.utcnow() - timedelta(hours=period_hours)

    stmt = (
        select(RequestMetrics)
        .where(RequestMetrics.timestamp >= time_threshold)
        .order_by(RequestMetrics.timestamp)
    )
    metrics = session.exec(stmt).all()

    # Групуємо по інтервалах
    timeline_data = {}

    for metric in metrics:
        # Округляємо до інтервалу
        interval_time = metric.timestamp.replace(second=0, microsecond=0)
        minutes = (interval_time.minute // interval_minutes) * interval_minutes
        interval_time = interval_time.replace(minute=minutes)
        time_key = interval_time.isoformat()

        if time_key not in timeline_data:
            timeline_data[time_key] = {
                "timestamp": time_key,
                "request_count": 0,
                "total_response_time": 0,
                "min_response_time": float("inf"),
                "max_response_time": 0,
                "error_count": 0,
            }

        timeline_data[time_key]["request_count"] += 1
        timeline_data[time_key]["total_response_time"] += metric.response_time_ms
        timeline_data[time_key]["min_response_time"] = min(
            timeline_data[time_key]["min_response_time"], metric.response_time_ms
        )
        timeline_data[time_key]["max_response_time"] = max(
            timeline_data[time_key]["max_response_time"], metric.response_time_ms
        )

        if metric.status_code >= 400:
            timeline_data[time_key]["error_count"] += 1

    # Формуємо результат
    timeline = []
    for data in sorted(timeline_data.values(), key=lambda x: x["timestamp"]):
        avg_response_time = (
            data["total_response_time"] / data["request_count"]
            if data["request_count"] > 0
            else 0
        )

        timeline.append(
            {
                "timestamp": data["timestamp"],
                "request_count": data["request_count"],
                "avg_response_time_ms": round(avg_response_time, 2),
                "min_response_time_ms": round(data["min_response_time"], 2)
                if data["min_response_time"] != float("inf")
                else 0,
                "max_response_time_ms": round(data["max_response_time"], 2),
                "error_count": data["error_count"],
            }
        )

    return {
        "period_hours": period_hours,
        "interval_minutes": interval_minutes,
        "timeline": timeline,
    }


@admin_router.get("/metrics/response-time/endpoints")
def get_endpoints_response_time(
    period_hours: int = Query(default=24, ge=1, le=168),
    session: SessionDep = None,
):
    """Час відповіді по ендпоінтам"""
    time_threshold = datetime.utcnow() - timedelta(hours=period_hours)

    stmt = (
        select(
            RequestMetrics.endpoint,
            func.count(RequestMetrics.id).label("request_count"),
            func.avg(RequestMetrics.response_time_ms).label("avg_response_time"),
            func.min(RequestMetrics.response_time_ms).label("min_response_time"),
            func.max(RequestMetrics.response_time_ms).label("max_response_time"),
            func.count(RequestMetrics.id)
            .filter(RequestMetrics.status_code >= 400)
            .label("error_count"),
        )
        .where(RequestMetrics.timestamp >= time_threshold)
        .group_by(RequestMetrics.endpoint)
    )

    results = session.exec(stmt).all()

    endpoints_data = []
    for row in results:
        success_rate = (
            ((row.request_count - row.error_count) / row.request_count * 100)
            if row.request_count > 0
            else 100
        )

        endpoints_data.append(
            {
                "endpoint": row.endpoint,
                "request_count": row.request_count,
                "avg_response_time_ms": round(row.avg_response_time, 2),
                "min_response_time_ms": round(row.min_response_time, 2),
                "max_response_time_ms": round(row.max_response_time, 2),
                "error_count": row.error_count,
                "success_rate_percent": round(success_rate, 2),
            }
        )

    endpoints_data.sort(key=lambda x: x["request_count"], reverse=True)

    return {
        "period_hours": period_hours,
        "endpoints": endpoints_data,
    }
