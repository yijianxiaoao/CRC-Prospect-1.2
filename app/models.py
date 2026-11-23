# -*- coding: utf-8 -*-
"""Data model for the prospect theory colorectal cancer screening study. """
import datetime

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, Text

from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    """Platform account. """
    __tablename__ = 't_user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    nickname = Column(String(50), default='')
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default='viewer')
    must_change_password = Column(Integer, default=0)
    session_version = Column(Integer, default=1)
    status = Column(String(20), default='active')
    email = Column(String(255), default='')
    auth_source = Column(String(20), default='local')
    sso_provider = Column(String(50), default='')
    sso_subject = Column(String(255), default='')
    mfa_enabled = Column(Integer, default=0)
    mfa_secret_enc = Column(Text, default='')
    mfa_recovery_hashes = Column(Text, default='')
    last_mfa_counter = Column(Integer, default=0)
    approved_by = Column(String(50), default='')
    approved_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(64), default='')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Subject(Base):
    """De-identified study participants and Part 1 general information. """
    __tablename__ = 't_subject'
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_code = Column(String(30), nullable=False, unique=True)
    consent_obtained = Column(Integer, default=1)
    high_risk_source = Column(String(64), default='')
    city = Column(String(30), default='')
    district = Column(String(30), default='')
    community = Column(String(50), default='')
    age = Column(Integer, default=0)
    age_group = Column(String(20), default='')
    gender = Column(String(16), default='')
    education = Column(String(80), default='')
    education_years = Column(Float, default=0)
    marital = Column(String(20), default='')
    insurance = Column(Text, default='')
    prior_malignancy = Column(Integer, default=0)
    family_crc = Column(Integer, default=0)
    family_relations = Column(Text, default='')
    parent_early_onset = Column(Integer, default=0)
    sibling_early_onset = Column(Integer, default=0)
    child_early_onset = Column(Integer, default=0)
    chronic_disease = Column(Integer, default=0)
    chronic_types = Column(Text, default='')
    living_status = Column(String(80), default='')
    occupation = Column(String(100), default='')
    income_2025 = Column(String(30), default='')
    acceptable_cost = Column(String(30), default='')
    discuss_with = Column(Text, default='')
    family_doctor = Column(Integer, default=0)
    doctor_health_education = Column(Integer, default=0)
    health_worker_relative = Column(Integer, default=0)
    bowel_knowledge = Column(Integer, default=0)
    colonoscopy_early_detection = Column(Integer, default=0)
    health_score = Column(Integer, default=0)
    medical_satisfaction = Column(Integer, default=0)
    review_status = Column(String(32), default='Pending Review')
    reviewed_by = Column(String(50), default='')
    reviewed_at = Column(DateTime, nullable=True)
    review_note = Column(String(200), default='')
    blind_code = Column(String(30), default='')
    blinded = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ScreeningDecision(Base):
    """Part 2: Screening willingness, prior experience, and final screening behavior. """
    __tablename__ = 't_screening_decision'
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, nullable=False, index=True)
    intention_6m = Column(Integer, default=0)
    hospital_level = Column(String(64), default='')
    barriers = Column(Text, default='')
    prior_colonoscopy_count = Column(Integer, default=0)
    prior_fit_count = Column(Integer, default=0)
    prior_experience_effect = Column(Integer, default=0)
    actual_participated = Column(Integer, default=0)
    screening_method = Column(String(30), default='')
    colonoscopy_done = Column(Integer, default=0)
    screening_timing = Column(String(30), default='')
    screen_date = Column(Date, nullable=True)
    reason_no = Column(String(100), default='')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class DiseaseCognition(Base):
    """Disease cognition, health values, and mental accounts. """
    __tablename__ = 't_disease_cognition'
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, nullable=False, index=True)
    disease_knowledge = Column(Float, default=0)
    perceived_susceptibility = Column(Float, default=0)
    perceived_severity = Column(Float, default=0)
    screening_benefit = Column(Float, default=0)
    screening_barrier = Column(Float, default=0)
    medical_trust = Column(Float, default=0)
    optimism_bias = Column(Float, default=0)
    health_value = Column(Float, default=0)
    economic_burden = Column(Float, default=0)
    service_accessibility = Column(Float, default=0)
    policy_support = Column(Float, default=0)
    decision_reference = Column(Float, default=0)


