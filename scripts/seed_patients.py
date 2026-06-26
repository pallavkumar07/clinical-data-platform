"""Seed the Medplum project with test patients.

Usage:
    python scripts/seed_patients.py

Reads credentials from .env via core.config. Creates FHIR Patient resources
so they show up in the Medplum admin app under Patients.
"""

from __future__ import annotations

import asyncio

from clinical_data_platform.services.medplum import MedplumClient

# Synthetic, clearly-fake test data. Not real people.
TEST_PATIENTS: list[dict] = [
    {"given": ["Ada"], "family": "Lovelace", "gender": "female", "birth": "1985-12-10",
     "phone": "555-0101", "email": "ada.test@example.com", "city": "Boston", "state": "MA"},
    {"given": ["Alan"], "family": "Turing", "gender": "male", "birth": "1978-06-23",
     "phone": "555-0102", "email": "alan.test@example.com", "city": "Cambridge", "state": "MA"},
    {"given": ["Grace"], "family": "Hopper", "gender": "female", "birth": "1990-12-09",
     "phone": "555-0103", "email": "grace.test@example.com", "city": "New York", "state": "NY"},
    {"given": ["Katherine"], "family": "Johnson", "gender": "female", "birth": "1972-08-26",
     "phone": "555-0104", "email": "katherine.test@example.com", "city": "Hampton", "state": "VA"},
    {"given": ["Charles"], "family": "Babbage", "gender": "male", "birth": "1965-12-26",
     "phone": "555-0105", "email": "charles.test@example.com", "city": "Chicago", "state": "IL"},
    {"given": ["Marie"], "family": "Curie", "gender": "female", "birth": "1980-11-07",
     "phone": "555-0106", "email": "marie.test@example.com", "city": "Denver", "state": "CO"},
    {"given": ["Rosalind"], "family": "Franklin", "gender": "female", "birth": "1988-07-25",
     "phone": "555-0107", "email": "rosalind.test@example.com", "city": "Seattle", "state": "WA"},
    {"given": ["Nikola"], "family": "Tesla", "gender": "male", "birth": "1970-07-10",
     "phone": "555-0108", "email": "nikola.test@example.com", "city": "Austin", "state": "TX"},
    {"given": ["Dorothy"], "family": "Vaughan", "gender": "female", "birth": "1968-09-20",
     "phone": "555-0109", "email": "dorothy.test@example.com", "city": "Atlanta", "state": "GA"},
    {"given": ["George"], "family": "Washington Carver", "gender": "male", "birth": "1975-01-05",
     "phone": "555-0110", "email": "george.test@example.com", "city": "Phoenix", "state": "AZ"},
]


def to_fhir_patient(p: dict) -> dict:
    """Build a FHIR R4 Patient resource from a simple dict."""
    return {
        "resourceType": "Patient",
        "active": True,
        "name": [{"use": "official", "given": p["given"], "family": p["family"]}],
        "gender": p["gender"],
        "birthDate": p["birth"],
        "telecom": [
            {"system": "phone", "value": p["phone"], "use": "home"},
            {"system": "email", "value": p["email"]},
        ],
        "address": [{"use": "home", "city": p["city"], "state": p["state"], "country": "US"}],
    }


async def main() -> None:
    client = MedplumClient()
    if not client.is_configured:
        raise SystemExit("Medplum not configured — set CDP_MEDPLUM_* in .env")

    print(f"Seeding {len(TEST_PATIENTS)} test patients into Medplum...\n")
    for p in TEST_PATIENTS:
        created = await client.create("Patient", to_fhir_patient(p))
        name = f"{p['given'][0]} {p['family']}"
        print(f"  ✓ {name:<28} id={created['id']}")
    print("\nDone. View them at https://app.medplum.com/Patient")


if __name__ == "__main__":
    asyncio.run(main())
