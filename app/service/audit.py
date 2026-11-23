# -*- coding: utf-8 -*-
"""
Audit log service for ethics and quality control.

In addition to regular operation records, each log entry is linked to the previous hash using an independent HMAC key.
Direct overwrites or deletions can be detected by ``verify_chain``.
"""
import datetime
import hashlib
import hmac
import json
import threading

from flask import has_request_context, request, session

import config
from app.db import Session
from app.models import AuditLog
from util_logger import get_logger

logger = get_logger(__name__)
_chain_lock = threading.RLock()
_GENESIS = 'GENESIS'


def _canonical(username, action, target, detail, ip, created_at) -> str:
    """Generate canonical JSON independent of database field order for HMAC calculation. """
    created = created_at.isoformat(timespec='microseconds') if created_at else ''
    return json.dumps([username or '', action or '', target or '', detail or '',
                       ip or '', created], ensure_ascii=False,
                      separators=(',', ':'), sort_keys=True)


def _entry_hash(prev_hash: str, username, action, target, detail, ip, created_at) -> str:
    payload = (prev_hash or _GENESIS) + '|' + _canonical(
        username, action, target, detail, ip, created_at)
    key = (config.AUDIT_HMAC_KEY or config.SECRET_KEY).encode('utf-8')
    return hmac.new(key, payload.encode('utf-8'), hashlib.sha256).hexdigest()


def _backfill_locked(sess) -> int:
    """Backfill only historical records that have not yet been hashed; do not overwrite existing hashes. """
    changed = 0
    prev_hash = _GENESIS
    rows = sess.query(AuditLog).order_by(AuditLog.id).all()
    for row in rows:
        expected = _entry_hash(prev_hash, row.username, row.action, row.target,
                               row.detail, row.ip, row.created_at)
        if not row.entry_hash:
            row.prev_hash = prev_hash
            row.entry_hash = expected
            changed += 1
        elif row.prev_hash != prev_hash or row.entry_hash != expected:
            logger.error('Audit hash chain break detected at record ID=%s; not overwriting automatically in order to preserve evidence', row.id)
        prev_hash = row.entry_hash or expected
    if changed:
        sess.commit()
    return changed


def backfill_audit_chain() -> int:
    """Backfill the historical audit log hash chain. This operation is idempotent. """
    with _chain_lock:
        sess = Session()
        try:
            return _backfill_locked(sess)
        except Exception:
            sess.rollback()
            logger.error('Failed to initialize the audit hash chain', exc_info=True)
            return 0
        finally:
            sess.close()


def log_action(action: str, target: str = '', detail: str = '', username: str = None) -> None:
    """
    Write an HMAC-chained audit record.

    :param action: Action type, such as Sign in, Data Import, Review, Unblinding, or Export
    :param target: Target
    :param detail: Details
    :param username: Operator (defaults to the current session user)
    """
    user = username
    ip = ''
    if has_request_context():
        if config.TRUST_PROXY:
            forwarded = (request.headers.get('X-Forwarded-For') or '').split(',')[0].strip()
        else:
            forwarded = ''
        user = user or session.get('username') or 'anonymous'
        ip = (forwarded or request.remote_addr or '')[:50]
    user = user or 'system'
    now = datetime.datetime.utcnow().replace(microsecond=0)

    with _chain_lock:
        sess = Session()
        try:
            # Initialization normally completes at application startup; this block is a safety net for legacy databases.
            last = sess.query(AuditLog).order_by(AuditLog.id.desc()).first()
            if last and not last.entry_hash:
                _backfill_locked(sess)
                last = sess.query(AuditLog).order_by(AuditLog.id.desc()).first()
            prev_hash = last.entry_hash if last and last.entry_hash else _GENESIS
            entry_hash = _entry_hash(prev_hash, user, action, target[:120],
                                     detail[:1000], ip, now)
            sess.add(AuditLog(username=user, action=action, target=target[:120],
                              detail=detail[:1000], ip=ip, created_at=now,
                              prev_hash=prev_hash, entry_hash=entry_hash))
            sess.commit()
        except Exception:
            sess.rollback()
            logger.warning('Audit log writing failed', exc_info=True)
        finally:
            sess.close()


def recent_logs(limit: int = 300, action: str = '') -> list:
    """Return recent audit records. """
    session = Session()
    try:
        query = session.query(AuditLog)
        if action:
            query = query.filter(AuditLog.action == action)
        rows = query.order_by(AuditLog.id.desc()).limit(max(1, min(1000, limit))).all()
        return [{
            'id': r.id, 'username': r.username, 'action': r.action,
            'target': r.target, 'detail': r.detail, 'ip': r.ip,
            'hash': (r.entry_hash or '')[:16],
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M:%S') if r.created_at else '',
        } for r in rows]
    finally:
        session.close()


def action_summary() -> list:
    """Statistics by operation type. """
    from collections import Counter
    session = Session()
    try:
        rows = session.query(AuditLog.action).all()
    finally:
        session.close()
    counter = Counter(r[0] for r in rows if r[0])
    return [{'name': k, 'value': v} for k, v in counter.most_common()]


def verify_chain() -> dict:
    """Validate the HMAC audit chain and return the position of any breakpoint. """
    session = Session()
    try:
        rows = session.query(AuditLog).order_by(AuditLog.id).all()
        prev_hash = _GENESIS
        for index, row in enumerate(rows, 1):
            expected = _entry_hash(prev_hash, row.username, row.action, row.target,
                                   row.detail, row.ip, row.created_at)
            if (row.prev_hash or _GENESIS) != prev_hash or row.entry_hash != expected:
                return {'valid': False, 'count': len(rows), 'checked': index,
                        'broken_id': row.id, 'reason': 'The hash chain is discontinuous or the record has been modified'}
            prev_hash = row.entry_hash
        return {'valid': True, 'count': len(rows), 'checked': len(rows),
                'broken_id': None, 'head': prev_hash}
    except Exception:
        logger.error('Audit chain verification failed', exc_info=True)
        return {'valid': False, 'count': 0, 'checked': 0,
                'broken_id': None, 'reason': 'Verification process failed'}
    finally:
        session.close()
