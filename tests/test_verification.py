"""Unit tests for the verification evaluation engine."""

from middleware.verify import VerificationEngine


def test_verification_all_pass():
    """Verifies that compliant values result in PASS verdicts across legacy checks."""
    reqs = {
        "maxStallSpeed": 11.0,
        "maxWingspan": 1800.0,
        "maxWingMass": 0.65
    }
    aero = {
        "calculated_stall_speed_mps": 10.5,
        "wing_area_m2": 0.25,
        "aspect_ratio": 8.0,
        "design_cl_cruise": 0.48
    }
    cad = {
        "span_mm": 1400.0,
        "total_wing_mass_kg": 0.35,
        "root_chord_mm": 210.0,
        "tip_chord_mm": 140.0,
        "center_of_gravity": [90.0, 300.0, 12.0]
    }

    engine = VerificationEngine(requirements=reqs)
    report = engine.evaluate(aero_results=aero, cad_results=cad)

    assert report["overall_pass"] is True
    assert report["passed_checks"] == 3
    assert report["total_checks"] == 3


def test_verification_failure_on_excess_mass():
    """Verifies that an overweight wing triggers a FAIL verdict."""
    reqs = {
        "maxStallSpeed": 11.0,
        "maxWingspan": 1800.0,
        "maxWingMass": 0.40  # Tight mass constraint
    }
    aero = {
        "calculated_stall_speed_mps": 10.5,
        "wing_area_m2": 0.25,
        "aspect_ratio": 8.0,
        "design_cl_cruise": 0.48
    }
    cad = {
        "span_mm": 1400.0,
        "total_wing_mass_kg": 0.55,  # Exceeds 0.40 kg limit
        "root_chord_mm": 210.0,
        "tip_chord_mm": 140.0,
        "center_of_gravity": [90.0, 300.0, 12.0]
    }

    engine = VerificationEngine(requirements=reqs)
    report = engine.evaluate(aero_results=aero, cad_results=cad)

    assert report["overall_pass"] is False
    assert report["passed_checks"] == 2
    mass_check = next(c for c in report["checks"] if c["case_id"] == "verifyIcarusMass")
    assert mass_check["verdict"] == "FAIL"


def test_verification_all_five_mission_parameters_pass():
    """Verifies compliance across all 5 primary Phase 1 mission requirements."""
    reqs = {
        "maxStallSpeed": 11.0,
        "maxWingspan": 1800.0,
        "maxWingMass": 0.65,
        "minFlightDuration": 30.0,
        "minPayloadMass": 1.2
    }
    aero = {
        "calculated_stall_speed_mps": 10.4,
        "wing_area_m2": 0.27,
        "aspect_ratio": 8.0,
        "design_cl_cruise": 0.50,
        "achievable_duration_min": 32.5,
        "payload_mass_kg": 1.2,
        "total_mass_kg": 2.35,
        "battery_mass_kg": 0.32,
        "cruise_power_watts": 71.0
    }
    cad = {
        "span_mm": 1470.0,
        "total_wing_mass_kg": 0.41,
        "root_chord_mm": 222.0,
        "tip_chord_mm": 145.0,
        "center_of_gravity": [95.0, 310.0, 12.0]
    }

    engine = VerificationEngine(requirements=reqs)
    report = engine.evaluate(aero_results=aero, cad_results=cad)

    assert report["overall_pass"] is True
    assert report["passed_checks"] == 5
    assert report["total_checks"] == 5


def test_verification_duration_and_payload_failure():
    """Verifies that deficient duration or payload fails specific cases."""
    reqs = {
        "maxStallSpeed": 11.0,
        "maxWingspan": 1800.0,
        "maxWingMass": 0.65,
        "minFlightDuration": 45.0,  # Requires 45 min
        "minPayloadMass": 1.5       # Requires 1.5 kg
    }
    aero = {
        "calculated_stall_speed_mps": 10.4,
        "wing_area_m2": 0.27,
        "aspect_ratio": 8.0,
        "design_cl_cruise": 0.50,
        "achievable_duration_min": 30.0,  # Only achieves 30 min -> FAIL
        "payload_mass_kg": 1.0,           # Only carries 1.0 kg -> FAIL
    }
    cad = {
        "span_mm": 1470.0,
        "total_wing_mass_kg": 0.41,
        "root_chord_mm": 222.0,
        "tip_chord_mm": 145.0,
        "center_of_gravity": [95.0, 310.0, 12.0]
    }

    engine = VerificationEngine(requirements=reqs)
    report = engine.evaluate(aero_results=aero, cad_results=cad)

    assert report["overall_pass"] is False
    assert report["passed_checks"] == 3
    assert report["total_checks"] == 5

    dur_check = next(c for c in report["checks"] if c["case_id"] == "verifyIcarusDuration")
    assert dur_check["verdict"] == "FAIL"

    payload_check = next(c for c in report["checks"] if c["case_id"] == "verifyIcarusPayload")
    assert payload_check["verdict"] == "FAIL"
