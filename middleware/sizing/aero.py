"""Physics-based aerodynamic and mission sizing module for Daedalus Thread.

Translates high-level mission requirements (cruise speed, stall speed, payload mass,
wingspan limit, and flight duration) into planform geometry and mass allocations
for downstream parametric CAD lofting and verification.
"""

import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

from middleware.sizing.powertrain import (
    evaluate_powertrain,
    calculate_cruise_power,
    size_battery,
    calculate_endurance,
    PowertrainMetrics,
)


@dataclass
class AeroSizingResult:
    """Calculated aerodynamic, planform, and vehicle mass properties."""
    wing_area_m2: float
    span_mm: float
    root_chord_mm: float
    tip_chord_mm: float
    mean_chord_mm: float
    aspect_ratio: float
    taper_ratio: float
    sweep_deg: float
    dihedral_deg: float
    airfoil: str
    design_cl_cruise: float
    calculated_stall_speed_mps: float
    stall_margin_percent: float
    wing_loading_kg_m2: float
    total_mass_kg: float = 2.4
    payload_mass_kg: float = 1.2
    battery_mass_kg: float = 0.35
    estimated_wing_mass_kg: float = 0.42
    cots_base_mass_kg: float = 0.42
    flight_duration_target_min: float = 30.0
    achievable_duration_min: float = 30.0
    cruise_power_watts: float = 75.0
    lift_to_drag_ratio: float = 10.0

    def to_dict(self) -> Dict[str, Any]:
        """Converts result to dictionary representation."""
        return asdict(self)


def estimate_wing_mass_kg(
    span_mm: float,
    root_chord_mm: float,
    tip_chord_mm: float,
    thickness_ratio: float = 0.12,
    density_g_mm3: float = 0.000085,
    hardware_mass_g: float = 58.0
) -> float:
    """Estimates 3D printed wing mass including spars and servos.

    Args:
        span_mm: Total wingspan in millimeters.
        root_chord_mm: Root chord in millimeters.
        tip_chord_mm: Tip chord in millimeters.
        thickness_ratio: Maximum airfoil thickness ratio (t/c).
        density_g_mm3: Effective printed material density (LW-PLA).
        hardware_mass_g: Spars, joiners, and servo hardware mass in grams.

    Returns:
        Total wing mass in kilograms.
    """
    mean_chord = (root_chord_mm + tip_chord_mm) / 2.0
    half_span = span_mm / 2.0
    area_cross_section = 0.68 * mean_chord * (mean_chord * thickness_ratio)
    half_volume_mm3 = area_cross_section * half_span
    both_wings_volume = half_volume_mm3 * 2.0
    printed_mass_g = both_wings_volume * density_g_mm3
    return round((printed_mass_g + hardware_mass_g) / 1000.0, 3)


