# Healthcare demo data

The development catalog `demo` contains 3,729 synthetic records across three schemas.
All identities, contacts, observations and treatments are fictional.

| Table | Rows | Contents |
| --- | ---: | --- |
| `administrative.departments` | 6 | Hospital departments |
| `administrative.patients` | 200 | Identities, contacts and birth dates |
| `administrative.practitioners` | 20 | Staff and department assignments |
| `clinical.encounters` | 600 | Patient stays |
| `clinical.observations` | 1,800 | Synthetic measurements |
| `clinical.prescriptions` | 600 | Fictional treatments |
| `clinical.clinical_notes` | 200 | Free-text reports |
| `research.studies` | 3 | Fictional studies |
| `research.consents` | 200 | Consent records |
| `research.enrollments` | 100 | Study participation |

## Load and explore

New development databases load the data automatically. On an existing running stack:

```bash
make demo-data
```

This adds missing records and demo rules, then refreshes the `demo` catalog inventory.
Existing records and rules are preserved. Reload the interface and select `demo`,
then `administrative`, `clinical` or `research`.

The `demo` user can read these schemas. Patient names are encrypted; email and
phone values are hidden. Use the before/after preview to compare the results.
The [quickstart](QUICKSTART.md) walks through creating a separate user and rules.

```sql
SELECT p.patient_id, p.last_name, p.first_name, s.encounter_id
FROM demo.administrative.patients p
JOIN demo.clinical.encounters s ON s.patient_id = p.patient_id
ORDER BY p.patient_id, s.encounter_id
LIMIT 10;
```

## Cases to try

- Joins between patients, stays, observations and research records.
- Text with accents and apostrophes, empty strings, `NULL`, long reports and short identifiers.
- Booleans, integer sizes, decimals, floating-point values and dates.
- Times and timestamps with different precisions and time zones.
- Compatible and incompatible mask expressions, row filters and JSON rule imports.

The seeded name encryption uses `TEXT`. Short `CHAR`/`VARCHAR` identifiers are also
available to reproduce the known encryption truncation issue; they have no preset
encryption rule.

The dataset is defined in [healthcare.sql](../tests/fixtures/healthcare.sql).
The integration tests in [test_masking.py](../tests/test_masking.py) cover table
reads, patient masking and clinical/research joins.
