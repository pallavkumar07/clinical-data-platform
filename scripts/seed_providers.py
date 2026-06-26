"""Seed the Medplum project with test providers (FHIR Practitioner resources).

Usage:
    python scripts/seed_providers.py

Reads credentials from .env via core.config. Creates FHIR Practitioner
resources so they show up in the Medplum admin app under Practitioner.
"""

from __future__ import annotations

import asyncio

from clinical_data_platform.services.medplum import MedplumClient

# Synthetic, clearly-fake test data. Not real clinicians. NPIs are fake.
TEST_PROVIDERS: list[dict] = [
    {"prefix": "Dr.", "given": ["Sarah"], "family": "Chen", "suffix": "MD",
     "gender": "female", "npi": "1000000001", "specialty": "Family Medicine",
     "phone": "555-0201", "email": "s.chen.test@example.com"},
    {"prefix": "Dr.", "given": ["James"], "family": "Okafor", "suffix": "MD",
     "gender": "male", "npi": "1000000002", "specialty": "Cardiology",
     "phone": "555-0202", "email": "j.okafor.test@example.com"},
    {"prefix": "Dr.", "given": ["Priya"], "family": "Nair", "suffix": "DO",
     "gender": "female", "npi": "1000000003", "specialty": "Pediatrics",
     "phone": "555-0203", "email": "p.nair.test@example.com"},
    {"prefix": "Dr.", "given": ["Michael"], "family": "Reyes", "suffix": "MD",
     "gender": "male", "npi": "1000000004", "specialty": "Internal Medicine",
     "phone": "555-0204", "email": "m.reyes.test@example.com"},
    {"prefix": "", "given": ["Linda"], "family": "Hofstadter", "suffix": "NP",
     "gender": "female", "npi": "1000000005", "specialty": "Nurse Practitioner",
     "phone": "555-0205", "email": "l.hofstadter.test@example.com"},
]


def to_fhir_practitioner(p: dict) -> dict:
    """Build a FHIR R4 Practitioner resource from a simple dict."""
    name: dict = {"use": "official", "given": p["given"], "family": p["family"]}
    if p.get("prefix"):
        name["prefix"] = [p["prefix"]]
    if p.get("suffix"):
        name["suffix"] = [p["suffix"]]

    return {
        "resourceType": "Practitioner",
        "active": True,
        "identifier": [
            {"system": "http://hl7.org/fhir/sid/us-npi", "value": p["npi"]},
        ],
        "name": [name],
        "gender": p["gender"],
        "telecom": [
            {"system": "phone", "value": p["phone"], "use": "work"},
            {"system": "email", "value": p["email"], "use": "work"},
        ],
        "qualification": [
            {
                "code": {"text": p["specialty"]},
            }
        ],
    }


async def main() -> None:
    client = MedplumClient()
    if not client.is_configured:
        raise SystemExit("Medplum not configured — set CDP_MEDPLUM_* in .env")

    print(f"Seeding {len(TEST_PROVIDERS)} test providers into Medplum...\n")
    for p in TEST_PROVIDERS:
        created = await client.create("Practitioner", to_fhir_practitioner(p))
        label = f"{p.get('prefix', '')} {p['given'][0]} {p['family']} {p.get('suffix', '')}".strip()
        print(f"  ✓ {label:<28} {p['specialty']:<22} id={created['id']}")
    print("\nDone. View them at https://app.medplum.com/Practitioner")


if __name__ == "__main__":
    asyncio.run(main())
