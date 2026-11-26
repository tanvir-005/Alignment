import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

STATUS_MESSAGES = {
    400: "Validation failed.",
    401: "Authentication required.",
    403: "Permission denied.",
    404: "Resource not found.",
    405: "Method not allowed.",
    429: "Too many requests.",
}


def _first_message(data):
    """Pull a readable message out of DRF's nested error structures."""
    if isinstance(data, dict):
        for key, value in data.items():
            msg = _first_message(value)
            if msg:
                if key in ("detail", "non_field_errors", "error"):
                    return msg
                return f"{key.replace('_', ' ').capitalize()}: {msg}"
        return None
    if isinstance(data, (list, tuple)):
        for item in data:
            msg = _first_message(item)
            if msg:
                return msg
        return None
    return str(data) if data else None


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        logger.error(
            "Unhandled API exception",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return Response(
            {"error": "Internal server error.", "code": status.HTTP_500_INTERNAL_SERVER_ERROR},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    raw = response.data
    message = _first_message(raw) or STATUS_MESSAGES.get(
        response.status_code, "Request failed."
    )
    body = {"error": message, "code": response.status_code}
    if response.status_code == 400 and isinstance(raw, dict):
        body["errors"] = raw
    response.data = body
    return response
