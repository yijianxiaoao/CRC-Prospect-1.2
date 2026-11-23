# -*- coding: utf-8 -*-
"""
Role-based access control (RBAC) and forced password-change enforcement.

Roles and permissions:

============  ==========================================================
"Role"          Permission
============  ==========================================================
viewer        Read-only: view the dashboard and analysis results
researcher    View data, import data, and review data (no unblinding, bulk review, or data locking)
admin         Full permissions, including unblinding, bulk review, data locking, image batch detection, and model training
============  ==========================================================

Permissions are enforced through the ``role_required`` decorator. Unauthenticated or unauthorized requests return 403 or redirect to sign-in.
"""
import functools

from flask import jsonify, redirect, request, session, url_for

from util_logger import get_logger

logger = get_logger(__name__)

# Role definitions and display names
ROLES = {
    'viewer': 'Viewer',
    'researcher': 'Researcher',
    'admin': 'Administrator',
}

# "Role hierarchy" (The larger the value, the higher the authority)
ROLE_LEVEL = {'viewer': 1, 'researcher': 2, 'admin': 3}

# Paths exempt from mandatory password-change redirection to avoid an infinite loop
PASSWORD_EXEMPT_PATHS = {'/change_password', '/logout', '/login', '/register'}
PASSWORD_EXEMPT_PREFIXES = ('/static',)


def current_role() -> str:
    """Return the role of the currently signed-in user. """
    return session.get('role') or 'viewer'


def role_level(role: str = None) -> int:
    """Return the permission level for a role. """
    return ROLE_LEVEL.get(role or current_role(), 0)


def has_permission(min_role: str) -> bool:
    """Return whether the current user meets the required role level. """
    return role_level() >= ROLE_LEVEL.get(min_role, 99)


def wants_json() -> bool:
    """Return whether the request expects a JSON response. """
    return (request.path.startswith('/api/')
            or request.path in {'/login', '/register', '/change_password'}
            or request.is_json
            or request.accept_mimetypes.best == 'application/json'
            or request.headers.get('X-Requested-With') == 'XMLHttpRequest')


def role_required(min_role: str = 'researcher'):
    """
    Route decorator requiring the current user to have at least the specified role.

    :param min_role: Minimum role (viewer, researcher, or admin)
    """
    def decorator(view):
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            if not session.get('uid'):
                if wants_json():
                    return jsonify(ok=False, msg='Please sign in first.'), 401
                return redirect(url_for('auth.login', next=request.path))
            if not has_permission(min_role):
                logger.warning('Insufficient permissions: "User %s (%s)Try to visit %s (Need to %s)',
                               session.get('username'), current_role(),
                               request.path, min_role)
                if wants_json():
                    return jsonify(ok=False,
                                   msg='Insufficient permissions: this operation requires the %s role or higher.'
                                       % ROLES.get(min_role, min_role)), 403
                return render_template_403(min_role)
            return view(*args, **kwargs)
        return wrapper
    return decorator


def data_write_guard(view):
    """Prevent study-data writes while data are locked. """
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        from app.service import advanced
        if advanced.is_locked():
            logger.warning('Data locked; write operation refused: user %s, path %s',
                           session.get('username'), request.path)
            if wants_json():
                return jsonify(ok=False, code='DATA_LOCKED',
                               msg='Data are locked. An administrator must unlock them before changes can be made.'), 423
            return render_template_403('admin')
        return view(*args, **kwargs)
    return wrapper


def render_template_403(min_role: str):
    """Render the insufficient-permissions page. """
    from flask import render_template
    return render_template('403.html', required_role=ROLES.get(min_role, min_role),
                           current_role=ROLES.get(current_role(), current_role())), 403


def check_password_change_required() -> bool:
    """
    Return whether the current user must change their password at first login.

    Return True when the caller should redirect to the password-change page.
    """
    if not session.get('uid'):
        return False
    if not session.get('must_change_password'):
        return False
    path = request.path
    if path in PASSWORD_EXEMPT_PATHS:
        return False
    if any(path.startswith(p) for p in PASSWORD_EXEMPT_PREFIXES):
        return False
    return True