"""
Top-level MBSE-to-CAD Pipeline Orchestrator CLI.
Connects mission requirements -> MBSE sizing math -> dynamic airfoil generation -> FreeCAD 3D model generation & STL export -> aerodynamic simulation -> success verification report.
"""
import os
import sys
import argparse
import json
from middleware.sysml_adapter import SysMLAdapter
from cad.run_cad_headless import run_cad_generation
from cad.simulate_aerodynamics import run_aerodynamic_analysis


def main():
    parser = argparse.ArgumentParser(description="MBSE-to-CAD Wing Sizing, CAD Generation & Verification Pipeline")
    parser.add_argument("--mission", type=str, default="model/requirements/mission_reqs.sysml",
                        help="Path to mission requirements file (.sysml or .json) or inline JSON string.")
    parser.add_argument("--output_dir", type=str, default="output",
                        help="Directory to save output STL, STEP, and CAD files.")
    parser.add_argument("--cruise_speed", type=float, help="Cruise airspeed target (m/s)")
    parser.add_argument("--stall_speed", type=float, help="Stall speed limit (m/s)")
    parser.add_argument("--payload_mass", type=float, help="Payload mass (kg)")
    parser.add_argument("--max_span", type=float, help="Wingspan upper bound (mm)")
    parser.add_argument("--duration", "--flight_duration", dest="flight_duration", type=float,
                        help="Target flight duration (minutes)")
    parser.add_argument("--skip_cad", action="store_true",
                        help="Skip 3D FreeCAD mesh generation (run MBSE sizing and aero verification only).")
    parser.add_argument("--cfd_visuals", action="store_true",
                        help="Trigger ParaView CFD cross-section post-processing if case exists.")

    args = parser.parse_args()

    project_root = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Resolve mission input path if relative
    mission_input = args.mission
    if isinstance(mission_input, str) and not os.path.isabs(mission_input) and not mission_input.startswith("{"):
        potential_path = os.path.join(project_root, mission_input)
        if os.path.exists(potential_path):
            mission_input = potential_path

    # Initialize adapter
    adapter = SysMLAdapter()

    # Load mission requirements
    if isinstance(mission_input, str) and mission_input.startswith("{"):
        mission_reqs = json.loads(mission_input)
    else:
        mission_reqs = adapter.process_mission(mission_input)["mission_requirements"]

    # Apply CLI overrides if present
    if args.cruise_speed is not None:
        mission_reqs["cruise_speed"] = args.cruise_speed
    if args.stall_speed is not None:
        mission_reqs["stall_speed_max"] = args.stall_speed
    if args.payload_mass is not None:
        mission_reqs["payload_mass"] = args.payload_mass
    if args.max_span is not None:
        mission_reqs["max_span_mm"] = args.max_span
    if args.flight_duration is not None:
        mission_reqs["flight_duration_min"] = args.flight_duration

    print("======================================================================")
    print("           DAEDALUS THREAD: MISSION -> MBSE -> CAD PIPELINE           ")
    print("======================================================================")
    print("Mission Input Parameters:")
    print(f"  1. Cruise Airspeed Target:   {mission_reqs.get('cruise_speed', 18.0):.1f} m/s")
    print(f"  2. Stall Speed Limit:        {mission_reqs.get('stall_speed_max', 11.0):.1f} m/s")
    print(f"  3. Payload Mass:             {mission_reqs.get('payload_mass', 1.2):.2f} kg")
    print(f"  4. Wingspan Upper Bound:     {mission_reqs.get('max_span_mm', 1800.0):.1f} mm")
    print(f"  5. Target Flight Duration:   {mission_reqs.get('flight_duration_min', 45.0):.1f} min")

    # 1. Process sizing and dynamic airfoil generation
    pipeline_result = adapter.process_mission(mission_reqs)
    sizing = pipeline_result["sizing_results"]
    cad_params = pipeline_result["cad_parameters"]

    print("\n--- 1. MBSE Wing Sizing Results ---")
    print(f"  - Total Aircraft Gross Mass: {sizing['total_mass_kg']:.2f} kg")
    print(f"    * Payload Mass:            {sizing['payload_mass_kg']:.2f} kg")
    print(f"    * Structural Airframe:     {sizing['airframe_mass_kg']:.2f} kg")
    print(f"    * Battery Pack:            {sizing['battery_mass_kg']:.2f} kg ({sizing['battery_energy_wh']:.1f} Wh)")
    print(f"  - Wing Surface Area:         {sizing['wing_area_m2']:.4f} m^2")
    print(f"  - Aspect Ratio:              {sizing['aspect_ratio']:.2f}")
    print(f"  - Wingspan:                  {sizing['span_mm']:.1f} mm {'(Clamped to max limit)' if sizing['is_span_clamped'] else ''}")
    print(f"  - Root Chord / Tip Chord:    {sizing['root_chord_mm']:.1f} mm / {sizing['tip_chord_mm']:.1f} mm")
    print(f"  - Airfoil Profile:           {sizing['airfoil_designation']}")
    print(f"  - Wing Pitch Incidence Trim: {sizing['pitch_angle_deg']:.1f} deg")

    # 2. Synchronize sized architecture back to SysML model
    sysml_out = adapter.sync_to_sysml(sizing)
    print(f"\n--- 2. SysML Architecture Updated ---")
    print(f"  - SysML v2 Architecture:     {sysml_out}")

    # 3. 3D CAD Generation via FreeCAD headless
    cad_files = {}
    cad_success = True
    if not args.skip_cad:
        print("\n--- 3. Invoking Headless FreeCAD CAD Generator ---")
        cad_success = run_cad_generation(pipeline_result, output_dir)
        if cad_success:
            cad_files = {
                "Wing Main STL": os.path.join(output_dir, "wing_main.stl"),
                "Wing Aileron STL": os.path.join(output_dir, "wing_aileron.stl"),
                "Wing Assembly STEP": os.path.join(output_dir, "wing_assembly.step"),
                "FreeCAD Document": os.path.join(output_dir, "generated_wing.FCStd"),
            }
            print("  [SUCCESS] CAD models and 3D mesh files generated.")
        else:
            print("  [WARNING] FreeCAD generation returned failure or missing STL.")
    else:
        print("\n--- 3. Skipping FreeCAD CAD Generation (--skip_cad specified) ---")

    # 4. Aerodynamic Simulation & Flight Performance Analysis
    print("\n--- 4. Running Aerodynamic Simulation & Performance Analysis ---")
    aero_report = run_aerodynamic_analysis(
        target_mass_kg=sizing["total_mass_kg"],
        empty_mass_kg=sizing["airframe_mass_kg"],
        cruise_speed_mps=mission_reqs["cruise_speed"],
        output_dir=output_dir,
        params_override=cad_params,
    )
    cad_files["Aerodynamic Report JSON"] = os.path.join(output_dir, "aerodynamic_report.json")

    # 5. Optional CFD Visuals post-processing
    if args.cfd_visuals:
        print("\n--- 5. Triggering ParaView CFD Post-Processing ---")
        try:
            from cad.export_cfd_visuals import run_paraview_postprocess
            run_paraview_postprocess()
            cad_files["CFD Midspan Pressure PNG"] = os.path.join(project_root, "cad", "output", "cfd_midspan_pressure.png")
            cad_files["CFD Midspan Velocity PNG"] = os.path.join(project_root, "cad", "output", "cfd_midspan_velocity.png")
        except Exception as e:
            print(f"  [NOTE] CFD visuals generation: {e}")

    # 6. Generate Success / Mission Requirements Verification Report
    print("\n--- 6. Verifying Mission Requirements & Compiling Report ---")
    report = adapter.generate_verification_report(
        mission_reqs=mission_reqs,
        sizing_results=sizing,
        aero_results=aero_report,
        cad_files=cad_files,
        output_dir=output_dir,
    )

    print("\n======================================================================")
    print(f" MISSION REQUIREMENTS VERIFICATION SUMMARY: [{report['overall_status']}]")
    print("======================================================================")
    print(f"{'Requirement Parameter':<26} | {'Target':<12} | {'Achieved':<12} | {'Margin':<16} | {'Status':<6}")
    print("-" * 80)
    for c in report["checks"]:
        print(f"{c['parameter']:<26} | {c['target_value']:<12} | {c['achieved_value']:<12} | {c['margin']:<16} | {c['status']:<6}")
    print("=" * 80)
    print(f"Mission Success Report & Visuals:")
    print(f"  - Report Directory: {report.get('report_dir', output_dir)}")
    print(f"  - Markdown Report:  {report.get('markdown_file')}")
    print(f"  - JSON Report:      {report.get('json_file')}")
    if report.get("images"):
        print(f"  - Generated Visuals in report/:")
        for img_type, img_name in report["images"].items():
            print(f"    * {img_type}: {img_name}")
    print(f"Root Output Directory: {output_dir}")
    if report["overall_status"] != "SUCCESS":
        sys.exit(2)


if __name__ == "__main__":
    main()

