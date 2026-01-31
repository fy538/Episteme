import logging
from typing import Any, Dict, Optional

from apps.common.correlation import get_correlation_id


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or __name__)


def build_log_extra(
    correlation_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    extra: Dict[str, Any] = {}
    resolved_correlation_id = correlation_id or get_correlation_id()
    if resolved_correlation_id:
        extra["correlation_id"] = resolved_correlation_id
    if kwargs:
        extra.update(kwargs)
    return extra


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = get_correlation_id()
        return True
