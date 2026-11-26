# Behavioral Mechanisms of Colonoscopy Screening in High-Risk Colorectal Cancer Populations: Prospect Theory Edition

The platform maps the editing stage, evaluation stage, value function, weighting function, reference points, systematic biases, and risk preferences of prospect theory to willingness to undergo colonoscopy screening and actual screening behavior among high-risk colorectal cancer populations.

| Software | Requirement | Purpose | Official Download |
|---|---|---|---|
| **Python 3.12 (64-bit)** | Required | Runs the Flask application and installs Python dependencies | [Download Python](https://www.python.org/downloads/windows/) |
| **MySQL Community Server 8.0/8.4 LTS** | Required | Stores research data and account information | [Download MySQL Installer](https://dev.mysql.com/downloads/installer/) · [Download MySQL Server](https://dev.mysql.com/downloads/mysql/) |
| **Microsoft Edge or Google Chrome** | Required | Accesses the web application | [Download Google Chrome](https://www.google.com/chrome/) |
| **PyCharm Community / PyCharm** | Optional, recommended | Edits code, configures the Python environment, and runs the project | [Download PyCharm](https://www.jetbrains.com/pycharm/download/) |





## 1. Theoretical Framework

The model has four layers:

1. **Individual and external factors**: age, sex, education, marital status, medical insurance, income, family history, chronic disease, health literacy, self-efficacy, service accessibility, and policy support.
2. **Information cognition and editing**: representativeness heuristic, availability heuristic, anchoring and adjustment, disease cognition, health value accounts, and cost/time/risk reference points.
3. **Evaluation and preference**: certainty effect, reflection effect, isolation effect, and risk aversion.
4. **Screening decision outcomes**: screening intention over the next six months, hospital level, screening method, timing decision, and actual colonoscopy participation.

The theoretical pathway is:

```text
Individual and external factors + Systematic biases
        ↓
Belief structure + Risk preference → Decision reference point
        ↓
Screening intention → Actual screening behavior
```

## 2. Questionnaire-to-System Variable Mapping

| Questionnaire section | System variables | Research location |
| --- | --- | --- |
| 1.1-1.2 Name, national ID number | Not stored in the database | Privacy protection |
| 1.3-1.14 | Sex, age, education, marital status, medical insurance, family history, chronic disease, occupation, income, cost reference | `t_subject` |
| 1.15-1.21 | Discussion partner, family doctor, health promotion, knowledge, health score, medical satisfaction | `t_subject` |
| 2.1-2.4 | Screening intention, hospital level, barriers, prior colonoscopy/FIT experience | `t_screening_decision` |
| 3.1-3.11 | Representativeness, availability, anchoring and adjustment, disease cognition, cost reference | `t_scenario_response` |
| 3.12-3.18 | Certainty and probability choices, gain/loss framing, time preference | `t_scenario_response` |
| 3.19-3.22 | Screening choices under risk-information and benefit-information framing | `t_scenario_response` |
| 4.1-4.3 | Brief Health Literacy Scale | `t_health_literacy` |
| 5.1-5.10 | General Self-Efficacy Scale | `t_self_efficacy` |

Names, national ID numbers, contact information, signatures, and residential addresses are not written to the study database. The import process detects and rejects these fields.

## 3. Main Functional Modules

- **Dashboard**: study participants, screening willingness, actual screening, bias levels, and main barriers.
- **Study Participants and Baseline**: demographics, region, medical insurance, income, family history, and health status.
- **Screening Willingness and Outcomes**: willingness, prior screening experience, barriers, and behavioral outcomes.
- **Scenario-Based Decisions**: response distributions for questions 3.1-3.22.
- **Systematic Biases**: representativeness, availability, anchoring and adjustment, certainty, reflection, and isolation effects.
- **Risk Preference**: risk aversion, certainty and probability choices, and loss/gain framing.
- **Constructs and Correlation Matrix**: for path analysis and structural equation modeling.
- **Decision Path Model**: standardized path coefficients and model explanatory power.
- **Structural Equation Model**: chi-square/df, CFI, TLI, RMSEA, and SRMR.
- **Probit Analysis**: regression coefficients, average marginal effects (AMEs), AIC/BIC, and McFadden's R-squared.
- **Forest Plot**: crude ORs, adjusted ORs, and subgroup effects by region, education, medical insurance, and high-risk source.
- **Scale Reliability and Validity**: Cronbach's alpha, CITC, and EFA for the health literacy and general self-efficacy scales.
- **Questionnaire Data Import and Quality Control**: CSV/XLSX import, template download, PII blocking, and row-level transactions.
- **Audit and Account Management**: RBAC, MFA, SSO, account approval, and a tamper-evident audit chain.

## 4. Data Tables

| Table | Purpose |
| --- | --- |
| `t_subject` | De-identified study participants and general information |
| `t_screening_decision` | Screening willingness, prior experience, and actual behavior |
| `t_disease_cognition` | Disease cognition, health value accounts, and decision reference points |
| `t_scenario_response` | Raw responses to 22 scenario-experiment questions and derived prospect theory scores |
| `t_health_literacy` | Brief Health Literacy Scale items |
| `t_self_efficacy` | General Self-Efficacy Scale items |
| `t_prospect_construct` | Latent variables used by SEM, Probit, and forest plots |
| `t_audit` | HMAC-protected tamper-evident audit log |
| `t_data_lock` | Data lock records |
| `t_user` | Platform accounts and authentication information |

## 5. Simulated Data

The project uses reproducible simulated data. The data-generating function is located at:

```text
app/service/seed.py
```

By default, it generates 1,600 simulated study participants. The random seed is `20260929`. The model includes the following relationships:

- Representativeness, availability, and anchoring biases reduce screening intention.
- Health literacy, self-efficacy, disease cognition, and service accessibility increase willingness to undergo screening.
- Decision reference points and policy support promote conversion from intention to behavior.
- Certainty and reflection effects alter risk choices and screening behavior.

## 6. Running the Platform

Use a Python virtual environment and install the dependencies:

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py init
.\.venv\Scripts\python.exe manage.py seed
.\.venv\Scripts\python.exe manage.py status
.\.venv\Scripts\python.exe run.py
```

The default address is `http://127.0.0.1:5012`.

## 7. Database and Security

- Default database: `crc_prospect_en`.
- Application database account: `crc_app`.
- Local credential files are stored in `app/data/` and must not be committed to version control.
- The platform supports MFA, OIDC single sign-on, account approval, and configurable self-registration.
- Account creation, import, review, export, and account-management actions are written to the audit log.
- Data import and research-data writes are blocked while data are locked.

## 8. Important Notice

This project uses simulated data to demonstrate prospect-theory decision-making mechanisms and platform functions. It must not be used for clinical diagnosis or real-world policy inference. Formal applications require ethics-approved questionnaire data and compliance with data-minimization and local privacy regulations.