def size_wing(
    total_mass_kg: Optional[float] = None,
    stall_speed_max_mps: float = 11.0,
    cruise_speed_min_mps: float = 18.0,
    span_limit_mm: float = 1800.0,
    payload_mass_kg: float = 1.2,
    flight_duration_min: float = 30.0,
    airfoil_max_cl: float = 1.4,
    airfoil_designation: str = "NACA 2412",
    target_aspect_ratio: float = 8.0,
    taper_ratio: float = 0.65,
    sweep_deg: float = 3.5,
    dihedral_deg: float = 2.0,
    air_density_kg_m3: float = 1.225,
    cots_base_mass_kg: float = 0.42
) -> AeroSizingResult:
    """Sizes wing geometry and vehicle mass from mission parameters.

    If total_mass_kg is provided, sizes planform directly for that mass.
    Otherwise, executes an iterative mass convergence loop using payload mass,
    flight duration, and aerodynamic drag.

    Args:
        total_mass_kg: Optional explicit vehicle mass (kg).
        stall_speed_max_mps: Maximum permissible stall speed (m/s).
        cruise_speed_min_mps: Target level cruise airspeed (m/s).
        span_limit_mm: Maximum allowable wingspan constraint (mm).
        payload_mass_kg: Usable payload mass (kg).
        flight_duration_min: Target flight duration in minutes.
        airfoil_max_cl: Maximum clean section lift coefficient.
        airfoil_designation: Airfoil profile designation.
        target_aspect_ratio: Nominal wing aspect ratio.
        taper_ratio: Wing taper ratio (c_tip / c_root).
        sweep_deg: Leading-edge sweep angle in degrees.
        dihedral_deg: Dihedral angle in degrees.
        air_density_kg_m3: Atmospheric air density in kg/m^3.
        cots_base_mass_kg: Baseline mass of COTS fuselage, avionics, motor, and ESC.

    Returns:
        AeroSizingResult containing sized planform geometry, metrics, and mass breakdown.
    """
    g = 9.80665

    # Requirement sanity and feasibility checks
    if stall_speed_max_mps >= cruise_speed_min_mps:
        raise ValueError(
            f"Stall speed limit ({stall_speed_max_mps} m/s) must be strictly less than "
            f"cruise airspeed target ({cruise_speed_min_mps} m/s)."
        )
    if flight_duration_min <= 0.0:
        raise ValueError("Flight duration target must be positive.")
    if payload_mass_kg <= 0.0:
        raise ValueError("Payload mass must be positive.")

    # 1. Vehicle mass convergence loop if total_mass_kg is not fixed
    fixed_mass_mode = total_mass_kg is not None
    m_vehicle = float(total_mass_kg) if fixed_mass_mode else (payload_mass_kg + cots_base_mass_kg + 0.8)

    batt_mass = 0.35
    wing_mass = 0.42
    pt_metrics: Optional[PowertrainMetrics] = None
    ld_ratio = 10.0

    max_iterations = 1 if fixed_mass_mode else 40
    tolerance_kg = 0.002

    for _ in range(max_iterations):
        # Minimum required wing area to meet stall speed limit (with 8% design margin)
        min_area_m2 = (2.0 * m_vehicle * g) / (
            air_density_kg_m3 * (stall_speed_max_mps ** 2.0) * airfoil_max_cl
        )
        wing_area_m2 = round(min_area_m2 * 1.08, 4)

        # Wingspan constrained by span_limit_mm
        span_from_ar_m = math.sqrt(wing_area_m2 * target_aspect_ratio)
        span_from_ar_mm = span_from_ar_m * 1000.0
        span_mm = round(min(span_from_ar_mm, span_limit_mm), 1)
        span_m = span_mm / 1000.0

        # Effective planform aspect ratio
        aspect_ratio = round((span_m ** 2.0) / wing_area_m2, 2)

        # Root and tip chords for linearly tapered wing
        mean_chord_m = wing_area_m2 / span_m
        root_chord_m = (2.0 * wing_area_m2) / (span_m * (1.0 + taper_ratio))
        tip_chord_m = root_chord_m * taper_ratio
        root_chord_mm = round(root_chord_m * 1000.0, 1)
        tip_chord_mm = round(tip_chord_m * 1000.0, 1)
        mean_chord_mm = round(mean_chord_m * 1000.0, 1)

        # Aerodynamic cruise lift coefficient and drag estimate
        design_cl_cruise = (2.0 * m_vehicle * g) / (
            air_density_kg_m3 * (cruise_speed_min_mps ** 2.0) * wing_area_m2
        )
        cd_parasitic = 0.026
        cd_induced = (design_cl_cruise ** 2.0) / (math.pi * aspect_ratio * 0.80)
        cd_total = cd_parasitic + cd_induced
        ld_ratio = round(design_cl_cruise / cd_total, 2)

        # Powertrain and battery mass evaluation
        pt_metrics = evaluate_powertrain(
            total_mass_kg=m_vehicle,
            cruise_speed_mps=cruise_speed_min_mps,
            lift_to_drag_ratio=ld_ratio,
            target_duration_min=flight_duration_min
        )
        batt_mass = pt_metrics.battery_mass_kg

        # Wing structural mass estimation
        wing_mass = estimate_wing_mass_kg(
            span_mm=span_mm,
            root_chord_mm=root_chord_mm,
            tip_chord_mm=tip_chord_mm
        )

        if fixed_mass_mode:
            break

        # Updated all-up weight
        m_new = payload_mass_kg + batt_mass + wing_mass + cots_base_mass_kg
        if abs(m_new - m_vehicle) < tolerance_kg:
            m_vehicle = round(m_new, 3)
            break
        # Damped update to avoid oscillations
        m_vehicle = 0.5 * m_vehicle + 0.5 * m_new
    else:
        if not fixed_mass_mode:
            m_vehicle = round(m_vehicle, 3)

    # 2. Performance validation metrics
    calculated_stall_mps = math.sqrt(
        (2.0 * m_vehicle * g) / (air_density_kg_m3 * wing_area_m2 * airfoil_max_cl)
    )
    stall_margin_percent = round(
        ((stall_speed_max_mps - calculated_stall_mps) / stall_speed_max_mps) * 100.0, 2
    )
    wing_loading_kg_m2 = round(m_vehicle / wing_area_m2, 2)

    cruise_power = pt_metrics.cruise_power_watts if pt_metrics else 70.0
    achievable_duration = pt_metrics.achievable_duration_min if pt_metrics else flight_duration_min

    return AeroSizingResult(
        wing_area_m2=wing_area_m2,
        span_mm=span_mm,
        root_chord_mm=root_chord_mm,
        tip_chord_mm=tip_chord_mm,
        mean_chord_mm=mean_chord_mm,
        aspect_ratio=aspect_ratio,
        taper_ratio=taper_ratio,
        sweep_deg=sweep_deg,
        dihedral_deg=dihedral_deg,
        airfoil=airfoil_designation,
        design_cl_cruise=round(design_cl_cruise, 3),
        calculated_stall_speed_mps=round(calculated_stall_mps, 2),
        stall_margin_percent=stall_margin_percent,
        wing_loading_kg_m2=wing_loading_kg_m2,
        total_mass_kg=round(m_vehicle, 3),
        payload_mass_kg=round(payload_mass_kg, 3),
        battery_mass_kg=round(batt_mass, 3),
        estimated_wing_mass_kg=round(wing_mass, 3),
        cots_base_mass_kg=round(cots_base_mass_kg, 3),
        flight_duration_target_min=round(flight_duration_min, 1),
        achievable_duration_min=round(achievable_duration, 1),
        cruise_power_watts=round(cruise_power, 2),
        lift_to_drag_ratio=ld_ratio
    )
