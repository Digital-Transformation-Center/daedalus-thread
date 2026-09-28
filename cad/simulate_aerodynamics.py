"""Aerodynamic simulation and flight performance analyzer for the parametric wing.

Calculates lift, drag, trim angle of attack, stall speed, and power requirements
across different flight speeds for a specified aircraft mass (e.g. 1.0 kg at 30 mph).
Can be executed as a FreeCAD macro or directly via Python CLI.
"""
import json
import math
import os
import sys
from typing import Dict, List, Any, Optional

# Ensure cad directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def mph_to_mps(mph: float) -> float:
    """Converts miles per hour to meters per second."""
    return float(mph) * 0.44704


def mps_to_mph(mps: float) -> float:
    """Converts meters per second to miles per hour."""
    return float(mps) / 0.44704


class WingAeroSimulator:
    """Calculates 3D finite wing aerodynamic forces and flight performance."""

    def __init__(
        self,
        span_mm: float = 700.0,
        root_chord_mm: float = 200.0,
        tip_chord_mm: float = 90.0,
        sweep_deg: float = 0.0,
        dihedral_deg: float = 0.0,
        pitch_deg: float = 0.0,
        airfoil_name: str = "NACA 2412",
        air_density: float = 1.225,
        kinematic_viscosity: float = 1.5e-5,
    ):
        self.span_m = span_mm / 1000.0
        self.root_m = root_chord_mm / 1000.0
        self.tip_m = tip_chord_mm / 1000.0
        self.sweep_rad = math.radians(sweep_deg)
        self.dihedral_rad = math.radians(dihedral_deg)
        self.pitch_deg = float(pitch_deg)
        self.airfoil = airfoil_name
        self.rho = air_density
        self.nu = kinematic_viscosity

        # Wing planform properties
        self.taper_ratio = self.tip_m / self.root_m if self.root_m > 0 else 1.0
        # Reference area for full symmetrical wing (both half-wings)
        self.area_m2 = (self.root_m + self.tip_m) * 0.5 * self.span_m
        self.aspect_ratio = (self.span_m ** 2) / self.area_m2 if self.area_m2 > 0 else 1.0
        self.mean_chord_m = self.area_m2 / self.span_m

        # Oswald efficiency factor approximation for trapezoidal wing
        self.oswald_e = 1.78 * (1.0 - 0.045 * (self.aspect_ratio ** 0.68)) - 0.64
        self.oswald_e = max(0.70, min(0.95, self.oswald_e))

        # Airfoil characteristics (NACA 2412 baseline)
        self.alpha_0_deg = -2.0  # Zero-lift angle of attack in degrees
        self.cl_max_2d = 1.35     # Maximum section lift coefficient
        self.a0_per_deg = 0.102   # 2D lift curve slope per degree (~5.85 / rad)

        # 3D finite wing lift curve slope (Helmbold equation)
        a0_rad = self.a0_per_deg * (180.0 / math.pi)
        denom = 1.0 + (a0_rad / (math.pi * self.aspect_ratio * self.oswald_e))
        self.a3d_rad = a0_rad / denom
        self.a3d_per_deg = self.a3d_rad * (math.pi / 180.0)

        # 3D maximum lift coefficient
        self.cl_max_3d = self.cl_max_2d * 0.90

    def compute_flight_point(self, speed_mph: float, aircraft_mass_kg: float = 1.0) -> Dict[str, Any]:
        """Calculates aerodynamic state and trim angle of attack for a given flight speed."""
        v_mps = mph_to_mps(speed_mph)
        q = 0.5 * self.rho * (v_mps ** 2)
        weight_n = aircraft_mass_kg * 9.80665

        # Reynolds number based on mean aerodynamic chord
        reynolds = (v_mps * self.mean_chord_m) / self.nu

        # Required lift coefficient for steady level flight (Lift = Weight)
        cl_required = weight_n / (q * self.area_m2) if (q * self.area_m2) > 0 else 999.0

        # Required trim angle of attack in degrees: CL = a3d * (alpha - alpha_0)
        alpha_trim_deg = (cl_required / self.a3d_per_deg) + self.alpha_0_deg

        # Stall check
        is_stalled = cl_required > self.cl_max_3d

        # 2D profile drag coefficient estimate (low-Reynolds skin friction + form drag)
        cd_profile = 0.009 + 0.005 * ((1.5e5 / max(reynolds, 1e4)) ** 0.35)
        # Induced drag: CL^2 / (pi * e * AR)
        cd_induced = (cl_required ** 2) / (math.pi * self.oswald_e * self.aspect_ratio)
        cd_total = cd_profile + cd_induced

        # Forces in Newtons
        lift_n = cl_required * q * self.area_m2
        drag_n = cd_total * q * self.area_m2
        lift_to_drag = lift_n / drag_n if drag_n > 0 else 0.0

        # Power required for level flight in Watts: P = Drag * Velocity
        power_watts = drag_n * v_mps

        return {
            "speed_mph": speed_mph,
            "speed_mps": round(v_mps, 2),
            "reynolds": int(reynolds),
            "dynamic_pressure_pa": round(q, 2),
            "cl_required": round(cl_required, 3),
            "alpha_trim_deg": round(alpha_trim_deg, 2),
            "cd_total": round(cd_total, 4),
            "cd_profile": round(cd_profile, 4),
            "cd_induced": round(cd_induced, 4),
            "lift_n": round(lift_n, 2),
            "drag_n": round(drag_n, 2),
            "drag_gf": round(drag_n * 101.97, 1),  # Grams of drag force
            "lift_to_drag": round(lift_to_drag, 2),
            "power_watts": round(power_watts, 2),
            "is_stalled": is_stalled,
        }

    def compute_stall_speed(self, aircraft_mass_kg: float = 1.0) -> float:
        """Calculates stall speed in mph for the given aircraft mass."""
        weight_n = aircraft_mass_kg * 9.80665
        v_stall_mps = math.sqrt((2.0 * weight_n) / (self.rho * self.area_m2 * self.cl_max_3d))
        return mps_to_mph(v_stall_mps)

    def compute_max_payload(
        self,
        cruise_speed_mph: float = 30.0,
        empty_mass_kg: float = 0.5,
        stall_margin_factor: float = 1.2,
    ) -> Dict[str, float]:
        """Calculates maximum aerodynamic lift and payload capacity at cruise speed.

        Args:
            cruise_speed_mph: Operational cruise speed in mph.
            empty_mass_kg: Structural/empty airframe mass in kg.
            stall_margin_factor: Required ratio of V_cruise / V_stall (standard = 1.20).

        Returns:
            Dict containing gross weight capacity, safe payload, and absolute payload.
        """
        v_mps = mph_to_mps(cruise_speed_mph)
        q = 0.5 * self.rho * (v_mps ** 2)

        # 1. Absolute Maximum Lift before immediate wing stall (CL = CL_max_3D)
        lift_absolute_max_n = q * self.area_m2 * self.cl_max_3d
        gross_absolute_max_kg = lift_absolute_max_n / 9.80665
        payload_absolute_max_kg = max(0.0, gross_absolute_max_kg - empty_mass_kg)

        # 2. Maximum Safe Lift maintaining stall margin (V_cruise >= factor * V_stall)
        # Since V_stall ~ 1/sqrt(CL), CL_safe = CL_max / (factor^2)
        cl_safe = self.cl_max_3d / (stall_margin_factor ** 2)
        lift_safe_max_n = q * self.area_m2 * cl_safe
        gross_safe_max_kg = lift_safe_max_n / 9.80665
        payload_safe_max_kg = max(0.0, gross_safe_max_kg - empty_mass_kg)

        return {
            "cruise_speed_mph": cruise_speed_mph,
            "empty_mass_kg": empty_mass_kg,
            "stall_margin_factor": stall_margin_factor,
            "cl_safe_limit": round(cl_safe, 3),
            "gross_safe_max_kg": round(gross_safe_max_kg, 2),
            "payload_safe_max_kg": round(payload_safe_max_kg, 2),
            "gross_absolute_max_kg": round(gross_absolute_max_kg, 2),
            "payload_absolute_max_kg": round(payload_absolute_max_kg, 2),
        }

    def compute_pitch_trim_state(
        self,
        speed_mph: float,
        aircraft_mass_kg: float = 1.0,
    ) -> Dict[str, Any]:
        """Evaluates aerodynamic trim when the fuselage is at zero pitch attitude.

        With geometric wing incidence (pitch_deg), the wing operates at alpha = pitch_deg
        when the fuselage is level.
        """
        v_mps = mph_to_mps(speed_mph)
        q = 0.5 * self.rho * (v_mps ** 2)
        weight_n = aircraft_mass_kg * 9.80665

        # Lift coefficient produced at geometric pitch angle (fuselage AoA = 0)
        cl_at_pitch = self.a3d_per_deg * (self.pitch_deg - self.alpha_0_deg)
        lift_at_pitch_n = cl_at_pitch * q * self.area_m2
        mass_supported_kg = lift_at_pitch_n / 9.80665

        # Required lift coefficient for 1g level flight
        cl_req = weight_n / (q * self.area_m2) if (q * self.area_m2) > 0 else 999.0
        alpha_trim_deg = (cl_req / self.a3d_per_deg) + self.alpha_0_deg
        delta_trim_deg = alpha_trim_deg - self.pitch_deg

        return {
            "pitch_deg": self.pitch_deg,
            "cl_at_level_fuselage": round(cl_at_pitch, 3),
            "lift_at_level_fuselage_n": round(lift_at_pitch_n, 2),
            "mass_supported_at_level_fuselage_kg": round(mass_supported_kg, 2),
            "required_trim_aoa_deg": round(alpha_trim_deg, 2),
            "fuselage_trim_angle_deg": round(delta_trim_deg, 2),
            "is_aligned_with_cruise": abs(delta_trim_deg) <= 1.0,
        }

    def sweep_speeds(
        self,
        speed_list_mph: List[float],
        aircraft_mass_kg: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """Sweeps an array of speeds and returns performance records."""
        return [self.compute_flight_point(spd, aircraft_mass_kg) for spd in speed_list_mph]


def run_aerodynamic_analysis(
    doc=None,
    target_mass_kg: float = 1.0,
    empty_mass_kg: float = 0.5,
    cruise_speed_mph: Optional[float] = None,
    cruise_speed_mps: Optional[float] = None,
    output_dir: Optional[str] = None,
    params_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Reads CAD wing parameters and runs aerodynamic performance analysis."""
    if cruise_speed_mps is not None:
        cruise_speed_mph = mps_to_mph(cruise_speed_mps)
    elif cruise_speed_mph is None:
        cruise_speed_mph = 30.0

    span = 700.0
    root = 200.0
    tip = 90.0
    sweep = 0.0
    dihedral = 0.0
    pitch = 0.0
    airfoil = "NACA 2412"

    try:
        import FreeCAD as App
        try:
            import builtins, FreeCADGui
            if not hasattr(FreeCADGui, "addCommand"):
                FreeCADGui.addCommand = lambda *args, **kwargs: None
            builtins.FreeCADGui = FreeCADGui
        except Exception:
            pass

        if doc is None and not params_override:
            doc = App.ActiveDocument
            if not doc:
                cfd_path = os.path.join(SCRIPT_DIR, "MBSE_Params_CFD.FCStd")
                if os.path.exists(cfd_path):
                    doc = App.openDocument(cfd_path)

        if doc:
            sheets = doc.getObjectsByLabel("MBSE_Params")
            if sheets:
                sheet = sheets[0]
                span = float(sheet.get("Span"))
                root = float(sheet.get("RootChord"))
                tip = float(sheet.get("TipChord"))
                sweep = float(sheet.get("SweepAngle"))
                dihedral = float(sheet.get("DihedralAngle"))
                try:
                    pitch = float(sheet.get("PitchAngle"))
                except Exception:
                    pitch = 0.0
                raw_af = str(sheet.get("AirfoilPath")).strip("'\"")
                airfoil = os.path.basename(raw_af).replace(".dat", "").replace("_", " ")
    except Exception as e:
        print(f"Note: Running with standard CAD parameters ({e})")

    # Apply external parameters from middleware if provided
    if params_override:
        span = float(params_override.get("Span", span))
        root = float(params_override.get("RootChord", root))
        tip = float(params_override.get("TipChord", tip))
        sweep = float(params_override.get("SweepAngle", sweep))
        dihedral = float(params_override.get("DihedralAngle", dihedral))
        pitch = float(params_override.get("PitchAngle", pitch))
        if "AirfoilPath" in params_override:
            raw_af = str(params_override["AirfoilPath"]).strip("'\"")
            airfoil = os.path.basename(raw_af).replace(".dat", "").replace("_", " ")

    simulator = WingAeroSimulator(
        span_mm=span,
        root_chord_mm=root,
        tip_chord_mm=tip,
        sweep_deg=sweep,
        dihedral_deg=dihedral,
        pitch_deg=pitch,
        airfoil_name=airfoil,
    )

    stall_speed_gross_mph = simulator.compute_stall_speed(target_mass_kg)
    stall_speed_empty_mph = simulator.compute_stall_speed(empty_mass_kg)
    cruise_point = simulator.compute_flight_point(cruise_speed_mph, target_mass_kg)
    payload_info = simulator.compute_max_payload(cruise_speed_mph, empty_mass_kg=empty_mass_kg)
    pitch_trim_info = simulator.compute_pitch_trim_state(cruise_speed_mph, target_mass_kg)

    speeds = [15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0]
    sweep_results = simulator.sweep_speeds(speeds, target_mass_kg)

    # Print comprehensive performance report
    print("\n" + "=" * 78)
    print(f"  AERODYNAMIC SIMULATION REPORT: 1.0 kg AIRCRAFT WING")
    print("=" * 78)
    print(f"Wing Geometry:")
    print(f"  - Wingspan:            {simulator.span_m * 1000.0:.1f} mm")
    print(f"  - Root Chord:          {simulator.root_m * 1000.0:.1f} mm")
    print(f"  - Tip Chord:           {simulator.tip_m * 1000.0:.1f} mm")
    print(f"  - Wing Area (S):       {simulator.area_m2:.4f} m^2 ({simulator.area_m2 * 1e4:.1f} cm^2)")
    print(f"  - Aspect Ratio:        {simulator.aspect_ratio:.2f}")
    print(f"  - Mean Chord:          {simulator.mean_chord_m * 1000.0:.1f} mm")
    print(f"  - Airfoil Section:     {simulator.airfoil}")
    print(f"  - Built-in Wing Pitch: {simulator.pitch_deg:.1f} deg (Incidence Angle)")
    print(f"  - Aircraft Gross Mass: {target_mass_kg:.2f} kg (Weight = {target_mass_kg * 9.80665:.2f} N)")
    print(f"  - Airframe Empty Mass: {empty_mass_kg:.2f} kg")
    print("-" * 78)
    print("FLIGHT PERFORMANCE & PAYLOAD LIMITS:")
    print(f"  - Stall Speed (Empty): {stall_speed_empty_mph:.1f} mph ({mph_to_mps(stall_speed_empty_mph):.1f} m/s)")
    print(f"  - Stall Speed (Gross): {stall_speed_gross_mph:.1f} mph ({mph_to_mps(stall_speed_gross_mph):.1f} m/s)")
    print(f"  - Cruise Stall Margin: {cruise_speed_mph - stall_speed_gross_mph:.1f} mph above stall")
    print(f"  - Max Safe Gross Mass: {payload_info['gross_safe_max_kg']:.2f} kg (20% stall speed margin at {cruise_speed_mph:.0f} mph)")
    print(f"  - Max Safe Payload:    {payload_info['payload_safe_max_kg']:.2f} kg ({payload_info['payload_safe_max_kg'] * 1000.0:.0f} g)")
    print(f"  - Absolute Max Payload:{payload_info['payload_absolute_max_kg']:.2f} kg ({payload_info['payload_absolute_max_kg'] * 1000.0:.0f} g, at CL_max)")
    print("-" * 78)
    print("FUSELAGE ATTITUDE & PITCH ALIGNMENT AT CRUISE:")
    print(f"  - Required Trim AoA:   {pitch_trim_info['required_trim_aoa_deg']:.1f} deg")
    print(f"  - Fuselage Trim Angle: {pitch_trim_info['fuselage_trim_angle_deg']:.1f} deg (Fuselage AoA relative to horizon)")
    if pitch_trim_info["is_aligned_with_cruise"]:
        print(f"  - Alignment Status:    OPTIMAL! Fuselage flies near 0 deg attitude at cruise.")
    elif pitch_trim_info["fuselage_trim_angle_deg"] > 0:
        print(f"  - Alignment Status:    Fuselage pitches nose-up by {pitch_trim_info['fuselage_trim_angle_deg']:.1f} deg. Consider increasing PitchAngle.")
    else:
        print(f"  - Alignment Status:    Fuselage pitches nose-down by {abs(pitch_trim_info['fuselage_trim_angle_deg']):.1f} deg.")
    print("-" * 78)
    print("SPEED SWEEP ANALYSIS (Level Flight Trim Condition):")
    print(f"{'Speed':>9} | {'Dyn.P':>7} | {'Re':>7} | {'Req.CL':>7} | {'Trim AoA':>9} | {'Drag':>7} | {'L/D':>6} | {'Power':>7} | {'Status':>8}")
    print(f"{'(mph)':>9} | {'(Pa)':>7} | {'':>7} | {'':>7} | {'(deg)':>9} | {'(g)':>7} | {'':>6} | {'(W)':>7} | {'':>8}")
    print("-" * 78)

    for r in sweep_results:
        status = "STALL" if r["is_stalled"] else ("CRUISE" if r["speed_mph"] == cruise_speed_mph else "OK")
        aoa_str = f"{r['alpha_trim_deg']:.1f} deg" if not r["is_stalled"] else "N/A"
        print(
            f"{r['speed_mph']:>7.0f} mph | "
            f"{r['dynamic_pressure_pa']:>7.1f} | "
            f"{r['reynolds']:>7d} | "
            f"{r['cl_required']:>7.3f} | "
            f"{aoa_str:>9} | "
            f"{r['drag_gf']:>6.1f}g | "
            f"{r['lift_to_drag']:>6.1f} | "
            f"{r['power_watts']:>6.1f}W | "
            f"{status:>8}"
        )

    print("-" * 78)
    print(f"CRUISE EVALUATION AT {cruise_speed_mph:.0f} MPH:")
    if cruise_point["is_stalled"]:
        print(f"  [FAIL] Wing is STALLED at {cruise_speed_mph:.0f} mph! Increase wing area or cruise faster.")
    elif cruise_point["cl_required"] > 0.8:
        print(f"  [CAUTION] Cruise CL ({cruise_point['cl_required']:.2f}) is high. Wing flies at {cruise_point['alpha_trim_deg']:.1f} deg AoA.")
        print(f"            Speed margin above stall: {cruise_speed_mph - stall_speed_gross_mph:.1f} mph.")
    else:
        print(f"  [PASS] Wing operates in ideal cruise regime!")
        print(f"  - Lift Generated:      {cruise_point['lift_n']:.2f} N (Supports {target_mass_kg:.2f} kg aircraft)")
        print(f"  - Trim AoA:            {cruise_point['alpha_trim_deg']:.1f} deg")
        print(f"  - Total Drag:          {cruise_point['drag_gf']:.1f} grams ({cruise_point['drag_n']:.2f} N)")
        print(f"  - Aerodynamic L/D:     {cruise_point['lift_to_drag']:.1f}")
        print(f"  - Motor Power Req:     {cruise_point['power_watts']:.1f} Watts (thrust power)")
        print(f"  - Stall Margin:        Safe by {cruise_speed_mph - stall_speed_gross_mph:.1f} mph (Stall = {stall_speed_gross_mph:.1f} mph)")
    print("=" * 78 + "\n")

    stall_speed_gross_mps = mph_to_mps(stall_speed_gross_mph)
    stall_speed_empty_mps = mph_to_mps(stall_speed_empty_mph)
    cruise_speed_mps = mph_to_mps(cruise_speed_mph)

    report_data = {
        "aircraft": {
            "target_mass_kg": target_mass_kg,
            "empty_mass_kg": empty_mass_kg,
            "weight_n": round(target_mass_kg * 9.80665, 2),
            "cruise_speed_mph": round(cruise_speed_mph, 1),
            "cruise_speed_mps": round(cruise_speed_mps, 2),
        },
        "wing_geometry": {
            "span_mm": simulator.span_m * 1000.0,
            "root_chord_mm": simulator.root_m * 1000.0,
            "tip_chord_mm": simulator.tip_m * 1000.0,
            "wing_area_m2": round(simulator.area_m2, 4),
            "aspect_ratio": round(simulator.aspect_ratio, 2),
            "mean_chord_mm": round(simulator.mean_chord_m * 1000.0, 1),
            "pitch_deg": simulator.pitch_deg,
            "sweep_deg": sweep,
            "dihedral_deg": dihedral,
            "airfoil": simulator.airfoil,
        },
        "flight_performance": {
            "stall_speed_empty_mph": round(stall_speed_empty_mph, 1),
            "stall_speed_empty_mps": round(stall_speed_empty_mps, 2),
            "stall_speed_gross_mph": round(stall_speed_gross_mph, 1),
            "stall_speed_gross_mps": round(stall_speed_gross_mps, 2),
            "stall_margin_mph": round(cruise_speed_mph - stall_speed_gross_mph, 1),
            "stall_margin_mps": round(cruise_speed_mps - stall_speed_gross_mps, 2),
            "payload_capacity": payload_info,
            "pitch_trim": pitch_trim_info,
            "cruise_condition": cruise_point,
        },
        "speed_sweep": sweep_results,
    }

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, "aerodynamic_report.json")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)
            print(f"Saved structured aerodynamic report: {json_path}")
        except Exception as e:
            print(f"Warning: Failed to write JSON report ({e})")

    return report_data


if __name__ == "__main__":
    out_dir = None
    override_dict = None
    target_mass = 1.0
    empty_mass = 0.5
    cruise_speed = 30.0

    if len(sys.argv) > 1:
        arg1 = sys.argv[1]
        if arg1.lower().endswith(".json") and os.path.exists(arg1):
            with open(arg1, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                override_dict = cfg.get("cad_parameters", cfg)
                out_dir = cfg.get("output_dir", None)
                target_mass = float(cfg.get("target_mass_kg", target_mass))
                empty_mass = float(cfg.get("empty_mass_kg", empty_mass))
                cruise_speed = float(cfg.get("cruise_speed_mph", cruise_speed))
        elif not arg1.startswith("-"):
            out_dir = arg1

    if len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
        out_dir = sys.argv[2]

    run_aerodynamic_analysis(
        target_mass_kg=target_mass,
        empty_mass_kg=empty_mass,
        cruise_speed_mph=cruise_speed,
        output_dir=out_dir,
        params_override=override_dict,
    )
