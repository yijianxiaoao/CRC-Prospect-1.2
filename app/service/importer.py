# -*- coding: utf-8 -*-
"""Questionnaire Data Import: CSV/XLSX, De-identification and line-by-line transactions. """
import io
import re

import numpy as np
import pandas as pd
from sqlalchemy.exc import IntegrityError

import config
from app.db import Session
from app.models import (DiseaseCognition, HealthLiteracyItem, ProspectConstruct,
                        ScenarioResponse, ScreeningDecision, SelfEfficacyItem, Subject)

PII_COLUMNS = {'Name', 'name', 'National ID number', 'id_card', 'Mobile phone number', 'phone', 'Contact information', 'contact', 'Address', 'address'}
CANONICAL = {
    'Study ID': 'subject_code', 'subject_code': 'subject_code', 'high-risk source': 'high_risk_source',
    'Age': 'age', 'age': 'age', 'Sex': 'gender', 'gender': 'gender',
    'Education level': 'education', 'Educational background': 'education', 'education': 'education',
    'Marital status': 'marital', 'marital': 'marital', 'Medical insurance': 'insurance', 'insurance': 'insurance',
    'Family history': 'family_crc', 'family_crc': 'family_crc', 'Chronic disease': 'chronic_disease',
    'Do you want to have a colonoscopy': 'intention_6m', 'intention_6m': 'intention_6m',
    'Has the colonoscopy been completed': 'actual_participated', 'actual_participated': 'actual_participated',
    'Disease cognition': 'disease_knowledge', 'disease_cognition': 'disease_knowledge',
    'Health literacy': 'health_literacy', 'health_literacy': 'health_literacy',
    'Self-efficacy': 'self_efficacy', 'self_efficacy': 'self_efficacy',
    'Representativeness bias': 'representative_bias', 'representative_bias': 'representative_bias',
    'Availability bias': 'availability_bias', 'availability_bias': 'availability_bias',
    'Anchoring and adjustment bias': 'anchoring_adjustment', 'anchoring_adjustment': 'anchoring_adjustment',
    'Certainty effect': 'certainty_effect', 'certainty_effect': 'certainty_effect',
    'Reflection effect': 'reflection_effect', 'reflection_effect': 'reflection_effect',
    'Isolation effect': 'isolation_effect', 'isolation_effect': 'isolation_effect',
}

BOOL_MAP = {'is': 1, 'have': 1, 'Intends to undergo': 1, 'Screened': 1, 'Completed': 1, 'yes': 1, 'true': 1, '1': 1,
            'no': 0, 'no': 0, 'Does not intend to undergo': 0, 'Not screened': 0, 'no': 0, 'false': 0, '0': 0}


