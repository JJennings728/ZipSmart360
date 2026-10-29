-- AeroCIE phase 24 | synthetic general aviation underwriting research.
-- SQLite 3.25+ supports window functions. This schema does not infer insurance coverage or premium.
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS source_registry (
  source_id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  dataset_name TEXT NOT NULL,
  source_url TEXT,
  source_as_of TEXT NOT NULL,
  retrieved_at TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL CHECK(length(payload_sha256)=64),
  license_status TEXT NOT NULL,
  is_synthetic INTEGER NOT NULL DEFAULT 1 CHECK(is_synthetic=1)
);
-- Local snapshot records catch edits to fixed synthetic dimensions and the model policy.
CREATE TABLE IF NOT EXISTS dataset_integrity (
  dataset_name TEXT PRIMARY KEY,
  payload_sha256 TEXT NOT NULL CHECK(length(payload_sha256)=64)
);
CREATE TABLE IF NOT EXISTS dim_aircraft (
  aircraft_id TEXT PRIMARY KEY,
  registration TEXT NOT NULL UNIQUE,
  manufacturer TEXT NOT NULL,
  model TEXT NOT NULL,
  category TEXT NOT NULL CHECK(category IN ('FIXED_WING','ROTOR_WING','BUSINESS_JET')),
  year_built INTEGER CHECK(year_built BETWEEN 1940 AND 2100),
  composite_material_flag INTEGER NOT NULL CHECK(composite_material_flag IN (0,1))
);
CREATE TABLE IF NOT EXISTS dim_pilot (
  pilot_id TEXT PRIMARY KEY,
  certificate_level TEXT NOT NULL,
  total_flight_hours INTEGER CHECK(total_flight_hours>=0),
  make_model_hours INTEGER CHECK(make_model_hours>=0),
  recurrent_training_verified INTEGER CHECK(recurrent_training_verified IN (0,1))
);
CREATE TABLE IF NOT EXISTS dim_mro_facility (
  facility_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  region TEXT NOT NULL,
  country_code TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fact_mro_constraints (
  constraint_id TEXT PRIMARY KEY,
  facility_id TEXT NOT NULL REFERENCES dim_mro_facility(facility_id),
  manufacturer TEXT NOT NULL,
  model TEXT NOT NULL,
  as_of TEXT NOT NULL,
  repair_wait_days INTEGER NOT NULL CHECK(repair_wait_days>=0),
  parts_availability_index REAL NOT NULL CHECK(parts_availability_index>=0 AND parts_availability_index<=1),
  parts_cost_index REAL NOT NULL CHECK(parts_cost_index>=0),
  source_id TEXT NOT NULL REFERENCES source_registry(source_id)
);
CREATE INDEX IF NOT EXISTS idx_mro_latest ON fact_mro_constraints(manufacturer,model,facility_id,as_of DESC);
CREATE TABLE IF NOT EXISTS fact_underwriting_submissions (
  submission_id TEXT PRIMARY KEY,
  submitted_on TEXT NOT NULL,
  aircraft_id TEXT NOT NULL REFERENCES dim_aircraft(aircraft_id),
  pilot_id TEXT REFERENCES dim_pilot(pilot_id),
  operation_type TEXT NOT NULL,
  annual_flight_hours INTEGER CHECK(annual_flight_hours>=0),
  losses_last_five_years INTEGER CHECK(losses_last_five_years>=0),
  requested_hull_value_usd INTEGER CHECK(requested_hull_value_usd>0),
  source_id TEXT NOT NULL REFERENCES source_registry(source_id)
);
CREATE INDEX IF NOT EXISTS idx_submission_model ON fact_underwriting_submissions(aircraft_id,pilot_id);
-- Incident counts are model-wide aggregates; they do not identify a pilot or imply an individual's claims history.
CREATE TABLE IF NOT EXISTS fact_ntsb_model_context (
  context_id TEXT PRIMARY KEY,
  manufacturer TEXT NOT NULL,
  model TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  event_count INTEGER NOT NULL CHECK(event_count>=0),
  denominator_flight_hours INTEGER CHECK(denominator_flight_hours>0),
  source_id TEXT NOT NULL REFERENCES source_registry(source_id)
);
-- Synthetic SWIM-like operational counts, not FAA-maintenance or pilot-history data.
CREATE TABLE IF NOT EXISTS fact_swim_operations (
  observation_id TEXT PRIMARY KEY,
  manufacturer TEXT NOT NULL,
  model TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  operations_count INTEGER NOT NULL CHECK(operations_count>=0),
  source_id TEXT NOT NULL REFERENCES source_registry(source_id)
);
CREATE TABLE IF NOT EXISTS model_policy (
  policy_id TEXT PRIMARY KEY,
  policy_version TEXT NOT NULL,
  quote_max_risk_points INTEGER NOT NULL,
  decline_review_min_risk_points INTEGER NOT NULL,
  approved_for_automatic_binding INTEGER NOT NULL DEFAULT 0 CHECK(approved_for_automatic_binding=0),
  note TEXT NOT NULL
);
-- Latest observation per facility and model. Historical snapshots are retained for provenance.
CREATE VIEW IF NOT EXISTS v_mro_latest AS
SELECT constraint_id,facility_id,manufacturer,model,as_of,repair_wait_days,
       parts_availability_index,parts_cost_index,source_id,
       (2.0-parts_availability_index) AS shortage_weight
FROM (
 SELECT m.*,ROW_NUMBER() OVER(PARTITION BY facility_id,manufacturer,model ORDER BY as_of DESC,constraint_id DESC) rn
 FROM fact_mro_constraints m
) WHERE rn=1;
-- No MRO record produces NULL severity rather than a falsely safe zero.
CREATE VIEW IF NOT EXISTS v_mro_model_metrics AS
SELECT manufacturer,model,COUNT(*) AS facility_count,MAX(as_of) AS latest_observation, MIN(as_of) AS oldest_observation,
 ROUND(SUM(repair_wait_days*shortage_weight)/NULLIF(SUM(shortage_weight),0),2) AS mro_severity_days,
 ROUND(SUM(parts_cost_index*shortage_weight)/NULLIF(SUM(shortage_weight),0),3) AS mro_cost_pressure_index,
 ROUND(AVG(parts_availability_index),3) AS mean_parts_availability,
 COUNT(DISTINCT source_id) AS provenance_source_count
FROM v_mro_latest GROUP BY manufacturer,model;
CREATE VIEW IF NOT EXISTS v_submission_features AS
SELECT s.submission_id,s.submitted_on,s.operation_type,s.annual_flight_hours,
 s.losses_last_five_years,s.requested_hull_value_usd,s.source_id AS submission_source_id,
 a.aircraft_id,a.registration,a.manufacturer,a.model,a.category,a.year_built,
 CAST(substr(s.submitted_on,1,4) AS INTEGER)-a.year_built AS aircraft_age_years,
 a.composite_material_flag,p.pilot_id,p.certificate_level,p.total_flight_hours,
 p.make_model_hours,p.recurrent_training_verified,m.facility_count,m.mro_severity_days,
 m.mro_cost_pressure_index,m.mean_parts_availability,m.latest_observation,m.oldest_observation,
 CASE WHEN p.pilot_id IS NULL OR p.total_flight_hours IS NULL OR p.make_model_hours IS NULL
 OR p.recurrent_training_verified IS NULL OR a.year_built IS NULL
 OR s.losses_last_five_years IS NULL OR m.mro_severity_days IS NULL
 OR s.annual_flight_hours IS NULL
 OR s.requested_hull_value_usd IS NULL
 OR m.mro_cost_pressure_index IS NULL
 OR a.year_built > CAST(substr(s.submitted_on,1,4) AS INTEGER)
 OR p.make_model_hours > p.total_flight_hours
 OR date(s.submitted_on) IS NULL
 OR m.latest_observation < date(s.submitted_on,'-30 days')
 OR m.oldest_observation < date(s.submitted_on,'-30 days')
 OR m.latest_observation > s.submitted_on
 THEN 1 ELSE 0 END AS insufficient_evidence
FROM fact_underwriting_submissions s JOIN dim_aircraft a ON a.aircraft_id=s.aircraft_id
LEFT JOIN dim_pilot p ON p.pilot_id=s.pilot_id
LEFT JOIN v_mro_model_metrics m ON m.manufacturer=a.manufacturer AND m.model=a.model;
CREATE VIEW IF NOT EXISTS v_triage_factors AS
SELECT f.*,
CASE WHEN insufficient_evidence=1 THEN NULL
 WHEN aircraft_age_years>30 THEN 20 WHEN aircraft_age_years>15 THEN 10 ELSE 0 END AS age_points,
CASE WHEN insufficient_evidence=1 THEN NULL
 WHEN total_flight_hours<500 THEN 18 WHEN total_flight_hours<1500 THEN 8 ELSE 0 END AS total_time_points,
CASE WHEN insufficient_evidence=1 THEN NULL
 WHEN make_model_hours<25 THEN 18 WHEN make_model_hours<100 THEN 8 ELSE 0 END AS type_time_points,
CASE WHEN insufficient_evidence=1 THEN NULL
 WHEN losses_last_five_years>=2 THEN 30 WHEN losses_last_five_years=1 THEN 15 ELSE 0 END AS loss_points,
CASE WHEN insufficient_evidence=1 THEN NULL
 WHEN mro_severity_days>60 THEN 20 WHEN mro_severity_days>30 THEN 10 ELSE 0 END AS mro_points,
CASE WHEN insufficient_evidence=1 THEN NULL
 WHEN composite_material_flag=1 THEN 5 ELSE 0 END AS composite_points,
CASE WHEN insufficient_evidence=1 THEN NULL
 WHEN recurrent_training_verified=0 THEN 10 ELSE 0 END AS training_points
FROM v_submission_features f;
CREATE VIEW IF NOT EXISTS v_submission_triage AS
WITH scores AS (
SELECT f.*,
CASE WHEN insufficient_evidence=1 THEN NULL ELSE MIN(100,
 age_points+total_time_points+type_time_points+loss_points+mro_points+composite_points+training_points)
END AS risk_points
FROM v_triage_factors f)
SELECT s.*,
CASE WHEN risk_points IS NULL THEN 'Refer'
 WHEN risk_points <= (SELECT quote_max_risk_points FROM model_policy WHERE policy_id='SYNTHETIC_V1') THEN 'Quote'
 WHEN risk_points >= (SELECT decline_review_min_risk_points FROM model_policy WHERE policy_id='SYNTHETIC_V1') THEN 'Decline'
 ELSE 'Refer' END AS triage_recommendation,
'UNDERWRITER_REVIEW_REQUIRED' AS decision_authority,
'SYNTHETIC_HEURISTIC_NOT_PRICING_MODEL' AS model_scope
FROM scores s;

-- Illustrative scenario sensitivity only. Values are assumptions, not estimated claims
-- or identified pricing gaps. Source fields and review status stay visible.
CREATE VIEW IF NOT EXISTS v_severity_scenarios AS
SELECT submission_id, manufacturer, model, category, triage_recommendation,
       decision_authority, insufficient_evidence, submitted_on,
       requested_hull_value_usd, mro_severity_days, mro_cost_pressure_index,
       oldest_observation, latest_observation, submission_source_id,
       CASE WHEN insufficient_evidence = 1 OR requested_hull_value_usd IS NULL
             OR mro_severity_days IS NULL OR mro_cost_pressure_index IS NULL
            THEN NULL ELSE ROUND(
              mro_severity_days * 100.0 + requested_hull_value_usd * 0.0025 *
              MAX(mro_cost_pressure_index - 1.0, 0.0), 0) END AS scenario_low_usd,
       CASE WHEN insufficient_evidence = 1 OR requested_hull_value_usd IS NULL
             OR mro_severity_days IS NULL OR mro_cost_pressure_index IS NULL
            THEN NULL ELSE ROUND(
              mro_severity_days * 250.0 + requested_hull_value_usd * 0.005 *
              MAX(mro_cost_pressure_index - 1.0, 0.0), 0) END AS scenario_base_usd,
       CASE WHEN insufficient_evidence = 1 OR requested_hull_value_usd IS NULL
             OR mro_severity_days IS NULL OR mro_cost_pressure_index IS NULL
            THEN NULL ELSE ROUND(
              mro_severity_days * 500.0 + requested_hull_value_usd * 0.010 *
              MAX(mro_cost_pressure_index - 1.0, 0.0), 0) END AS scenario_high_usd,
       'SYNTHETIC_ASSUMPTION_NOT_CLAIM_FORECAST' AS scenario_basis,
       'NOT_DETERMINED_WITHOUT_PREMIUM_AND_VALIDATED_LOSS_MODEL' AS pricing_adequacy_status
FROM v_submission_triage;
