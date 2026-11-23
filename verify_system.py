# -*- coding: utf-8 -*-
"""Prospect Theory Edition research platform regression acceptance tests. """
import sys

from werkzeug.security import generate_password_hash

from app import create_app
from app.db import Session
from app.models import User

PAGES = ['/', '/about', '/subjects', '/intention', '/scenarios', '/biases', '/risk',
         '/psychometrics', '/constructs', '/mechanism', '/sem', '/probit', '/forest',
         '/import', '/qc', '/audit', '/datadict', '/report', '/users']
APIS = ['/api/overview', '/api/subjects', '/api/scenarios', '/api/biases', '/api/risk',
        '/api/constructs', '/api/mechanism', '/api/sem', '/api/probit', '/api/forest',
        '/api/psychometrics', '/api/qc', '/api/audit', '/api/datadict', '/api/users',
        '/api/outputs', '/api/import/template']


def main():
    app = create_app()
    username = 'prospect_verify_admin'; password = 'Prospect-Verify-2026'
    sess = Session()
    try:
        user = sess.query(User).filter_by(username=username).first()
        if not user:
            user = User(username=username, nickname='Regression acceptance', role='admin', status='active',
                        password_hash=generate_password_hash(password), must_change_password=0)
            sess.add(user)
        else:
            user.password_hash = generate_password_hash(password)
            user.role = 'admin'; user.status = 'active'; user.must_change_password = 0
        sess.commit()
    finally:
        sess.close()
    client = app.test_client(); checks = []
    def check(name, condition, detail=''):
        checks.append(bool(condition)); print(('PASS' if condition else 'FAIL'), name, detail)
    client.get('/login')
    with client.session_transaction() as session:
        token = session.get('_csrf_token')
    denied = client.post('/api/import/execute', data={}, headers={'X-CSRF-Token': token, 'Accept': 'application/json'})
    check('CSRF and auth guard', denied.status_code in (400, 401))
    logged = client.post('/login', data={'username': username, 'password': password},
                         headers={'X-CSRF-Token': token, 'Accept': 'application/json'})
    check('login', logged.status_code == 200 and logged.get_json().get('ok'))
    for path in PAGES:
        response = client.get(path)
        check('page ' + path, response.status_code == 200, str(response.status_code))
    for path in APIS:
        response = client.get(path)
        check('api ' + path, response.status_code == 200, str(response.status_code))
    sess = Session()
    try:
        user = sess.query(User).filter_by(username=username).first()
        if user:
            sess.delete(user); sess.commit()
    finally:
        sess.close()
    failed = sum(1 for value in checks if not value)
    print('\nPROSPECT PLATFORM CHECKS:', 'ALL PASSED' if not failed else 'FAILED %d' % failed)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())