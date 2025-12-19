"""Logging helpers."""
import logging
from .context import get_request_id


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id() or "-"
        return True
