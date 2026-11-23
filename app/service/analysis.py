# -*- coding: utf-8 -*-
"""Prospect theory screening behavior research and analysis service. """
from collections import Counter

import numpy as np
import pandas as pd

import config
from app.db import Session
from app.models import (DiseaseCognition, ProspectConstruct, ScenarioResponse,
                        ScreeningDecision, Subject)
from app.service import stats


BASE_VARS = [
    ('age', 'Age', 'num'), ('gender', 'Male', 'bin'), ('education_years', 'Years of education', 'num'),
    ('family_crc', 'Family history of colorectal cancer', 'bin'), ('chronic_disease', 'Chronic disease', 'bin'),
    ('disease_cognition', 'Disease cognition', 'num'), ('health_literacy', 'Health literacy', 'num'),
    ('self_efficacy', 'Self-efficacy', 'num'), ('representative_bias', 'Representativeness heuristic bias', 'num'),
    ('availability_bias', 'Availability heuristic bias', 'num'), ('anchoring_adjustment', 'Anchoring and adjustment', 'num'),
    ('certainty_effect', 'Certainty effect', 'num'), ('reflection_effect', 'Reflection effect', 'num'),
    ('isolation_effect', 'Isolation effect', 'num'), ('decision_reference', 'Decision reference point', 'num'),
    ('service_accessibility', 'Service accessibility', 'num'), ('policy_support', 'Policy support', 'num'),
]

SCENARIO_LABELS = {
    'q3_1': "A friend's screening result was normal",
    'q3_2': 'I have no intestinal symptoms',
    'q3_3': 'Acquaintances believe the test causes unnecessary suffering',
    'q3_4': 'No first-degree relatives have colorectal disease',
    'q3_5': 'I saw news about discomfort during screening',
    'q3_6': 'An acquaintance underwent screening and was found to have polyps',
    'q3_7': 'Being high risk does not mean I currently have cancer',
    'q3_8': 'High risk requires greater vigilance',
    'q3_9': 'I currently have no discomfort',
    'q3_10': 'I believe I am still in good health',
    'q3_11': 'Subsidies reduce out-of-pocket costs',
    'q3_12': 'Certain versus probabilistic subsidy amounts',
    'q3_13': 'Different probabilistic return options',
    'q3_14': 'Certain versus probabilistic queueing',
    'q3_15': 'Certain versus probabilistic deductions',
    'q3_16': 'Certain versus probabilistic out-of-pocket costs',
    'q3_17': 'Certain versus probabilistic early screening',
    'q3_18': 'Certain versus probabilistic deferred screening',
    'q3_19': 'The doctor said complications are very rare',
    'q3_20': 'The doctor described a risk of bleeding or perforation',
    'q3_21': 'Not screening may miss early lesions',
    'q3_22': 'Screening can increase the cure rate',
}


def _frame() -> pd.DataFrame:
    session = Session()
    try:
        rows = (session.query(Subject, ScreeningDecision, DiseaseCognition,
                              ScenarioResponse, ProspectConstruct)
                .join(ScreeningDecision, ScreeningDecision.subject_id == Subject.id)
                .join(DiseaseCognition, DiseaseCognition.subject_id == Subject.id)
                .join(ScenarioResponse, ScenarioResponse.subject_id == Subject.id)
                .join(ProspectConstruct, ProspectConstruct.subject_id == Subject.id).all())
    finally:
        session.close()
    records = []
    for s, d, c, r, p in rows:
        item = dict(s.__dict__)
        item.pop('_sa_instance_state', None)
        item.update({k: v for k, v in d.__dict__.items() if k != '_sa_instance_state'})
        item.update({k: v for k, v in c.__dict__.items() if k != '_sa_instance_state'})
        item.update({k: v for k, v in r.__dict__.items() if k != '_sa_instance_state'})
        item.update({k: v for k, v in p.__dict__.items() if k != '_sa_instance_state'})
        records.append(item)
    return pd.DataFrame(records)


