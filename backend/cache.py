import os
import json
import logging
from functools import wraps
from flask import current_app, has_app_context

try:
    from flask_caching import Cache
except ImportError:
    Cache = None

try:
    from upstash_redis import Redis
except ImportError:
    Redis = None

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "cealeg"

CACHE_TTL_MAP = {
    "off:alt": 600,
    "off:prod": 3600,
    "search": 900,
    "prices": 1800,
    "ai:status": 30,
    "leaderboard": 60,
    "catalog:stats": 300,
    "rec:family": 3600,
    "rec:text": 3600,
}

DEFAULT_TTL = 300


def build_cache_key(cache_type, key):
    return f"{CACHE_KEY_PREFIX}:{cache_type}:{key}"


def get_ttl_for_type(cache_type):
    return CACHE_TTL_MAP.get(cache_type, DEFAULT_TTL)


class CacheManager:
    def __init__(self, app=None):
        self.cache = None
        self.redis_client = None
        self._enabled = False
        if app:
            self.init_app(app)

    def init_app(self, app):
        redis_url = os.environ.get("UPSTASH_REDIS_URL") or os.environ.get("REDIS_URL")
        redis_token = os.environ.get("UPSTASH_REDIS_TOKEN")

        if not redis_url or Redis is None or Cache is None:
            logger.warning("Redis/Flask-Caching not available, cache disabled")
            self._enabled = False
            return

        try:
            self.redis_client = Redis(url=redis_url, token=redis_token)
            self.redis_client.ping()

            app.config["CACHE_TYPE"] = "redis"
            app.config["CACHE_REDIS_URL"] = redis_url
            if redis_token:
                app.config["CACHE_REDIS_PASSWORD"] = redis_token
            app.config["CACHE_KEY_PREFIX"] = f"{CACHE_KEY_PREFIX}:"
            app.config["CACHE_DEFAULT_TIMEOUT"] = DEFAULT_TTL

            self.cache = Cache(app)
            self._enabled = True
            logger.info("Flask-Caching with Upstash Redis initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache: {e}. Falling back to no-cache mode.")
            self._enabled = False
            self.cache = None
            self.redis_client = None

    @property
    def enabled(self):
        return self._enabled and self.cache is not None

    def get(self, key):
        if not self.enabled:
            return None
        try:
            value = self.cache.get(key)
            if value is not None:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    def set(self, key, value, ttl=None):
        if not self.enabled:
            return False
        try:
            serialized = json.dumps(value)
            timeout = ttl if ttl is not None else DEFAULT_TTL
            return self.cache.set(key, serialized, timeout=timeout)
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key):
        if not self.enabled:
            return False
        try:
            return self.cache.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    def delete_pattern(self, pattern):
        if not self.enabled or not self.redis_client:
            return 0
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache delete_pattern error for pattern {pattern}: {e}")
            return 0

    def get_cached(self, cache_type, key, factory, ttl=None):
        cache_key = build_cache_key(cache_type, key)
        cached = self.get(cache_key)
        if cached is not None:
            return cached

        if not self.enabled:
            return factory()

        try:
            value = factory()
            self.set(cache_key, value, ttl)
            return value
        except Exception as e:
            logger.warning(f"Factory error for cache key {cache_key}: {e}")
            return factory()

    def invalidate_pattern(self, pattern):
        full_pattern = f"{CACHE_KEY_PREFIX}:{pattern}*"
        return self.delete_pattern(full_pattern)


cache = CacheManager()


def get_cached(cache_type, key, factory, ttl=None):
    return cache.get_cached(cache_type, key, factory, ttl)


def invalidate_pattern(pattern):
    return cache.invalidate_pattern(pattern)