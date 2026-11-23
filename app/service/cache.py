# -*- coding: utf-8 -*-
"""In-process TTL cache for expensive read-only statistical analyses. The cache is invalidated after write operations. """
import threading
import time

_lock = threading.RLock()
_store = {}
_version_cache = {'checked_at': 0.0, 'value': 'na'}


def _data_version(ttl: int = 2) -> str:
    """Use a single SQL query to obtain a data version so the cache can expire quickly after writes by other processes. """
    now = time.time()
    if _version_cache['value'] != 'na' and now - _version_cache['checked_at'] < ttl:
        return _version_cache['value']
    try:
        from sqlalchemy import text
        from app.db import engine
        sql = text(
            'SELECT (SELECT COUNT(*) FROM t_subject), '
            '(SELECT COUNT(*) FROM t_screening), '
            '(SELECT COUNT(*) FROM t_item_response), '
            '(SELECT COUNT(*) FROM t_image), '
            '(SELECT COUNT(*) FROM t_detection), '
            '(SELECT COUNT(*) FROM t_multimodal), '
            '(SELECT COALESCE(MAX(id), 0) FROM t_multimodal), '
            '(SELECT COALESCE(MAX(id), 0) FROM t_data_lock), '
            '(SELECT COALESCE(MAX(id), 0) FROM t_audit)')
        with engine.connect() as conn:
            value = '|'.join(str(x) for x in conn.execute(sql).one())
    except Exception:
        value = 'na'
    _version_cache.update({'checked_at': now, 'value': value})
    return value


def get_or_set(key: str, ttl: int, producer):
    """Return the cached value; call the producer when the value is missing or expired. """
    now = time.time()
    full_key = '%s@%s' % (key, _data_version())
    with _lock:
        item = _store.get(full_key)
        if item and item['expires'] > now:
            return item['value']
    value = producer()
    with _lock:
        _store[full_key] = {'value': value, 'expires': time.time() + max(1, ttl)}
    return value


def invalidate(prefix: str = '') -> int:
    """Clear all cached entries or entries with a given prefix and return the number removed. """
    with _lock:
        keys = [key for key in _store if not prefix or key.startswith(prefix)]
        for key in keys:
            _store.pop(key, None)
        return len(keys)


def stats() -> dict:
    """Return cache status for health checks and diagnostics. """
    now = time.time()
    with _lock:
        expired = sum(1 for item in _store.values() if item['expires'] <= now)
        return {'entries': len(_store), 'expired': expired}
