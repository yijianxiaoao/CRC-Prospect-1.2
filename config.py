# -*- coding: utf-8 -*-
"""Prospect Theory Edition of the Research Platform for Behavioral Mechanisms of Colonoscopy Screening in High-Risk Colorectal Cancer Populations. Global configuration. """
import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'app', 'data')

DB_HOST = os.getenv('CRC_DB_HOST', 'localhost')
DB_PORT = int(os.getenv('CRC_DB_PORT', '3306'))
DB_NAME = os.getenv('CRC_PROSPECT_DB_NAME', 'crc_prospect_en')
DB_CHARSET = 'utf8mb4'


def _read_secret_file(name: str, default: str = '') -> str:
    path = os.path.join(DATA_DIR, name)
    try:
        if os.path.exists(path):
            value = open(path, encoding='utf-8').read().strip()
            if value:
                return value
    except OSError:
        pass
    return default


DB_USER = (os.getenv('CRC_DB_USER') or '').strip() or _read_secret_file('.db_user', 'root')
DB_PASSWORD = (os.getenv('CRC_DB_PASSWORD') if 'CRC_DB_PASSWORD' in os.environ
               else _read_secret_file('.db_password', ''))
DB_ADMIN_USER = (os.getenv('CRC_DB_ADMIN_USER') or '').strip() or _read_secret_file('.db_admin_user', 'root')
DB_ADMIN_PASSWORD = (os.getenv('CRC_DB_ADMIN_PASSWORD') if 'CRC_DB_ADMIN_PASSWORD' in os.environ
                     else _read_secret_file('.db_admin_password', DB_PASSWORD))
DB_URL = os.getenv('CRC_PROSPECT_DB_URL') or os.getenv('CRC_DB_URL') or (
    'mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset={charset}'
).format(user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT,
         name=DB_NAME, charset=DB_CHARSET)
MYSQL_CONNECT = {'host': DB_HOST, 'port': DB_PORT, 'user': DB_USER,
                 'password': DB_PASSWORD, 'charset': DB_CHARSET}
MYSQL_ADMIN_CONNECT = {'host': DB_HOST, 'port': DB_PORT, 'user': DB_ADMIN_USER,
                       'password': DB_ADMIN_PASSWORD, 'charset': DB_CHARSET}


def _load_secret_key() -> str:
    configured = (os.getenv('CRC_SECRET') or '').strip()
    if configured:
        return configured
    path = os.path.join(DATA_DIR, '.secret_key')
    try:
        if os.path.exists(path):
            saved = open(path, encoding='utf-8').read().strip()
            if len(saved) >= 32:
                return saved
        os.makedirs(DATA_DIR, exist_ok=True)
        generated = secrets.token_hex(32)
        with open(path, 'w', encoding='utf-8') as file:
            file.write(generated)
        return generated
    except OSError:
        return secrets.token_hex(32)


def _load_audit_key() -> str:
    configured = (os.getenv('CRC_AUDIT_KEY') or '').strip()
    if configured:
        return configured
    path = os.path.join(DATA_DIR, '.audit_key')
    try:
        if os.path.exists(path):
            saved = open(path, encoding='utf-8').read().strip()
            if len(saved) >= 32:
                return saved
        os.makedirs(DATA_DIR, exist_ok=True)
        generated = secrets.token_hex(32)
        with open(path, 'w', encoding='utf-8') as file:
            file.write(generated)
        return generated
    except OSError:
        return secrets.token_hex(32)


