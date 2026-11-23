# -*- coding: utf-8 -*-
"""Reliability and Validity of the Health Literacy and General Self-Efficacy Scales. """
import numpy as np
import pandas as pd

from app.db import Session
from app.models import HealthLiteracyItem, SelfEfficacyItem, ProspectConstruct
from app.service import stats


def _matrix(model, item_prefix):
    session = Session()
    try:
        rows = session.query(model).all()
    finally:
        session.close()
    if not rows:
        return pd.DataFrame()
    records = [{'subject_id': r.subject_id, 'item': r.item_code, 'value': r.value} for r in rows]
    return (pd.DataFrame(records).pivot_table(index='subject_id', columns='item', values='value', aggfunc='mean')
            .sort_index(axis=1))


def _alpha(df):
    if df.shape[1] < 2:
        return {'alpha': 0.0, 'items': [], 'n': int(len(df))}
    item_vars = df.var(axis=0, ddof=1)
    total_var = df.sum(axis=1).var(ddof=1)
    k = df.shape[1]
    alpha = k / (k - 1) * (1 - item_vars.sum() / total_var) if total_var else 0.0
    items = []
    for col in df.columns:
        rest = df.drop(columns=[col]).sum(axis=1)
        corr = df[col].corr(rest)
        items.append({'item': col, 'mean': round(float(df[col].mean()), 2),
                      'sd': round(float(df[col].std(ddof=1)), 2),
                      'citc': round(float(corr), 3) if pd.notna(corr) else None})
    return {'alpha': round(float(alpha), 3), 'items': items, 'n': int(len(df))}


def reliability_report():
    hl = _matrix(HealthLiteracyItem, 'HL')
    se = _matrix(SelfEfficacyItem, 'SE')
    return {'health_literacy': _alpha(hl), 'self_efficacy': _alpha(se)}


def validity_report():
    se = _matrix(SelfEfficacyItem, 'SE')
    efa = stats.efa_varimax(se.values.astype(float), n_factors=0) if not se.empty else {'n_factors': 0}
    return {'n_items': int(se.shape[1]) if not se.empty else 0,
            'n_subjects': int(se.shape[0]) if not se.empty else 0,
            'efa': efa,
            'item_names': list(se.columns) if not se.empty else []}


def construct_reliability():
    session = Session()
    try:
        rows = session.query(ProspectConstruct).all()
    finally:
        session.close()
    if not rows:
        return {}
    cols = ['belief_structure', 'risk_preference', 'representative_bias', 'availability_bias',
            'anchoring_adjustment', 'certainty_effect', 'reflection_effect', 'isolation_effect',
            'health_value_account', 'disease_cognition', 'health_literacy', 'self_efficacy']
    return {c: {'mean': round(float(np.mean([getattr(r, c) or 0 for r in rows])), 3),
                'sd': round(float(np.std([getattr(r, c) or 0 for r in rows], ddof=1)), 3)} for c in cols}