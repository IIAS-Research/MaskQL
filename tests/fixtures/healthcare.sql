\set ON_ERROR_STOP on

-- Entirely synthetic demonstration dataset, with no real patient information.
-- 3 schemas, 10 tables, 3,729 rows: 6 departments, 200 patients, 20 practitioners,
-- 600 encounters, 1,800 observations, 600 prescriptions, 200 clinical notes,
-- 3 studies, 200 consents and 100 enrollments.
-- Medical values and treatments are fictional and have no clinical use.
-- Running this file again adds missing rows without replacing existing ones.

BEGIN;

CREATE SCHEMA IF NOT EXISTS administrative;
CREATE SCHEMA IF NOT EXISTS clinical;
CREATE SCHEMA IF NOT EXISTS research;

CREATE TABLE IF NOT EXISTS administrative.departments (
    department_id SMALLINT PRIMARY KEY,
    code CHAR(6) NOT NULL UNIQUE,
    name TEXT NOT NULL,
    capacity SMALLINT NOT NULL,
    active BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS administrative.patients (
    patient_id BIGINT PRIMARY KEY,
    patient_uuid UUID NOT NULL UNIQUE,
    record_number CHAR(11) NOT NULL UNIQUE,
    patient_number VARCHAR(20) NOT NULL UNIQUE,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    birth_date DATE NOT NULL,
    sex CHAR(1),
    email VARCHAR(120),
    phone VARCHAR(20),
    address TEXT,
    postal_code CHAR(5),
    city VARCHAR(80),
    contact_allowed BOOLEAN,
    preferences JSONB,
    created_at TIMESTAMP(0) NOT NULL
);

CREATE TABLE IF NOT EXISTS administrative.practitioners (
    practitioner_id INTEGER PRIMARY KEY,
    department_id SMALLINT NOT NULL REFERENCES administrative.departments,
    code VARCHAR(12) NOT NULL UNIQUE,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    profession VARCHAR(60) NOT NULL,
    email VARCHAR(120),
    fte NUMERIC(4, 2) NOT NULL,
    active BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS clinical.encounters (
    encounter_id BIGINT PRIMARY KEY,
    patient_id BIGINT NOT NULL REFERENCES administrative.patients,
    department_id SMALLINT NOT NULL REFERENCES administrative.departments,
    practitioner_id INTEGER NOT NULL REFERENCES administrative.practitioners,
    reference VARCHAR(20) NOT NULL UNIQUE,
    admitted_at TIMESTAMP(0) NOT NULL,
    discharged_at TIMESTAMP(0),
    reason TEXT,
    encounter_type VARCHAR(30) NOT NULL,
    urgent BOOLEAN NOT NULL,
    CHECK (discharged_at IS NULL OR discharged_at >= admitted_at)
);

CREATE TABLE IF NOT EXISTS clinical.observations (
    observation_id BIGINT PRIMARY KEY,
    encounter_id BIGINT NOT NULL REFERENCES clinical.encounters,
    practitioner_id INTEGER NOT NULL REFERENCES administrative.practitioners,
    code VARCHAR(12) NOT NULL,
    label TEXT NOT NULL,
    value NUMERIC(8, 2),
    real_value REAL,
    index_value DOUBLE PRECISION,
    unit VARCHAR(12),
    observed_at TIMESTAMP(3) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    measurement_time TIME(3) NOT NULL,
    validated BOOLEAN,
    comment TEXT
);

CREATE TABLE IF NOT EXISTS clinical.prescriptions (
    prescription_id BIGINT PRIMARY KEY,
    encounter_id BIGINT NOT NULL REFERENCES clinical.encounters,
    practitioner_id INTEGER NOT NULL REFERENCES administrative.practitioners,
    product VARCHAR(80) NOT NULL,
    instruction TEXT,
    quantity NUMERIC(10, 3),
    start_date DATE NOT NULL,
    end_date DATE,
    scheduled_time TIME(0) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    canceled BOOLEAN NOT NULL,
    CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE TABLE IF NOT EXISTS clinical.clinical_notes (
    clinical_note_id BIGINT PRIMARY KEY,
    encounter_id BIGINT NOT NULL REFERENCES clinical.encounters,
    practitioner_id INTEGER NOT NULL REFERENCES administrative.practitioners,
    title VARCHAR(120) NOT NULL,
    text TEXT,
    dictated_at TIMESTAMP(2) NOT NULL,
    signed_at TIMESTAMP(6),
    version SMALLINT NOT NULL,
    is_final BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS research.studies (
    study_id SMALLINT PRIMARY KEY,
    code CHAR(8) NOT NULL UNIQUE,
    title TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    open BOOLEAN NOT NULL,
    CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE TABLE IF NOT EXISTS research.consents (
    consent_id BIGINT PRIMARY KEY,
    patient_id BIGINT NOT NULL UNIQUE REFERENCES administrative.patients,
    accepted BOOLEAN NOT NULL,
    signed_at TIMESTAMP(0) NOT NULL,
    channel VARCHAR(30) NOT NULL,
    comment TEXT
);

CREATE TABLE IF NOT EXISTS research.enrollments (
    enrollment_id BIGINT PRIMARY KEY,
    patient_id BIGINT NOT NULL UNIQUE REFERENCES administrative.patients,
    study_id SMALLINT NOT NULL REFERENCES research.studies,
    consent_id BIGINT NOT NULL REFERENCES research.consents,
    participant_code VARCHAR(20) NOT NULL UNIQUE,
    enrolled_at TIMESTAMP(6) NOT NULL,
    group_code CHAR(1) NOT NULL,
    baseline_score DOUBLE PRECISION,
    follow_up_complete BOOLEAN
);

CREATE INDEX IF NOT EXISTS encounters_patient_idx ON clinical.encounters (patient_id);
CREATE INDEX IF NOT EXISTS observations_encounter_idx ON clinical.observations (encounter_id);
CREATE INDEX IF NOT EXISTS prescriptions_encounter_idx ON clinical.prescriptions (encounter_id);
CREATE INDEX IF NOT EXISTS clinical_notes_encounter_idx ON clinical.clinical_notes (encounter_id);

INSERT INTO administrative.departments (department_id, code, name, capacity, active)
VALUES
    (1, 'FICT01', 'Fictional reception and consultations', 12, TRUE),
    (2, 'FICT02', 'Demonstration medicine', 24, TRUE),
    (3, 'FICT03', 'Demonstration surgery', 18, TRUE),
    (4, 'FICT04', 'Fictional imaging', 8, TRUE),
    (5, 'FICT05', 'Demonstration rehabilitation', 16, TRUE),
    (6, 'FICT06', 'Archived fictional department', 0, FALSE)
ON CONFLICT DO NOTHING;

-- Names and free text support testing masks without a length limit.
-- CHAR(11) and VARCHAR(20) also cover short fields: do not automatically
-- apply encryption that increases the length of their contents.
INSERT INTO administrative.patients (
    patient_id, patient_uuid, record_number, patient_number, last_name, first_name, birth_date,
    sex, email, phone, address, postal_code, city, contact_allowed,
    preferences, created_at
)
SELECT
    n,
    md5('maskql-patient-fictional-' || n)::UUID,
    'FICT' || lpad(n::TEXT, 7, '0'),
    'PAT-FICT-' || lpad(n::TEXT, 6, '0'),
    'Fictional-' || (ARRAY['Martin', 'Lefèvre', 'O''Connor', 'Müller', 'Nguyen',
        'Ben Demo', 'Noël', 'Test', 'García', 'Dupré'])[(n - 1) % 10 + 1],
    (ARRAY['Élodie', 'Gabriel', 'Zoé', 'Raphaël', 'Anaïs', 'Noé', 'Inès',
        'Léon', 'Chloé', 'Maël'])[((n - 1) / 10) % 10 + 1],
    DATE '1925-01-01' + (n * 149 % 30000),
    CASE WHEN n % 13 = 0 THEN NULL ELSE (ARRAY['F', 'M', 'X'])[(n - 1) % 3 + 1] END,
    CASE WHEN n % 10 = 0 THEN NULL WHEN n % 11 = 0 THEN ''
        ELSE 'fictional.patient.' || n || '@example.test' END,
    CASE WHEN n % 7 = 0 THEN NULL ELSE 'PHONE-FICT-' || lpad(n::TEXT, 4, '0') END,
    CASE WHEN n % 9 = 0 THEN NULL WHEN n % 17 = 0 THEN ''
        ELSE n || ' Fictional Summer Lane' END,
    '00000',
    (ARRAY['Demo Town', 'Test-on-River', 'Saint Fiction', 'O''Example'])[(n - 1) % 4 + 1],
    CASE WHEN n % 8 = 0 THEN NULL ELSE n % 3 <> 0 END,
    CASE WHEN n % 12 = 0 THEN NULL ELSE jsonb_build_object(
        'dataset', 'synthetic', 'language', (ARRAY['fr', 'en', 'es'])[(n - 1) % 3 + 1],
        'reminder', n % 2 = 0
    ) END,
    TIMESTAMP '2024-01-01 08:00:00' + n * INTERVAL '1 hour'
FROM generate_series(1, 200) AS patients(n)
ON CONFLICT DO NOTHING;

INSERT INTO administrative.practitioners (
    practitioner_id, department_id, code, last_name, first_name, profession, email, fte, active
)
SELECT
    n,
    (n - 1) % 5 + 1,
    'PRC-FICT-' || lpad(n::TEXT, 3, '0'),
    'Fictional-' || (ARRAY['Aubert', 'Benoît', 'O''Brien', 'Faure', 'Roy'])[(n - 1) % 5 + 1],
    (ARRAY['Camille', 'Alexis', 'Lou', 'Andréa'])[((n - 1) / 5) % 4 + 1],
    (ARRAY['Physician', 'Nurse', 'Physiotherapist', 'Technician'])[((n - 1) / 5) % 4 + 1],
    'fictional.practitioner.' || n || '@example.test',
    (ARRAY[1.00, 0.80, 0.50])[(n - 1) % 3 + 1],
    TRUE
FROM generate_series(1, 20) AS practitioners(n)
ON CONFLICT DO NOTHING;

-- Three encounters per patient, one hundred days apart. Department and
-- practitioner references agree. Dates are fixed and independent of today.
INSERT INTO clinical.encounters (
    encounter_id, patient_id, department_id, practitioner_id, reference,
    admitted_at, discharged_at, reason, encounter_type, urgent
)
SELECT
    n,
    (n - 1) % 200 + 1,
    (n - 1) % 5 + 1,
    (n - 1) % 20 + 1,
    'ENC-FICT-' || lpad(n::TEXT, 6, '0'),
    admitted_at,
    admitted_at + ((n - 1) % 5 + 1) * INTERVAL '1 day',
    (ARRAY['Fictional follow-up consultation', 'Demonstration assessment',
        'Simulated rehabilitation encounter', 'Fictional post-examination review',
        'Demonstration evaluation'])[(n - 1) % 5 + 1],
    (ARRAY['Consultation', 'Inpatient', 'Outpatient'])[(n - 1) % 3 + 1],
    n % 9 = 0
FROM (
    SELECT n, TIMESTAMP '2025-01-06 08:00:00'
        + ((n - 1) / 200 * 100 + (n - 1) % 200 % 60) * INTERVAL '1 day'
        + (n % 6) * INTERVAL '1 hour' AS admitted_at
    FROM generate_series(1, 600) AS encounters(n)
) AS source
ON CONFLICT DO NOTHING;

-- Three demonstration measurements per encounter: positive and negative
-- numbers, decimals and NULLs, with nonzero fractional seconds.
INSERT INTO clinical.observations (
    observation_id, encounter_id, practitioner_id, code, label, value,
    real_value, index_value, unit, observed_at, recorded_at, measurement_time,
    validated, comment
)
SELECT
    (s.encounter_id - 1) * 3 + m,
    s.encounter_id,
    s.practitioner_id,
    (ARRAY['TEST_MOB', 'TEST_COMF', 'TEST_SLEEP']) [m],
    (ARRAY['Simulated mobility', 'Simulated comfort', 'Simulated sleep'])[m],
    CASE WHEN s.encounter_id % 17 = 0 AND m = 1 THEN NULL
        ELSE ((s.encounter_id * 17 + m) % 1000 - 200) / 10.0 END,
    CASE WHEN s.encounter_id % 19 = 0 THEN NULL
        ELSE ((s.encounter_id % 101 - 50) / 3.0 + m / 10.0)::REAL END,
    CASE WHEN s.encounter_id % 23 = 0 THEN NULL
        ELSE (s.encounter_id - 300)::DOUBLE PRECISION / 7.0 + m / 100.0 END,
    CASE WHEN s.encounter_id % 17 = 0 AND m = 1 THEN NULL ELSE 'test.unit' END,
    s.admitted_at + m * INTERVAL '2 hours' + m * INTERVAL '0.123 seconds',
    (s.admitted_at + m * INTERVAL '2 hours' + m * INTERVAL '0.123 seconds'
        + INTERVAL '1 minute') AT TIME ZONE 'Europe/Paris',
    (s.admitted_at + m * INTERVAL '2 hours' + m * INTERVAL '0.123 seconds')::TIME(3),
    CASE WHEN s.encounter_id % 13 = 0 THEN NULL ELSE s.encounter_id % 7 <> 0 END,
    CASE WHEN s.encounter_id % 5 = 0 THEN NULL WHEN s.encounter_id % 11 = 0 THEN ''
        ELSE 'Fictional observation: the patient''s assessment describes a test scenario with no clinical interpretation.' END
FROM clinical.encounters AS s
CROSS JOIN generate_series(1, 3) AS measurements(m)
WHERE s.encounter_id BETWEEN 1 AND 600
ON CONFLICT DO NOTHING;

INSERT INTO clinical.prescriptions (
    prescription_id, encounter_id, practitioner_id, product, instruction, quantity,
    start_date, end_date, scheduled_time, created_at, canceled
)
SELECT
    s.encounter_id,
    s.encounter_id,
    s.practitioner_id,
    (ARRAY['Fictional product Alpha', 'Fictional product Beta',
        'Fictional product Gamma', 'Fictional product Omega'])[(s.encounter_id - 1) % 4 + 1],
    CASE WHEN s.encounter_id % 11 = 0 THEN NULL WHEN s.encounter_id % 17 = 0 THEN ''
        ELSE 'Demonstration instruction only — no actual dosage.' END,
    CASE WHEN s.encounter_id % 13 = 0 THEN NULL ELSE (s.encounter_id % 25 + 1) / 8.0 END,
    s.admitted_at::DATE,
    CASE WHEN s.encounter_id % 7 = 0 THEN NULL ELSE s.discharged_at::DATE END,
    TIME '18:30:00',
    s.admitted_at + INTERVAL '30 minutes 0.123456 seconds',
    s.encounter_id % 19 = 0
FROM clinical.encounters AS s
WHERE s.encounter_id BETWEEN 1 AND 600
ON CONFLICT DO NOTHING;

-- Notes refer only to fictional identities from this dataset. They cover
-- accents, apostrophes, line breaks, test contacts and some empty text.
INSERT INTO clinical.clinical_notes (
    clinical_note_id, encounter_id, practitioner_id, title, text,
    dictated_at, signed_at, version, is_final
)
SELECT
    s.encounter_id,
    s.encounter_id,
    s.practitioner_id,
    'Fictional clinical note — encounter ' || s.reference,
    CASE WHEN s.encounter_id % 25 = 0 THEN NULL WHEN s.encounter_id % 29 = 0 THEN ''
        ELSE concat(
            'SYNTHETIC DOCUMENT — MASKQL DEMONSTRATION', E'\n',
            'Fictional patient: ', p.first_name, ' ', p.last_name, ', record ', trim(p.record_number), '.', E'\n',
            'Admitted on ', to_char(s.admitted_at, 'YYYY-MM-DD "at" HH24:MI'),
            ' for: ', lower(s.reason), '.', E'\n',
            'Fictional practitioner: ', i.first_name, ' ', i.last_name, '.', E'\n',
            (ARRAY[
                'The simulated interview describes the patient''s fictional discomfort and imaginary sleep.',
                'The scenario describes movement with demonstration equipment.',
                'The examination is invented; the words café, naïve and résumé test accented characters.',
                'The follow-up described here is an example for pseudonymization tests.'
            ])[(s.encounter_id - 1) % 4 + 1], E'\n',
            'Test contact: ', coalesce(nullif(p.email, ''), 'not provided'),
            '; ', coalesce(p.phone, 'phone unavailable'), '.', E'\n',
            'No medical conclusion: all information in this document is fictional.'
        ) END,
    s.admitted_at + INTERVAL '6 hours 0.12 seconds',
    CASE WHEN s.encounter_id % 6 = 0 THEN NULL
        ELSE s.admitted_at + INTERVAL '8 hours 0.654321 seconds' END,
    (s.encounter_id - 1) % 3 + 1,
    s.encounter_id % 6 <> 0
FROM clinical.encounters AS s
JOIN administrative.patients AS p ON p.patient_id = s.patient_id
JOIN administrative.practitioners AS i ON i.practitioner_id = s.practitioner_id
WHERE s.encounter_id BETWEEN 1 AND 200
ON CONFLICT DO NOTHING;

INSERT INTO research.studies (study_id, code, title, start_date, end_date, open)
VALUES
    (1, 'TEST0001', 'Fictional study of demonstration care pathways', '2024-12-01', NULL, TRUE),
    (2, 'TEST0002', 'Fictional study of data quality', '2024-12-01', NULL, TRUE),
    (3, 'TEST0003', 'Fictional study of clinical text', '2024-12-01', '2025-12-31', FALSE)
ON CONFLICT DO NOTHING;

INSERT INTO research.consents (
    consent_id, patient_id, accepted, signed_at, channel, comment
)
SELECT
    n,
    n,
    n % 4 <> 0,
    TIMESTAMP '2024-12-02 09:00:00' + (n % 20) * INTERVAL '1 day',
    (ARRAY['Fictional form', 'Simulated interview', 'Test portal'])[(n - 1) % 3 + 1],
    CASE WHEN n % 4 = 0 THEN 'Fictional refusal for testing access filters.'
        WHEN n % 9 = 0 THEN NULL
        ELSE 'Synthetic consent for demonstration studies.' END
FROM generate_series(1, 200) AS consents(n)
ON CONFLICT DO NOTHING;

-- All 100 patients with odd identifiers have previously given consent.
INSERT INTO research.enrollments (
    enrollment_id, patient_id, study_id, consent_id, participant_code,
    enrolled_at, group_code, baseline_score, follow_up_complete
)
SELECT
    n,
    2 * n - 1,
    (n - 1) % 3 + 1,
    2 * n - 1,
    'PART-FICT-' || lpad(n::TEXT, 5, '0'),
    TIMESTAMP '2025-01-01 10:00:00.123456' + (n % 30) * INTERVAL '1 day',
    (ARRAY['A', 'B', 'C'])[(n - 1) % 3 + 1],
    CASE WHEN n % 10 = 0 THEN NULL ELSE (n - 50)::DOUBLE PRECISION / 9.0 END,
    CASE WHEN n % 7 = 0 THEN NULL ELSE n % 5 <> 0 END
FROM generate_series(1, 100) AS enrollments(n)
ON CONFLICT DO NOTHING;

COMMIT;
