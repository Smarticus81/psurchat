# PSUR Evidence Types -- 100% Coverage Checklist

This document lists every evidence type required to fully populate all 13 PSUR sections,
cover page fields, data tables (MDCG 2022-21 Annex II), and charts. Each item maps to the
PSURContext field(s) it feeds, the section(s) it supports, and the expected file format.

---

## 1. COVER PAGE / SESSION SETUP (Master Context)

These are entered manually during session setup or extracted from uploaded documents.

| # | Evidence Type | PSURContext Field(s) | Format | Required |
|---|---|---|---|---|
| 1.1 | Manufacturer Name | `manufacturer` | Text | Yes |
| 1.2 | Manufacturer Address | `manufacturer_address` | Text | Yes |
| 1.3 | Single Registration Number (SRN) | `manufacturer_srn` | Text | EU/UK only |
| 1.4 | Authorised Representative Name | `authorized_rep` | Text | EU/UK only |
| 1.5 | Authorised Representative Address | `authorized_rep_address` | Text | No |
| 1.6 | Notified Body Name | `notified_body` | Text | EU/UK only |
| 1.7 | Notified Body Number | `notified_body_number` | Text | EU/UK only |
| 1.8 | Certificate Number | (cover page only) | Text | No |
| 1.9 | PSUR Cadence | `psur_cadence` | Text | Yes |
| 1.10 | Reporting Period Start Date | `period_start` | Date | Yes |
| 1.11 | Reporting Period End Date | `period_end` | Date | Yes |
| 1.12 | PSUR Sequence Number | `psur_sequence_number` | Integer | Yes |
| 1.13 | Template / Regulatory Framework | `template_id` | Selection (eu_uk_mdr / non_ce) | Yes |

---

## 2. DEVICE IDENTIFICATION

| # | Evidence Type | PSURContext Field(s) | Format | Sections |
|---|---|---|---|---|
| 2.1 | Device Name | `device_name` | Text | A, B |
| 2.2 | Device Variants / Models | `device_variants` | List of strings | A |
| 2.3 | UDI-DI | `udi_di` | Text | A, B |
| 2.4 | Intended Use / Purpose | `intended_use` | Text | A, B |
| 2.5 | Device Type | `device_type` | Text | A, B |
| 2.6 | Regulatory Classification(s) | `regulatory_classification` | Dict (system -> class) | A, B |
| 2.7 | Sterilization Method | `sterilization_method` | Text | A |
| 2.8 | Submission Deadline | `submission_deadline` | Date | Cover |

---

## 3. SALES / DISTRIBUTION DATA (Section C)

**File type tag:** `sales`
**Accepted formats:** CSV, Excel (.xls/.xlsx)
**Agent:** Raj
**Required columns detected:** units, year, region

| # | Evidence Type | PSURContext Field(s) | Required Columns | Tables/Charts |
|---|---|---|---|---|
| 3.1 | Annual units distributed | `total_units_sold`, `total_units_by_year` | units, year | Table 1 chart, complaint rate denominator |
| 3.2 | Regional distribution breakdown | `total_units_by_region`, `regions` | units, region | Table 2 chart |
| 3.3 | Cumulative units (all time) | `cumulative_units_all_time` | units | Section C narrative |

**Column keywords recognized:**
- Units: units, quantity, qty, sold, distributed, shipped, volume, devices, amount
- Year: year, date, period, fiscal, quarter, month, ship_date, sale_date
- Region: region, country, market, territory, geography, location

---

## 4. COMPLAINT DATA (Sections E, F)

**File type tag:** `complaints`
**Accepted formats:** CSV, Excel (.xls/.xlsx)
**Agent:** Carla
**Required columns detected:** type, severity, root_cause, closure, year, description