SECRET_KEY = _load_secret_key()
AUDIT_HMAC_KEY = _load_audit_key()
SESSION_COOKIE_SECURE = os.getenv('CRC_COOKIE_SECURE', '0').lower() in ('1', 'true', 'yes')
TRUST_PROXY = os.getenv('CRC_TRUST_PROXY', '0').lower() in ('1', 'true', 'yes')
SESSION_LIFETIME_HOURS = int(os.getenv('CRC_SESSION_HOURS', '8'))
REGISTRATION_ENABLED = os.getenv('CRC_ALLOW_REGISTRATION', '1').lower() in ('1', 'true', 'yes')
REGISTRATION_REQUIRES_APPROVAL = os.getenv('CRC_REGISTRATION_REQUIRES_APPROVAL', '1').lower() in ('1', 'true', 'yes')
DEFAULT_REGISTRATION_ROLE = 'viewer'
ADMIN_INITIAL_PASSWORD = (os.getenv('CRC_ADMIN_PASSWORD') or '').strip()
ADMIN_INITIAL_PASSWORD_FILE = os.path.join(DATA_DIR, '.admin_initial_password')
MAX_UPLOAD_MB = int(os.getenv('CRC_MAX_UPLOAD_MB', '16'))
MAX_EXCEL_UNCOMPRESSED_MB = int(os.getenv('CRC_MAX_EXCEL_UNCOMPRESSED_MB', '100'))
SQL_DUMP_PATH = os.path.join(BASE_DIR, 'crc_prospect.sql.enc')
SQL_PLAIN_PATH = os.path.join(BASE_DIR, 'crc_prospect.sql')
SEED_FILE = os.path.join(DATA_DIR, 'prospect_seed.json')

MFA_ENABLED = os.getenv('CRC_MFA_ENABLED', '1').lower() in ('1', 'true', 'yes')
MFA_REQUIRED = MFA_ENABLED and os.getenv('CRC_MFA_REQUIRED', '0').lower() in ('1', 'true', 'yes')
MFA_ISSUER = os.getenv('CRC_MFA_ISSUER', 'CRC Prospect Theory Research').strip() or 'CRC Prospect Theory Research'
MFA_VALID_WINDOW = max(0, min(2, int(os.getenv('CRC_MFA_VALID_WINDOW', '1'))))
MFA_SESSION_TTL_SECONDS = max(120, int(os.getenv('CRC_MFA_SESSION_TTL_SECONDS', '600')))
MFA_RECOVERY_CODE_COUNT = max(4, min(20, int(os.getenv('CRC_MFA_RECOVERY_CODE_COUNT', '8'))))
SSO_ENABLED = os.getenv('CRC_SSO_ENABLED', '0').lower() in ('1', 'true', 'yes')
SSO_PROVIDER_NAME = (os.getenv('CRC_SSO_PROVIDER_NAME', 'Single Sign-On') or 'Single Sign-On').strip()
SSO_DISCOVERY_URL = (os.getenv('CRC_SSO_DISCOVERY_URL') or '').strip()
SSO_CLIENT_ID = (os.getenv('CRC_SSO_CLIENT_ID') or '').strip()
SSO_CLIENT_SECRET = (os.getenv('CRC_SSO_CLIENT_SECRET') or '').strip()
SSO_SCOPE = (os.getenv('CRC_SSO_SCOPE', 'openid profile email') or 'openid profile email').strip()
SSO_SUBJECT_CLAIM = (os.getenv('CRC_SSO_SUBJECT_CLAIM', 'sub') or 'sub').strip()
SSO_USERNAME_CLAIM = (os.getenv('CRC_SSO_USERNAME_CLAIM', 'preferred_username') or 'preferred_username').strip()
SSO_NAME_CLAIM = (os.getenv('CRC_SSO_NAME_CLAIM', 'name') or 'name').strip()
SSO_EMAIL_CLAIM = (os.getenv('CRC_SSO_EMAIL_CLAIM', 'email') or 'email').strip()
SSO_AUTO_CREATE = os.getenv('CRC_SSO_AUTO_CREATE', '0').lower() in ('1', 'true', 'yes')
SSO_LINK_BY_USERNAME = os.getenv('CRC_SSO_LINK_BY_USERNAME', '0').lower() in ('1', 'true', 'yes')
SSO_TRUST_IDP_MFA = os.getenv('CRC_SSO_TRUST_IDP_MFA', '0').lower() in ('1', 'true', 'yes')
SSO_DEFAULT_ROLE = 'viewer'
SSO_DEFAULT_STATUS = 'pending'
SSO_USE_PKCE = os.getenv('CRC_SSO_USE_PKCE', '1').lower() in ('1', 'true', 'yes')
SSO_TOKEN_AUTH_METHOD = (os.getenv('CRC_SSO_TOKEN_AUTH_METHOD', 'client_secret_basic') or 'client_secret_basic').strip()
LOGIN_MAX_FAILURES = int(os.getenv('CRC_LOGIN_MAX_FAILURES', '5'))
LOGIN_WINDOW_SECONDS = int(os.getenv('CRC_LOGIN_WINDOW_SECONDS', '900'))
LOGIN_LOCK_SECONDS = int(os.getenv('CRC_LOGIN_LOCK_SECONDS', '900'))
REGISTER_MAX_PER_HOUR = int(os.getenv('CRC_REGISTER_MAX_PER_HOUR', '5'))

