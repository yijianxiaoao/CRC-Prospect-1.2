# -*- coding: utf-8 -*-
"""Sign in / Register / SSO / MFA / Exit / Change Password. """
import datetime
import json
import re
import secrets
import time
from urllib.parse import urlsplit

from flask import (Blueprint, jsonify, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import config
from app.auth import mfa as mfa_utils
from app.auth import security, sso
from app.db import Session
from app.models import User
from app.service import audit
from util_logger import get_logger

logger = get_logger(__name__)
bp = Blueprint('auth', __name__)

_PENDING_KEYS = (
    'pending_uid', 'pending_username', 'pending_session_version',
    'pending_started_at', 'pending_stage', 'pending_auth_method',
    'pending_next',
)


def _safe_next() -> str:
    """Only in-site redirects are allowed, Avoid open redirection. """
    target = request.args.get('next') or ''
    if not target or '\\' in target or target.startswith('//'):
        return url_for('web.index')
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith('/') \
            or parsed.path.startswith('//'):
        return url_for('web.index')
    return target


def _safe_internal_path(target: str) -> str:
    """Verify the in-station redirect address already saved in the session. """
    value = target or ''
    if not value or '\\' in value or value.startswith('//'):
        return url_for('web.index')
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith('/') \
            or parsed.path.startswith('//'):
        return url_for('web.index')
    return value


def _clear_pending() -> None:
    for key in _PENDING_KEYS:
        session.pop(key, None)


def _pending_context() -> dict:
    """Read and verify two-stage login context. """
    uid = session.get('pending_uid')
    stage = session.get('pending_stage')
    if not uid or stage not in ('challenge', 'setup'):
        return {}
    try:
        started_at = int(session.get('pending_started_at') or 0)
    except (TypeError, ValueError):
        started_at = 0
    if not started_at or time.time() - started_at > config.MFA_SESSION_TTL_SECONDS:
        _clear_pending()
        return {}
    return {
        'uid': int(uid),
        'username': session.get('pending_username') or '',
        'session_version': int(session.get('pending_session_version') or 1),
        'stage': stage,
        'auth_method': session.get('pending_auth_method') or 'password',
        'next_url': _safe_internal_path(session.get('pending_next') or '/'),
    }


def _set_pending(user: User, stage: str, auth_method: str, next_url: str) -> None:
    """Clear old sessions and establish short-term, Unauthorized two-phase login context. """
    csrf_token = session.get('_csrf_token')
    session.clear()
    if csrf_token:
        session['_csrf_token'] = csrf_token
    session.permanent = True
    session['pending_uid'] = int(user.id)
    session['pending_username'] = user.username
    session['pending_session_version'] = int(user.session_version or 1)
    session['pending_started_at'] = int(time.time())
    session['pending_stage'] = stage
    session['pending_auth_method'] = auth_method
    session['pending_next'] = _safe_internal_path(next_url)


def _load_pending_user(sess) -> tuple:
    """Loading to be completed MFA The user; Reject immediately if account status or session version changes. """
    context = _pending_context()
    if not context:
        return None, {}
    user = sess.get(User, context['uid'])
    if (not user or (user.status or 'active') != 'active'
            or int(user.session_version or 1) != context['session_version']):
        _clear_pending()
        return None, {}
    return user, context


def _full_user(sess):
    """Load signed-in users and verify account status and session_version in real time. """
    uid = session.get('uid')
    if not uid:
        return None
    user = sess.get(User, uid)
    if (not user or (user.status or 'active') != 'active'
            or int(user.session_version or 1) != int(session.get('session_version') or 0)):
        session.clear()
        return None
    return user


def _establish_session(user: User, auth_method: str, mfa_verified: bool) -> None:
    """Password/SSO with MFA After all are passed, Write to formal login session only. """
    csrf_token = session.get('_csrf_token')
    session.clear()
    if csrf_token:
        session['_csrf_token'] = csrf_token
    session.permanent = True
    session['uid'] = int(user.id)
    session['username'] = user.username
    session['nickname'] = user.nickname or user.username
    session['role'] = user.role or 'viewer'
    session['must_change_password'] = int(user.must_change_password or 0)
    session['session_version'] = int(user.session_version or 1)
    session['auth_method'] = auth_method or 'password'
    session['mfa_verified'] = bool(mfa_verified)


def _mark_login(user: User) -> None:
    user.last_login_at = datetime.datetime.utcnow()
    user.last_login_ip = security.client_ip()[:64]


def _trusted_sso_mfa(auth_method: str) -> bool:
    return bool(auth_method == 'sso' and config.SSO_TRUST_IDP_MFA)


def _start_login_flow(sess, user: User, auth_method: str, next_url: str) -> dict:
    """According to MFA Strategy determines entry TOTP Verification, TOTP Binding or formal session. """
    next_url = _safe_internal_path(next_url)
    trusted_idp_mfa = _trusted_sso_mfa(auth_method)
    mfa_enabled_for_user = bool(int(user.mfa_enabled or 0) and user.mfa_secret_enc)

    if config.MFA_ENABLED and not trusted_idp_mfa:
        if mfa_enabled_for_user:
            _set_pending(user, 'challenge', auth_method, next_url)
            return {
                'ok': True,
                'stage': 'challenge',
                'msg': 'Identity verification passed, Please enter the authenticator code',
                'redirect': url_for('auth.mfa_challenge'),
            }
        if config.MFA_REQUIRED:
            _set_pending(user, 'setup', auth_method, next_url)
            return {
                'ok': True,
                'stage': 'setup',
                'msg': 'The platform requires activation. MFA, Please bind the authenticator first',
                'redirect': url_for('auth.mfa_setup'),
            }

    _establish_session(user, auth_method, mfa_verified=mfa_enabled_for_user or trusted_idp_mfa)
    _mark_login(user)
    return {'ok': True, 'stage': 'complete', 'msg': 'Login successful', 'redirect': next_url}


def _claim(userinfo: dict, name: str) -> str:
    value = userinfo.get(name) if isinstance(userinfo, dict) else None
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ''
    return str(value or '').strip()


def _upsert_sso_user(sess, userinfo: dict) -> tuple:
    """According to the OIDC subject Search for an account; Optionally create automatically or explicitly allow bindings by username. """
    subject = _claim(userinfo, config.SSO_SUBJECT_CLAIM)
    if not subject:
        raise ValueError('Identity provider did not return a unique user ID (%s)' % config.SSO_SUBJECT_CLAIM)

    username_hint = (_claim(userinfo, config.SSO_USERNAME_CLAIM)
                     or _claim(userinfo, config.SSO_EMAIL_CLAIM).split('@')[0]
                     or subject)
    username = security.sanitize_username(username_hint)
    if not username:
        raise ValueError('"Cannot from SSO Claim a valid account name')
    nickname = _claim(userinfo, config.SSO_NAME_CLAIM)[:50] or username
    email = _claim(userinfo, config.SSO_EMAIL_CLAIM)[:255]

    user = (sess.query(User)
            .filter(User.sso_provider == 'oidc', User.sso_subject == subject)
            .first())
    if user:
        if not user.nickname and nickname:
            user.nickname = nickname
        if email:
            user.email = email
        return user, False

    existing = sess.query(User).filter_by(username=username).first()
    if existing:
        if not config.SSO_LINK_BY_USERNAME:
            raise ValueError('Username %s Already exists, Please ask the administrator to complete. SSO "Binding' % username)
        if existing.sso_subject and existing.sso_subject != subject:
            raise ValueError('Username %s Bound to others SSO Identity' % username)
        existing.sso_provider = 'oidc'
        existing.sso_subject = subject
        existing.auth_source = 'sso'
        if not existing.nickname and nickname:
            existing.nickname = nickname
        if email:
            existing.email = email
        return existing, False

    if not config.SSO_AUTO_CREATE:
        raise ValueError('SSO The account has not been activated yet., Please contact the administrator to review or complete the registration first')

    user = User(
        username=username,
        nickname=nickname,
        email=email,
        password_hash=generate_password_hash(secrets.token_urlsafe(32)),
        role=config.SSO_DEFAULT_ROLE,
        status=config.SSO_DEFAULT_STATUS,
        auth_source='sso',
        sso_provider='oidc',
        sso_subject=subject,
        must_change_password=0,
    )
    if user.status == 'active':
        user.approved_by = 'sso-policy'
        user.approved_at = datetime.datetime.utcnow()
    sess.add(user)
    sess.flush()
    return user, True


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page / Local password login interface. """
    if request.method == 'GET':
        if session.get('uid'):
            return redirect(_safe_next())
        return render_template(
            'login.html',
            registration_enabled=config.REGISTRATION_ENABLED,
            sso_available=sso.available(),
            sso_provider_name=config.SSO_PROVIDER_NAME,
            sso_error=(request.args.get('sso_error') or '').strip(),
        )

    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    if not username or not password:
        return jsonify(ok=False, msg='Please enter your username and password.')

    allowed, wait_seconds = security.login_allowed(username)
    if not allowed:
        audit.log_action('Login speed limit', username, 'Account is temporarily locked', username=username)
        return jsonify(ok=False, retry_after=wait_seconds,
                       msg='Too many attempts. Please try again in %d minutes.'
                           % max(1, wait_seconds // 60)), 429

    sess = Session()
    try:
        user = sess.query(User).filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            remaining = security.record_login_failure(username)
            audit.log_action('Login failed', username, 'Incorrect username or password.', username=username)
            return jsonify(ok=False, remaining=remaining, msg='Incorrect username or password.')
        if (user.status or 'active') != 'active':
            audit.log_action('Login denied', username, 'Account not activated or deactivated', username=username)
            return jsonify(ok=False, msg='Account pending administrator review or disabled.'), 403
        security.clear_login_failures(username)
        result = _start_login_flow(sess, user, 'password', _safe_next())
        sess.commit()
        if result['stage'] == 'complete':
            detail = 'Login successful, "Role" %s%s' % (
                user.role or 'viewer',
                ' (A mandatory password change is required)' if user.must_change_password else '')
        else:
            detail = 'Password authentication passed, Enter %s' % (
                'MFA Verification' if result['stage'] == 'challenge' else 'MFA "Binding')
        audit.log_action('Sign in', username, detail, username=username)
        logger.info('"User %s Complete password authentication ("Stage: %s)', username, result['stage'])
        return jsonify(ok=True, msg=result['msg'], redirect=result['redirect'],
                       mfa_stage=result['stage'])
    except Exception:
        sess.rollback()
        logger.error('Login exception', exc_info=True)
        return jsonify(ok=False, msg='Sign-in error. Please try again later.')
    finally:
        sess.close()


@bp.route('/register', methods=['POST'])
def register():
    """Registration interface. """
    if not config.REGISTRATION_ENABLED:
        return jsonify(ok=False, msg='Self-registration is currently disabled. Please contact an administrator.'), 403
    reg_allowed, retry_after = security.registration_allowed()
    if not reg_allowed:
        return jsonify(ok=False, retry_after=retry_after,
                       msg='Too many registration requests. Please try again later.'), 429

    username = (request.form.get('username') or '').strip()
    nickname = (request.form.get('nickname') or '').strip()
    password = request.form.get('password') or ''
    password2 = request.form.get('password2') or ''

    if not username or not password:
        return jsonify(ok=False, msg='Please complete all required fields.')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{3,50}', username):
        return jsonify(ok=False, msg='Username must be 3-50 characters and may contain letters, numbers, periods, underscores, or hyphens.')
    pwd_error = security.password_error(password)
    if pwd_error:
        return jsonify(ok=False, msg=pwd_error)
    if password != password2:
        return jsonify(ok=False, msg='The passwords do not match.')

    requires_approval = config.REGISTRATION_REQUIRES_APPROVAL
    new_status = 'pending' if requires_approval else 'active'
    sess = Session()
    try:
        if sess.query(User).filter_by(username=username).first():
            return jsonify(ok=False, msg='This username is already registered. Please choose another one.')
        user = User(username=username, nickname=nickname or username,
                    password_hash=generate_password_hash(password),
                    role=config.DEFAULT_REGISTRATION_ROLE,
                    status=new_status, must_change_password=0,
                    auth_source='local')
        if not requires_approval:
            user.approved_by = 'registration-policy'
            user.approved_at = datetime.datetime.utcnow()
        sess.add(user)
        sess.commit()
        security.record_registration()
        detail = ("New account registration. Waiting for administrator review" if requires_approval
                  else "New account registration. The policy allows direct activation")
        audit.log_action('User registration', username, detail, username=username)
        message = ('Registration has been submitted., Admin approval required to log in'
                   if requires_approval else 'Registration successful, You can log in now')
        return jsonify(ok=True, msg=message, status=new_status)
    except Exception:
        sess.rollback()
        logger.error('Abnormal registration', exc_info=True)
        return jsonify(ok=False, msg='Registration failed. Please try again later.')
    finally:
        sess.close()


@bp.route('/security', methods=['GET'])
def account_security():
    """Current user's account security settings page. """
    if not session.get('uid'):
        return redirect(url_for('auth.login', next=url_for('auth.account_security')))
    sess = Session()
    try:
        user = _full_user(sess)
        if not user:
            return redirect(url_for('auth.login'))
        try:
            recovery_count = len(json.loads(user.mfa_recovery_hashes or '[]'))
        except (TypeError, ValueError):
            recovery_count = 0
        effective_required = bool(
            config.MFA_REQUIRED and not _trusted_sso_mfa(session.get('auth_method') or ''))
        return render_template(
            'account_security.html',
            mfa_available=config.MFA_ENABLED,
            mfa_enabled=bool(int(user.mfa_enabled or 0) and user.mfa_secret_enc),
            mfa_required=effective_required,
            recovery_count=recovery_count,
            sso_linked=bool(user.sso_subject),
            auth_source=user.auth_source or 'local',
        )
    finally:
        sess.close()


@bp.route('/account/mfa/disable', methods=['POST'])
def disable_mfa():
    """Closing a Voluntarily Enabled by a Valid Dynamic Code or Recovery Code MFA. """
    if not config.MFA_ENABLED:
        return jsonify(ok=False, msg='MFA is not enabled on this platform.'), 403
    sess = Session()
    try:
        user = _full_user(sess)
        if not user:
            return jsonify(ok=False, msg='Your session has expired. Please sign in again.'), 401
        effective_required = bool(
            config.MFA_REQUIRED and not _trusted_sso_mfa(session.get('auth_method') or ''))
        if effective_required:
            return jsonify(ok=False, msg='MFA is required platform-wide and cannot be disabled by individual users.'), 403

        code = (request.form.get('code') or '').strip()
        verified, remaining = mfa_utils.verify_recovery_code(
            user.mfa_recovery_hashes or '', code)
        if not verified:
            secret = mfa_utils.decrypt_secret(user.mfa_secret_enc or '')
            verified, counter = mfa_utils.verify_totp(
                secret, code, int(user.last_mfa_counter or 0))
            if verified:
                user.last_mfa_counter = counter
        if not verified:
            return jsonify(ok=False, msg='Invalid authenticator code or recovery code.')

        user.mfa_enabled = 0
        user.mfa_secret_enc = ''
        user.mfa_recovery_hashes = ''
        user.last_mfa_counter = 0
        user.session_version = int(user.session_version or 1) + 1
        sess.commit()
        session['session_version'] = int(user.session_version)
        session['mfa_verified'] = False
        audit.log_action('MFA Disabled', user.username, 'User disabled TOTP two-factor authentication',
                         username=user.username)
        return jsonify(ok=True, msg='MFA disabled.')
    except Exception:
        sess.rollback()
        logger.error('Failed to disable MFA', exc_info=True)
        return jsonify(ok=False, msg='Operation failed. Please try again later.')
    finally:
        sess.close()


@bp.route('/account/mfa/recovery_codes', methods=['POST'])
def regenerate_recovery_codes():
    """Regenerate the recovery code, Old recovery codes are all voided immediately. """
    sess = Session()
    try:
        user = _full_user(sess)
        if not user:
            return jsonify(ok=False, msg='Your session has expired. Please sign in again.'), 401
        if not int(user.mfa_enabled or 0):
            return jsonify(ok=False, msg='MFA has not been enabled for the current account.')
        code = (request.form.get('code') or '').strip()
        secret = mfa_utils.decrypt_secret(user.mfa_secret_enc or '')
        verified, counter = mfa_utils.verify_totp(
            secret, code, int(user.last_mfa_counter or 0))
        if not verified:
            return jsonify(ok=False, msg='The authenticator code is invalid.')
        codes = mfa_utils.generate_recovery_codes()
        user.mfa_recovery_hashes = mfa_utils.hash_recovery_codes(codes)
        user.last_mfa_counter = counter
        sess.commit()
        audit.log_action('Update MFA recovery code', user.username, 'All old recovery codes have expired',
                         username=user.username)
        return jsonify(ok=True, msg='Recovery codes have been regenerated.', recovery_codes=codes)
    except Exception:
        sess.rollback()
        logger.error('Failed to update the recovery code', exc_info=True)
        return jsonify(ok=False, msg='Operation failed. Please try again later.')
    finally:
        sess.close()


@bp.route('/sso/login', methods=['GET'])
def sso_login():
    """Jump to Enterprise Unified Identity (OIDC Authorization Code + PKCE). """
    if not sso.available():
        return redirect(url_for('auth.login', sso_error='SSO Not enabled or incomplete configuration'))
    session['sso_next'] = _safe_next()
    _clear_pending()
    redirect_uri = url_for('auth.sso_callback', _external=True)
    try:
        return sso.oauth.sso.authorize_redirect(redirect_uri)
    except Exception:
        logger.error('SSO Failed authorization redirect', exc_info=True)
        return redirect(url_for('auth.login', sso_error='SSO Initialization failed, Please contact the administrator.'))


@bp.route('/sso/callback', methods=['GET'])
def sso_callback():
    """"Processing" OIDC Callback, Account binding/Open an account and continue to unify MFA Strategy. """
    if not sso.available():
        return redirect(url_for('auth.login', sso_error='SSO Not enabled or incomplete configuration'))

    next_url = _safe_internal_path(session.pop('sso_next', url_for('web.index')))
    try:
        token = sso.oauth.sso.authorize_access_token()
        userinfo = token.get('userinfo') if token else None
        if not userinfo:
            userinfo = sso.oauth.sso.userinfo(token=token)
        if not isinstance(userinfo, dict):
            raise ValueError('SSO No valid user information returned')
    except Exception:
        logger.error('SSO The callback verification failed', exc_info=True)
        audit.log_action('SSO Login failed', '', 'Authorization code, state, nonce Or the token verification failed')
        return redirect(url_for('auth.login',
                                sso_error='SSO Login verification failed, Please try again.'))

    sess = Session()
    try:
        user, created = _upsert_sso_user(sess, userinfo)
        username = user.username
        status = user.status or 'active'
        role = user.role or 'viewer'
        if status != 'active':
            sess.commit()
            if created:
                audit.log_action('SSO Auto-provisioning', username,
                                 'Source %s, Status %s, "Role" %s' % (
                                     config.SSO_PROVIDER_NAME, status, role),
                                 username=username)
            audit.log_action('SSO Login denied', username,
                             "Account status %s. Waiting for administrator approval" % status,
                             username=username)
            return redirect(url_for('auth.login',
                                    sso_error=("SSO account created. Waiting for administrator review"
                                               if created else "SSO account is pending administrator review")))

        result = _start_login_flow(sess, user, 'sso', next_url)
        sess.commit()
        if created:
            audit.log_action('SSO Auto-provisioning', username,
                             'Source %s, Status %s, "Role" %s' % (
                                 config.SSO_PROVIDER_NAME, status, role),
                             username=username)
        audit.log_action('SSO Sign in', username,
                         'Identity provider authentication passed, "Stage %s' % result['stage'],
                         username=username)
        return redirect(result['redirect'])
    except ValueError as exc:
        sess.rollback()
        audit.log_action('SSO Login denied', '', str(exc)[:300])
        return redirect(url_for('auth.login', sso_error=str(exc)[:200]))
    except Exception:
        sess.rollback()
        logger.error('SSO User processing failed', exc_info=True)
        return redirect(url_for('auth.login',
                                sso_error='SSO Account processing failed, Please contact the administrator.'))
    finally:
        sess.close()


@bp.route('/mfa', methods=['GET', 'POST'])
def mfa_challenge():
    """Two-phase login in progress TOTP Verification page. """
    if request.method == 'GET':
        context = _pending_context()
        if context.get('stage') != 'challenge':
            return redirect(url_for('auth.login'))
        return render_template('mfa_challenge.html',
                               auth_method=context.get('auth_method', 'password'))

    sess = Session()
    try:
        user, context = _load_pending_user(sess)
        if not user or context.get('stage') != 'challenge':
            return jsonify(ok=False, msg='The verification session has expired. Please sign in again.'), 401

        allowed, wait_seconds = security.login_allowed(user.username)
        if not allowed:
            return jsonify(ok=False, retry_after=wait_seconds,
                           msg='Too many failed verification attempts. Please try again later.'), 429

        code = (request.form.get('code') or '').strip()
        use_recovery = (request.form.get('use_recovery') or '').lower() in (
            '1', 'true', 'yes', 'on')
        verified = False
        if use_recovery:
            verified, remaining = mfa_utils.verify_recovery_code(
                user.mfa_recovery_hashes or '', code)
            if verified:
                user.mfa_recovery_hashes = remaining
        else:
            secret = mfa_utils.decrypt_secret(user.mfa_secret_enc or '')
            verified, counter = mfa_utils.verify_totp(
                secret, code, int(user.last_mfa_counter or 0))
            if verified:
                user.last_mfa_counter = counter

        if not verified:
            remaining = security.record_login_failure(user.username)
            audit.log_action('MFA Verification failed', user.username,
                             'Invalid authenticator code or recovery code.', username=user.username)
            return jsonify(ok=False, remaining=remaining,
                           msg='Invalid authenticator code or recovery code.')

        security.clear_login_failures(user.username)
        _establish_session(user, context.get('auth_method') or 'password', True)
        _mark_login(user)
        sess.commit()
        audit.log_action('Sign in', user.username, 'MFA The secondary verification was passed.', username=user.username)
        return jsonify(ok=True, msg='Verification successful.', redirect=context['next_url'])
    except Exception:
        sess.rollback()
        logger.error('MFA Verification exception', exc_info=True)
        return jsonify(ok=False, msg='Verification failed. Please try again later.')
    finally:
        sess.close()


@bp.route('/mfa/setup', methods=['GET', 'POST'])
def mfa_setup():
    """"Binding TOTP Authenticator; Supports forced first login binding and active activation after login. """
    if not config.MFA_ENABLED:
        return jsonify(ok=False, msg='MFA is not enabled on this platform.'), 403

    sess = Session()
    try:
        context = _pending_context()
        pending_mode = context.get('stage') == 'setup'
        if pending_mode:
            user, context = _load_pending_user(sess)
        else:
            context = {}
            user = _full_user(sess)
        if not user:
            if request.method == 'GET':
                return redirect(url_for('auth.login'))
            return jsonify(ok=False, msg='Your session has expired. Please sign in again.'), 401
        if int(user.mfa_enabled or 0) and user.mfa_secret_enc and not pending_mode:
            if request.method == 'GET':
                return redirect(url_for('auth.account_security'))
            return jsonify(ok=False, msg='MFA is already enabled for the current account.')

        if request.method == 'GET':
            secret = session.get('mfa_setup_secret') or ''
            if (not secret or session.get('mfa_setup_uid') != user.id):
                secret = mfa_utils.generate_secret()
                session['mfa_setup_secret'] = secret
                session['mfa_setup_uid'] = user.id
            uri = mfa_utils.provisioning_uri(secret, user.username)
            return render_template(
                'mfa_setup.html',
                secret_display=mfa_utils.secret_display(secret),
                qr_svg=mfa_utils.qr_svg(uri),
                force_setup=bool(pending_mode or config.MFA_REQUIRED),
                auth_method=context.get('auth_method', 'password'),
            )

        allowed, retry_after = security.consume_rate(
            'mfa-setup:%s' % security.client_ip(), 10, 300)
        if not allowed:
            return jsonify(ok=False, retry_after=retry_after,
                           msg='Too many MFA setup attempts. Please try again later.'), 429
        code = (request.form.get('code') or '').strip()
        secret = session.get('mfa_setup_secret') or ''
        if session.get('mfa_setup_uid') != user.id or not secret:
            return jsonify(ok=False, msg='The setup session has expired. Please refresh the page and try again.'), 400
        verified, counter = mfa_utils.verify_totp(secret, code, 0)
        if not verified:
            return jsonify(ok=False, msg="The authenticator code is invalid. Make sure your phone's time is accurate")

        recovery_codes = mfa_utils.generate_recovery_codes()
        user.mfa_enabled = 1
        user.mfa_secret_enc = mfa_utils.encrypt_secret(secret)
        user.mfa_recovery_hashes = mfa_utils.hash_recovery_codes(recovery_codes)
        user.last_mfa_counter = counter
        session.pop('mfa_setup_secret', None)
        session.pop('mfa_setup_uid', None)

        if pending_mode:
            _establish_session(user, context.get('auth_method') or 'password', True)
            _mark_login(user)
            redirect_to = context['next_url']
        else:
            session['mfa_verified'] = True
            redirect_to = url_for('auth.account_security')
        sess.commit()
        audit.log_action('MFA Enabled', user.username, 'TOTP enabled and recovery codes generated',
                         username=user.username)
        return jsonify(ok=True, msg='MFA enabled. Store your recovery codes securely.',
                       recovery_codes=recovery_codes, redirect=redirect_to)
    except Exception:
        sess.rollback()
        logger.error('settings MFA Failed', exc_info=True)
        return jsonify(ok=False, msg='MFA setup failed. Please try again later.')
    finally:
        sess.close()


@bp.route('/logout', methods=['POST'])
def logout():
    """Sign Out (POST + CSRF, Avoid being forcibly logged out by third party pages). """
    audit.log_action('Sign Out', session.get('username', ''), 'The user voluntarily exits')
    session.clear()
    return redirect(url_for('auth.login'))


@bp.route('/change_password', methods=['GET'])
def change_password_page():
    """Password modification page (The first time you log in, you will be forced to jump here). """
    if not session.get('uid'):
        return redirect(url_for('auth.login'))
    from app.auth.permissions import ROLES
    return render_template('change_password.html',
                           forced=bool(session.get('must_change_password')),
                           role_name=ROLES.get(session.get('role'), session.get('role', '')))


@bp.route('/change_password', methods=['POST'])
def change_password():
    """Change Password. """
    if not session.get('uid'):
        return jsonify(ok=False, msg='Please sign in first')
    old = request.form.get('old_password') or ''
    new = request.form.get('new_password') or ''
    new2 = request.form.get('new_password2') or ''
    if not old or not new:
        return jsonify(ok=False, msg='Please complete all three fields.')
    pwd_error = security.password_error(new)
    if pwd_error:
        return jsonify(ok=False, msg=pwd_error)
    if new != new2:
        return jsonify(ok=False, msg='The new passwords do not match.')

    was_forced = bool(session.get('must_change_password'))
    sess = Session()
    try:
        user = _full_user(sess)
        if not user:
            return jsonify(ok=False, msg='Your session has expired. Please sign in again.'), 401
        if int(user.mfa_enabled or 0) and not session.get('mfa_verified'):
            return jsonify(ok=False, msg='Please complete MFA verification again.'), 403
        if not check_password_hash(user.password_hash, old):
            return jsonify(ok=False, msg='The current password is incorrect.')
        if check_password_hash(user.password_hash, new):
            return jsonify(ok=False, msg='The new password cannot be the same as the current password.')
        user.password_hash = generate_password_hash(new)
        user.must_change_password = 0
        user.session_version = int(user.session_version or 1) + 1
        sess.commit()
        _establish_session(user, session.get('auth_method') or 'password',
                           bool(session.get('mfa_verified')))
        session['must_change_password'] = 0
        session['session_version'] = int(user.session_version)
        audit.log_action('Change Password', user.username,
                         'The password has been modified successfully.%s' % (' (Forced decryption at first login)' if was_forced else ''))
        return jsonify(ok=True, msg='Password updated. Use the new password the next time you sign in.')
    except Exception:
        sess.rollback()
        return jsonify(ok=False, msg='Password change failed. Please try again later.')
    finally:
        sess.close()
