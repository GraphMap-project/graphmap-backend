import json
import time
from datetime import datetime
from typing import Callable, Optional

from fastapi import Request, Response
from sqlmodel import Session, select
from starlette.middleware.base import BaseHTTPMiddleware

from config.database import engine
from models.endpoint_metrics import EndpointMetrics
from models.request_metrics import RequestMetrics


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware для автоматичного збору метрик часу відповіді"""

    # Методи, для яких зберігаємо метрики
    TRACKED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Ігноруємо service endpoints
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/health"]:
            return await call_next(request)

        # Ігноруємо OPTIONS, HEAD та інші методи
        if request.method not in self.TRACKED_METHODS:
            return await call_next(request)

        # Витягуємо algorithm з body (якщо є)
        algorithm = await self._extract_algorithm(request)

        # Вимірюємо час
        start_time = time.time()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            raise
        finally:
            response_time_ms = (time.time() - start_time) * 1000

            # Зберігаємо метрики
            try:
                with Session(engine) as session:
                    metrics = RequestMetrics(
                        endpoint=request.url.path,
                        method=request.method,
                        response_time_ms=response_time_ms,
                        status_code=status_code,
                        timestamp=datetime.utcnow(),
                    )
                    session.add(metrics)
                    # 2. Оновлюємо агреговані метрики
                    self._update_endpoint_metrics(
                        session=session,
                        endpoint=request.url.path,
                        method=request.method,
                        response_time_ms=response_time_ms,
                        status_code=status_code,
                        algorithm=algorithm,
                    )
                    session.commit()
            except Exception as e:
                print(f"Error saving metrics: {e}")

    async def _extract_algorithm(self, request: Request) -> Optional[str]:
        """Витягує algorithm з body запиту (якщо є)"""
        if request.method not in ["POST", "PUT", "PATCH"]:
            return None

        try:
            # Зберігаємо body для повторного читання
            body = await request.body()

            if not body:
                return None

            # Парсимо JSON
            body_json = json.loads(body)
            algorithm = body_json.get("algorithm")

            # Відновлюємо body для наступних обробників
            async def receive():
                return {"type": "http.request", "body": body}

            request._receive = receive

            return algorithm

        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            return None

    def _update_endpoint_metrics(
        self,
        session: Session,
        endpoint: str,
        method: str,
        response_time_ms: float,
        status_code: int,
        algorithm: Optional[str] = None,
    ):
        """Оновлює агреговані метрики для ендпоінту"""

        # Шукаємо існуючі метрики
        stmt = (
            select(EndpointMetrics)
            .where(EndpointMetrics.endpoint == endpoint)
            .where(EndpointMetrics.algorithm == algorithm)
        )
        metrics = session.exec(stmt).first()

        if metrics is None:
            # Створюємо нові метрики
            metrics = EndpointMetrics(
                endpoint=endpoint,
                method=method,
                total_requests=1,
                algorithm=algorithm,
                avg_response_time_ms=response_time_ms,
                min_response_time_ms=response_time_ms,
                max_response_time_ms=response_time_ms,
                last_request_time_ms=response_time_ms,
                error_count=1 if status_code >= 400 else 0,
                first_request_at=datetime.utcnow(),
                last_request_at=datetime.utcnow(),
            )
            metrics.success_rate_percent = 0.0 if status_code >= 400 else 100.0
        else:
            # Оновлюємо існуючі метрики
            total_requests = metrics.total_requests + 1

            # Оновлюємо середній час (інкрементальне обчислення)
            total_time = metrics.avg_response_time_ms * metrics.total_requests
            metrics.avg_response_time_ms = (
                total_time + response_time_ms
            ) / total_requests

            # Оновлюємо min/max
            metrics.min_response_time_ms = min(
                metrics.min_response_time_ms, response_time_ms
            )
            metrics.max_response_time_ms = max(
                metrics.max_response_time_ms, response_time_ms
            )

            metrics.last_request_time_ms = response_time_ms

            # Оновлюємо помилки
            if status_code >= 400:
                metrics.error_count += 1

            # Оновлюємо лічильники
            metrics.total_requests = total_requests
            metrics.success_rate_percent = (
                ((total_requests - metrics.error_count) / total_requests * 100)
                if total_requests > 0
                else 100.0
            )

            metrics.last_request_at = datetime.utcnow()

        session.add(metrics)
