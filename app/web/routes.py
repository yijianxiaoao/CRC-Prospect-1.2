# -*- coding: utf-8 -*-
"""Prospect Theoretical Edition Colorectal Cancer Screening Research Platform Page vs. API. """
import datetime
import io
import json

from flask import Response, jsonify, redirect, render_template, request, send_file, session, url_for
from sqlalchemy import func

import config
from app.auth.permissions import check_password_change_required, role_required
from app.auth.security import rate_limit
from app.db import Session
from app.models import (AuditLog, DataLock, DiseaseCognition, HealthLiteracyItem,
                        ProspectConstruct, ScenarioResponse, ScreeningDecision,
                        SelfEfficacyItem, Subject, User)
from app.service import analysis, audit, cache, importer, psychometrics
from app.web import bp
from util_logger import get_logger

logger = get_logger(__name__)


@bp.before_request
def require_login():
    if not session.get('uid'):
        if request.path.startswith('/api/'):
            return jsonify(ok=False, code='UNAUTHORIZED', msg='Please sign in first.'), 401
        return redirect(url_for('auth.login', next=request.path))
    mfa_enabled = False
    sess = Session()
    try:
        user = sess.get(User, session.get('uid'))
        if (not user or (user.status or 'active') != 'active'
                or int(session.get('session_version', 0)) != int(user.session_version or 1)):
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify(ok=False, code='SESSION_EXPIRED', msg='Your session has expired. Please sign in again.'), 401
            return redirect(url_for('auth.login', next=request.path))
        session['role'] = user.role or 'viewer'
        session['must_change_password'] = int(user.must_change_password or 0)
        mfa_enabled = bool(int(user.mfa_enabled or 0))
    finally:
        sess.close()
    if config.MFA_ENABLED and mfa_enabled and not session.get('mfa_verified'):
        session.clear()
        return redirect(url_for('auth.login', next=request.path))
    if check_password_change_required():
        if request.path.startswith('/api/'):
            return jsonify(ok=False, code='PASSWORD_CHANGE_REQUIRED', msg='Please change your initial password first.'), 403
        return redirect(url_for('auth.change_password_page'))
    return None


# "Page ---------------------------------------------------------------------

@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/about')
def about():
    return render_template('about.html')


@bp.route('/subjects')
def subjects_page():
    return render_template('subjects.html')


@bp.route('/intention')
def intention_page():
    return render_template('intention.html')


@bp.route('/scenarios')
def scenarios_page():
    return render_template('scenarios.html')


@bp.route('/biases')
def biases_page():
    return render_template('biases.html')


@bp.route('/risk')
def risk_page():
    return render_template('risk.html')


@bp.route('/psychometrics')
def psychometrics_page():
    return render_template('psychometrics.html')


@bp.route('/constructs')
def constructs_page():
    return render_template('constructs.html')


@bp.route('/mechanism')
def mechanism_page():
    return render_template('mechanism.html')


@bp.route('/sem')
def sem_page():
    return render_template('sem.html')


@bp.route('/probit')
def probit_page():
    return render_template('probit.html')


@bp.route('/forest')
def forest_page():
    return render_template('forest.html')


@bp.route('/import')
def import_page():
    return render_template('import.html')


@bp.route('/qc')
def qc_page():
    return render_template('qc.html')


@bp.route('/audit')
@role_required('admin')
def audit_page():
    return render_template('audit.html')


@bp.route('/datadict')
def datadict_page():
    return render_template('datadict.html')


@bp.route('/report')
def report_page():
    return render_template('report.html')


@bp.route('/users')
@role_required('admin')
def users_page():
    return render_template('users.html')


# API ----------------------------------------------------------------------

@bp.route('/api/overview')
def api_overview():
    return jsonify(cache.get_or_set('dashboard:overview', 120, lambda: {
        'kpis': analysis.kpis(),
        'baseline': analysis.baseline_distribution(),
        'risk_sources': analysis.risk_source_distribution(),
        'intention': analysis.intention_distribution(),
        'outcomes': analysis.screening_outcome_distribution(),
        'barriers': analysis.barrier_analysis(),
    }))


@bp.route('/api/subjects')
def api_subjects():
    return jsonify(cache.get_or_set('dashboard:subjects', 180, lambda: {
        'baseline': analysis.baseline_distribution(),
        'rows': analysis.subject_rows(500),
    }))