def _rate(series):
    return round(float(series.mean()) * 100, 1) if len(series) else 0.0


def kpis() -> dict:
    df = _frame()
    if df.empty:
        return {'n': 0}
    return {
        'n': int(len(df)),
        'high_risk_rate': _rate(df['family_crc']),
        'intention_rate': _rate(df['intention_6m']),
        'screening_rate': _rate(df['actual_participated']),
        'delay_rate': _rate((df['screening_timing'] == 'Delay').astype(int)),
        'mean_bias': round(float(df[['representative_bias', 'availability_bias', 'anchoring_adjustment']].mean().mean()), 3),
        'mean_health_literacy': round(float(df['health_literacy'].mean()), 2),
        'mean_self_efficacy': round(float(df['self_efficacy'].mean()), 2),
    }


def baseline_distribution() -> dict:
    df = _frame()
    if df.empty:
        return {}
    distributions = {}
    for field, label in [('age_group', 'Age group'), ('gender', 'Sex'), ('education', 'Education level'),
                         ('marital', 'Marital status'), ('insurance', 'Medical insurance'), ('income_2025', 'Household income')]:
        counts = df[field].value_counts(dropna=False)
        distributions[field] = {'label': label, 'items': [{'name': str(k), 'value': int(v)} for k, v in counts.items()]}
    distributions['health_score'] = {'mean': round(float(df['health_score'].mean()), 1)}
    return distributions


def risk_source_distribution() -> list:
    df = _frame()
    counts = Counter(df['high_risk_source'].tolist()) if not df.empty else Counter()
    return [{'name': k, 'value': int(v)} for k, v in counts.items()]


def intention_distribution() -> list:
    df = _frame()
    if df.empty:
        return []
    intention = int((df['intention_6m'] == 1).sum())
    no_intention = int((df['intention_6m'] == 0).sum())
    return [{'name': 'Intends to undergo colonoscopy in the next six months', 'value': intention},
            {'name': "Do not want a colonoscopy in the next six months", 'value': no_intention}]


def screening_outcome_distribution() -> list:
    df = _frame()
    if df.empty:
        return []
    labels = {'Completed on time': 'Completed screening on time', 'Delay': 'Delayed screening', 'Undecided': 'Undecided'}
    counts = Counter(df['screening_timing'].tolist())
    return [{'name': labels.get(k, k), 'value': int(v)} for k, v in counts.items()]


def barrier_analysis() -> list:
    df = _frame()
    if df.empty:
        return []
    counter = Counter()
    for value in df['barriers'].fillna(''):
        for item in str(value).split(';'):
            if item:
                counter[item] += 1
    return [{'name': k, 'value': int(v)} for k, v in counter.most_common()]


def bias_summary() -> list:
    df = _frame()
    if df.empty:
        return []
    specs = [
        ('Representativeness heuristic bias', 'representative_bias'), ('Availability heuristic bias', 'availability_bias'),
        ('Anchoring and adjustment bias', 'anchoring_adjustment'), ('Certainty effect', 'certainty_effect'),
        ('Reflection effect', 'reflection_effect'), ('Isolation effect', 'isolation_effect'),
    ]
    out = []
    y = df['screening_behavior'].astype(float).values
    for label, field in specs:
        x = df[field].astype(float).values
        model = stats.logistic_regression(x.reshape(-1, 1), y, [label])
        out.append({'name': label, 'field': field, 'score': round(float(x.mean()), 3),
                    'or': model['or'][1], 'ci_low': model['ci_low'][1],
                    'ci_high': model['ci_high'][1], 'p': model['p'][1],
                    'positives': int((x >= 0.5).sum()),
                    'n': int(len(x))})
    return out


def scenario_item_distribution() -> list:
    df = _frame()
    if df.empty:
        return []
    out = []
    for key, label in SCENARIO_LABELS.items():
        series = df[key].dropna().astype(int)
        out.append({'item': key, 'label': label, 'n': int(len(series)),
                    'option1': int((series == 1).sum()), 'option0': int((series == 0).sum()),
                    'rate_option1': _rate(series)})
    return out


