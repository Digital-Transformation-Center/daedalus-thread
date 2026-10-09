"""End-to-End Digital Thread Pipeline Runner for Phase 1.

Orchestrates the entire flow from five mission parameter requirements:
1. Cruise airspeed target (m/s)
2. Stall speed limit (m/s)
3. Payload mass (kg)
4. Wingspan upper bound (mm)
5. Target flight duration (minutes)

Ingests requirements, executes aeromechanical and powertrain mass convergence,
drives headless FreeCAD to generate CAD geometry and export 3D-printable STLs,
evaluates verification cases, and posts verdicts to SysML v2.
"""

import argparse
import json
import os
import sys
from typing import Optional

from middleware.sysml_client import SysMLClient
from middleware.sizing.aero import size_wing
from middleware.bridge_cad import run_headless_cad
from middleware.verify import VerificationEngine


def run_pipeline(
    offline: bool = False,
    mock_cad: bool = False,
    export_step: bool = False,
    export_stl: bool = False,
    output_dir: str = "output/phase1_run",
    server_url: str = "http://localhost:9000",
    cruise_speed: Optional[float] = None,
    stall_speed: Optional[float] = None,
    payload_mass: Optional[float] = None,
    max_span: Optional[float] = None,
    duration: Optional[float] = None,
    total_mass: Optional[float] = None
) -> int:
    """Executes the Phase 1 Digital Thread orchestration."""
    os.makedirs(output_dir, exist_ok=True)
    print("=" * 78)
    print("Starting Daedalus Thread Phase 1 Pipeline Execution")
    print("=" * 78)

    # 1. SysML v2 Client Initialization & Requirement Retrieval
    print("\n[Step 1/5] Ingesting SysML v2 Requirements...")
    client = SysMLClient(base_url=server_url, offline=offline)
    if client.is_server_available():
        print(f"Connected to SysML v2 REST API at {server_url}")
    else:
        print("Using local SysML v2 model repository.")

    reqs = client.load_requirements()

    # Apply mission parameter overrides if provided by engineer
    if cruise_speed is not None:
        reqs["minCruiseSpeed"] = cruise_speed
    if stall_speed is not None:
        reqs["maxStallSpeed"] = stall_speed
    if payload_mass is not None:
        reqs["minPayloadMass"] = payload_mass
    if max_span is not None:
        reqs["maxWingspan"] = max_span
    if duration is not None:
        reqs["minFlightDuration"] = duration

    print(f"Active Mission Requirements:")
    print(f"  Cruise Airspeed Target: >= {reqs.get('minCruiseSpeed')} m/s")
    print(f"  Stall Speed Limit:     <= {reqs.get('maxStallSpeed')} m/s")
    print(f"  Payload Mass:          >= {reqs.get('minPayloadMass')} kg")
    print(f"  Wingspan Upper Bound:  <= {reqs.get('maxWingspan')} mm")
    print(f"  Flight Duration Target: >= {reqs.get('minFlightDuration')} min")

    # 2. Physics Aerodynamic & Powertrain Mass Convergence Sizing
    print("\n[Step 2/5] Executing Physics Mass Convergence & Aero Sizing...")
    aero_sizing = size_wing(
        total_mass_kg=total_mass,
        stall_speed_max_mps=float(reqs.get("maxStallSpeed", 11.0)),
        cruise_speed_min_mps=float(reqs.get("minCruiseSpeed", 18.0)),
        payload_mass_kg=float(reqs.get("minPayloadMass", 1.2)),
        span_limit_mm=float(reqs.get("maxWingspan", 1800.0)),
        flight_duration_min=float(reqs.get("minFlightDuration", 30.0)),
        airfoil_max_cl=float(reqs.get("airfoilMaxCL", 1.4)),
        airfoil_designation=str(reqs.get("airfoilDesignation", "NACA 2412"))
    )

    print(f"Sized Vehicle Mass Budget:")
    print(f"  Converged AUW:    {aero_sizing.total_mass_kg} kg")
    print(f"  Payload Mass:     {aero_sizing.payload_mass_kg} kg")
    print(f"  Battery Mass:     {aero_sizing.battery_mass_kg} kg")
    print(f"  Est. Wing Mass:   {aero_sizing.estimated_wing_mass_kg} kg")
    print(f"  COTS Base Mass:   {aero_sizing.cots_base_mass_kg} kg")
    print(f"Sized Planform Geometry:")
    print(f"  Wingspan:         {aero_sizing.span_mm} mm (AR: {aero_sizing.aspect_ratio})")
    print(f"  Root Chord:       {aero_sizing.root_chord_mm} mm | Tip Chord: {aero_sizing.tip_chord_mm} mm")
    print(f"  Wing Area:        {aero_sizing.wing_area_m2} m^2")
    print(f"  Cruise Power:     {aero_sizing.cruise_power_watts} W")
    print(f"  Calculated Stall: {aero_sizing.calculated_stall_speed_mps} m/s")

    # 3. Parametric CAD Generation & Mass Extraction
    print("\n[Step 3/5] Driving Parametric CAD via Headless FreeCAD...")
    cad_params = {
        "span_mm": aero_sizing.span_mm,
        "root_chord_mm": aero_sizing.root_chord_mm,
        "tip_chord_mm": aero_sizing.tip_chord_mm,
        "sweep_deg": aero_sizing.sweep_deg,
        "dihedral_deg": aero_sizing.dihedral_deg,
        "airfoil_path": "airfoils/NACA_2412.dat"
    }

    cad_results = run_headless_cad(
        params=cad_params,
        output_dir=output_dir,
        export_step=export_step,
        export_stl=export_stl,
        mock=mock_cad
    )

    print(f"CAD Solid Generated:")
    print(f"  Total Wing Mass:   {cad_results.get('total_wing_mass_kg')} kg")
    print(f"  Half-Wing Volume:  {cad_results.get('half_volume_mm3')} mm^3")
    print(f"  Center of Gravity: {cad_results.get('center_of_gravity')} mm")
    if "build_envelope_mm" in cad_results:
        env = cad_results["build_envelope_mm"]
        print(f"  Build Envelope:    X: {env.get('chord_x')} mm, Y: {env.get('span_y')} mm, Z: {env.get('thickness_z')} mm")

    if cad_results.get("exported_files"):
        print(f"Exported CAD Files:")
        for ef in cad_results["exported_files"]:
            print(f"  - {ef}")

    # 4. Requirements Verification
    print("\n[Step 4/5] Evaluating Verification Cases Against Requirements...")
    engine = VerificationEngine(requirements=reqs)
    report = engine.evaluate(aero_results=aero_sizing.to_dict(), cad_results=cad_results)

    # 5. Publishing Verdicts Back to SysML v2
    print("\n[Step 5/5] Recording Verification Verdicts to SysML v2...")
    client.post_verification_result(report)

    # Print Formatted Verification Table
    print("\n" + engine.format_text_report(report))

    # Save Report Files
    report_path = os.path.join(output_dir, "verification_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nVerification report written to: {report_path}")

    return 0 if report.get("overall_pass") else 1


