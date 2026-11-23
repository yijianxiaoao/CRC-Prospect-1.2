# Questionnaire-to-Data Model and Page Mapping

Source file: `Prospect Theory-Formal Questionnaire (1).doc`. Names, national ID numbers, contact numbers, and signatures are used only for on-site informed consent and identity verification. They are not stored in the platform database.

## Part 1: General Information

| Question number | Content | Data field / construct | Page |
| --- | --- | --- | --- |
| 1.3-1.4 | Sex and age | gender, age, age_group | Study Participants and Baseline |
| 1.5 | Education level | education, education_years | Study Participants and Baseline |
| 1.6 | Marital status | marital | Study Participants and Baseline |
| 1.7 | Medical insurance | insurance | Study Participants and Baseline |
| 1.8 | History of malignancy | prior_malignancy | Study Participants and Baseline |
| 1.9-1.9.4 | First-degree relative with colorectal cancer and age at onset | family_crc, family_relations, early_onset | Study Participants and Baseline |
| 1.10-1.10.1 | Chronic disease and type | chronic_disease, chronic_types | Study Participants and Baseline |
| 1.11-1.13 | Living arrangement, occupation, and income | living_status, occupation, income_2025 | Study Participants and Baseline |
| 1.14 | Reasonable cost reference | acceptable_cost | Decision reference point |
| 1.15-1.17 | Discussion partner, family doctor, and relatives or friends who are health workers | discuss_with, family_doctor, health_worker_relative | Service accessibility |
| 1.18-1.19 | Knowledge of intestinal diseases and awareness of early colonoscopy screening | bowel_knowledge, colonoscopy_early_detection | Disease cognition |
| 1.20-1.21 | Health score and medical satisfaction | health_score, medical_satisfaction | Perceived health and service evaluation |

## Part 2: Screening Willingness and Prior Experience

| Question number | Content | Data field / construct |
| --- | --- | --- |
| 2.1 | Willingness to undergo colonoscopy in the next six months | intention_6m, screening_intention |
| 2.1.1 | Hospital-level choice | hospital_level |
| 2.1.2 | Barriers to screening | barriers |
| 2.3-2.4 | Prior colonoscopy/FIT experience and its influence | prior_colonoscopy_count, prior_fit_count, prior_experience_effect |

## Part 3: Scenario Experiment

| Question number | Theoretical dimension | Derived indicator |
| --- | --- | --- |
| 3.1-3.4 | Representativeness heuristic bias | representative_bias |
| 3.5-3.6 | Availability heuristic bias | availability_bias |
| 3.7-3.11 | Anchoring and adjustment, disease cognition, and cost reference | anchoring_adjustment, decision_reference |
| 3.12, 3.14, 3.15, 3.17 | Certainty effect | certainty_effect, risk_aversion |
| 3.13, 3.16, 3.18 | Reflection effect and loss framing | reflection_effect |
| 3.13, 3.15, 3.16 | Isolation effect | isolation_effect |
| 3.19, 3.21, 3.22 | Response to positive information framing | positive_frame_response |
| 3.20 | Response to negative risk-information framing | negative_frame_response |

## Part 4: Health Literacy

Three items are coded as `HL1-HL3`, with scores ranging from 1 to 5. The analysis reports Cronbach's alpha, CITC, and EFA for the total Health Literacy Scale.

## Part 5: General Self-Efficacy

Ten items are coded as `SE1-SE10`, with scores ranging from 1 to 4. The analysis covers internal consistency, item-total score correlations, and single-factor structure.

## Privacy and Security

- Names, national ID numbers, contact information, signatures, and addresses are not imported into the database.
- Study IDs are regenerated during import and checked for uniqueness.
- The original questionnaires should be stored in a restricted physical space or an encrypted directory.
- Exported data contain only de-identified variables.