| # | Evidence Type | PSURContext Field(s) | Required Columns | Tables/Charts |
|---|---|---|---|---|
| 4.1 | Complaint records (one row per complaint) | `total_complaints` | (row count) | All complaint tables |
| 4.2 | Complaint type/category | `complaints_by_type` | type/category column | Type breakdown chart |
| 4.3 | Complaint severity | `complaints_by_severity` | severity column | Severity distribution chart |
| 4.4 | Root cause determination | `complaints_product_defect`, `complaints_user_error`, `complaints_unrelated`, `complaints_unconfirmed`, `complaints_with_root_cause_identified` | root_cause column | Root cause distribution chart |
| 4.5 | Investigation closure status | `complaints_closed_count`, `investigation_closure_rate` | closure/status column | Section F narrative |
| 4.6 | Complaint date/year | `total_complaints_by_year`, `complaint_rate_by_year` | year/date column | Table 3 chart, complaint rate trend |
| 4.7 | Complaint description/narrative | (raw sample for agents) | description column | Agent context |

**Column keywords recognized:**
- Type: type, category, classification, complaint_type, issue_type, event_type
- Severity: severity, priority, criticality, harm, seriousness, risk_level, patient_impact
- Root Cause: root, cause, determination, root_cause, failure_mode, investigation_result
- Closure: closed, closure, status, investigation, resolved, disposition, case_status
- Description: description, narrative, detail, summary, text, notes

---

## 5. VIGILANCE / SERIOUS INCIDENT DATA (Section D)

**File type tag:** `vigilance`
**Accepted formats:** CSV, Excel (.xls/.xlsx)
**Agent:** Vera
**Required columns detected:** type, severity

| # | Evidence Type | PSURContext Field(s) | Required Columns | Tables/Charts |
|---|---|---|---|---|
| 5.1 | Vigilance event records | `total_vigilance_events` | (row count) | Table 4, 5, 6 |
| 5.2 | Incident type classification | `serious_incidents_by_type` | type column | Table 5 pie chart |
| 5.3 | Severity classification | `serious_incidents`, `deaths`, `serious_injuries` | severity column | Table 4 bar chart |

**Severity keywords that flag "serious":** serious, death, fatal, life-threatening, hospitalization, permanent, critical, severe

---

## 6. GOLDEN SOURCE / MASTER CONTEXT OVERRIDES

These are set during session setup or calculated from uploaded data. They enforce cross-section consistency.

| # | Evidence Type | PSURContext Field(s) | Source |
|---|---|---|---|
| 6.1 | Exposure denominator (golden) | `exposure_denominator_golden` | Calculated or manual override |
| 6.2 | Exposure denominator scope | `exposure_denominator_scope` | Selection (reporting_period_only / cumulative) |
| 6.3 | Annual units (golden) | `annual_units_golden` | Calculated from sales data |
| 6.4 | Closure definition text | `closure_definition_text` | Manual entry |
| 6.5 | Canonical complaints closed count | `complaints_closed_canonical` | Manual override or calculated |
| 6.6 | Inference policy | `inference_policy` | Selection (strictly_factual / limited_inference) |
| 6.7 | External vigilance searched (Y/N) | `data_availability_external_vigilance` | Manual entry |
| 6.8 | Complaint closures complete (Y/N) | `data_availability_complaint_closures_complete` | Manual entry |
| 6.9 | RMF hazard list available (Y/N) | `data_availability_rmf_hazard_list` | Manual entry |
| 6.10 | Intended use provided (Y/N) | `data_availability_intended_use` | Auto-detected or manual |

---

## 7. TEXT DOCUMENTS (Sections B, J, K, L)

**File type tags:** `ifu`, `cer`, `rmf`, `pmcf`, `literature`, `general`
**Accepted formats:** DOCX, PDF, TXT
**Agents:** Sam (B), Brianna (J), Eddie (K), Clara (L)

| # | Evidence Type | PSURContext Field(s) | Typical Format | Sections |
|---|---|---|---|---|
| 7.1 | Instructions for Use (IFU) | `text_documents`, `intended_use` (auto-extracted) | DOCX/PDF | B |
| 7.2 | Clinical Evaluation Report (CER) | `text_documents`, `supplementary_raw_samples` | DOCX/PDF | J, L |
| 7.3 | Risk Management File (RMF) / ISO 14971 | `text_documents`, `supplementary_raw_samples`, `known_residual_risks` | DOCX/PDF | H, J |
| 7.4 | PMCF Plan / Report | `text_documents`, `supplementary_raw_samples` | DOCX/PDF | L |
| 7.5 | Literature search results | `text_documents` | DOCX/PDF | J, K |
| 7.6 | Previous PSUR or PMS report | `text_documents`, `previous_psur_safety_concerns`, `previous_psur_recommendations` | DOCX/PDF | B, M |
| 7.7 | Declaration of Conformity | `text_documents` | DOCX/PDF | A, B |
| 7.8 | Regulatory certificates (CE/UKCA) | `text_documents` | PDF | A, B |

