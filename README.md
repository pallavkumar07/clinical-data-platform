# Clinical Data Platform

A platform for ingesting, normalizing, and serving clinical data — built with Python and FastAPI.

> 🚧 Early-stage scaffold. Structure and scope will evolve as the product takes shape.

## Vision

Provide a clean, interoperable foundation for working with clinical data (e.g. FHIR/HL7),
exposing it through a well-documented API for downstream applications and analytics.

## Tech Stack

- **Language:** Python 3.11+
- **API framework:** [FastAPI](https://fastapi.tiangolo.com/)
- **Data backend:** [Medplum](https://www.medplum.com/) (hosted FHIR server) — see [docs/medplum.md](docs/medplum.md)
- **Server:** Uvicorn
- **Testing:** pytest
- **Tooling:** ruff (lint + format)

## Project Structure

```
clinical-data-platform/
├── src/clinical_data_platform/
│   ├── api/          # FastAPI routers / endpoints
│   ├── core/         # Config, settings, app wiring
│   ├── models/       # Pydantic schemas / data models
│   └── services/     # Business logic, integrations (Medplum FHIR client)
├── tests/            # pytest test suite
├── docs/             # Design docs, architecture notes
└── scripts/          # Dev / ops helper scripts
```

## Getting Started

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install in editable mode with dev dependencies
pip install -e ".[dev]"

# 3. Run the API (hot reload)
uvicorn clinical_data_platform.main:app --reload

# 4. Open the interactive API docs
open http://localhost:8000/docs
```

## Sample data

Populate your Medplum project with synthetic test patients, providers, and rich
clinical data — see [docs/sample-data.md](docs/sample-data.md):

```bash
python scripts/seed_patients.py        # 10 test patients
python scripts/seed_providers.py       # 5 test providers
python scripts/seed_clinical_data.py   # demographics, conditions, vitals, labs, meds, etc.
```

## Development

```bash
pytest            # run tests
ruff check .      # lint
ruff format .     # format
```

## License

See [LICENSE](LICENSE).