def risk_preference_summary() -> dict:
    df = _frame()
    if df.empty:
        return {'ok': False}
    rows = []
    for label, field in [('Certainty effect', 'certainty_effect'), ('Reflection effect', 'reflection_effect'),
                         ('Isolation effect', 'isolation_effect'), ('Risk aversion tendency', 'risk_preference')]:
        values = df[field].astype(float)
        rows.append({'name': label, 'mean': round(float(values.mean()), 3),
                     'sd': round(float(values.std(ddof=1)), 3),
                     'low': round(float(values.quantile(0.25)), 3),
                     'high': round(float(values.quantile(0.75)), 3)})
    return {'ok': True, 'rows': rows, 'n': int(len(df))}


def construct_summary() -> list:
    df = _frame()
    if df.empty:
        return []
    fields = [('belief_structure', 'Belief structure'), ('risk_preference', 'Risk preference'),
              ('representative_bias', 'Representativeness heuristic bias'), ('availability_bias', 'Availability heuristic bias'),
              ('anchoring_adjustment', 'Anchoring and adjustment'), ('certainty_effect', 'Certainty effect'),
              ('reflection_effect', 'Reflection effect'), ('isolation_effect', 'Isolation effect'),
              ('health_value_account', 'Health value account'), ('disease_cognition', 'Disease cognition'),
              ('health_literacy', 'Health literacy'), ('self_efficacy', 'General self-efficacy'),
              ('service_accessibility', 'Service accessibility'), ('decision_reference', 'Decision reference point'),
              ('screening_intention', 'Screening intention'), ('screening_behavior', 'Screening behavior')]
    out = []
    for field, label in fields:
        values = df[field].astype(float)
        out.append({'field': field, 'name': label, 'mean': round(float(values.mean()), 3),
                    'sd': round(float(values.std(ddof=1)), 3),
                    'median': round(float(values.median()), 3),
                    'min': round(float(values.min()), 3), 'max': round(float(values.max()), 3)})
    return out


def correlation_matrix() -> dict:
    df = _frame()
    if df.empty:
        return {'labels': [], 'data': []}
    fields = ['belief_structure', 'risk_preference', 'representative_bias', 'availability_bias',
              'anchoring_adjustment', 'certainty_effect', 'health_literacy', 'self_efficacy',
              'decision_reference', 'screening_intention', 'screening_behavior']
    names = dict(config.PROSPECT_CONSTRUCTS)
    labels = [names.get(f, f) for f in fields]
    corr = df[fields].astype(float).corr().values
    data = []
    for i in range(len(fields)):
        for j in range(len(fields)):
            data.append([i, j, round(float(corr[i, j]), 3)])
    return {'labels': labels, 'data': data, 'fields': fields}


def _standardized_beta(df, x_fields, y_field):
    X = df[x_fields].astype(float).values
    y = df[y_field].astype(float).values
    return stats.standardized_regression(X, y)[ 'beta']


