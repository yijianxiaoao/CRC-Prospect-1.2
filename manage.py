# -*- coding: utf-8 -*-
"""Database and demonstration-data management commands. """
import secrets
import sys
from pathlib import Path

from app import create_app
from app.db import Session, engine, init_db
import config


def do_init():
    app = create_app()
    print('Database initialization complete:', config.DB_NAME)


def do_seed():
    from app.service.seed import generate_cohort
    print('Generate simulated study cohort:', generate_cohort(config.DEFAULT_N))


def do_reseed():
    from app.service.seed import generate_cohort
    print('Rebuild simulated study cohort:', generate_cohort(config.DEFAULT_N, reset=True))


def do_status():
    from app.models import (AuditLog, DataLock, DiseaseCognition, HealthLiteracyItem,
                            ProspectConstruct, ScenarioResponse, ScreeningDecision,
                            SelfEfficacyItem, Subject, User)
    sess = Session()
    try:
        for model in (User, Subject, ScreeningDecision, DiseaseCognition, ScenarioResponse,
                      HealthLiteracyItem, SelfEfficacyItem, ProspectConstruct, DataLock, AuditLog):
            print('%-24s %8d' % (model.__tablename__, sess.query(model).count()))
    finally:
        sess.close()


def do_reset_admin():
    from werkzeug.security import generate_password_hash
    from app.models import User
    password = 'Adm-' + secrets.token_urlsafe(12) + '9'
    sess = Session()
    try:
        admin = sess.query(User).filter_by(username='admin').first()
        if not admin:
            raise RuntimeError('Admin account not found')
        admin.password_hash = generate_password_hash(password)
        admin.must_change_password = 1
        admin.session_version = int(admin.session_version or 1) + 1
        sess.commit()
        Path(config.ADMIN_INITIAL_PASSWORD_FILE).write_text(password, encoding='utf-8')
        print('Administrator password reset; file:', config.ADMIN_INITIAL_PASSWORD_FILE)
    finally:
        sess.close()


def do_verify():
    from verify_system import main as verify_main
    raise SystemExit(verify_main())


COMMANDS = {'init': do_init, 'seed': do_seed, 'reseed': do_reseed,
            'status': do_status, 'reset_admin': do_reset_admin, 'verify': do_verify}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print('Available commands:', ', '.join(COMMANDS))
        return
    COMMANDS[sys.argv[1]]()


if __name__ == '__main__':
    main()
