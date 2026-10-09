"""Unit tests for aerodynamic and mission parameter sizing calculations."""

import pytest
from middleware.sizing.aero import size_wing, AeroSizingResult


def test_size_wing_baseline():
    """Validates that baseline inputs produce compliant aerodynamic planform."""
    result = size_wing(
        total_mass_kg=2.4,
        stall_speed_max_mps=11.0,
        cruise_speed_min_mps=18.0,
        span_limit_mm=1800.0,
        airfoil_max_cl=1.4
    )

    assert isinstance(result, AeroSizingResult)
    # Stall speed must be below or equal to max stall speed limit
    assert result.calculated_stall_speed_mps <= 11.0
    assert result.stall_margin_percent > 0.0

    # Wingspan must satisfy geometric constraint
    assert result.span_mm <= 1800.0
    assert result.span_mm > 800.0

    # Trapezoidal area relation: S = (c_root + c_tip) / 2 * span
    calculated_area_mm2 = ((result.root_chord_mm + result.tip_chord_mm) / 2.0) * result.span_mm
    calculated_area_m2 = calculated_area_mm2 / 1e6
    assert pytest.approx(result.wing_area_m2, 0.01) == calculated_area_m2

    # Aspect ratio check
    expected_ar = ((result.span_mm / 1000.0) ** 2.0) / result.wing_area_m2
    assert pytest.approx(result.aspect_ratio, 0.05) == expected_ar


def test_size_wing_heavy_payload():
    """Validates that higher mass correctly expands required wing area."""
    light = size_wing(total_mass_kg=2.0)
    heavy = size_wing(total_mass_kg=3.5)

    assert heavy.wing_area_m2 > light.wing_area_m2
    assert heavy.root_chord_mm > light.root_chord_mm


def test_mission_parameter_convergence():
    """Validates end-to-end mass convergence from the 5 primary mission parameters."""
    result = size_wing(
        cruise_speed_min_mps=18.0,
        stall_speed_max_mps=11.0,
        payload_mass_kg=1.2,
        span_limit_mm=1800.0,
        flight_duration_min=30.0
    )

    assert isinstance(result, AeroSizingResult)
    # AUW budget validation
    assert result.total_mass_kg > 1.8
    assert result.total_mass_kg < 3.2
    assert result.payload_mass_kg == 1.2
    assert result.battery_mass_kg > 0.15
    assert result.estimated_wing_mass_kg > 0.20

    # Mission requirements satisfaction
    assert result.calculated_stall_speed_mps <= 11.0
    assert result.span_mm <= 1800.0
    assert result.achievable_duration_min >= 30.0
    assert result.cruise_power_watts > 30.0


def test_mission_duration_scaling():
    """Validates that longer endurance increases battery mass and wing area."""
    short_mission = size_wing(
        cruise_speed_min_mps=18.0,
        stall_speed_max_mps=11.0,
        payload_mass_kg=1.0,
        span_limit_mm=1800.0,
        flight_duration_min=20.0
    )

    long_mission = size_wing(
        cruise_speed_min_mps=18.0,
        stall_speed_max_mps=11.0,
        payload_mass_kg=1.0,
        span_limit_mm=1800.0,
        flight_duration_min=50.0
    )

    assert long_mission.battery_mass_kg > short_mission.battery_mass_kg
    assert long_mission.total_mass_kg > short_mission.total_mass_kg
    assert long_mission.wing_area_m2 > short_mission.wing_area_m2


def test_mission_span_limit_clamping():
    """Validates that a strict span limit clamps the wingspan."""
    unclamped = size_wing(
        payload_mass_kg=1.5,
        span_limit_mm=2200.0
    )
    clamped = size_wing(
        payload_mass_kg=1.5,
        span_limit_mm=1300.0
    )

    assert clamped.span_mm <= 1300.0
    assert clamped.aspect_ratio < unclamped.aspect_ratio


def test_mission_infeasible_inputs():
    """Validates that physically invalid inputs raise clear exceptions."""
    with pytest.raises(ValueError, match="Stall speed limit .* must be strictly less"):
        size_wing(
            cruise_speed_min_mps=12.0,
            stall_speed_max_mps=15.0  # Invalid: stall > cruise
        )

    with pytest.raises(ValueError, match="Flight duration target must be positive"):
        size_wing(flight_duration_min=-5.0)

    with pytest.raises(ValueError, match="Payload mass must be positive"):
        size_wing(payload_mass_kg=0.0)
