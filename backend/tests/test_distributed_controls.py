import json
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor

import app as app_module


class FakePipeline:
    def __init__(self, client):
        self.client = client
        self.key = None

    def incr(self, key):
        self.key = key
        return self

    def expire(self, _key, _seconds):
        return self

    def execute(self):
        self.client.counters[self.key] = self.client.counters.get(self.key, 0) + 1
        return [self.client.counters[self.key], True]


class FakeRedisClient:
    def __init__(self):
        self.values = {}
        self.counters = {}
        self.ping_calls = 0

    def ping(self):
        self.ping_calls += 1
        return True

    def get(self, key):
        return self.values.get(key)

    def setex(self, key, ttl, value):
        self.values[key] = value
        self.values[f"{key}:ttl"] = ttl

    def pipeline(self, transaction=True):
        assert transaction is True
        return FakePipeline(self)


def reset_distributed_state():
    app_module.REDIS_CLIENT = None
    app_module.REDIS_RETRY_AFTER = 0
    app_module.RATE_LIMIT_BUCKETS.clear()
    app_module.CACHE_METRICS.update({"hits": 0, "misses": 0, "writes": 0, "errors": 0})


def test_redis_client_connects_once_and_enters_retry_window_on_failure(monkeypatch):
    reset_distributed_state()
    client = FakeRedisClient()
    calls = []

    class FakeRedisFactory:
        @staticmethod
        def from_url(url, **options):
            calls.append((url, options))
            return client

    monkeypatch.setattr(app_module, "REDIS_URL", "redis://free-tier.example/0")
    monkeypatch.setattr(app_module, "Redis", FakeRedisFactory)

    assert app_module.get_redis_client() is client
    assert app_module.get_redis_client() is client
    assert len(calls) == 1
    assert client.ping_calls == 1
    assert calls[0][1]["decode_responses"] is True

    reset_distributed_state()

    class BrokenRedisFactory:
        @staticmethod
        def from_url(*_args, **_kwargs):
            raise ConnectionError("redis unavailable")

    monkeypatch.setattr(app_module, "Redis", BrokenRedisFactory)
    monkeypatch.setattr(app_module.time, "time", lambda: 1000.0)
    assert app_module.get_redis_client() is None
    assert app_module.REDIS_RETRY_AFTER == 1030.0
    assert app_module.CACHE_METRICS["errors"] == 1

    # The retry window prevents a connection storm.
    assert app_module.get_redis_client() is None
    assert app_module.CACHE_METRICS["errors"] == 1


def test_distributed_cache_round_trip_metrics_and_error_fallback(monkeypatch):
    reset_distributed_state()
    client = FakeRedisClient()
    monkeypatch.setattr(app_module, "get_redis_client", lambda: client)

    assert app_module.distributed_cache_get("catalog", "missing") is None
    assert app_module.distributed_cache_set(
        "catalog", "iaurt", {"name": "Iaurt românesc"}, 90
    ) is True
    assert app_module.distributed_cache_get("catalog", "iaurt") == {
        "name": "Iaurt românesc"
    }
    assert app_module.CACHE_METRICS == {
        "hits": 1,
        "misses": 1,
        "writes": 1,
        "errors": 0,
    }

    cache_key = app_module.distributed_cache_key("catalog", "iaurt")
    assert client.values[f"{cache_key}:ttl"] == 90
    assert json.loads(client.values[cache_key])["name"] == "Iaurt românesc"
    assert "iaurt" not in cache_key

    class BrokenClient:
        def get(self, _key):
            raise ConnectionError("read failed")

        def setex(self, *_args):
            raise ConnectionError("write failed")

    monkeypatch.setattr(app_module, "get_redis_client", lambda: BrokenClient())
    assert app_module.distributed_cache_get("catalog", "iaurt") is None
    assert app_module.distributed_cache_set("catalog", "iaurt", {}, 0) is False
    assert app_module.CACHE_METRICS["errors"] == 2


def test_redis_rate_limit_is_shared_across_requests_and_identities(app, monkeypatch):
    reset_distributed_state()
    shared_redis = FakeRedisClient()
    monkeypatch.setattr(app_module, "get_redis_client", lambda: shared_redis)
    monkeypatch.setattr(app_module.time, "time", lambda: 120.0)

    with app.test_request_context("/login", environ_base={"REMOTE_ADDR": "10.0.0.1"}):
        assert app_module.rate_limit("login", 2, 60) is True
        assert app_module.rate_limit("login", 2, 60) is True

    # A new request sees the same Redis bucket, as another worker would.
    with app.test_request_context("/login", environ_base={"REMOTE_ADDR": "10.0.0.1"}):
        assert app_module.rate_limit("login", 2, 60) is False

    with app.test_request_context("/login", environ_base={"REMOTE_ADDR": "10.0.0.2"}):
        assert app_module.rate_limit("login", 2, 60) is True


def test_rate_limit_falls_back_locally_when_redis_pipeline_fails(app, monkeypatch):
    reset_distributed_state()

    class BrokenPipelineClient:
        def pipeline(self, transaction=True):
            assert transaction is True
            raise ConnectionError("pipeline unavailable")

    monkeypatch.setattr(app_module, "get_redis_client", lambda: BrokenPipelineClient())
    monkeypatch.setattr(app_module.time, "time", lambda: 200.0)

    with app.test_request_context("/support", environ_base={"REMOTE_ADDR": "10.0.0.3"}):
        assert app_module.rate_limit("support", 1, 60) is True
        assert app_module.rate_limit("support", 1, 60) is False


def test_local_rate_limit_is_atomic_across_server_threads(app, monkeypatch):
    class SlowDeque(deque):
        def __len__(self):
            # Widen the check/append race window so this test protects the lock.
            time.sleep(0.005)
            return super().__len__()

    reset_distributed_state()
    monkeypatch.setattr(app_module, "get_redis_client", lambda: None)
    monkeypatch.setattr(app_module, "RATE_LIMIT_BUCKETS", defaultdict(SlowDeque))
    monkeypatch.setattr(app_module.time, "time", lambda: 300.0)

    def attempt():
        with app.test_request_context(
            "/support", environ_base={"REMOTE_ADDR": "10.0.0.4"}
        ):
            return app_module.rate_limit("support", 1, 60)

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(lambda _index: attempt(), range(24)))

    assert results.count(True) == 1
    assert results.count(False) == 23
