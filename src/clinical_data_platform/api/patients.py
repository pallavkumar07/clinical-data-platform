"""Example FHIR-backed endpoints reading from Medplum.

Demonstrates the integration pattern: the route delegates to the Medplum
client and returns FHIR resources. Extend with your own resource types.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from clinical_data_platform.services.medplum import MedplumError, medplum

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("")
async def list_patients(name: str | None = Query(default=None)) -> dict[str, Any]:
    """Search patients in Medplum, optionally filtered by name."""
    params = {"name": name} if name else {}
    try:
        return await medplum.search("Patient", **params)
    except MedplumError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{patient_id}")
async def get_patient(patient_id: str) -> dict[str, Any]:
    """Read a single patient by FHIR resource id."""
    try:
        return await medplum.read("Patient", patient_id)
    except MedplumError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
