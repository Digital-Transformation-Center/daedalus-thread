"""
SysML adapter module bridging SysML v2 model requirement definitions and JSON configs with the CAD generator.
"""
import os
import json
import re
from typing import Dict, Any
from .wing_sizer import WingSizer
from generators.airfoil_generator import generate_naca4_dat


class SysMLAdapter:
    """Loads mission requirements, computes wing sizing, generates dynamic airfoil, formats CAD inputs, and generates verification reports."""

    def __init__(self, sysml_dir: str = None, cad_dir: str = None):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.root_dir = root_dir
        self.sysml_dir = sysml_dir or os.path.join(root_dir, "model")
        self.cad_dir = cad_dir or os.path.join(root_dir, "cad")
        self.sizer = WingSizer()

    def parse_sysml_requirements(self, sysml_file_path: str) -> Dict[str, Any]:
        """Extracts mission requirement attributes from SysML v2 files."""
        if not os.path.exists(sysml_file_path):
            return {}

        reqs = {}
        with open(sysml_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract attribute statements: attribute :>> name = value; or attribute name = value;
        matches = re.findall(r'attribute\s+(?::>>\s+)?(\w+)\s*=\s*([\d.]+);', content)
        for attr_name, val_str in matches:
            val = float(val_str)
            lower_name = attr_name.lower()
            if "cruisespeed" in lower_name:
                reqs["cruise_speed"] = val
            elif "stallspeed" in lower_name:
                reqs["stall_speed_max"] = val
            elif "payloadmass" in lower_name:
                reqs["payload_mass"] = val
            elif "wingspan" in lower_name or "maxspan" in lower_name or "spanmax" in lower_name:
                reqs["max_span_mm"] = val
            elif "duration" in lower_name or "endurance" in lower_name:
                reqs["flight_duration_min"] = val

        return reqs

    def process_mission(self, mission_input: Dict[str, Any] or str) -> Dict[str, Any]:
        """
        Processes mission requirement inputs from dict, JSON file path, or SysML file path.
        Returns full parameter payload ready for CAD generation.
        """
        mission_reqs = {}
        if isinstance(mission_input, str):
            if mission_input.endswith(".json") and os.path.exists(mission_input):
                with open(mission_input, "r", encoding="utf-8") as f:
                    mission_reqs = json.load(f)
            elif mission_input.endswith(".sysml") and os.path.exists(mission_input):
                mission_reqs = self.parse_sysml_requirements(mission_input)
            else:
                raise ValueError(f"Unsupported mission input file: {mission_input}")
        elif isinstance(mission_input, dict):
            mission_reqs = mission_input
        else:
            raise ValueError("mission_input must be a dict or valid file path string")

        # Compute wing sizing
        sizing_results = self.sizer.calculate_sizing(mission_reqs)

        # Generate dynamic NACA airfoil .dat file in cad/airfoils/
        airfoil_code = sizing_results["airfoil_designation"]
        airfoil_filename = f"{airfoil_code.replace(' ', '_')}.dat"
        airfoil_output_path = os.path.join(self.cad_dir, "airfoils", airfoil_filename)

        generate_naca4_dat(airfoil_code, airfoil_output_path)
        rel_airfoil_path = os.path.relpath(airfoil_output_path, self.cad_dir)

        # Construct CAD spreadsheet parameters dictionary
        cad_params = {
            "Span": sizing_results["span_mm"],
            "RootChord": sizing_results["root_chord_mm"],
            "TipChord": sizing_results["tip_chord_mm"],
            "SweepAngle": sizing_results["sweep_angle_deg"],
            "DihedralAngle": sizing_results["dihedral_angle_deg"],
            "PitchAngle": sizing_results.get("pitch_angle_deg", 0.0),
            "AirfoilPath": rel_airfoil_path.replace("\\", "/"),
            # Retain defaults for aileron and servo if not specified
            "AileronStartRatio": 0.20,
            "AileronEndRatio": 0.70,
            "AileronChordRatio": 0.25,
            "HingeGap": 0.6,
            "HingeBevelAngle": 35.0,
            "HingePinDiameter": 1.6,
            "HingeTabCount": 3,
            "ServoType": "HeeWing_FX5G",
            "ServoSpanOffsetRatio": 0.25,
        }

        return {
            "mission_requirements": mission_reqs,
            "sizing_results": sizing_results,
            "cad_parameters": cad_params,
            "airfoil_file_path": airfoil_output_path
        }

    def sync_to_sysml(self, sizing_results: Dict[str, Any], output_path: str = None) -> str:
        """
        Synchronizes the generated wing sizing parameters back into a SysML v2 architecture model.
        Returns the path to the updated SysML file.
        """
        if output_path is None:
            output_path = os.path.join(self.sysml_dir, "architecture", "generated_airframe.sysml")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        span = sizing_results.get("span_mm", 1800.0)
        root = sizing_results.get("root_chord_mm", 240.0)
        tip = sizing_results.get("tip_chord_mm", 160.0)
        sweep = sizing_results.get("sweep_angle_deg", 3.5)
        dihedral = sizing_results.get("dihedral_angle_deg", 2.0)
        pitch = sizing_results.get("pitch_angle_deg", 2.5)
        wing_area = sizing_results.get("wing_area_m2", 0.36)
        ar = sizing_results.get("aspect_ratio", 7.5)
        cl_cruise = sizing_results.get("cruise_cl", 0.45)
        gross_mass = sizing_results.get("total_mass_kg", 3.0)
        payload_mass = sizing_results.get("payload_mass_kg", 1.2)
        battery_mass = sizing_results.get("battery_mass_kg", 0.8)
        duration = sizing_results.get("flight_duration_min", 45.0)
        airfoil = sizing_results.get("airfoil_designation", "NACA 4412")
        camber = sizing_results.get("airfoil_max_camber_percent", 4.0)
        thickness = sizing_results.get("airfoil_max_thickness_percent", 12.0)

        sysml_code = f"""package GeneratedAirframeArchitecture {{
    private import ScalarValues::*;
    private import MissionRequirements::*;
    private import AirframeArchitecture::*;

    // Automatically generated UAV Wing instance synthesized by MBSE pipeline
    part generatedUavWing : WingAssembly {{
        doc /* Synthesized instance from mission requirements */
        attribute :>> span = {span:.1f}; // mm
        attribute :>> rootChord = {root:.1f}; // mm
        attribute :>> tipChord = {tip:.1f}; // mm
        attribute :>> sweepAngle = {sweep:.1f}; // deg
        attribute :>> dihedralAngle = {dihedral:.1f}; // deg
        attribute :>> pitchAngle = {pitch:.1f}; // deg

        attribute :>> wingAreaM2 = {wing_area:.4f}; // m^2
        attribute :>> aspectRatio = {ar:.2f};
        attribute :>> cruiseCL = {cl_cruise:.3f};

        attribute :>> grossMassKg = {gross_mass:.3f};
        attribute :>> payloadMassKg = {payload_mass:.3f};
        attribute :>> batteryMassKg = {battery_mass:.3f};
        attribute :>> flightDurationMin = {duration:.1f};

        part :>> profile {{
            attribute :>> designation = "{airfoil}";
            attribute :>> maxThicknessPercent = {thickness:.1f};
            attribute :>> maxCamberPercent = {camber:.1f};
            attribute :>> designCL = {cl_cruise:.3f};
        }}

        satisfy reconMissionReq;
    }}
}}
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(sysml_code)

        return output_path

    def generate_verification_report(
        self,
        mission_reqs: Dict[str, Any],
        sizing_results: Dict[str, Any],
        aero_results: Dict[str, Any],
        cad_files: Dict[str, str] = None,
        output_dir: str = None
    ) -> Dict[str, Any]:
        """
        Creates structured JSON and Markdown success verification reports in output_dir/report/,
        including embedded images of the 3D CAD wing, airfoil profile, and CFD cross-sections.
        """
        import shutil
        verification = self.sizer.verify_mission_requirements(mission_reqs, sizing_results, aero_results)

        report_dir = os.path.join(output_dir, "report") if output_dir else None
        if report_dir:
            os.makedirs(report_dir, exist_ok=True)

        images = {}

        # 1. Generate Wing 3D CAD render and Airfoil profile plot in report/
        if report_dir:
            from cad.render_wing import render_wing_cad, render_airfoil_plot

            wing_stl = None
            aileron_stl = None
            if cad_files:
                wing_stl = cad_files.get("Wing Main STL")
                aileron_stl = cad_files.get("Wing Aileron STL")

            if not wing_stl and output_dir:
                candidate_w = os.path.join(output_dir, "wing_main.stl")
                if os.path.exists(candidate_w):
                    wing_stl = candidate_w
                candidate_a = os.path.join(output_dir, "wing_aileron.stl")
                if os.path.exists(candidate_a):
                    aileron_stl = candidate_a

            wing_3d_png = os.path.join(report_dir, "wing_render_3d.png")
            if wing_stl and os.path.exists(wing_stl):
                if render_wing_cad(wing_stl, aileron_stl, wing_3d_png):
                    images["wing_3d"] = "wing_render_3d.png"

            # Render Airfoil profile
            airfoil_name = sizing_results.get("airfoil_designation", "NACA 4412")
            airfoil_dat = os.path.join(self.cad_dir, "airfoils", f"{airfoil_name.replace(' ', '_')}.dat")
            airfoil_png = os.path.join(report_dir, "airfoil_profile.png")
            if os.path.exists(airfoil_dat):
                if render_airfoil_plot(airfoil_dat, airfoil_png, airfoil_name):
                    images["airfoil"] = "airfoil_profile.png"

            # 2. Copy CFD Cross-Section Images from cad/output into report/
            cad_out_dir = os.path.join(self.cad_dir, "output")
            cfd_p_src = os.path.join(cad_out_dir, "cfd_midspan_pressure.png")
            cfd_u_src = os.path.join(cad_out_dir, "cfd_midspan_velocity.png")

            cfd_p_dst = os.path.join(report_dir, "cfd_midspan_pressure.png")
            cfd_u_dst = os.path.join(report_dir, "cfd_midspan_velocity.png")

            if os.path.exists(cfd_p_src):
                shutil.copy2(cfd_p_src, cfd_p_dst)
                images["cfd_pressure"] = "cfd_midspan_pressure.png"

            if os.path.exists(cfd_u_src):
                shutil.copy2(cfd_u_src, cfd_u_dst)
                images["cfd_velocity"] = "cfd_midspan_velocity.png"

        report = {
            "title": "Daedalus Thread: Mission Requirements Verification Report",
            "overall_status": verification["overall_status"],
            "summary": verification["summary"],
            "mission_requirements": mission_reqs,
            "sizing_results": sizing_results,
            "checks": verification["checks"],
            "metrics": verification["metrics"],
            "images": images,
            "cad_artifacts": cad_files or {},
        }

        # Generate human-readable Markdown report
        status_badge = "[SUCCESS: ALL REQUIREMENTS MET]" if verification["overall_status"] == "SUCCESS" else "[DEFICIENT: REQUIREMENTS VIOLATED]"

        md_lines = [
            f"# Daedalus Thread: Mission Requirements Verification Report",
            f"",
            f"**Overall Verdict**: **{status_badge}**",
            f"",
            f"---",
            f"",
            f"## 1. Mission Input Parameters",
            f"",
            f"The mission requirements define the operational flight envelope and constraints driving the MBSE sizing and CAD generation:",
            f"",
            f"| Parameter | Input Value | Target Constraint | Description |",
            f"| :--- | :--- | :--- | :--- |",
            f"| **Cruise Airspeed Target** | `{mission_reqs.get('cruise_speed', 18.0):.1f} m/s` | Nominal operational cruise | Target flight airspeed for mapping/reconnaissance (~{mission_reqs.get('cruise_speed', 18.0)*1.94384:.1f} knots) |",
            f"| **Stall Speed Limit** | `<= {mission_reqs.get('stall_speed_max', 11.0):.1f} m/s` | Maximum allowable gross stall | Must not exceed limit to ensure low-speed safety (~{mission_reqs.get('stall_speed_max', 11.0)*1.94384:.1f} knots) |",
            f"| **Payload Mass** | `{mission_reqs.get('payload_mass', 1.2):.2f} kg` | Minimum payload capacity | Useful mission payload (sensor gimbal, camera, avionics) |",
            f"| **Wingspan Upper Bound** | `<= {mission_reqs.get('max_span_mm', 1800.0):.1f} mm` | Maximum wingspan limit | Transport, storage, and manufacturing envelope upper bound |",
            f"| **Target Flight Duration** | `{mission_reqs.get('flight_duration_min', 45.0):.1f} min` | Minimum operational endurance | Required on-station mission duration under cruise power |",
            f"",
            f"---",
            f"",
            f"## 2. Success Margins & Compliance Matrix",
            f"",
            f"| Requirement Parameter | Target Limit | Achieved Value | Margin | Status | Engineering Notes |",
            f"| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for c in verification["checks"]:
            md_lines.append(f"| **{c['parameter']}** | {c['target_value']} | {c['achieved_value']} | {c['margin']} | **{c['status']}** | {c['notes']} |")

        md_lines.extend([
            f"",
            f"---",
            f"",
            f"## 3. Designed Wing Specifications & Flight Performance",
            f"",
            f"### 3.1 Aerodynamic Geometry",
            f"- **Airfoil Profile**: `{sizing_results.get('airfoil_designation')}`",
            f"- **Wingspan**: `{sizing_results.get('span_mm', 0.0):.1f} mm` ({sizing_results.get('span_mm', 0.0)/1000.0:.2f} m)",
            f"- **Root Chord / Tip Chord**: `{sizing_results.get('root_chord_mm', 0.0):.1f} mm` / `{sizing_results.get('tip_chord_mm', 0.0):.1f} mm`",
            f"- **Wing Surface Area (S)**: `{sizing_results.get('wing_area_m2', 0.0):.4f} m^2` ({sizing_results.get('wing_area_m2', 0.0)*1e4:.1f} cm^2)",
            f"- **Aspect Ratio (AR)**: `{sizing_results.get('aspect_ratio', 0.0):.2f}`",
            f"- **Taper Ratio**: `0.65`",
            f"- **Leading Edge Sweep**: `{sizing_results.get('sweep_angle_deg', 0.0):.1f} deg`",
            f"- **Dihedral Angle**: `{sizing_results.get('dihedral_angle_deg', 0.0):.1f} deg`",
            f"- **Incidence Pitch Trim Angle**: `{sizing_results.get('pitch_angle_deg', 0.0):.1f} deg` (optimizes level fuselage attitude at cruise)",
            f"",
            f"### 3.2 Mass & Energy Budget",
            f"- **Total Gross Aircraft Mass**: `{sizing_results.get('total_mass_kg', 0.0):.2f} kg` (Weight = {sizing_results.get('total_mass_kg', 0.0)*9.80665:.2f} N)",
            f"- **Mission Payload Mass**: `{sizing_results.get('payload_mass_kg', 0.0):.2f} kg`",
            f"- **Structural Airframe Mass**: `{sizing_results.get('airframe_mass_kg', 0.0):.2f} kg`",
            f"- **Battery Pack Mass**: `{sizing_results.get('battery_mass_kg', 0.0):.2f} kg`",
            f"- **Usable Battery Energy**: `{sizing_results.get('battery_energy_wh', 0.0):.1f} Wh`",
            f"- **Cruise Electrical Power**: `{verification['metrics'].get('cruise_power_elec_watts', 0.0):.1f} W`",
            f"- **Calculated Endurance**: `{verification['metrics'].get('endurance_min', 0.0):.1f} min`",
            f"",
            f"### 3.3 Aerodynamic State at Cruise",
            f"- **Cruise Dynamic Pressure**: `{0.5 * 1.225 * (mission_reqs.get('cruise_speed', 18.0)**2):.1f} Pa`",
            f"- **Required Lift Coefficient ($C_L$)**: `{sizing_results.get('cruise_cl', 0.0):.3f}`",
            f"- **Lift-to-Drag Ratio ($L/D$)**: `{aero_results.get('flight_performance', {}).get('cruise_condition', {}).get('lift_to_drag', 0.0):.1f}`",
            f"- **Motor Thrust Power Required**: `{aero_results.get('flight_performance', {}).get('cruise_condition', {}).get('power_watts', 0.0):.1f} W`",
            f"",
            f"---",
            f"",
            f"## 4. Generated Wing & Control Surface Visuals",
            f"",
        ])

        if "wing_3d" in images:
            md_lines.extend([
                f"### 4.1 3D CAD Wing Assembly",
                f"Isometric perspective render of the parametric wing solid (blue) with integrated aileron control surface (orange), hinge tabs, and servo pocket:",
                f"",
                f"![3D CAD Wing Assembly]({images['wing_3d']})",
                f"",
            ])

        if "airfoil" in images:
            md_lines.extend([
                f"### 4.2 Airfoil Cross-Section Geometry",
                f"Normalized Selig coordinate profile for `{sizing_results.get('airfoil_designation')}`:",
                f"",
                f"![Airfoil Profile]({images['airfoil']})",
                f"",
            ])

        md_lines.extend([
            f"---",
            f"",
            f"## 5. CFD Aerodynamic Simulation Cross-Sections",
            f"",
            f"High-resolution mid-span fluid domain cross-sections from CfdOF / OpenFOAM simpleFoam simulation at nominal cruise velocity:",
            f"",
        ])

        if "cfd_pressure" in images:
            md_lines.extend([
                f"### 5.1 Air Pressure Field ($p$)",
                f"Static pressure contours across the mid-span airfoil profile showing suction peak on upper leading edge:",
                f"",
                f"![CFD Mid-Span Air Pressure Contours]({images['cfd_pressure']})",
                f"",
            ])

        if "cfd_velocity" in images:
            md_lines.extend([
                f"### 5.2 Velocity Magnitude Field ($|U|$)",
                f"Flow velocity magnitude contours showing upper surface acceleration and clean boundary layer attachment:",
                f"",
                f"![CFD Mid-Span Velocity Magnitude Contours]({images['cfd_velocity']})",
                f"",
            ])

        if cad_files:
            md_lines.extend([
                f"---",
                f"",
                f"## 6. Digital Thread Artifacts & Traceability",
                f"",
            ])
            for k, v in cad_files.items():
                md_lines.append(f"- **{k}**: `{v}`")
            md_lines.append("")

        md_content = "\n".join(md_lines)
        report["markdown_content"] = md_content

        if report_dir:
            json_file = os.path.join(report_dir, "mission_success_report.json")
            md_file = os.path.join(report_dir, "mission_success_report.md")
            alias_md = os.path.join(report_dir, "report.md")
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(md_content)
            with open(alias_md, "w", encoding="utf-8") as f:
                f.write(md_content)

            # Also maintain backward-compatible root files in output_dir
            with open(os.path.join(output_dir, "verification_report.json"), "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            with open(os.path.join(output_dir, "verification_report.md"), "w", encoding="utf-8") as f:
                f.write(md_content)

            report["json_file"] = json_file
            report["markdown_file"] = md_file
            report["report_dir"] = report_dir

        return report

