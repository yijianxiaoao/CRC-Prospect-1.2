# -*- coding: utf-8 -*-
"""Login and registration security assistance: Brute force to crack the speed limit, Password strength and client IP. """
import functools
import re
import threading
import time
from collections import defaultdict, deque

from flask import jsonify, request

import config

_lock = threading.Lock()
_failures = defaultdict(deque)
_locked_until = {}
_registrations = defaultdict(deque)


def client_ip() -> str:
    """Adopted only in trusted reverse proxy mode X-Forwarded-For, Prevent bypassing the speed limit. """
    if config.TRUST_PROXY:
        forwarded = (request.headers.get('X-Forwarded-For') or '').split(',')[0].strip()
        return forwarded or (request.remote_addr or 'unknown')
    return request.remote_addr or 'unknown'


def _prune(key: str, now: float, window: int) -> None:
    q = _failures[key]
    while q and q[0] < now - window:
        q.popleft()
    if not q:
        _failures.pop(key, None)


def login_allowed(username: str) -> tuple:
    """Check the username and source IP Whether or not the login is locked. """
    now = time.time()
    user_key = 'user:%s' % (username or '').strip().lower()
    ip_key = 'ip:%s' % client_ip()
    with _lock:
        for key in (user_key, ip_key):
            until = _locked_until.get(key, 0)
            if until > now:
                return False, max(1, int(until - now))
            if until:
                _locked_until.pop(key, None)
            _prune(key, now, config.LOGIN_WINDOW_SECONDS)
    return True, 0


def record_login_failure(username: str) -> int:
    """Record a failure, Returns the number of attempts remaining for the username. """
    now = time.time()
    user_key = 'user:%s' % (username or '').strip().lower()
    ip_key = 'ip:%s' % client_ip()
    with _lock:
        for key in (user_key, ip_key):
            _failures[key].append(now)
            _prune(key, now, config.LOGIN_WINDOW_SECONDS)
        if len(_failures[user_key]) >= config.LOGIN_MAX_FAILURES:
            _locked_until[user_key] = now + config.LOGIN_LOCK_SECONDS
        # IP The threshold is wider, Avoid multiple accidental injuries in the same office.
        if len(_failures[ip_key]) >= config.LOGIN_MAX_FAILURES * 4:
            _locked_until[ip_key] = now + config.LOGIN_LOCK_SECONDS
        remaining = max(0, config.LOGIN_MAX_FAILURES - len(_failures[user_key]))
    return remaining


def clear_login_failures(username: str) -> None:
    """Failed to clean up the account after successful login. """
    user_key = 'user:%s' % (username or '').strip().lower()
    with _lock:
        _failures.pop(user_key, None)
        _locked_until.pop(user_key, None)


def registration_allowed() -> tuple:
    """Limit the number of registrations per hour from a single source, Reduce the risk of bulk spam accounts. """
    now = time.time()
    key = 'register:%s' % client_ip()
    with _lock:
        q = _registrations[key]
        while q and q[0] < now - 3600:
            q.popleft()
        if len(q) >= config.REGISTER_MAX_PER_HOUR:
            return False, max(1, int(3600 - (now - q[0])))
    return True, 0


def record_registration() -> None:
    """Record a successful registration. """
    with _lock:
        _registrations['register:%s' % client_ip()].append(time.time())


def consume_rate(key: str, limit: int, window_seconds: int) -> tuple:
    """Universal sliding window speed limit, Back (allowed, retry_after_seconds). """
    now = time.time()
    bucket = 'rate:%s' % key
    with _lock:
        q = _registrations[bucket]
        while q and q[0] < now - window_seconds:
            q.popleft()
        if len(q) >= limit:
            return False, max(1, int(window_seconds - (now - q[0])))
        q.append(now)
        return True, 0


def rate_limit(limit: int, window_seconds: int = 60):
    """Interface-level rate-limiting decorator, scoped by source IP and route. """
    def decorator(view):
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            allowed, retry_after = consume_rate(
                '%s:%s' % (client_ip(), request.path), limit, window_seconds)
            if not allowed:
                return jsonify(ok=False, msg='Too many requests. Please try again later.',
                               retry_after=retry_after), 429
            return view(*args, **kwargs)
        return wrapper
    return decorator


COMMON_PASSWORDS = {
    '12345678', 'password', 'password1', 'admin123', '123456789',
    'qwerty123', 'abc12345', '11111111', '88888888',
}


def sanitize_username(value: str) -> str:
    """Convert an SSO claim to a stable username using the same rules as local accounts. """
    raw = (value or '').strip().lower()
    raw = re.sub(r'[^a-z0-9_.-]+', '-', raw).strip('.-_')
    if len(raw) < 3:
        raw = ('sso-' + raw).strip('-')
    return raw[:50]


def password_error(password: str) -> str:
    """Return the reason a password is non-compliant, or an empty string if it is compliant. """
    value = password or ''
    if len(value) < 8:
        return 'Password must be at least 8 characters.'
    if value.lower() in COMMON_PASSWORDS:
        return 'Common weak passwords are not allowed.'
    if len(set(value)) < 3:
        return 'The password uses too few distinct characters.'
    categories = sum(bool(x) for x in (
        any(ch.islower() for ch in value),
        any(ch.isupper() for ch in value),
        any(ch.isdigit() for ch in value),
        any(not ch.isalnum() for ch in value),
    ))
    if categories < 2:
        return 'The password must include at least two of the following: letters, numbers, and symbols.'
    return ''