RESEARCH_TITLE = 'Behavioral Mechanisms of Colonoscopy Screening in High-Risk Colorectal Cancer Populations'
RESEARCH_SUBTITLE = 'Prospect Theory-Based Colonoscopy Screening Decision Study'
THEORY_NAME = 'Prospect Theory'
MODEL_VERSION = 'prospect-crc-v1'
DEFAULT_SEED = 20260929
DEFAULT_N = 1600
HIGH_RISK_SOURCES = ['Questionnaire-positive', 'FIT-positive', 'Questionnaire- and FIT-positive']
EDUCATION_LEVELS = ['No formal schooling', 'Primary school', 'Junior high school', 'Senior high school/Technical secondary school', 'College/Associate degree', 'Postgraduate or above']
MARITAL_STATUSES = ['Never married', 'Married', 'Widowed', 'Divorced', 'Other']
INSURANCE_TYPES = ['Employee Basic Medical Insurance', 'Urban and Rural Residents Basic Medical Insurance', 'Government-Funded Medical Care', 'Commercial Health Insurance', 'Medical Assistance', 'Other', 'Not insured', 'Unknown']
LIVING_STATUSES = ['Living with children', 'Living with spouse', 'Living with spouse, children, and other relatives', 'Living alone']
OCCUPATIONS = ['Agriculture, forestry, animal husbandry, or fishing worker', 'Industrial worker', 'Administrative or managerial personnel', 'Professional or technical personnel', 'Sales or service worker', 'Homemaker', 'Private business owner', 'Retired or former worker', 'Unemployed or laid off', 'Other']
INCOME_LEVELS = ['<20,000 CNY', '20,000-39,999 CNY', '40,000-59,999 CNY', '60,000-79,999 CNY', '80,000-149,999 CNY', '>=150,000 CNY', 'Not sure']
COST_REFERENCE = ['<300 CNY', '300-500 CNY', '500-1,000 CNY', '>=1,000 CNY']
BARRIERS = ['High cost', 'No time/Difficulty taking leave', 'Long travel distance', 'No companion', 'Limited knowledge about screening', 'Worry or fear', 'No trusted doctor', 'Lack of family support', 'No symptoms', 'Other']
HOSPITAL_LEVELS = ['County-level hospital or below', 'Municipal hospital', 'Provincial hospital', 'Other']
OUTCOMES = ['Definitely undergo colonoscopy', 'Delay or decline for now', 'Needs further intervention']

PROSPECT_CONSTRUCTS = [
    ('belief_structure', 'Belief structure'),
    ('risk_preference', 'Risk preference'),
    ('representative_bias', 'Representativeness heuristic bias'),
    ('availability_bias', 'Availability heuristic bias'),
    ('anchoring_adjustment', 'Anchoring and adjustment bias'),
    ('certainty_effect', 'Certainty effect'),
    ('reflection_effect', 'Reflection effect'),
    ('isolation_effect', 'Isolation effect'),
    ('health_value_account', 'Health value account'),
    ('disease_cognition', 'Disease cognition'),
    ('health_literacy', 'Health literacy'),
    ('self_efficacy', 'General self-efficacy'),
    ('service_accessibility', 'Service accessibility'),
    ('decision_reference', 'Decision reference point'),
    ('screening_intention', 'Screening intention'),
    ('screening_behavior', 'Screening behavior'),
]

PUBLIC_SOURCES = [
    ('National Cancer Center', 'https://www.chinancpcn.org.cn/'),
    ('National Health Commission', 'http://www.nhc.gov.cn/'),
    ('China Center for Disease Control and Prevention', 'https://www.chinacdc.cn/'),
]