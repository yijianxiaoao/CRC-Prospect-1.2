# -*- coding: utf-8 -*-
"""Security regression acceptance tests: CSRF, Registration switch, MFA, Account approval, Session failure, Speed limit, Audit chain, Backup. """
import sys

import pyotp
from werkzeug.security import generate_password_hash

import config
from app import create_app
from app.auth import mfa
from app.auth.routes import _safe_next
from app.db import Session
from app.models import User
from app.service import audit, backup_crypto


def csrf(client):
    client.get('/login')
    with client.session_transaction() as session:
        return session.get('_csrf_token')


def login(client, username, password):
    token = csrf(client)
    return client.post('/login', data={'username': username, 'password': password},
                       headers={'X-CSRF-Token': token, 'Accept': 'application/json'})


def main():
    app = create_app()
    checks = []

    def check(name, condition, detail=''):
        checks.append((name, bool(condition), detail))
        print(('PASS' if condition else 'FAIL'), name, detail)

    # 1) Safety response head
    response = app.test_client().get('/healthz')
    check('security headers', response.headers.get('X-Content-Type-Options') == 'nosniff'
          and response.headers.get('X-Frame-Options') == 'DENY'
          and response.headers.get('Strict-Transport-Security')
          and 'default-src' in response.headers.get('Content-Security-Policy', ''))

    # 2) CSRF
    response = app.test_client().post('/register', data={})
    check('csrf rejection', response.status_code == 400)

    # 3) Self-registration closure policy fail-closed
    disabled_client = app.test_client()
    token = csrf(disabled_client)
    registration_was_enabled = config.REGISTRATION_ENABLED
    config.REGISTRATION_ENABLED = False
    try:
        disabled_page = disabled_client.get('/login').get_data(as_text=True)
        disabled = disabled_client.post('/register', data={
            'username': 'security_disabled', 'password': 'Security-Disabled-2026',
            'password2': 'Security-Disabled-2026'},
            headers={'X-CSRF-Token': token, 'Accept': 'application/json'})
    finally:
        config.REGISTRATION_ENABLED = registration_was_enabled
    check('registration switch enforced',
          disabled.status_code == 403 and 'id="tabReg"' not in disabled_page)

    # 4) TOTP Generate, Verification and anti-replay
    secret = mfa.generate_secret()
    totp_code = pyotp.TOTP(secret).now()
    verified, counter = mfa.verify_totp(secret, totp_code, 0)
    replayed, _ = mfa.verify_totp(secret, totp_code, counter)
    recovery_codes = mfa.generate_recovery_codes(4)
    recovery_hashes = mfa.hash_recovery_codes(recovery_codes)
    recovery_ok, remaining_hashes = mfa.verify_recovery_code(
        recovery_hashes, recovery_codes[0])
    recovery_replay, _ = mfa.verify_recovery_code(remaining_hashes, recovery_codes[0])
    check('mfa totp and recovery codes',
          verified and not replayed and recovery_ok and not recovery_replay)

    # 5) Open Redirection
    with app.test_request_context('/login?next=/%5Cevil.com'):
        check('open redirect blocked', _safe_next() == '/')

    # 6) Audit Chain and Encrypted Backup Foundational Capabilities
    chain = audit.verify_chain()
    check('audit hash chain', chain.get('valid') is True, str(chain))
    sample = 'sensitive-backup-sample'.encode('utf-8')
    check('encrypted backup roundtrip', backup_crypto.decrypt_bytes(
        backup_crypto.encrypt_bytes(sample)) == sample)

    # 7) After registration pending, Administrator approval, Disabling disables the old session
    session = Session()
    try:
        admin = session.query(User).filter_by(username='security_admin').first()
        if not admin:
            admin = User(username='security_admin', nickname='Safe return', role='admin',
                         status='active', password_hash=generate_password_hash('Security-Admin-2026'),
                         must_change_password=0)
            session.add(admin)
            session.commit()
    finally:
        session.close()

    pending_client = app.test_client()
    token = csrf(pending_client)
    registered = pending_client.post('/register', data={
        'username': 'security_pending', 'nickname': 'Pending review',
        'password': 'Security-User-2026', 'password2': 'Security-User-2026'},
        headers={'X-CSRF-Token': token, 'Accept': 'application/json'})
    check('registration accepted', registered.status_code == 200 and registered.get_json().get('ok'))
    session = Session()
    pending = session.query(User).filter_by(username='security_pending').first()
    check('new account pending', pending is not None and pending.status == 'pending')
    pending_id = pending.id if pending else None
    session.close()

    denied = login(app.test_client(), 'security_pending', 'Security-User-2026')
    check('pending login denied', denied.status_code == 403)

    admin_client = app.test_client()
    logged = login(admin_client, 'security_admin', 'Security-Admin-2026')
    check('temporary admin login', logged.get_json().get('ok'))
    token = csrf(admin_client)
    approved = admin_client.post('/api/users/%d/status' % pending_id,
                                 data={'status': 'active'},
                                 headers={'X-CSRF-Token': token, 'Accept': 'application/json'})
    check('admin approval', approved.get_json().get('ok'))
    user_client = app.test_client()
    approved_login = login(user_client, 'security_pending', 'Security-User-2026')
    check('approved login', approved_login.get_json().get('ok'))
    token = csrf(admin_client)
    suspended = admin_client.post('/api/users/%d/status' % pending_id,
                                  data={'status': 'suspended'},
                                  headers={'X-CSRF-Token': token, 'Accept': 'application/json'})
    check('admin suspend', suspended.get_json().get('ok'))
    check('old session invalidated', user_client.get('/api/overview').status_code == 401)

    # 8) Write-endpoint rate limit: the 21st request should return 429 without writing to the database
    researcher = Session()
    try:
        user = researcher.query(User).filter_by(username='security_researcher').first()
        if not user:
            user = User(username='security_researcher', nickname='Speed-limited return', role='researcher',
                        status='active', password_hash=generate_password_hash('Security-Researcher-2026'),
                        must_change_password=0)
            researcher.add(user)
            researcher.commit()
    finally:
        researcher.close()
    limited = app.test_client()
    login(limited, 'security_researcher', 'Security-Researcher-2026')
    token = csrf(limited)
    statuses = []
    for _ in range(21):
        response = limited.post('/api/import/execute', data={},
                                headers={'X-CSRF-Token': token, 'Accept': 'application/json'})
        statuses.append(response.status_code)
    check('heavy endpoint rate limit', statuses[-1] == 429, str(statuses[-3:]))

    # cleanup
    session = Session()
    try:
        session.query(User).filter(User.username.in_(
            ['security_admin', 'security_pending', 'security_researcher'])).delete(
                synchronize_session=False)
        session.commit()
    finally:
        session.close()

    failed = [name for name, ok, _ in checks if not ok]
    print('\nSECURITY CHECKS:', 'ALL PASSED' if not failed else 'FAILED ' + ', '.join(failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