class ScenarioResponse(Base):
    """Part 3: Raw responses to 22 scenario-experiment questions and prospect theory dimension scores. """
    __tablename__ = 't_scenario_response'
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, nullable=False, index=True)
    q3_1 = Column(Integer, default=0)
    q3_2 = Column(Integer, default=0)
    q3_3 = Column(Integer, default=0)
    q3_4 = Column(Integer, default=0)
    q3_5 = Column(Integer, default=0)
    q3_6 = Column(Integer, default=0)
    q3_7 = Column(Integer, default=0)
    q3_8 = Column(Integer, default=0)
    q3_9 = Column(Integer, default=0)
    q3_10 = Column(Integer, default=0)
    q3_11 = Column(Integer, default=0)
    q3_12 = Column(Integer, default=0)
    q3_13 = Column(Integer, default=0)
    q3_14 = Column(Integer, default=0)
    q3_15 = Column(Integer, default=0)
    q3_16 = Column(Integer, default=0)
    q3_17 = Column(Integer, default=0)
    q3_18 = Column(Integer, default=0)
    q3_19 = Column(Integer, default=0)
    q3_20 = Column(Integer, default=0)
    q3_21 = Column(Integer, default=0)
    q3_22 = Column(Integer, default=0)
    representative_bias = Column(Float, default=0)
    availability_bias = Column(Float, default=0)
    anchoring_adjustment = Column(Float, default=0)
    certainty_effect = Column(Float, default=0)
    reflection_effect = Column(Float, default=0)
    isolation_effect = Column(Float, default=0)
    risk_aversion = Column(Float, default=0)
    positive_frame_response = Column(Float, default=0)
    negative_frame_response = Column(Float, default=0)
    decision_consistency = Column(Float, default=0)


class HealthLiteracyItem(Base):
    """Part 4: Brief Health Literacy Scale items. """
    __tablename__ = 't_health_literacy'
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, nullable=False, index=True)
    item_code = Column(String(10), default='')
    value = Column(Float, default=0)


class SelfEfficacyItem(Base):
    """Part 5: General Self-Efficacy Scale items. """
    __tablename__ = 't_self_efficacy'
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, nullable=False, index=True)
    item_code = Column(String(10), default='')
    value = Column(Float, default=0)


class ProspectConstruct(Base):
    """Summary constructs used for SEM, Probit, and forest plots. """
    __tablename__ = 't_prospect_construct'
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, nullable=False, index=True)
    belief_structure = Column(Float, default=0)
    risk_preference = Column(Float, default=0)
    representative_bias = Column(Float, default=0)
    availability_bias = Column(Float, default=0)
    anchoring_adjustment = Column(Float, default=0)
    certainty_effect = Column(Float, default=0)
    reflection_effect = Column(Float, default=0)
    isolation_effect = Column(Float, default=0)
    health_value_account = Column(Float, default=0)
    disease_cognition = Column(Float, default=0)
    health_literacy = Column(Float, default=0)
    self_efficacy = Column(Float, default=0)
    service_accessibility = Column(Float, default=0)
    decision_reference = Column(Float, default=0)
    screening_intention = Column(Float, default=0)
    screening_behavior = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ResearchOutput(Base):
    __tablename__ = 't_output'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), default='')
    authors = Column(String(200), default='')
    source = Column(String(200), default='')
    year = Column(Integer, default=0)
    kind = Column(String(20), default='Thesis')
    url = Column(String(300), default='')
    summary = Column(Text, default='')


class DataLock(Base):
    __tablename__ = 't_data_lock'
    id = Column(Integer, primary_key=True, autoincrement=True)
    locked = Column(Integer, default=0)
    locked_by = Column(String(50), default='')
    locked_at = Column(DateTime, nullable=True)
    subject_count = Column(Integer, default=0)
    checksum = Column(String(64), default='')
    note = Column(String(200), default='')


class AuditLog(Base):
    __tablename__ = 't_audit'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), default='')
    action = Column(String(40), default='')
    target = Column(String(120), default='')
    detail = Column(Text, default='')
    ip = Column(String(50), default='')
    prev_hash = Column(String(64), default='')
    entry_hash = Column(String(64), default='')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)