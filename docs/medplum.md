# Medplum Integration

We use **[Medplum](https://www.medplum.com/)** as the FHIR data backend — the
clinical "database." The FastAPI app talks to a **hosted** Medplum server over
the FHIR R4 REST API, authenticating with the OAuth2 client-credentials flow.

## 1. Create a Medplum project

1. Sign up at [app.medplum.com](https://app.medplum.com/) (free tier available).
2. A default Project is created for you.

## 2. Create a Client Application (machine credentials)

1. In the Medplum admin app, go to **Admin → Project → Clients** (or visit
   `https://app.medplum.com/admin/clients`).
2. Click **New Client Application**.
3. Copy the generated **Client ID** and **Client Secret**.

These are service credentials for server-to-server access — keep the secret out
of version control.

## 3. Configure the backend

Copy `.env.example` to `.env` and fill in:

```bash
CDP_MEDPLUM_BASE_URL=https://api.medplum.com/
CDP_MEDPLUM_CLIENT_ID=<your client id>
CDP_MEDPLUM_CLIENT_SECRET=<your client secret>
```

`.env` is git-ignored.

## 4. Try it

```bash
source .venv/bin/activate
uvicorn clinical_data_platform.main:app --reload

# In another terminal — searches Patient resources in Medplum:
curl http://localhost:8000/patients
curl "http://localhost:8000/patients?name=smith"
```

## How it works

| Piece | Location |
|-------|----------|
| Client (auth + FHIR REST helpers) | `src/clinical_data_platform/services/medplum.py` |
| Example endpoints | `src/clinical_data_platform/api/patients.py` |
| Settings | `src/clinical_data_platform/core/config.py` |

The client (`MedplumClient`) caches the access token and refreshes it before
expiry. Use `search()`, `read()`, and `create()` for any FHIR resource type:

```python
from clinical_data_platform.services.medplum import medplum

await medplum.create("Patient", {"resourceType": "Patient", "name": [{"given": ["Ada"], "family": "Lovelace"}]})
await medplum.search("Observation", subject="Patient/123")
```

## Optional: Medplum web/admin app

Medplum also ships a React app starter if you want a custom front end:

```bash
npm init medplum
```

This is independent of the Python backend and not required to use Medplum as
your database.

## Self-hosting (later)

To run Medplum on your own infra instead of the hosted server, clone the
monorepo and run it with Docker (Postgres + Redis):

```bash
git clone https://github.com/medplum/medplum.git
```

Docker is **not** currently installed on this machine, so this path needs
Docker Desktop first. See https://www.medplum.com/docs/self-hosting.
