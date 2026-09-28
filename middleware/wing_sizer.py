"""
MBSE Aerodynamic & Structural Wing Sizing Middleware Module.
Translates flight mission requirements into parametric wing dimensions for CAD generation.
"""
import math
from typing import Dict, Any


class WingSizer:
    """Calculates aerodynamic wing parameters from high-level mission requirements."""

    def __init__(
        self,
        air_density: float = 1.225,  # kg/m^3 (standard sea level)
        gravity: float = 9.80665,    # m/s^2
        max_cl: float = 1.215,       # 3D finite wing max CL (0.90 * 1.35 2D max CL)
        aspect_ratio: float = 7.5,   # Target aspect ratio b^2 / S
        taper_ratio: float = 0.65,   # Tip chord / Root chord
        sweep_angle_deg: float = 3.5,# Wing leading edge sweep
        dihedral_angle_deg: float = 2.0, # Dihedral angle
        battery_specific_energy_wh_kg: float = 180.0, # LiPo/Li-ion specific energy
        powertrain_efficiency: float = 0.70, # Motor, ESC, prop combined efficiency
        usable_battery_dod: float = 0.80 # Usable depth of discharge
    ):
        self.air_density = air_density
        self.gravity = gravity
        self.max_cl = max_cl
        self.aspect_ratio = aspect_ratio
        self.taper_ratio = taper_ratio
        self.sweep_angle_deg = sweep_angle_deg
        self.dihedral_angle_deg = dihedral_angle_deg
        self.battery_specific_energy_wh_kg = battery_specific_energy_wh_kg
        self.powertrain_efficiency = powertrain_efficiency
        self.usable_battery_dod = usable_battery_dod

    def calculate_sizing(self, mission_reqs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates wing dimensions and mass budget from mission requirement inputs.

        Expected mission_reqs keys:
        - cruise_speed: float (m/s)
        - stall_speed_max: float (m/s)
        - payload_mass: float (kg)
        - max_span_mm: float (mm, upper bound limit)
        - flight_duration_min: float (minutes)
        """
        cruise_speed = float(mission_reqs.get("cruise_speed", 18.0))
        stall_speed_max = float(mission_reqs.get("stall_speed_max", 11.0))
        payload_mass = float(mission_reqs.get("payload_mass", 1.2))
        max_span_mm = float(mission_reqs.get("max_span_mm", 2000.0))
        flight_duration_min = float(mission_reqs.get("flight_duration_min", 45.0))

        # Baseline airframe structural mass estimate (1.2x payload mass)
        airframe_mass = payload_mass * 1.2

        # Coupled mass and energy convergence for battery mass
        # Initial mass guess
        total_mass = payload_mass + airframe_mass + 0.8
        est_ld = 12.5 # Estimated cruise L/D ratio
        battery_mass = 0.8
        cruise_power_watts = 30.0

        for _ in range(5):
            weight_n = total_mass * self.gravity
            drag_n = weight_n / est_ld
            # Cruise electrical power required in Watts
            cruise_power_watts = (drag_n * cruise_speed) / self.powertrain_efficiency
            # Required battery capacity in Wh for desired duration
            energy_required_wh = cruise_power_watts * (flight_duration_min / 60.0)
            battery_mass = energy_required_wh / (self.battery_specific_energy_wh_kg * self.usable_battery_dod)
            total_mass = payload_mass + airframe_mass + battery_mass

        total_weight = total_mass * self.gravity # Newtons

        # 1. Minimum wing surface area needed to meet stall speed limit
        # V_stall = sqrt(2 * Weight / (rho * S * CL_max))
        # => S_min = (2 * Weight) / (rho * V_stall_max^2 * CL_max)
        wing_area_m2 = (2.0 * total_weight) / (self.air_density * (stall_speed_max ** 2) * self.max_cl)

        # 2. Wingspan calculation: b = sqrt(AR * S), bounded by max_span_mm
        span_m = math.sqrt(self.aspect_ratio * wing_area_m2)
        max_span_m = max_span_mm / 1000.0

        is_span_clamped = False
        if span_m > max_span_m:
            span_m = max_span_m
            is_span_clamped = True
            # Recalculate area for max allowed span
            wing_area_m2 = (span_m ** 2) / self.aspect_ratio

        span_mm = span_m * 1000.0

        # 3. Chords calculation using trapezoidal planform
        # S = 0.5 * (c_root + c_tip) * b = c_root * 0.5 * (1 + taper_ratio) * b
        c_root_m = (2.0 * wing_area_m2) / ((1.0 + self.taper_ratio) * span_m)
        c_tip_m = c_root_m * self.taper_ratio

        root_chord_mm = c_root_m * 1000.0
        tip_chord_mm = c_tip_m * 1000.0

        # 4. Cruise Lift Coefficient CL_cruise
        cl_cruise = (2.0 * total_weight) / (self.air_density * (cruise_speed ** 2) * wing_area_m2)

        # 5. Airfoil Selection logic based on cl_cruise
        if cl_cruise >= 0.40:
            airfoil_designation = "NACA 4412"
            max_camber = 4.0
            max_thickness = 12.0
            alpha_0_deg = -3.0
        elif cl_cruise >= 0.25:
            airfoil_designation = "NACA 2412"
            max_camber = 2.0
            max_thickness = 12.0
            alpha_0_deg = -2.0
        else:
            airfoil_designation = "NACA 0012"
            max_camber = 0.0
            max_thickness = 12.0
            alpha_0_deg = 0.0

        # 6. Recommended wing incidence pitch angle for level fuselage trim at cruise
        a0_rad = 5.85
        denom = 1.0 + (a0_rad / (math.pi * self.aspect_ratio * 0.85))
        a3d_per_deg = (a0_rad / denom) * (math.pi / 180.0)
        pitch_angle_deg = (cl_cruise / a3d_per_deg) + alpha_0_deg
        pitch_angle_deg = max(0.0, min(8.0, round(pitch_angle_deg, 1)))

        battery_energy_wh = battery_mass * self.battery_specific_energy_wh_kg * self.usable_battery_dod

        return {
            "span_mm": round(span_mm, 2),
            "root_chord_mm": round(root_chord_mm, 2),
            "tip_chord_mm": round(tip_chord_mm, 2),
            "sweep_angle_deg": round(self.sweep_angle_deg, 2),
            "dihedral_angle_deg": round(self.dihedral_angle_deg, 2),
            "pitch_angle_deg": pitch_angle_deg,
            "airfoil_designation": airfoil_designation,
            "airfoil_max_camber_percent": max_camber,
            "airfoil_max_thickness_percent": max_thickness,
            "cruise_cl": round(cl_cruise, 4),
            "total_mass_kg": round(total_mass, 3),
            "payload_mass_kg": round(payload_mass, 3),
            "airframe_mass_kg": round(airframe_mass, 3),
            "battery_mass_kg": round(battery_mass, 3),
            "wing_area_m2": round(wing_area_m2, 4),
            "aspect_ratio": round(self.aspect_ratio, 2),
            "cruise_power_watts": round(cruise_power_watts, 1),
            "battery_energy_wh": round(battery_energy_wh, 1),
            "flight_duration_min": round(flight_duration_min, 1),
            "is_span_clamped": is_span_clamped,
        }

    def verify_mission_requirements(
        self,
        mission_reqs: Dict[str, Any],
        sizing_results: Dict[str, Any],
        aero_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Formally verifies simulation and sizing performance against the 5 target mission parameters.
        Returns detailed compliance checks and an overall mission success verdict.
        """
        cruise_speed_target = float(mission_reqs.get("cruise_speed", 18.0))
        stall_speed_max = float(mission_reqs.get("stall_speed_max", 11.0))
        payload_mass_target = float(mission_reqs.get("payload_mass", 1.2))
        wingspan_max = float(mission_reqs.get("max_span_mm", 2000.0))
        duration_target = float(mission_reqs.get("flight_duration_min", 45.0))

        flight_perf = aero_results.get("flight_performance", {})
        cruise_cond = flight_perf.get("cruise_condition", {})
        payload_cap = flight_perf.get("payload_capacity", {})

        actual_stall_speed_mps = flight_perf.get("stall_speed_gross_mps")
        if actual_stall_speed_mps is None:
            actual_stall_speed_mph = flight_perf.get("stall_speed_gross_mph", 0.0)
            actual_stall_speed_mps = actual_stall_speed_mph * 0.44704

        actual_span_mm = sizing_results.get("span_mm", 0.0)
        actual_safe_payload_kg = payload_cap.get("payload_safe_max_kg", 0.0)
        actual_cruise_speed_mps = cruise_cond.get("speed_mps", cruise_speed_target)
        actual_cruise_power_w = cruise_cond.get("power_watts", sizing_results.get("cruise_power_watts", 30.0))

        # Electrical power required including powertrain efficiency
        elec_power_w = actual_cruise_power_w / self.powertrain_efficiency if actual_cruise_power_w > 0 else 1.0
        battery_energy_wh = sizing_results.get("battery_energy_wh", 50.0)
        actual_endurance_min = (battery_energy_wh / elec_power_w) * 60.0

        checks = []

        # 1. Cruise Airspeed Verification
        stall_margin_mps = actual_cruise_speed_mps - actual_stall_speed_mps
        cruise_passed = stall_margin_mps >= 2.0 and not cruise_cond.get("is_stalled", False)
        checks.append({
            "parameter": "Cruise Airspeed Target",
            "target_value": f"{cruise_speed_target:.1f} m/s",
            "achieved_value": f"{actual_cruise_speed_mps:.1f} m/s",
            "margin": f"+{stall_margin_mps:.1f} m/s above stall",
            "status": "PASS" if cruise_passed else "FAIL",
            "notes": f"L/D = {cruise_cond.get('lift_to_drag', 0.0):.1f}, CL = {cruise_cond.get('cl_required', 0.0):.2f}"
        })

        # 2. Stall Speed Limit Verification
        stall_margin = stall_speed_max - actual_stall_speed_mps
        stall_passed = actual_stall_speed_mps <= (stall_speed_max + 0.1) # 0.1 m/s numerical tolerance
        checks.append({
            "parameter": "Stall Speed Limit",
            "target_value": f"<= {stall_speed_max:.1f} m/s",
            "achieved_value": f"{actual_stall_speed_mps:.1f} m/s",
            "margin": f"{stall_margin:+.2f} m/s margin",
            "status": "PASS" if stall_passed else "FAIL",
            "notes": "Ensures clean stall margin at full gross weight"
        })

        # 3. Payload Mass Verification
        payload_margin = actual_safe_payload_kg - payload_mass_target
        payload_passed = actual_safe_payload_kg >= (payload_mass_target - 0.05)
        checks.append({
            "parameter": "Payload Mass Capacity",
            "target_value": f">= {payload_mass_target:.2f} kg",
            "achieved_value": f"{actual_safe_payload_kg:.2f} kg",
            "margin": f"{payload_margin:+.2f} kg margin",
            "status": "PASS" if payload_passed else "FAIL",
            "notes": f"Absolute maximum payload before stall: {payload_cap.get('payload_absolute_max_kg', 0.0):.2f} kg"
        })

        # 4. Wingspan Upper Bound Verification
        span_margin = wingspan_max - actual_span_mm
        span_passed = actual_span_mm <= (wingspan_max + 1.0)
        checks.append({
            "parameter": "Wingspan Upper Bound",
            "target_value": f"<= {wingspan_max:.1f} mm",
            "achieved_value": f"{actual_span_mm:.1f} mm",
            "margin": f"{span_margin:+.1f} mm margin",
            "status": "PASS" if span_passed else "FAIL",
            "notes": "Bounded by transport/manufacturing limit"
        })

        # 5. Target Flight Duration Verification
        duration_margin = actual_endurance_min - duration_target
        duration_passed = actual_endurance_min >= (duration_target - 1.0)
        checks.append({
            "parameter": "Target Flight Duration",
            "target_value": f">= {duration_target:.1f} min",
            "achieved_value": f"{actual_endurance_min:.1f} min",
            "margin": f"{duration_margin:+.1f} min margin",
            "status": "PASS" if duration_passed else "FAIL",
            "notes": f"Battery: {sizing_results.get('battery_mass_kg', 0.0):.2f} kg ({battery_energy_wh:.1f} Wh usable)"
        })

        all_passed = all(c["status"] == "PASS" for c in checks)

        return {
            "overall_status": "SUCCESS" if all_passed else "DEFICIENT",
            "summary": "All 5 mission parameters satisfied" if all_passed else "One or more mission parameters violated",
            "checks": checks,
            "metrics": {
                "cruise_speed_mps": round(actual_cruise_speed_mps, 2),
                "stall_speed_mps": round(actual_stall_speed_mps, 2),
                "payload_safe_max_kg": round(actual_safe_payload_kg, 2),
                "wingspan_mm": round(actual_span_mm, 1),
                "endurance_min": round(actual_endurance_min, 1),
                "cruise_power_elec_watts": round(elec_power_w, 1),
            }
        }

