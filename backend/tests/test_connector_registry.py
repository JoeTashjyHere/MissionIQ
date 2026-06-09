"""Connector provider registry contracts.

Mirrors test_registry.py for the intelligence modules: every provider is
registered with a complete descriptor, Phase 1 providers are implemented,
Phase 2/3 providers are extension points that refuse execution with a
structured error.
"""
from __future__ import annotations

import pytest

from app.connectors import get_connector_registry
from app.connectors.base import AUTH_MODES, ConnectorNotImplementedError
from app.models.connector import CONNECTOR_TYPES

PHASE_1 = {"salesforce", "sharepoint", "local_repository"}
PHASE_2 = {"govwin", "bloomberg_gov"}
PHASE_3 = {"servicenow", "dynamics", "jira"}


def test_all_providers_registered():
    ids = {p.provider_id for p in get_connector_registry().all()}
    assert ids == PHASE_1 | PHASE_2 | PHASE_3


def test_provider_ids_unique_and_descriptors_complete():
    providers = get_connector_registry().all()
    assert len({p.provider_id for p in providers}) == len(providers)
    for p in providers:
        assert p.label, p.provider_id
        assert p.description, p.provider_id
        assert p.connector_type in CONNECTOR_TYPES, p.provider_id
        assert p.auth_mode in AUTH_MODES, p.provider_id
        assert p.phase in (1, 2, 3), p.provider_id


def test_phase_1_implemented_phase_2_3_planned():
    for p in get_connector_registry().all():
        if p.provider_id in PHASE_1:
            assert p.implemented, f"{p.provider_id} must be implemented (Phase 1)"
        else:
            assert not p.implemented, f"{p.provider_id} must be a planned extension point"


def test_govwin_is_customer_authorized_only():
    govwin = get_connector_registry().require("govwin")
    assert govwin.requires_customer_authorization is True


def test_connector_type_coverage():
    """The framework declares all five connector types; the registry covers
    CRM, document repository, market intelligence, project management, and
    knowledge management across its providers."""
    types = {p.connector_type for p in get_connector_registry().all()}
    assert types == set(CONNECTOR_TYPES)


@pytest.mark.asyncio
async def test_planned_providers_refuse_execution_with_structured_error():
    provider = get_connector_registry().require("govwin")()
    with pytest.raises(ConnectorNotImplementedError) as exc:
        await provider.discover(config={}, secret=None)
    assert exc.value.code == "connector.not_implemented"
    assert exc.value.status_code == 501


def test_unknown_provider_raises_not_found():
    from app.core.errors import NotFoundError

    with pytest.raises(NotFoundError):
        get_connector_registry().require("hubspot")
