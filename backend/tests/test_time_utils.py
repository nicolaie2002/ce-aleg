from datetime import datetime, timezone

from time_utils import utcnow


def test_utcnow_preserves_naive_utc_database_contract():
    value = utcnow()
    current_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    assert value.tzinfo is None
    assert abs((current_utc - value).total_seconds()) < 1