---

## 8. SUPPLEMENTARY TABULAR DATA

**File type tags:** `risk`, `cer`, `pmcf`
**Accepted formats:** CSV, Excel (.xls/.xlsx)
**Stored in:** `supplementary_raw_samples`, `supplementary_columns`

| # | Evidence Type | Sections |
|---|---|---|
| 8.1 | Risk management data (hazard table, risk matrix) | H, J |
| 8.2 | CER data tables (clinical evidence summary) | J |
| 8.3 | PMCF data tables (study results, endpoints) | L |

---

## 9. CAPA EVIDENCE (Section I)

| # | Evidence Type | PSURContext Field(s) | Format | Tables/Charts |
|---|---|---|---|---|
| 9.1 | Open CAPA count | `capa_actions_open` | Integer | Table 8 |
| 9.2 | CAPAs closed this period | `capa_actions_closed_this_period` | Integer | Table 8 |
| 9.3 | CAPAs with effectiveness verified | `capa_actions_effectiveness_verified` | Integer | Table 8 |
| 9.4 | CAPA detail records | `capa_details` (list of dicts: id, description, status) | Structured | CAPA details table |

---

## 10. FSCA EVIDENCE (Section H)

| # | Evidence Type | PSURContext Field(s) | Format | Tables/Charts |
|---|---|---|---|---|
| 10.1 | FSCA records (if any) | (via capa_details or narrative) | Structured/Text | Table 7 |
| 10.2 | Field Safety Notice documents | `text_documents` | DOCX/PDF | H |

---

## 11. EXTERNAL DATABASE SEARCH EVIDENCE (Section K)

| # | Evidence Type | PSURContext Field(s) | Format | Tables/Charts |
|---|---|---|---|---|
| 11.1 | FDA MAUDE search results | `data_availability_external_vigilance` | Structured/Text | External DB table |
| 11.2 | BfArM search results | `data_availability_external_vigilance` | Structured/Text | External DB table |
| 11.3 | MHRA search results | `data_availability_external_vigilance` | Structured/Text | External DB table |
| 11.4 | Eudamed search results | `data_availability_external_vigilance` | Structured/Text | External DB table |

---

## 12. PMCF EVIDENCE (Section L)

| # | Evidence Type | PSURContext Field(s) | Format | Sections |
|---|---|---|---|---|
| 12.1 | PMCF plan approval status | `pmcf_plan_approved` | Boolean | L |
| 12.2 | Active PMCF studies | `pmcf_studies_active` | List of strings | L |
| 12.3 | PMCF safety concerns | `pmcf_safety_concerns` | List of strings | L |

---

## 13. TEMPORAL CONTINUITY (Previous PSUR Findings)

| # | Evidence Type | PSURContext Field(s) | Format | Sections |
|---|---|---|---|---|
| 13.1 | Previous PSUR safety concerns | `previous_psur_safety_concerns` | List of strings | B, M |
| 13.2 | Previous PSUR recommendations | `previous_psur_recommendations` | List of strings | M |
| 13.3 | Actions taken on previous findings | `actions_taken_on_previous_findings` | List of strings | M |
| 13.4 | Previous CAPA status summary | `previous_capa_status_summary` | Text | I, M |
| 13.5 | Trending across periods narrative | `trending_across_periods_narrative` | Text | G, M |

---

## 14. RISK MANAGEMENT SIGNALS

| # | Evidence Type | PSURContext Field(s) | Format | Sections |
|---|---|---|---|---|
| 14.1 | Known residual risks | `known_residual_risks` | List of strings | H, J |
| 14.2 | New signals identified | `new_signals_identified` | List of strings | G, M |
| 14.3 | Changed risk profiles | `changed_risk_profiles` | List of strings | H, M |

---

## COVERAGE MATRIX: Evidence to Section Mapping