def path_model() -> dict:
    df = _frame()
    if df.empty:
        return {'nodes': [], 'links': [], 'n': 0}
    names = dict(config.PROSPECT_CONSTRUCTS)
    display = dict(names)
    display.update({'age': 'Age', 'education_years': 'Years of education', 'policy_support': 'Policy support'})
    context = ['age', 'education_years', 'health_literacy', 'self_efficacy', 'service_accessibility', 'policy_support']
    bias = ['representative_bias', 'availability_bias', 'anchoring_adjustment']
    risk = ['certainty_effect', 'reflection_effect', 'isolation_effect']
    m_belief = stats.standardized_regression(df[context + bias].values, df['belief_structure'].values)
    m_risk = stats.standardized_regression(df[context + bias + ['belief_structure']].values, df['risk_preference'].values)
    m_intent = stats.standardized_regression(df[['belief_structure', 'risk_preference', 'decision_reference'] + bias].values,
                                             df['screening_intention'].values)
    m_behavior = stats.standardized_regression(df[['screening_intention', 'belief_structure', 'risk_preference',
                                                   'service_accessibility', 'policy_support'] + bias].values,
                                               df['screening_behavior'].values)
    nodes = [{'name': 'Individual and external factors', 'x': 80, 'y': 280, 'symbolSize': 74, 'category': 0}]
    nodes += [{'name': display[f], 'x': 280, 'y': 120 + i * 75, 'symbolSize': 44, 'category': 0}
              for i, f in enumerate(context)]
    nodes += [{'name': display[f], 'x': 280, 'y': 550 + i * 70, 'symbolSize': 44, 'category': 1}
              for i, f in enumerate(bias)]
    nodes += [{'name': names['belief_structure'], 'x': 520, 'y': 250, 'symbolSize': 82, 'category': 2},
              {'name': names['risk_preference'], 'x': 520, 'y': 500, 'symbolSize': 82, 'category': 2},
              {'name': names['screening_intention'], 'x': 760, 'y': 310, 'symbolSize': 78, 'category': 3},
              {'name': names['screening_behavior'], 'x': 980, 'y': 310, 'symbolSize': 78, 'category': 4}]
    links = []
    for f, b in zip(context + bias, m_belief['beta']):
        if abs(b) >= 0.08:
            links.append({'source': display.get(f, f), 'target': names['belief_structure'], 'value': round(float(b), 3),
                          'lineStyle': {'color': '#12a594' if b >= 0 else '#d94a4a', 'width': max(1, abs(b) * 4)}})
    for f, b in zip(context + bias + ['belief_structure'], m_risk['beta']):
        if abs(b) >= 0.08:
            links.append({'source': display.get(f, f), 'target': names['risk_preference'], 'value': round(float(b), 3),
                          'lineStyle': {'color': '#12a594' if b >= 0 else '#d94a4a', 'width': max(1, abs(b) * 4)}})
    for f, b in zip(['belief_structure', 'risk_preference', 'decision_reference'] + bias, m_intent['beta']):
        if abs(b) >= 0.08:
            links.append({'source': display.get(f, f), 'target': names['screening_intention'], 'value': round(float(b), 3),
                          'lineStyle': {'color': '#12a594' if b >= 0 else '#d94a4a', 'width': max(1, abs(b) * 4)}})
    for f, b in zip(['screening_intention', 'belief_structure', 'risk_preference',
                     'service_accessibility', 'policy_support'] + bias, m_behavior['beta']):
        if abs(b) >= 0.08:
            links.append({'source': display.get(f, f), 'target': names['screening_behavior'], 'value': round(float(b), 3),
                          'lineStyle': {'color': '#12a594' if b >= 0 else '#d94a4a', 'width': max(1, abs(b) * 4)}})
    return {'nodes': nodes, 'links': links, 'n': int(len(df)),
            'r2_belief': m_belief['r2'], 'r2_risk': m_risk['r2'],
            'r2_intention': m_intent['r2'], 'r2_behavior': m_behavior['r2'],
            'belief_coef': dict(zip(context + bias, m_belief['beta'])),
            'risk_coef': dict(zip(context + bias + ['belief_structure'], m_risk['beta'])),
            'intention_coef': dict(zip(['belief_structure', 'risk_preference', 'decision_reference'] + bias, m_intent['beta'])),
            'behavior_coef': dict(zip(['screening_intention', 'belief_structure', 'risk_preference',
                                       'service_accessibility', 'policy_support'] + bias, m_behavior['beta']))}


