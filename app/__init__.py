# -*- coding: utf-8 -*-
"""Application factory for the research platform on behavioral mechanisms of colonoscopy screening in high-risk colorectal cancer populations. """
import datetime
import secrets
import time

import numpy as np
from flask import (Flask, g, jsonify, render_template, request, session)
from flask.json.provider import DefaultJSONProvider
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import text

import config


class NumpyJSONProvider(DefaultJSONProvider):
    """Allow jsonify to serialize NumPy and pandas numeric types. """

    @staticmethod
    def default(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return DefaultJSONProvider.default(obj)


def _wants_json() -> bool:
    return (request.path.startswith('/api/')
            or request.path in {'/login', '/register', '/change_password'}
            or request.is_json
            or request.accept_mimetypes.best == 'application/json')


def create_app() -> Flask:
    """Create and configure the Flask application and register security, logging, and health-check components. """
    app = Flask(__name__, static_folder='web/static', static_url_path='/static')
    app.secret_key = config.SECRET_KEY
    if config.TRUST_PROXY:
        # Enable only when a trusted reverse proxy is explicitly configured, avoiding forged forwarding headers on direct exposure.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.json = NumpyJSONProvider(app)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=config.SESSION_COOKIE_SECURE,
        PERMANENT_SESSION_LIFETIME=datetime.timedelta(hours=config.SESSION_LIFETIME_HOURS),
        MAX_CONTENT_LENGTH=config.MAX_UPLOAD_MB * 1024 * 1024,
        MAX_FORM_MEMORY_SIZE=config.MAX_UPLOAD_MB * 1024 * 1024,
        JSON_AS_ASCII=False,
    )

    from app import db
    db.init_db()

    from app.auth import csrf
    from app.auth import routes as auth_routes
    from app.auth import sso
    from app.web import bp as web_bp

    sso.init_app(app)

    app.jinja_env.globals['csrf_token'] = csrf.csrf_token

    @app.before_request
    def _start_request():
        g.request_started = time.perf_counter()
        g.request_id = request.headers.get('X-Request-ID') or secrets.token_hex(8)

    @app.before_request
    def _csrf_protect():
        return csrf.protect()

    @app.after_request
    def _finish_request(response):
        if not request.path.startswith('/static/'):
            duration_ms = (time.perf_counter() - getattr(g, 'request_started', time.perf_counter())) * 1000
            from util_logger import get_logger
            get_logger('app.request').info(
                '%s %s -> %s %.1fms user=%s req=%s',
                request.method, request.path, response.status_code, duration_ms,
                session.get('username', 'anonymous'), getattr(g, 'request_id', '-'))
        response.headers.setdefault('X-Request-ID', getattr(g, 'request_id', '-'))
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        response.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        response.headers.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        forwarded_proto = (request.headers.get('X-Forwarded-Proto') or '').lower()
        cf_visitor = request.headers.get('CF-Visitor') or ''
        secure_request = request.is_secure or (
            config.TRUST_PROXY and (forwarded_proto == 'https' or
                                    '"scheme":"https"' in cf_visitor.replace(' ', '')))
        # Browsers accept HSTS only over HTTPS; this header is ignored in local HTTP responses.
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000')
        if secure_request:
            # The same app supports local HTTP and public HTTPS; add Secure only when the request is confirmed as HTTPS.
            cookies = response.headers.getlist('Set-Cookie')
            if cookies:
                response.headers.remove('Set-Cookie')
                for cookie in cookies:
                    if cookie.startswith('session=') and '; Secure' not in cookie:
                        cookie += '; Secure'
                    response.headers.add('Set-Cookie', cookie)
        response.headers.setdefault(
            'Content-Security-Policy',
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
            "connect-src 'self'; font-src 'self' data:; object-src 'none'; "
            "base-uri 'self'; frame-ancestors 'none'; form-action 'self'")
        if (request.path.startswith(('/api/', '/mfa', '/sso', '/account'))
                or request.path in {'/login', '/register', '/change_password', '/security'}):
            response.headers.setdefault('Cache-Control', 'no-store')
        return response

    @app.errorhandler(400)
    def _bad_request(exc):
        msg = getattr(exc, 'description', 'Invalid request parameters')
        if _wants_json():
            return jsonify(ok=False, msg=msg), 400
        return render_template('error.html', code=400, title='Invalid request', message=msg), 400

    @app.errorhandler(403)
    def _forbidden(exc):
        msg = getattr(exc, 'description', 'You do not have permission to access this resource')
        if _wants_json():
            return jsonify(ok=False, msg=msg), 403
        return render_template('error.html', code=403, title='Insufficient permissions', message=msg), 403

    @app.errorhandler(404)
    def _not_found(exc):
        if _wants_json():
            return jsonify(ok=False, msg='The interface or resource does not exist'), 404
        return render_template('error.html', code=404, title='Page not found',
                               message='Please check that the access address is correct'), 404

    @app.errorhandler(413)
    def _too_large(exc):
        msg = 'The uploaded file exceeds the %d MB limit' % config.MAX_UPLOAD_MB
        if _wants_json():
            return jsonify(ok=False, msg=msg), 413
        return render_template('error.html', code=413, title='File too large', message=msg), 413

    @app.errorhandler(500)
    def _server_error(exc):
        app.logger.error('Unhandled exception: %s', exc, exc_info=True)
        msg = 'Internal server error. Please try again later.'
        if _wants_json():
            return jsonify(ok=False, msg=msg), 500
        return render_template('error.html', code=500, title='Service error', message=msg), 500

    @app.get('/healthz')
    def _healthz():
        """Process liveness probe that does not access the database."""
        return jsonify(ok=True, service='crc-prospect-theory-research')

    @app.get('/readyz')
    def _readyz():
        """Database readiness probe. """
        try:
            with db.engine.connect() as conn:
                conn.execute(text('SELECT 1'))
        except Exception as exc:
            app.logger.error('Database readiness check failed: %s', exc)
            return jsonify(ok=False, database=False), 503
        return jsonify(ok=True, database=True)

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(web_bp)
    return app