| Section | Agent | Mandatory Evidence Types | Optional Evidence Types |
|---|---|---|---|
| A (Executive Summary) | Diana | 2.1-2.7, 6.1-6.10 | 7.7, 7.8 |
| B (Scope) | Sam | 2.1-2.6, 7.1, 7.7 | 7.6, 7.8, 13.1 |
| C (Units Distributed) | Raj | 3.1-3.3 | -- |
| D (Serious Incidents) | Vera | 5.1-5.3 | -- |
| E (Customer Feedback) | Carla | 4.1-4.3 | 4.7 |
| F (Complaints Management) | Carla | 4.1, 4.4-4.6 | 4.7 |
| G (Trend Analysis) | Tara | 3.1, 4.6, 5.3 | 13.5, 14.2 |
| H (FSCA) | Frank | 10.1-10.2, 7.3 | 14.1, 14.3 |
| I (CAPA) | Cameron | 9.1-9.4 | 13.4 |
| J (Benefit-Risk / Literature) | Brianna | 7.2, 7.3, 7.5 | 8.1, 8.2, 14.1 |
| K (External Databases) | Eddie | 11.1-11.4 | -- |
| L (PMCF) | Clara | 12.1-12.3, 7.4 | 8.3 |
| M (Overall Conclusions) | Marcus | 6.1-6.10, 13.1-13.3 | 13.4, 13.5, 14.2, 14.3 |

---

## CHARTS AND TABLES GENERATED (Data Dependencies)

| Chart/Table ID | Title | Section | Data Required |
|---|---|---|---|
| table1_units_year | Units Distributed by Year | C | `total_units_by_year` |
| table2_units_region | Units Distributed by Region | C | `total_units_by_region` |
| table3_complaints_year | Complaint Summary by Year | E | `total_complaints_by_year`, `complaint_rate_by_year` |
| table4_si_summary | Serious Incident Summary | D | `deaths`, `serious_injuries`, `serious_incidents` |
| table5_si_type | Serious Incidents by Type | D | `serious_incidents_by_type` |
| table6_si_time | Events Over Time | G | `total_units_by_year`, `total_complaints_by_year` |
| table7_fsca | FSCA Summary | H | `capa_details` |
| table8_capa | CAPA Summary | I | `capa_actions_open`, `capa_actions_closed_this_period`, `capa_actions_effectiveness_verified` |
| trend_complaint_rate | Complaint Rate Trend | G | `complaint_rate_by_year` |
| dist_severity | Severity Distribution | E | `complaints_by_severity` |
| dist_type | Complaint Type Breakdown | E | `complaints_by_type` |
| dist_root_cause | Root Cause Distribution | F | `complaints_product_defect`, `complaints_user_error`, `complaints_unrelated`, `complaints_unconfirmed` |
| classification | Device Classification | A | `regulatory_classification` |
| device_timeline | Device Timeline | A | `device_name`, `udi_di`, `intended_use`, `device_type` |
| model_catalog | Model Catalog | A | `device_variants` |
| sales_by_region | Sales by Region (DOCX table) | C | `total_units_by_year`, `total_units_by_region` |
| serious_incident | Serious Incident (DOCX table) | D | `deaths`, `serious_injuries`, `serious_incidents_by_type` |
| feedback | Customer Feedback (DOCX table) | E | `complaints_by_type`, `complaints_by_severity` |
| complaint_rate | Complaint Rate (DOCX table) | F | `total_complaints_by_year`, `total_units_by_year` |
| fsca | FSCA (DOCX table) | H | `capa_details` |
| capa | CAPA (DOCX table) | I | `capa_actions_*`, `capa_details` |
| external_db | External DB (DOCX table) | K | `data_availability_external_vigilance`, `total_vigilance_events` |

---

## TOTAL EVIDENCE TYPES: 68

- **Manual / Session Setup:** 23 (categories 1, 2, 6)
- **Tabular Data Files:** 13 (categories 3, 4, 5)
- **Text Documents:** 8 (category 7)
- **Supplementary Tabular:** 3 (category 8)
- **CAPA Records:** 4 (category 9)
- **FSCA Records:** 2 (category 10)
- **External DB Searches:** 4 (category 11)
- **PMCF Records:** 3 (category 12)
- **Temporal Continuity:** 5 (category 13)
- **Risk Signals:** 3 (category 14)
