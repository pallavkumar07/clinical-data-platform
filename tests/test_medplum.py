"""Tests for the Medplum client wiring (no live network calls)."""

import pytest

from clinical_data_platform.services.medplum import MedplumClient, MedplumError


def test_client_reports_unconfigured_without_credentials():
    client = MedplumClient(client_id="", client_secret="")
    assert client.is_configured is False


def test_client_reports_configured_with_credentials():
    client = MedplumClient(client_id="abc", client_secret="shh")
    assert client.is_configured is True


@pytest.mark.asyncio
async def test_token_fetch_raises_when_unconfigured():
    client = MedplumClient(client_id="", client_secret="")
    with pytest.raises(MedplumError):
        await client._get_token()


def test_base_url_is_normalized():
    client = MedplumClient(base_url="https://api.medplum.com/")
    assert client.base_url == "https://api.medplum.com"
