"""Unit tests for the SysML v2 client module."""

import os
from middleware.sysml_client import SysMLClient


def test_sysml_client_offline_loading():
    """Verifies that the offline fallback correctly extracts requirements from SysML files."""
    client = SysMLClient(offline=True)
    assert not client.is_server_available()

    reqs = client.load_requirements()
    assert reqs["maxStallSpeed"] == 11.0
    assert reqs["minCruiseSpeed"] == 18.0
    assert reqs["minPayloadMass"] == 1.2
    assert reqs["maxWingspan"] == 1800.0
    assert reqs["maxWingMass"] == 0.65
    assert reqs["totalMass"] == 2.4
    assert reqs["airfoilDesignation"] == "NACA 2412"
    assert reqs["airfoilMaxCL"] == 1.4


def test_sysml_client_post_offline():
    """Verifies posting verification records in offline mode completes without error."""
    client = SysMLClient(offline=True)
    success = client.post_verification_result({"overall_pass": True})
    assert not success  # In offline mode, does not attempt network post
