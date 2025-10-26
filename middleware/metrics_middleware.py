import time
from datetime import datetime
from typing import Callable

from fastapi import Request, Response
from sqlmodel import Session
from starlette.middleware.base import BaseHTTPMiddleware

from config.database import engine
from models.request_metrics import RequestMetrics


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware для автоматичного збору метрик часу відповіді"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Ігноруємо service endpoints
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/health"]:
            return await call_next(request)

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
                    session.commit()
            except Exception as e:
                print(f"Error saving metrics: {e}")
