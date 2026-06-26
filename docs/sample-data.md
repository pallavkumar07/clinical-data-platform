# Sample Data

Scripts under [`scripts/`](../scripts) populate a Medplum project with realistic,
**synthetic** test data so the platform and the Medplum admin UI have something
to show. All data is fake (famous scientists, `@example.com` emails, `555-01xx`
phones, fake NPIs) — never real PHI.

## Prerequisites

1. A configured `.env` with your Medplum credentials (see [medplum.md](medplum.md)).
2. The virtual environment activated and deps installed:
   ```bash
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

## Run order

Run these in order — clinical data depends on the patients and providers
existing first.

| # | Script | Creates |
|---|--------|---------|
| 1 | `python scripts/seed_patients.py`        | 10 test **Patients** |
| 2 | `python scripts/seed_providers.py`       | 5 test **Practitioners** (providers), with test NPIs `1000000001`–`1000000005` |
| 3 | `python scripts/seed_clinical_data.py`   | Rich clinical data for every test patient (see below) |

## What `seed_clinical_data.py` adds

For each test patient (discovered by their `@example.com` email):

- **Demographics** — US Core race, ethnicity, and birth sex; marital status;
  preferred language; and an emergency contact.
- **Provider associations** — a random primary-care `generalPractitioner`, plus
  a `CareTeam` containing **all 5 test providers**. Providers are selected by
  their test NPIs, which **excludes your own Practitioner profile** by design.
- **Conditions** — 1–2 problems (e.g. hypertension, type 2 diabetes) with
  coherent **MedicationRequests** (e.g. diabetes → metformin).
- **Observations** — a vitals panel (BP, HR, temp, resp rate, SpO₂, height,
  weight, BMI) and a lab panel (glucose, HbA1c, lipid panel, creatinine).
- **AllergyIntolerance**, **Immunizations** (2–3), and a recent **Encounter**.

### Key properties

- **Idempotent.** Every generated resource carries a stable identifier under
  `https://clinical-data-platform.example/sample-data` and is created with
  FHIR `If-None-Exist`, so re-running the script never produces duplicates.
- **Deterministic.** Randomness is seeded per-patient (by resource id), so a
  given patient always gets the same generated data.
- **Self-discovering.** Patients and providers are read from Medplum at
  runtime, so re-seeding the base resources and re-running still works.

## Reset / cleanup

To start clean, delete the sample resources from the Medplum admin app
(filter by the `sample-data` identifier), or delete the patients/practitioners
directly. The seed scripts will recreate everything on the next run.
