"""Client for talking to a hosted Medplum FHIR server.

Authenticates with the OAuth2 client-credentials flow and exposes thin
helpers over the FHIR R4 REST API. Configure credentials via the
``CDP_MEDPLUM_*`` environment variables (see ``core.config``).
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from clinical_data_platform.core.config import settings


class MedplumError(RuntimeError):
    """Raised when Medplum is misconfigured or returns an error."""


class MedplumClient:
    """Minimal async client for the Medplum FHIR API.

    Caches the access token and refreshes it shortly before expiry.
    """

    def __init__(
        self,
        base_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        self.base_url = (base_url or settings.medplum_base_url).rstrip("/")
        self.client_id = client_id or settings.medplum_client_id
        self.client_secret = client_secret or settings.medplum_client_secret
        self._token: str | None = None
        self._token_expiry: float = 0.0

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    async def _get_token(self) -> str:
        """Return a valid access token, fetching a new one if needed."""
        if not self.is_configured:
            raise MedplumError(
                "Medplum is not configured. Set CDP_MEDPLUM_CLIENT_ID and "
                "CDP_MEDPLUM_CLIENT_SECRET (see docs/medplum.md)."
            )
        # Refresh ~60s before expiry.
        if self._token and time.monotonic() < self._token_expiry - 60:
            return self._token

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            resp = await client.post(
                "/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
        if resp.status_code != 200:
            raise MedplumError(f"Medplum auth failed ({resp.status_code}): {resp.text}")
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expiry = time.monotonic() + float(payload.get("expires_in", 3600))
        return self._token

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}", **kwargs.pop("headers", {})}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            resp = await client.request(method, f"/fhir/R4{path}", headers=headers, **kwargs)
        if resp.status_code >= 400:
            raise MedplumError(f"Medplum {method} {path} -> {resp.status_code}: {resp.text}")
        return resp

    async def search(self, resource_type: str, **params: Any) -> dict[str, Any]:
        """Search a FHIR resource type, e.g. ``search("Patient", name="smith")``."""
        resp = await self._request("GET", f"/{resource_type}", params=params)
        return resp.json()

    async def read(self, resource_type: str, resource_id: str) -> dict[str, Any]:
        """Read a single resource by id."""
        resp = await self._request("GET", f"/{resource_type}/{resource_id}")
        return resp.json()

    async def create(self, resource_type: str, resource: dict[str, Any]) -> dict[str, Any]:
        """Create a new FHIR resource."""
        resp = await self._request("POST", f"/{resource_type}", json=resource)
        return resp.json()


# Shared instance for convenience; injected via core.config settings.
medplum = MedplumClient()