def _read(file_storage):
    name = (file_storage.filename or '').lower()
    data = file_storage.read()
    if name.endswith('.csv'):
        for encoding in ('utf-8-sig', 'utf-8', 'gbk'):
            try:
                return pd.read_csv(io.BytesIO(data), encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError('CSV encoding could not be detected.')
    if name.endswith(('.xlsx', '.xls')):
        return pd.read_excel(io.BytesIO(data))
    raise ValueError('Only CSV and XLSX files are supported.')


def preview(file_storage):
    df = _read(file_storage)
    normalized = [CANONICAL.get(str(c).strip(), str(c).strip()) for c in df.columns]
    rejected = sorted(set(normalized) & PII_COLUMNS)
    return {'ok': not rejected, 'columns': list(df.columns), 'normalized': normalized,
            'rows': df.head(20).fillna('').to_dict(orient='records'),
            'total': int(len(df)), 'rejected_pii': rejected}


def _bool(value, default=0):
    if pd.isna(value):
        return default
    if isinstance(value, (int, float, np.integer, np.floating)):
        return int(value) != 0
    return BOOL_MAP.get(str(value).strip().lower(), default)


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def template_bytes():
    columns = ['subject_code', 'high_risk_source', 'age', 'gender', 'education', 'marital', 'insurance',
               'family_crc', 'chronic_disease', 'intention_6m', 'actual_participated', 'disease_cognition',
               'health_literacy', 'self_efficacy', 'representative_bias', 'availability_bias',
               'anchoring_adjustment', 'certainty_effect', 'reflection_effect', 'isolation_effect']
    sample = [['PTS-00001', 'Questionnaire-positive', 58, 'Female', 'Junior high school', 'Married', 'Urban and Rural Residents Basic Medical Insurance',
               0, 1, 'Intends to undergo', 'Not screened', 3.2, 3.8, 2.6, 0.25, 0.35, 0.42, 0.55, 0.30, 0.20]]
    df = pd.DataFrame(sample, columns=columns)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data template')
    output.seek(0)
    return output


def execute_import(file_storage, mapping=None):
    df = _read(file_storage)
    df = df.rename(columns={c: CANONICAL.get(str(c).strip(), str(c).strip()) for c in df.columns})
    rejected = sorted(set(df.columns) & PII_COLUMNS)
    if rejected:
        return {'ok': False, 'error': 'Direct identifiers detected in columns: %s. Remove these columns before importing.' % ', '.join(rejected)}
    required = {'subject_code', 'age', 'gender', 'intention_6m', 'actual_participated'}
    missing = required - set(df.columns)
    if missing:
        return {'ok': False, 'error': 'Missing required fields: %s' % ', '.join(sorted(missing))}
    session = Session(); success = 0; failed = []; created_ids = []
    try:
        for index, row in df.iterrows():
            code = str(row.get('subject_code') or '').strip()
            if not code:
                failed.append({'row': int(index + 2), 'error': 'Study ID is blank.'}); continue
            if session.query(Subject).filter_by(subject_code=code).first():
                failed.append({'row': int(index + 2), 'error': 'Study ID already exists'}); continue
            try:
                with session.begin_nested():
                    age = _int(row.get('age'), 0)
                    gender = str(row.get('gender') or '').strip()
                    if not (40 <= age <= 75) or gender not in ('Male', 'Female'):
                        raise ValueError('Age or sex does not meet the inclusion criteria.')
                    subject = Subject(
                        subject_code=code, high_risk_source=str(row.get('high_risk_source') or 'Questionnaire-positive'),
                        city=str(row.get('city') or ''), district=str(row.get('district') or ''),
                        community=str(row.get('community') or ''), age=age,
                        age_group=('40-49age' if age < 50 else '50-59age' if age < 60 else '60-69age' if age < 70 else '70-75age'),
                        gender=gender, education=str(row.get('education') or ''),
                        education_years=_float(row.get('education_years'), 9), marital=str(row.get('marital') or ''),
                        insurance=str(row.get('insurance') or ''), family_crc=_bool(row.get('family_crc')),
                        chronic_disease=_bool(row.get('chronic_disease')), blind_code='BL-%s' % re.sub(r'\D', '', code)[-6:])
                    session.add(subject); session.flush(); sid = subject.id
                    intention = _bool(row.get('intention_6m')); behavior = _bool(row.get('actual_participated'))
                    session.add(ScreeningDecision(subject_id=sid, intention_6m=int(intention),
                                                  actual_participated=int(behavior), colonoscopy_done=int(behavior),
                                                  screening_timing='Completed on time' if behavior else ('Delay' if intention else 'Undecided')))
                    cognition = _float(row.get('disease_cognition'), 3.0)
                    hl = _float(row.get('health_literacy'), 3.0); se = _float(row.get('self_efficacy'), 2.5)
                    rep = _float(row.get('representative_bias'), 0.2); ava = _float(row.get('availability_bias'), 0.2)
                    anc = _float(row.get('anchoring_adjustment'), 0.2); cert = _float(row.get('certainty_effect'), 0.3)
                    refl = _float(row.get('reflection_effect'), 0.2); iso = _float(row.get('isolation_effect'), 0.2)
                    session.add(DiseaseCognition(subject_id=sid, disease_knowledge=cognition, perceived_severity=3.5,
                                                 perceived_susceptibility=3.0, screening_benefit=3.5,
                                                 screening_barrier=2.8, medical_trust=3.2, optimism_bias=0.3,
                                                 health_value=hl - 0.2 * anc, economic_burden=2.5,
                                                 service_accessibility=1.0, policy_support=1.0,
                                                 decision_reference=0.4 * hl - 0.3 * anc))
                    session.add(ScenarioResponse(subject_id=sid, representative_bias=rep, availability_bias=ava,
                                                 anchoring_adjustment=anc, certainty_effect=cert,
                                                 reflection_effect=refl, isolation_effect=iso,
                                                 risk_aversion=cert, positive_frame_response=1 - rep,
                                                 negative_frame_response=1 - refl, decision_consistency=1 - np.std([rep, ava, anc, cert, refl, iso])))
                    belief = 0.45 * hl + 0.35 * se + 0.35 * cognition - 0.35 * rep - 0.25 * ava
                    risk = 0.35 * cert + 0.30 * refl + 0.20 * iso
                    session.add(ProspectConstruct(subject_id=sid, belief_structure=belief, risk_preference=risk,
                                                  representative_bias=rep, availability_bias=ava,
                                                  anchoring_adjustment=anc, certainty_effect=cert,
                                                  reflection_effect=refl, isolation_effect=iso,
                                                  health_value_account=hl - 0.3 * anc, disease_cognition=cognition,
                                                  health_literacy=hl, self_efficacy=se, service_accessibility=1.0,
                                                  decision_reference=0.4 * hl - 0.35 * anc,
                                                  screening_intention=float(intention), screening_behavior=float(behavior)))
                    session._flush() if False else None
                    for item in ('HL1', 'HL2', 'HL3'):
                        session.add(HealthLiteracyItem(subject_id=sid, item_code=item, value=hl))
                    for j in range(1, 11):
                        session.add(SelfEfficacyItem(subject_id=sid, item_code='SE%d' % j, value=se))
                success += 1; created_ids.append(sid)
            except Exception as exc:
                failed.append({'row': int(index + 2), 'error': str(exc)[:160]})
        session.commit()
        return {'ok': True, 'success': success, 'failed': failed[:50], 'failed_count': len(failed),
                'subject_ids': created_ids}
    except Exception:
        session.rollback(); raise
    finally:
        session.close()