@bp.route('/api/scenarios')
def api_scenarios():
    return jsonify(cache.get_or_set('analytics:scenarios', 300, lambda: {
        'items': analysis.scenario_item_distribution(),
        'biases': analysis.bias_summary(),
        'risk': analysis.risk_preference_summary(),
    }))


@bp.route('/api/biases')
def api_biases():
    return jsonify(cache.get_or_set('analytics:biases', 300, lambda: {
        'biases': analysis.bias_summary(),
        'items': analysis.scenario_item_distribution(),
        'correlation': analysis.correlation_matrix(),
    }))


@bp.route('/api/risk')
def api_risk():
    return jsonify(cache.get_or_set('analytics:risk', 300, lambda: {
        'summary': analysis.risk_preference_summary(),
        'items': analysis.scenario_item_distribution(),
        'correlation': analysis.correlation_matrix(),
    }))


@bp.route('/api/constructs')
def api_constructs():
    return jsonify(cache.get_or_set('analytics:constructs', 300, lambda: {
        'rows': analysis.construct_summary(),
        'correlation': analysis.correlation_matrix(),
    }))


@bp.route('/api/mechanism')
def api_mechanism():
    return jsonify(cache.get_or_set('analytics:mechanism', 300, lambda: {
        'path': analysis.path_model(),
        'mediation': analysis.mediation_summary(),
        'constructs': analysis.construct_summary(),
    }))


@bp.route('/api/sem')
@rate_limit(10, 60)
def api_sem():
    return jsonify(cache.get_or_set('analytics:sem', 600, analysis.sem_model))


@bp.route('/api/probit')
@rate_limit(10, 60)
def api_probit():
    return jsonify(cache.get_or_set('analytics:probit', 300, analysis.probit_analysis))


@bp.route('/api/forest')
@rate_limit(5, 60)
def api_forest():
    return jsonify(cache.get_or_set('analytics:forest', 300, lambda: {
        'main': analysis.univariate_vs_multivariate(),
        'subgroup': analysis.subgroup_analysis('anchoring_adjustment'),
        'subgroup_exposure': 'Anchoring and adjustment bias',
    }))
@bp.route('/api/psychometrics')
@rate_limit(10, 60)
def api_psychometrics():
    return jsonify(cache.get_or_set('analytics:psychometrics', 600, lambda: {
        'reliability': psychometrics.reliability_report(),
        'validity': psychometrics.validity_report(),
        'constructs': psychometrics.construct_reliability(),
    }))


@bp.route('/api/qc')
def api_qc():
    """Questionnaire review, Integrity and Basic Quality Control Summary. """
    sess = Session()
    try:
        total = sess.query(Subject).count()
        status = {row[0]: int(row[1]) for row in sess.query(
            Subject.review_status, func.count(Subject.id)).group_by(Subject.review_status).all()}
        counts = {
            'subject': total,
            'decision': sess.query(ScreeningDecision).count(),
            'cognition': sess.query(DiseaseCognition).count(),
            'scenario': sess.query(ScenarioResponse).count(),
            'construct': sess.query(ProspectConstruct).count(),
            'health_literacy': sess.query(HealthLiteracyItem).count(),
            'self_efficacy': sess.query(SelfEfficacyItem).count(),
        }
    finally:
        sess.close()
    return jsonify({'counts': counts, 'review_status': status,
                    'complete': total > 0 and all(counts[k] >= total for k in ('decision', 'cognition', 'scenario', 'construct')),
                    'note': 'Name, National ID number, Fields such as contact details are rejected at the import stage, Do not enter the research database. '})


def _model_dict(model):
    notes = {
        't_subject': 'De-identified Study Participants and General Information',
        't_screening_decision': 'screening willingness, Past Screening Experience and Final Behavior',
        't_disease_cognition': 'Disease cognition, Health value, Mental Accounts and Decision Reference Points',
        't_scenario_response': '22 Dao Prospect Theory Situational Experiments and Derived Dimensions',
        't_health_literacy': 'Concise Health Literacy Scale Entry',
        't_self_efficacy': 'General Self-Efficacy Scale Entry',
        't_prospect_construct': 'SEM, Probit Summary of latent variables used by and forest plots',
        't_audit': 'Tamper-evident audit log',
    }
    fields = []
    for col in model.__table__.columns:
        fields.append({'name': col.name, 'type': str(col.type), 'nullable': bool(col.nullable), 'note': ''})
    return {'table': model.__tablename__, 'label': notes.get(model.__tablename__, model.__tablename__),
            'fields': fields}


