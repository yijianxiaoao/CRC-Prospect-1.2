# -*- coding: utf-8 -*-
"""Prospect theory colorectal cancer screening simulation cohort generator. """
import datetime
import random

import numpy as np

import config
from app.db import Session
from app.models import (AuditLog, DataLock, DiseaseCognition, HealthLiteracyItem,
                        ProspectConstruct, ResearchOutput, ScenarioResponse,
                        ScreeningDecision, SelfEfficacyItem, Subject)


def _logistic(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def _mean(values):
    return float(np.mean(values)) if len(values) else 0.0


def _age_group(age):
    if age < 50:
        return '40-49 years'
    if age < 60:
        return '50-59 years'
    if age < 70:
        return '60-69 years'
    return '70-75 years'


def _education_years(value):
    return {
        'No formal schooling': 0, 'Primary school': 6, 'Junior high school': 9,
        'Senior high school/Technical secondary school': 12, 'College/Associate degree': 15, 'Postgraduate or above': 19,
    }.get(value, 9)


def _insurance_factor(value):
    if value == 'Employee Basic Medical Insurance':
        return 1.0
    if value == 'Urban and Rural Residents Basic Medical Insurance':
        return 0.65
    if value == 'Government-Funded Medical Care':
        return 1.15
    if value == 'Commercial Health Insurance':
        return 0.95
    if value == 'Medical Assistance':
        return 0.45
    return 0.15


def _bias_series(rng, n, base, strength):
    return np.clip(rng.beta(base, 4.0 - base, n) * strength + rng.normal(0, 0.08, n), 0, 1)


def generate_cohort(n: int = 1600, reset: bool = False) -> dict:
    """Generate structured simulated data for platform demonstration and validation of statistical methods and SEM analysis."""
    rng = np.random.default_rng(config.DEFAULT_SEED)
    random.seed(config.DEFAULT_SEED)
    session = Session()
    try:
        if reset:
            for model in (ProspectConstruct, ScenarioResponse, HealthLiteracyItem,
                          SelfEfficacyItem, DiseaseCognition, ScreeningDecision,
                          Subject, DataLock):
                session.query(model).delete()
            session.commit()
        elif session.query(Subject).count():
            return {'subject': 0, 'decision': 0, 'scenario': 0}

        ages = rng.integers(40, 76, n)
        genders = rng.choice(['Male', 'Female'], n, p=[0.48, 0.52])
        educations = rng.choice(config.EDUCATION_LEVELS, n,
                                p=[0.08, 0.19, 0.28, 0.24, 0.17, 0.04])
        education_years = np.array([_education_years(v) for v in educations])
        maritals = rng.choice(config.MARITAL_STATUSES, n, p=[0.06, 0.78, 0.08, 0.07, 0.01])
        insurances = rng.choice(config.INSURANCE_TYPES, n,
                                p=[0.28, 0.55, 0.03, 0.04, 0.03, 0.03, 0.03, 0.01])
        incomes = rng.choice(config.INCOME_LEVELS[:6], n, p=[0.18, 0.24, 0.22, 0.17, 0.14, 0.05])
        costs = rng.choice(config.COST_REFERENCE, n, p=[0.31, 0.36, 0.23, 0.10])
        family_crc = rng.binomial(1, 0.12, n)
        prior_malignancy = rng.binomial(1, 0.035, n)
        chronic = rng.binomial(1, 0.42, n)
        family_doctor = rng.binomial(1, 0.46, n)
        doctor_education = np.where(family_doctor == 1, rng.binomial(1, 0.63, n), 0)
        health_worker_relative = rng.binomial(1, 0.11, n)

        # Prospect theory latent variables: higher bias scores are associated with lower screening intention or delayed decisions.
        representative = _bias_series(rng, n, 2.4, 0.78)
        availability = _bias_series(rng, n, 2.0, 0.72)
        anchoring = _bias_series(rng, n, 2.6, 0.82)
        certainty = _bias_series(rng, n, 2.8, 0.88)
        reflection = _bias_series(rng, n, 2.2, 0.75)
        isolation = _bias_series(rng, n, 1.9, 0.68)

        health_literacy = np.clip(rng.normal(3.35 + 0.035 * education_years, 0.70, n), 1, 5)
        self_efficacy = np.clip(rng.normal(2.75 + 0.025 * education_years, 0.48, n), 1, 4)
        bowel_knowledge = rng.binomial(1, np.clip(0.25 + 0.10 * health_literacy - 0.18 * representative, 0.05, 0.92))
        colonoscopy_knowledge = rng.binomial(1, np.clip(0.30 + 0.12 * health_literacy - 0.20 * availability, 0.05, 0.95))
        medical_satisfaction = rng.integers(1, 6, n)
        health_score = np.clip(rng.normal(72, 14, n), 10, 100).round().astype(int)

        disease_knowledge = np.clip(0.35 * health_literacy + 0.20 * self_efficacy +
                                    0.22 * bowel_knowledge + 0.18 * colonoscopy_knowledge +
                                    rng.normal(0, 0.35, n), 0, 5)
        perceived_severity = np.clip(rng.normal(3.6, 0.8, n), 1, 5)
        perceived_susceptibility = np.clip(rng.normal(2.8 + 0.35 * family_crc - 0.25 * representative, 0.75, n), 1, 5)
        screening_benefit = np.clip(rng.normal(3.5 + 0.20 * health_literacy - 0.28 * anchoring, 0.75, n), 1, 5)
        screening_barrier = np.clip(rng.normal(3.0 + 0.55 * availability + 0.45 * anchoring, 0.80, n), 1, 5)
        medical_trust = np.clip(rng.normal(3.3, 0.8, n), 1, 5)
        optimism_bias = np.clip(0.45 * representative + 0.35 * availability + rng.normal(0, 0.30, n), 0, 1)

        income_index = np.array([config.INCOME_LEVELS.index(v) for v in incomes])
        cost_index = np.array([config.COST_REFERENCE.index(v) for v in costs])
        insurance_score = np.array([_insurance_factor(v) for v in insurances])
        health_value = np.clip(0.20 * health_literacy + 0.15 * income_index - 0.25 * cost_index + 0.20 * insurance_score + rng.normal(0, 0.4, n), -2, 3)
        economic_burden = np.clip(2.8 - 0.25 * income_index + 0.35 * cost_index - 0.55 * insurance_score + rng.normal(0, 0.4, n), 0, 5)
        service_accessibility = np.clip(0.45 * family_doctor + 0.35 * doctor_education + 0.20 * (medical_satisfaction >= 4) + rng.normal(0, 0.35, n), 0, 2)
        policy_support = np.clip(0.55 * insurance_score + 0.30 * (cost_index <= 1) + rng.normal(0, 0.3, n), 0, 2)
        decision_reference = np.clip(0.35 * health_value - 0.40 * economic_burden + 0.25 * service_accessibility + rng.normal(0, 0.35, n), -3, 3)

        belief_structure = np.clip(
            0.34 * health_literacy + 0.28 * self_efficacy + 0.22 * disease_knowledge +
            0.18 * medical_trust - 0.30 * representative - 0.24 * availability + rng.normal(0, 0.35, n), -2, 3)
        risk_preference = np.clip(0.32 * certainty + 0.30 * reflection + 0.22 * isolation +
                                 0.16 * optimism_bias + rng.normal(0, 0.35, n), 0, 2)

        intention_eta = (-0.65 + 0.72 * belief_structure + 0.38 * decision_reference +
                         0.42 * service_accessibility + 0.34 * policy_support -
                         0.46 * representative - 0.38 * availability - 0.55 * anchoring -
                         0.28 * certainty - 0.18 * reflection + rng.normal(0, 0.45, n))
        intention_prob = _logistic(intention_eta)
        intention = rng.binomial(1, intention_prob)

        behavior_eta = (-1.20 + 1.25 * intention + 0.45 * belief_structure +
                        0.55 * decision_reference + 0.45 * service_accessibility +
                        0.35 * policy_support - 0.52 * anchoring - 0.30 * reflection +
                        rng.normal(0, 0.55, n))
        behavior_prob = _logistic(behavior_eta)
        actual = rng.binomial(1, behavior_prob)

        subjects, decisions = [], []
        for i in range(n):
            code = 'PTS-%05d' % (i + 1)
            blindness = 'BL-%05d' % (i + 1)
            subjects.append(Subject(
                subject_code=code, consent_obtained=1,
                high_risk_source=random.choices(config.HIGH_RISK_SOURCES, weights=[0.52, 0.19, 0.29])[0],
                city=random.choice(['Chongqing City', 'Chengdu City', 'Wuhan City', 'Changsha City', "Xi'an City", 'Zhengzhou City']),
                district='Simulated area', community='Simulated Community',
                age=int(ages[i]), age_group=_age_group(int(ages[i])), gender=str(genders[i]),
                education=str(educations[i]), education_years=float(education_years[i]),
                marital=str(maritals[i]), insurance=str(insurances[i]),
                prior_malignancy=int(prior_malignancy[i]), family_crc=int(family_crc[i]),
                family_relations='Parents' if family_crc[i] else '',
                parent_early_onset=int(family_crc[i] and rng.random() < 0.35),
                chronic_disease=int(chronic[i]), chronic_types='hypertension;diabetes' if chronic[i] else '',
                living_status=random.choice(config.LIVING_STATUSES), occupation=random.choice(config.OCCUPATIONS),
                income_2025=str(incomes[i]), acceptable_cost=str(costs[i]),
                discuss_with='Family members;Doctor' if rng.random() < 0.7 else 'Family members',
                family_doctor=int(family_doctor[i]), doctor_health_education=int(doctor_education[i]),
                health_worker_relative=int(health_worker_relative[i]),
                bowel_knowledge=int(bowel_knowledge[i]), colonoscopy_early_detection=int(colonoscopy_knowledge[i]),
                health_score=int(health_score[i]), medical_satisfaction=int(medical_satisfaction[i]),
                blind_code=blindness,
            ))
            decisions.append(ScreeningDecision(
                subject_id=i + 1, intention_6m=int(intention[i]),
                hospital_level=random.choice(config.HOSPITAL_LEVELS),
                barriers='High cost;Worried about the pain' if cost_index[i] >= 2 else 'No time/Difficulty taking leave',
                prior_colonoscopy_count=int(rng.poisson(0.20 + 0.25 * (ages[i] >= 55))),
                prior_fit_count=int(rng.poisson(0.25)), prior_experience_effect=int(rng.binomial(1, 0.35)),
                actual_participated=int(actual[i]),
                screening_method=('colonoscopy' if actual[i] else 'Not screened'),
                colonoscopy_done=int(actual[i]), screening_timing=('Completed on time' if actual[i] else ('Delay' if intention[i] else 'Undecided')),
                screen_date=(datetime.date.today() - datetime.timedelta(days=int(rng.integers(1, 180))) if actual[i] else None),
            ))

        session.add_all(subjects)
        session.commit()
        # ScreeningDecision Needed subject_id, Write after the body submits and generates the primary key.
        for row, subject in zip(decisions, subjects):
            row.subject_id = subject.id
        session.add_all(decisions)
        session.commit()
        ids = {s.subject_code: s.id for s in session.query(Subject).all()}

        scenario_scores = []
        for i in range(n):
            sid = ids['PTS-%05d' % (i + 1)]
            q = {}
            # Representativeness heuristic: option 2 is selected to preserve bias consistency.
            for idx in range(1, 5):
                p = np.clip(0.18 + 0.64 * representative[i], 0.02, 0.95)
                q['q3_%d' % idx] = int(rng.binomial(1, p))
            for idx in range(5, 7):
                q['q3_%d' % idx] = int(rng.binomial(1, np.clip(0.17 + 0.64 * availability[i], 0.02, 0.95)))
            for idx in range(7, 12):
                q['q3_%d' % idx] = int(rng.binomial(1, np.clip(0.14 + 0.65 * anchoring[i], 0.02, 0.95)))
            for idx in (12, 14, 15, 17):
                q['q3_%d' % idx] = int(rng.binomial(1, np.clip(0.20 + 0.68 * certainty[i], 0.02, 0.97)))
            for idx in (13, 16, 18):
                q['q3_%d' % idx] = int(rng.binomial(1, np.clip(0.20 + 0.65 * reflection[i], 0.02, 0.95)))
            # "Information Framework Title": 1 = undergo colonoscopy, 0 = defer. Positive and negative framing responses are generated separately.
            q['q3_19'] = int(rng.binomial(1, np.clip(0.72 - 0.30 * availability[i], 0.05, 0.95)))
            q['q3_20'] = int(rng.binomial(1, np.clip(0.58 - 0.42 * reflection[i], 0.05, 0.95)))
            q['q3_21'] = int(rng.binomial(1, np.clip(0.55 + 0.18 * perceived_severity[i] / 5 - 0.32 * isolation[i], 0.05, 0.95)))
            q['q3_22'] = int(rng.binomial(1, np.clip(0.76 + 0.13 * screening_benefit[i] / 5 - 0.28 * certainty[i], 0.05, 0.98)))
            rep = _mean([q['q3_1'], q['q3_2'], q['q3_3'], q['q3_4']])
            ava = _mean([q['q3_5'], q['q3_6']])
            anc = _mean([q['q3_7'], q['q3_8'], q['q3_9'], q['q3_10'], q['q3_11']])
            cert = _mean([q['q3_12'], q['q3_14'], q['q3_15'], q['q3_17']])
            refl = _mean([q['q3_13'], q['q3_16'], q['q3_18']])
            iso = _mean([q['q3_13'], q['q3_15'], q['q3_16']])
            pos = _mean([q['q3_19'], q['q3_21'], q['q3_22']])
            neg = q['q3_20']
            scenario_scores.append(dict(
                q, representative_bias=rep, availability_bias=ava, anchoring_adjustment=anc,
                certainty_effect=cert, reflection_effect=refl, isolation_effect=iso,
                risk_aversion=cert, positive_frame_response=pos, negative_frame_response=neg,
                decision_consistency=float(1 - np.std([rep, ava, anc, cert, refl, iso])),
            ))

        scenario_rows = [ScenarioResponse(subject_id=ids['PTS-%05d' % (i + 1)], **scenario_scores[i]) for i in range(n)]
        session.add_all(scenario_rows)
        session.commit()

        cognition_rows, construct_rows = [], []
        hl_rows, se_rows = [], []
        for i in range(n):
            sid = ids['PTS-%05d' % (i + 1)]
            cognition_rows.append(DiseaseCognition(
                subject_id=sid, disease_knowledge=float(disease_knowledge[i]),
                perceived_susceptibility=float(perceived_susceptibility[i]),
                perceived_severity=float(perceived_severity[i]),
                screening_benefit=float(screening_benefit[i]), screening_barrier=float(screening_barrier[i]),
                medical_trust=float(medical_trust[i]), optimism_bias=float(optimism_bias[i]),
                health_value=float(health_value[i]), economic_burden=float(economic_burden[i]),
                service_accessibility=float(service_accessibility[i]), policy_support=float(policy_support[i]),
                decision_reference=float(decision_reference[i])))
            construct_rows.append(ProspectConstruct(
                subject_id=sid, belief_structure=float(belief_structure[i]),
                risk_preference=float(risk_preference[i]), representative_bias=float(representative[i]),
                availability_bias=float(availability[i]), anchoring_adjustment=float(anchoring[i]),
                certainty_effect=float(certainty[i]), reflection_effect=float(reflection[i]),
                isolation_effect=float(isolation[i]), health_value_account=float(health_value[i]),
                disease_cognition=float(disease_knowledge[i]), health_literacy=float(health_literacy[i]),
                self_efficacy=float(self_efficacy[i]), service_accessibility=float(service_accessibility[i]),
                decision_reference=float(decision_reference[i]), screening_intention=float(intention[i]),
                screening_behavior=float(actual[i])))
            for j in range(1, 4):
                hl_rows.append(HealthLiteracyItem(subject_id=sid, item_code='HL%d' % j,
                                                  value=float(np.clip(round(health_literacy[i] + rng.normal(0, 0.55)), 1, 5))))
            for j in range(1, 11):
                se_rows.append(SelfEfficacyItem(subject_id=sid, item_code='SE%d' % j,
                                                value=float(np.clip(round(self_efficacy[i] + rng.normal(0, 0.55)), 1, 4))))
        session.add_all(cognition_rows)
        session.add_all(construct_rows)
        session.add_all(hl_rows)
        session.add_all(se_rows)
        session.commit()
        if session.query(ResearchOutput).count() == 0:
            session.add(ResearchOutput(title='Prospect Theory-Based Decision-Making Mechanisms for Colonoscopy Screening in High-Risk Colorectal Cancer Populations (Demonstration)',
                                       authors='Project Team', source='Demonstration results', year=2026,
                                       kind='Report', summary='For platform demonstration only; this does not represent findings from real data.'))
            session.commit()
        return {'subject': n, 'decision': n, 'scenario': n,
                'construct': n, 'health_literacy': len(hl_rows), 'self_efficacy': len(se_rows)}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
