import os
import logging
from functools import wraps
from flask import request, g, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

RATE_LIMIT_DEFAULTS = {
    "default": "300 per minute",
    "auth": "5 per 15 minutes",
    "barcode": "45 per minute",
    "translate": "120 per minute",
    "ai_off": "30 per minute",
    "contact": "20 per minute",
    "scan": "10 per minute",
    "search": "60 per minute",
}


def get_user_identifier():
    if hasattr(g, "current_user") and g.current_user:
        return f"user:{g.current_user.id}"
    return get_remote_address()


def create_limiter(app):
    redis_url = os.environ.get("UPSTASH_REDIS_URL") or os.environ.get("REDIS_URL")
    redis_token = os.environ.get("UPSTASH_REDIS_TOKEN")

    storage_uri = "memory://"
    if redis_url:
        if redis_token and redis_url.startswith("redis://"):
            storage_uri = redis_url.replace("redis://", f"redis://:{redis_token}@")
        elif redis_token and redis_url.startswith("rediss://"):
            storage_uri = redis_url.replace("rediss://", f"rediss://:{redis_token}@")
        else:
            storage_uri = redis_url

    limiter = Limiter(
        key_func=get_user_identifier,
        app=app,
        storage_uri=storage_uri,
        default_limits=[RATE_LIMIT_DEFAULTS["default"]],
        headers_enabled=True,
        header_mapping={
            "limit": "X-RateLimit-Limit",
            "remaining": "X-RateLimit-Remaining",
            "reset": "Retry-After",
        },
        strategy="fixed-window",
        in_memory_fallback=True,
    )

    logger.info(f"Rate limiter initialized with storage: {storage_uri}")
    return limiter


_limiter = None


def get_limiter():
    global _limiter
    return _limiter


def init_rate_limiter(app):
    global _limiter
    _limiter = create_limiter(app)
    return _limiter


def rate_limit(limit_string):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            limiter = get_limiter()
            if limiter:
                return limiter.limit(limit_string)(f)(*args, **kwargs)
            return f(*args, **kwargs)
        return wrapped
    return decorator


def auth_rate_limit():
    return rate_limit(RATE_LIMIT_DEFAULTS["auth"])


def barcode_rate_limit():
    return rate_limit(RATE_LIMIT_DEFAULTS["barcode"])


def translate_rate_limit():
    return rate_limit(RATE_LIMIT_DEFAULTS["translate"])


def ai_off_rate_limit():
    return rate_limit(RATE_LIMIT_DEFAULTS["ai_off"])


def contact_rate_limit():
    return rate_limit(RATE_LIMIT_DEFAULTS["contact"])


def scan_rate_limit():
    return rate_limit(RATE_LIMIT_DEFAULTS["scan"])


def search_rate_limit():
    return rate_limit(RATE_LIMIT_DEFAULTS["search"])


def default_rate_limit():
    return rate_limit(RATE_LIMIT_DEFAULTS["default"])