@bp.route('/api/datadict')
def api_datadict():
    models = [Subject, ScreeningDecision, DiseaseCognition, ScenarioResponse,
              HealthLiteracyItem, SelfEfficacyItem, ProspectConstruct, AuditLog]
    return jsonify({'tables': [_model_dict(m) for m in models],
                    'constructs': [{'key': k, 'name': v} for k, v in config.PROSPECT_CONSTRUCTS]})


@bp.route('/api/audit')
@role_required('admin')
def api_audit():
    action = request.args.get('action', '').strip()
    return jsonify({'items': audit.recent_logs(300, action),
                    'summary': audit.action_summary(), 'chain': audit.verify_chain()})


@bp.route('/api/datalock', methods=['GET', 'POST'])
@role_required('admin')
def api_datalock():
    sess = Session()
    try:
        row = sess.query(DataLock).order_by(DataLock.id.desc()).first()
        if request.method == 'GET':
            return jsonify({'locked': bool(row and row.locked), 'note': row.note if row else '',
                            'locked_by': row.locked_by if row else '', 'locked_at': row.locked_at.strftime('%Y-%m-%d %H:%M') if row and row.locked_at else ''})
        locked = (request.form.get('locked') or '').lower() in ('1', 'true', 'yes')
        reason = (request.form.get('reason') or '').strip()
        if not reason:
            return jsonify(ok=False, msg='Please provide a reason for locking or unlocking the data.')
        if not row:
            row = DataLock(); sess.add(row)
        row.locked = int(locked); row.locked_by = session.get('username') or ''
        row.locked_at = datetime.datetime.utcnow(); row.note = reason[:200]
        row.subject_count = sess.query(Subject).count()
        sess.commit()
        audit.log_action('Data lock' if locked else 'Unlock data', 'Research data', reason)
        return jsonify(ok=True, msg='Data locked.' if locked else 'Data unlocked.')
    finally:
        sess.close()


@bp.route('/api/users')
@role_required('admin')
def api_users():
    from app.auth.permissions import ROLES
    sess = Session()
    try:
        rows = sess.query(User).order_by(User.id).all()
        return jsonify({'items': [{
            'id': u.id, 'username': u.username, 'nickname': u.nickname or u.username,
            'role': u.role or 'viewer', 'status': u.status or 'active',
            'must_change_password': bool(u.must_change_password),
            'mfa_enabled': bool(int(u.mfa_enabled or 0)),
            'auth_source': u.auth_source or 'local', 'sso_linked': bool(u.sso_subject),
            'approved_by': u.approved_by or '', 'approved_at': u.approved_at.strftime('%Y-%m-%d %H:%M') if u.approved_at else '',
            'created_at': u.created_at.strftime('%Y-%m-%d %H:%M') if u.created_at else ''} for u in rows],
            'roles': ROLES, 'pending_count': sum(1 for u in rows if (u.status or 'active') == 'pending')})
    finally:
        sess.close()


@bp.route('/api/users/<int:user_id>/role', methods=['POST'])
@role_required('admin')
def api_user_role(user_id):
    from app.auth.permissions import ROLES
    role = (request.form.get('role') or '').strip()
    if role not in ROLES:
        return jsonify(ok=False, msg='Invalid role.')
    sess = Session()
    try:
        user = sess.get(User, user_id)
        if not user:
            return jsonify(ok=False, msg='Account not found.'), 404
        if user.username == 'admin' and role != 'admin':
            return jsonify(ok=False, msg='The built-in administrator account cannot be downgraded.')
        user.role = role; sess.commit()
        audit.log_action('Role change', user.username, 'Adjust to %s' % role)
        return jsonify(ok=True, msg='Role updated.')
    finally:
        sess.close()


@bp.route('/api/users/<int:user_id>/status', methods=['POST'])
@role_required('admin')
def api_user_status(user_id):
    status = (request.form.get('status') or '').strip()
    if status not in ('active', 'pending', 'suspended'):
        return jsonify(ok=False, msg='Invalid account status.')
    sess = Session()
    try:
        user = sess.get(User, user_id)
        if not user:
            return jsonify(ok=False, msg='Account not found.'), 404
        if user.username == 'admin' and status != 'active':
            return jsonify(ok=False, msg='The built-in administrator account cannot be deactivated.')
        if user.id == session.get('uid') and status != 'active':
            return jsonify(ok=False, msg='You cannot deactivate your current account.')
        user.status = status
        if status != 'active':
            user.session_version = int(user.session_version or 1) + 1
        else:
            user.approved_by = session.get('username') or 'admin'
            user.approved_at = datetime.datetime.utcnow()
        sess.commit()
        audit.log_action('Account status adjustment', user.username, 'Status updated to %s' % status)
        return jsonify(ok=True, msg='Account status updated.')
    finally:
        sess.close()


