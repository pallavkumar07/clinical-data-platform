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

### 1. Install

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### 2. Set up Medplum (required)

This platform uses [Medplum](https://www.medplum.com/) as its FHIR data
backend. The app authenticates to a **hosted** Medplum server with your own
credentials — nothing runs without this step. Full guide:
[docs/medplum.md](docs/medplum.md).

1. **Create a project.** Sign up at [app.medplum.com](https://app.medplum.com/)
   (free tier available). A default Project is created for you.

2. **Create machine credentials.** In the Medplum admin app, go to
   **Admin → Project → Clients** (or
   [app.medplum.com/admin/clients](https://app.medplum.com/admin/clients)) →
   **New Client Application**. Copy the generated **Client ID** and
   **Client Secret** — these let the backend talk to Medplum server-to-server.

3. **Create a `.env` file** in the project root with your own values:

   ```bash
   CDP_ENVIRONMENT=development
   CDP_DEBUG=true

   CDP_MEDPLUM_BASE_URL=https://api.medplum.com/
   CDP_MEDPLUM_CLIENT_ID=<your client id>
   CDP_MEDPLUM_CLIENT_SECRET=<your client secret>
   ```

   > `.env` is git-ignored, so your credentials are never committed. Each
   > developer supplies their own — see [docs/medplum.md](docs/medplum.md).

### 3. Run the API

```bash
# Start the server (hot reload)
uvicorn clinical_data_platform.main:app --reload

# Open the interactive API docs
open http://localhost:8000/docs

# Verify the Medplum connection (searches Patient resources)
curl http://localhost:8000/patients
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
