import logging
from typing import Any, Dict, Tuple

from celery.signals import task_prerun, task_postrun, task_failure, task_retry


logger = logging.getLogger(__name__)


def _sanitize_payload(args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> Dict[str, Any]:
    def _truncate(value: Any) -> Any:
        text = repr(value)
        if len(text) > 500:
            return text[:500] + "...(truncated)"
        return value

    return {
        "args": [_truncate(arg) for arg in args],
        "kwargs": {key: _truncate(val) for key, val in kwargs.items()},
    }


@task_prerun.connect
def log_task_prerun(sender=None, task_id=None, task=None, args=None, kwargs=None, **_):
    payload = _sanitize_payload(args or (), kwargs or {})
    logger.info(
        "celery_task_started",
        extra={
            "task_id": task_id,
            "task_name": getattr(sender, "name", None),
            **payload,
        },
    )


@task_postrun.connect
def log_task_postrun(sender=None, task_id=None, task=None, retval=None, state=None, **_):
    logger.info(
        "celery_task_completed",
        extra={
            "task_id": task_id,
            "task_name": getattr(sender, "name", None),
            "state": state,
        },
    )


@task_failure.connect
def log_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, **_):
    payload = _sanitize_payload(args or (), kwargs or {})
    logger.exception(
        "celery_task_failed",
        extra={
            "task_id": task_id,
            "task_name": getattr(sender, "name", None),
            "exception": repr(exception),
            **payload,
        },
    )


@task_retry.connect
def log_task_retry(sender=None, request=None, reason=None, **_):
    logger.warning(
        "celery_task_retry",
        extra={
            "task_id": getattr(request, "id", None),
            "task_name": getattr(sender, "name", None),
            "reason": repr(reason),
        },
    )
