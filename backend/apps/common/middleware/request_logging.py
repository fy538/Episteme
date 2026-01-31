import time
import uuid
from typing import Callable, Optional

from django.http import HttpRequest, HttpResponse

from apps.common.correlation import set_correlation_id
from apps.common.logging_utils import build_log_extra, get_logger


logger = get_logger(__name__)


def _get_user_id(request: HttpRequest) -> Optional[int]:
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return user.id
    return None


class RequestLoggingMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start_time = time.monotonic()
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.correlation_id = correlation_id
        set_correlation_id(correlation_id)

        try:
            response = self.get_response(request)
        except Exception:
            duration_ms = (time.monotonic() - start_time) * 1000.0
            extra = build_log_extra(
                correlation_id=correlation_id,
                method=request.method,
                path=request.path,
                status_code=500,
                duration_ms=round(duration_ms, 2),
                user_id=_get_user_id(request),
            )
            logger.exception("request_failed", extra=extra)
            set_correlation_id(None)
            raise

        duration_ms = (time.monotonic() - start_time) * 1000.0
        extra = build_log_extra(
            correlation_id=correlation_id,
            method=request.method,
            path=request.path,
            status_code=getattr(response, "status_code", None),
            duration_ms=round(duration_ms, 2),
            user_id=_get_user_id(request),
        )
        logger.info("request_completed", extra=extra)
        response["X-Correlation-ID"] = correlation_id
        set_correlation_id(None)
        return response
