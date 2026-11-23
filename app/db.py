# -*- coding: utf-8 -*-
"""Database engine and session management (direct MySQL access). """
import os
import secrets

import pymysql
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

import config
from util_logger import get_logger

logger = get_logger(__name__)


def ensure_database() -> None:
    """Ensure the target MySQL database exists and is accessible to the app account."""
    if not config.DB_URL.startswith('mysql'):
        return
    try:
        check = pymysql.connect(**config.MYSQL_CONNECT, database=config.DB_NAME)
        try:
            with check.cursor() as cursor:
                cursor.execute('SELECT 1')
        finally:
            check.close()
        logger.info('MySQL database is ready: %s', config.DB_NAME)
        return
    except pymysql.err.OperationalError as exc:
        # MySQL uses 1049 for a missing database, but can return 1044 when the
        # application account has no privilege on that not-yet-created database.
        # Both cases require the administrative account to provision access.
        if not exc.args or exc.args[0] not in (1044, 1049):
            raise

    # Use the authenticated account name rather than assuming that DB_HOST
    # exactly matches the host part stored in MySQL's account table.
    app_connection = pymysql.connect(**config.MYSQL_CONNECT)
    try:
        with app_connection.cursor() as cursor:
            cursor.execute('SELECT CURRENT_USER()')
            app_account = cursor.fetchone()[0]
    finally:
        app_connection.close()

    app_user, app_host = app_account.rsplit('@', 1)
    database_identifier = '`%s`' % config.DB_NAME.replace('`', '``')
    app_user_literal = "'%s'" % app_user.replace('\\', '\\\\').replace("'", "\\'")
    app_host_literal = "'%s'" % app_host.replace('\\', '\\\\').replace("'", "\\'")

    con = pymysql.connect(**config.MYSQL_ADMIN_CONNECT)
    try:
        with con.cursor() as cursor:
            cursor.execute(
                'CREATE DATABASE IF NOT EXISTS `%s` DEFAULT CHARACTER SET utf8mb4 '
                'COLLATE utf8mb4_unicode_ci' % config.DB_NAME.replace('`', '``'))
            cursor.execute(
                'GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES '
                'ON %s.* TO %s@%s' % (database_identifier, app_user_literal, app_host_literal))
        con.commit()
        logger.info('MySQL database and application grants are ready: %s', config.DB_NAME)
    finally:
        con.close()


ensure_database()

engine = create_engine(config.DB_URL, future=True, pool_pre_ping=True, pool_recycle=3600)
Session = scoped_session(sessionmaker(bind=engine, future=True))


def _sqlalchemy_type(column) -> str:
    """Convert model column type to MySQL Column definition. """
    from sqlalchemy.dialects import mysql
    try:
        return column.type.compile(dialect=mysql.dialect())
    except Exception:
        return 'TEXT'


def ensure_schema() -> list:
    """
    Lightweight schema synchronization: Fill in the new columns in the existing table model.

    ``create_all`` Only missing tables will be created, Does not modify existing table structure;
    Here we compare the model to the actual columns of the database, Perform on the missing columns ADD COLUMN,
    Avoid rebuilding the database every time you add fields.

    :return: List of added columns ['table.column', ...]
    """
    from sqlalchemy import LargeBinary, Text, inspect, text
    from app import models

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    added = []
    with engine.begin() as conn:
        for table in models.Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            db_column_types = {c['name']: c['type'] for c in inspector.get_columns(table.name)}
            db_columns = set(db_column_types)
            for column in table.columns:
                if column.name in db_columns:
                    desired_length = getattr(column.type, 'length', None)
                    actual_length = getattr(db_column_types[column.name], 'length', None)
                    if desired_length and actual_length and desired_length > actual_length:
                        definition = _sqlalchemy_type(column)
                        definition += ' NULL' if column.nullable else ' NOT NULL'
                        ddl = ('ALTER TABLE `%s` MODIFY COLUMN `%s` %s'
                               % (table.name, column.name, definition))
                        conn.execute(text(ddl))
                        added.append('%s.%s(%d)' % (table.name, column.name, desired_length))
                        logger.info('The column length has been expanded: %s.%s -> %d',
                                    table.name, column.name, desired_length)
                    continue
                ddl = ('ALTER TABLE `%s` ADD COLUMN `%s` %s'
                       % (table.name, column.name, _sqlalchemy_type(column)))
                # MySQL Not allowed TEXT/BLOB Column: Ordinary DEFAULT, You can omit the old table when it is added;
                # ORM/The application layer still specifies null values as ''.
                if (column.default is not None
                        and not isinstance(column.type, (Text, LargeBinary))
                        and getattr(column.default, 'arg', None) is not None
                        and not callable(column.default.arg)):
                    ddl += " DEFAULT %s" % (repr(column.default.arg)
                                            if isinstance(column.default.arg, str)
                                            else column.default.arg)
                conn.execute(text(ddl))
                added.append('%s.%s' % (table.name, column.name))
                logger.info('The missing columns have been supplemented: %s.%s', table.name, column.name)
    return added


def init_db() -> None:
    """"Create a table, Add columns simultaneously, and make sure the default account exists. """
    from app import models
    models.Base.metadata.create_all(engine)
    try:
        added = ensure_schema()
        if added:
            logger.info('Schema synchronization completed: %d change(s)', len(added))
    except Exception:
        logger.warning('Table structure synchronization failed (The database can be manually rebuilt)', exc_info=True)
    logger.info('The data table check is completed (%s)', config.DB_NAME)
    ensure_default_user()
    try:
        from app.service import audit
        backfilled = audit.backfill_audit_chain()
        if backfilled:
            logger.info('The audit hash chain has been completed %d A historical record', backfilled)
    except Exception:
        logger.warning('Failed to initialize the audit hash chain', exc_info=True)


def ensure_default_user() -> None:
    """Make sure there is an admin account admin; The initial password is not hard-coded, Force First Login Modification. """
    from werkzeug.security import generate_password_hash

    import config
    from app.models import User

    session = Session()
    try:
        if not session.query(User).filter_by(username='admin').first():
            password = config.ADMIN_INITIAL_PASSWORD
            password_file = config.ADMIN_INITIAL_PASSWORD_FILE
            if not password:
                try:
                    if os.path.exists(password_file):
                        password = open(password_file, encoding='utf-8').read().strip()
                    if len(password) < 12:
                        password = 'Adm-%s9' % secrets.token_urlsafe(10)
                        os.makedirs(os.path.dirname(password_file), exist_ok=True)
                        with open(password_file, 'w', encoding='utf-8') as file:
                            file.write(password)
                except OSError:
                    password = 'Adm-%s9' % secrets.token_urlsafe(10)
            session.add(User(username='admin', nickname='Research Administrator',
                             password_hash=generate_password_hash(password),
                             role='admin', must_change_password=1))
            session.commit()
            logger.warning('An administrator account has been created admin; The initial password is saved in %s, First login must be modified',
                           password_file)
    finally:
        session.close()
