# Architecture

> Living document — capture decisions here as the platform evolves.

## Overview

The Clinical Data Platform is organized into clear layers under
`src/clinical_data_platform/`:

| Layer       | Responsibility                                              |
|-------------|-------------------------------------------------------------|
| `api/`      | HTTP surface — FastAPI routers, request/response handling.  |
| `core/`     | Cross-cutting concerns — config, app wiring, logging.       |
| `models/`   | Pydantic schemas and domain models.                         |
| `services/` | Business logic and integrations (FHIR/HL7, storage, etc.).  |

## Request flow

```
client → api/ (router) → services/ (logic) → models/ (validation) → response
```

## Open questions / next steps

- [ ] Choose a persistence layer (Postgres? FHIR server?)
- [ ] Define the ingestion model (FHIR R4? HL7v2? CSV bulk load?)
- [ ] Auth & access control (clinical data → audit + RBAC requirements)
- [ ] Deployment target (containerized? cloud?)