def main():
    parser = argparse.ArgumentParser(description="Daedalus Thread Phase 1 Pipeline Runner")
    parser.add_argument("--offline", action="store_true", help="Run offline without remote SysML v2 server")
    parser.add_argument("--mock-cad", action="store_true", help="Use analytical mock instead of launching FreeCAD")
    parser.add_argument("--export-step", action="store_true", help="Export STEP CAD solid")
    parser.add_argument("--export-stl", action="store_true", help="Export STL surface meshes for 3D printing")
    parser.add_argument("--output-dir", type=str, default="output/phase1_run", help="Output directory")
    parser.add_argument("--server-url", type=str, default="http://localhost:9000", help="SysML v2 server URL")

    # The 5 primary mission parameter inputs
    parser.add_argument("--cruise-speed", type=float, help="Cruise airspeed target in m/s")
    parser.add_argument("--stall-speed", type=float, help="Stall speed limit in m/s")
    parser.add_argument("--payload-mass", type=float, help="Payload mass in kg")
    parser.add_argument("--max-span", type=float, help="Wingspan upper bound in mm")
    parser.add_argument("--duration", type=float, help="Target flight duration in minutes")
    parser.add_argument("--total-mass", type=float, help="Optional manual AUW override in kg")

    args = parser.parse_args()
    sys.exit(run_pipeline(
        offline=args.offline,
        mock_cad=args.mock_cad,
        export_step=args.export_step,
        export_stl=args.export_stl,
        output_dir=args.output_dir,
        server_url=args.server_url,
        cruise_speed=args.cruise_speed,
        stall_speed=args.stall_speed,
        payload_mass=args.payload_mass,
        max_span=args.max_span,
        duration=args.duration,
        total_mass=args.total_mass
    ))


if __name__ == "__main__":
    main()
