"""Thread-safe request context utilities."""
from contextvars import ContextVar

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(value: str | None) -> None:
    request_id_ctx.set(value)


def get_request_id() -> str | None:
    return request_id_ctx.get()
