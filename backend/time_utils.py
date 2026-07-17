from datetime import datetime, timezone


def utcnow():
    """Return naive UTC for compatibility with existing DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
