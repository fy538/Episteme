"""
Custom exceptions for Episteme
"""
from rest_framework.exceptions import APIException


class EventAppendError(APIException):
    """Raised when event append fails"""
    status_code = 500
    default_detail = 'Failed to append event to event store'
    default_code = 'event_append_error'


class InvalidEventPayload(APIException):
    """Raised when event payload is invalid"""
    status_code = 400
    default_detail = 'Invalid event payload'
    default_code = 'invalid_event_payload'


class CaseNotFound(APIException):
    """Raised when case is not found"""
    status_code = 404
    default_detail = 'Case not found'
    default_code = 'case_not_found'