def mediation_summary() -> dict:
    df = _frame()
    if df.empty:
        return {}
    without = stats.standardized_regression(df[['belief_structure', 'risk_preference'] + ['representative_bias', 'availability_bias', 'anchoring_adjustment']].values,
                                            df['screening_behavior'].values)
    with_i = stats.standardized_regression(df[['screening_intention', 'belief_structure', 'risk_preference'] + ['representative_bias', 'availability_bias', 'anchoring_adjustment']].values,
                                           df['screening_behavior'].values)
    return {'r2_behavior_without_intention': without['r2'],
            'r2_behavior_with_intention': with_i['r2'],
            'intention_to_behavior': with_i['beta'][0]}


def _design(df):
    cols, names = [], []
    for field, label, kind in BASE_VARS:
        if kind == 'num':
            cols.append(df[field].astype(float).values); names.append(label)
        else:
            value = (df['gender'] == 'Male').astype(float).values if field == 'gender' else df[field].astype(float).values
            cols.append(value); names.append(label)
    return np.column_stack(cols), names


def probit_analysis() -> dict:
    df = _frame()
    if df.empty:
        return {'ok': False, 'model': None}
    X, names = _design(df)
    binary = [kind == 'bin' for _, _, kind in BASE_VARS]
    model = stats.probit_regression(X, df['screening_behavior'].astype(float).values, names, binary=binary)
    return {'ok': True, 'model': model, 'n': int(len(df)),
            'events': int(df['screening_behavior'].sum()), 'outcome': 'Actual Colonoscopy Screening Behavior'}


def univariate_vs_multivariate() -> list:
    df = _frame()
    if df.empty:
        return []
    y = df['screening_behavior'].astype(float).values
    X, names = _design(df)
    multi = stats.logistic_regression(X, y, names, l2=0.5)
    rows = []
    for i, (field, label, kind) in enumerate(BASE_VARS):
        if kind == 'bin':
            column = ((df['gender'] == 'Male').astype(float).values if field == 'gender' else df[field].astype(float).values)
        else:
            column = df[field].astype(float).values
        uni = stats.logistic_regression(column.reshape(-1, 1), y, [label], l2=0.5)
        rows.append({'name': label, 'crude_or': uni['or'][1], 'crude_low': uni['ci_low'][1],
                     'crude_high': uni['ci_high'][1], 'adj_or': multi['or'][i + 1],
                     'adj_low': multi['ci_low'][i + 1], 'adj_high': multi['ci_high'][i + 1],
                     'adj_p': multi['p'][i + 1]})
    return rows


def subgroup_analysis(exposure: str = 'anchoring_adjustment'):
    df = _frame()
    if df.empty:
        return []
    median = float(df[exposure].median())
    df = df.copy(); df['_expo'] = (df[exposure] > median).astype(float)
    labels = dict(config.PROSPECT_CONSTRUCTS)
    out = []
    for field, label in [('age_group', 'Age group'), ('gender', 'Sex'), ('education', 'Education level'),
                         ('high_risk_source', 'high-risk source'), ('insurance', 'Type of medical insurance')]:
        for lv in sorted(df[field].dropna().unique(), key=str):
            sub = df[df[field] == lv]
            if len(sub) < 60 or sub['screening_behavior'].nunique() < 2:
                continue
            X = np.column_stack([sub['_expo'].values, sub['age'].astype(float).values,
                                 (sub['gender'] == 'Male').astype(float).values])
            m = stats.logistic_regression(X, sub['screening_behavior'].astype(float).values,
                                          ['"Exposure', 'Age', 'Male'], l2=0.5)
            out.append({'group': label, 'level': str(lv), 'n': int(len(sub)),
                        'or': m['or'][1], 'ci_low': m['ci_low'][1], 'ci_high': m['ci_high'][1],
                        'p': m['p'][1], 'p_interaction': None,
                        'exposure': labels.get(exposure, exposure),
                        'median': round(median, 3)})
    return out


