"""Custom middleware for request metadata and immutability enforcement."""
import uuid
from django.http import JsonResponse
from django.conf import settings
from .context import set_request_id


class RequestIdMiddleware:
    """Ensures every request has a stable request id for tracing."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        header = getattr(settings, "REQUEST_ID_HEADER", "HTTP_X_REQUEST_ID")
        request_id = request.META.get(header) or str(uuid.uuid4())
        request.request_id = request_id
        set_request_id(request_id)
        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response


class ImmutableRequestMiddleware:
    """Rejects unsafe verbs targeting immutable resources."""

    IMMUTABLE_PREFIXES = ("/api/v1/archive", "/api/v1/audit")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in ("GET", "HEAD", "OPTIONS", "POST"):
            if any(request.path.startswith(prefix) for prefix in self.IMMUTABLE_PREFIXES):
                return JsonResponse({"detail": "immutable_resource"}, status=405)
        return self.get_response(request)