@bp.route('/api/users/<int:user_id>/reset_password', methods=['POST'])
@role_required('admin')
def api_user_reset_password(user_id):
    import secrets
    from werkzeug.security import generate_password_hash
    from app.auth.security import password_error
    temp = (request.form.get('temp_password') or '').strip() or ('Tmp-%s9' % secrets.token_urlsafe(6))
    error = password_error(temp)
    if error:
        return jsonify(ok=False, msg=error)
    sess = Session()
    try:
        user = sess.get(User, user_id)
        if not user:
            return jsonify(ok=False, msg='Account not found.'), 404
        user.password_hash = generate_password_hash(temp)
        user.must_change_password = 1
        user.session_version = int(user.session_version or 1) + 1
        sess.commit()
        audit.log_action('Reset password', user.username, 'Admin Generated Temporary Password')
        return jsonify(ok=True, msg='Temporary password generated. It will be shown only once.', temporary_password=temp)
    finally:
        sess.close()


@bp.route('/api/users/<int:user_id>/reset_mfa', methods=['POST'])
@role_required('admin')
def api_user_reset_mfa(user_id):
    sess = Session()
    try:
        user = sess.get(User, user_id)
        if not user:
            return jsonify(ok=False, msg='Account not found.'), 404
        user.mfa_enabled = 0; user.mfa_secret_enc = ''; user.mfa_recovery_hashes = ''
        user.last_mfa_counter = 0; user.session_version = int(user.session_version or 1) + 1
        sess.commit()
        audit.log_action('Reset MFA', user.username, 'Administrator cleared TOTP Configuration')
        return jsonify(ok=True, msg='MFA reset.')
    finally:
        sess.close()


@bp.route('/api/import/template')
def api_import_template():
    output = importer.template_bytes()
    return send_file(output, as_attachment=True, download_name='Prospect Theory Screening Data Import Template.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@bp.route('/api/import/preview', methods=['POST'])
@role_required('researcher')
def api_import_preview():
    file = request.files.get('file')
    if not file:
        return jsonify(ok=False, msg='Please select a file.')
    try:
        return jsonify(importer.preview(file))
    except Exception as exc:
        return jsonify(ok=False, msg=str(exc)), 400


@bp.route('/api/import/execute', methods=['POST'])
@role_required('researcher')
@rate_limit(20, 60)
def api_import_execute():
    file = request.files.get('file')
    if not file:
        return jsonify(ok=False, msg='Please select a file.')
    try:
        result = importer.execute_import(file)
        if result.get('ok'):
            cache.invalidate()
            audit.log_action('Data import', file.filename, '%d records imported, %d failed' % (result['success'], result['failed_count']))
        return jsonify(result), (200 if result.get('ok') else 400)
    except Exception:
        logger.error('Import failed', exc_info=True)
        return jsonify(ok=False, msg='Import failed. Please check the file format and fields.'), 500


@bp.route('/api/report/export')
def api_report_export():
    summary = cache.get_or_set('report:summary', 300, analysis.report_summary)
    fmt = (request.args.get('format') or 'html').lower()
    if fmt == 'excel':
        import pandas as pd
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pd.DataFrame([summary.get('kpis', {})]).T.reset_index().rename(columns={'index': 'Indicator', 0: 'value'}).to_excel(writer, index=False, sheet_name='Key indicators')
            pd.DataFrame(summary.get('constructs', [])).to_excel(writer, index=False, sheet_name='Summary of constructs')
            pd.DataFrame(summary.get('biases', [])).to_excel(writer, index=False, sheet_name='Bias effect')
        output.seek(0)
        return send_file(output, as_attachment=True, download_name='Research Report on Prospective Theoretical Screening Mechanism.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    return render_template('report_print.html', summary=summary,
                           generated_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))


@bp.route('/api/outputs')
def api_outputs():
    from app.models import ResearchOutput
    sess = Session()
    try:
        rows = sess.query(ResearchOutput).order_by(ResearchOutput.year.desc()).all()
        return jsonify({'items': [{'title': r.title, 'authors': r.authors, 'source': r.source,
                                   'year': r.year, 'kind': r.kind, 'url': r.url, 'summary': r.summary} for r in rows]})
    finally:
        sess.close()