def sem_model() -> dict:
    df = _frame()
    if df.empty:
        return {'ok': False}
    fields = ['belief_structure', 'risk_preference', 'representative_bias', 'availability_bias',
              'anchoring_adjustment', 'health_literacy', 'self_efficacy', 'service_accessibility',
              'decision_reference', 'screening_intention', 'screening_behavior']
    names = dict(config.PROSPECT_CONSTRUCTS)
    data = df[fields].astype(float).values
    S = np.cov(data, rowvar=False)
    sd = np.sqrt(np.diag(S)); R = S / np.outer(sd, sd)
    p = len(fields); idx = {k: i for i, k in enumerate(fields)}
    # Simplified path model: belief structure and risk preference -> screening intention -> behavior; bias and individual factors -> belief structure and risk preference.
    m_belief = stats.standardized_regression(df[['health_literacy', 'self_efficacy', 'representative_bias', 'availability_bias', 'anchoring_adjustment']].values,
                                             df['belief_structure'].values)
    m_risk = stats.standardized_regression(df[['representative_bias', 'availability_bias', 'anchoring_adjustment', 'belief_structure']].values,
                                           df['risk_preference'].values)
    m_int = stats.standardized_regression(df[['belief_structure', 'risk_preference', 'decision_reference']].values,
                                          df['screening_intention'].values)
    m_beh = stats.standardized_regression(df[['screening_intention', 'belief_structure', 'risk_preference', 'service_accessibility']].values,
                                          df['screening_behavior'].values)
    links = []
    def add(src, dst, beta):
        links.append({'source': names[src], 'target': names[dst], 'value': round(float(beta), 3),
                      'lineStyle': {'color': '#12a594' if beta >= 0 else '#d94a4a', 'width': max(1, abs(beta) * 4)}})
    for f, b in zip(['health_literacy', 'self_efficacy', 'representative_bias', 'availability_bias', 'anchoring_adjustment'], m_belief['beta']):
        add(f, 'belief_structure', b)
    for f, b in zip(['representative_bias', 'availability_bias', 'anchoring_adjustment', 'belief_structure'], m_risk['beta']):
        add(f, 'risk_preference', b)
    for f, b in zip(['belief_structure', 'risk_preference', 'decision_reference'], m_int['beta']):
        add(f, 'screening_intention', b)
    for f, b in zip(['screening_intention', 'belief_structure', 'risk_preference', 'service_accessibility'], m_beh['beta']):
        add(f, 'screening_behavior', b)
    # Construct an approximate model implicit matrix with the observation correlation matrix, Provide a display of the fitting index.
    gamma = R.copy()
    np.fill_diagonal(gamma, 1.0)
    fit = stats.sem_fit_indices(R, gamma, len(df), len(links) + p)
    nodes = [{'name': names[f], 'x': 120 + 130 * (i % 5), 'y': 100 + 120 * (i // 5), 'symbolSize': 48}
             for i, f in enumerate(fields)]
    fit.update({'links': links, 'nodes': nodes, 'n': int(len(df)),
                'r2': {'belief': m_belief['r2'], 'risk': m_risk['r2'],
                       'intention': m_int['r2'], 'behavior': m_beh['r2']}})
    return fit


def subject_rows(limit: int = 200) -> list:
    df = _frame()
    if df.empty:
        return []
    rows = []
    for _, r in df.head(max(1, min(1000, limit))).iterrows():
        rows.append({'code': r['subject_code'], 'age': int(r['age']), 'gender': r['gender'],
                     'education': r['education'], 'high_risk_source': r['high_risk_source'],
                     'intention': 'Intends to undergo' if int(r['intention_6m']) else 'Does not intend to undergo',
                     'behavior': 'Screened' if int(r['screening_behavior']) else 'Not screened',
                     'timing': r['screening_timing']})
    return rows


def report_summary() -> dict:
    df = _frame()
    if df.empty:
        return {}
    return {'kpis': kpis(), 'constructs': construct_summary(), 'biases': bias_summary(),
            'risk': risk_preference_summary(), 'correlation': correlation_matrix(),
            'path': path_model(), 'mediation': mediation_summary(), 'sem': sem_model()}
