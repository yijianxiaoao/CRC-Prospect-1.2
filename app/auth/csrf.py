# -*- coding: utf-8 -*-
"""Lightweight CSRF protection.

All state-changing requests must carry a session-bound token. The browser sends the token
in the ``X-CSRF-Token`` request header or the ``_csrf_token`` form field.
"""
import hmac
import secrets

from flask import jsonify, render_template, request, session

from util_logger import get_logger

logger = get_logger(__name__)

SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS', 'TRACE'}
FORM_EXEMPT_ENDPOINTS = {'static'}


def csrf_token() -> str:
    """Return the current session CSRF token, generating one securely if needed. """
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


def _provided_token() -> str:
    return (request.headers.get('X-CSRF-Token')
            or request.form.get('_csrf_token')
            or '')


def validate_csrf() -> bool:
    """Verify the CSRF token for the current request. """
    if request.method.upper() in SAFE_METHODS:
        return True
    if request.endpoint in FORM_EXEMPT_ENDPOINTS:
        return True
    expected = session.get('_csrf_token') or ''
    supplied = _provided_token()
    return bool(expected and supplied and hmac.compare_digest(expected, supplied))


def _expects_json() -> bool:
    return (request.path.startswith('/api/')
            or request.path in {'/login', '/register', '/change_password'}
            or request.is_json
            or request.accept_mimetypes.best == 'application/json'
            or request.headers.get('X-Requested-With') == 'XMLHttpRequest')


def protect() -> object:
    """Flask before-request processor. """
    if validate_csrf():
        return None
    path = request.path
    logger.warning('CSRF verification failed: %s %s, source %s', request.method, path,
                   request.headers.get('X-Forwarded-For', request.remote_addr or ''))
    message = 'The page security token is no longer valid. Please refresh the page and try again.'
    if _expects_json():
        return jsonify(ok=False, code='CSRF_INVALID', msg=message), 400
    return render_template('csrf_error.html', message=message), 400
