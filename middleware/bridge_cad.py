"""CAD Bridge module orchestrating headless FreeCAD geometry generation.

Invokes FreeCAD headlessly to loft parametric wing geometry, apply control
surface and servo pocket cutters, calculate solid mass properties, and export STEP/STL.
"""

import json
import os
import shutil
import subprocess
import sys
from typing import Dict, Any, Optional


def find_freecad_cmd() -> Optional[str]:
    """Locates the freecadcmd executable across standard installation paths."""
    # 1. Check system PATH
    found = shutil.which("freecadcmd") or shutil.which("freecadcmd.exe")
    if found:
        return found

    # 2. Check LocalAppData on Windows
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        candidate = os.path.join(local_app_data, "Programs", "FreeCAD 1.1", "bin", "freecadcmd.exe")
        if os.path.isfile(candidate):
            return candidate

        # Search for any FreeCAD installation in LocalAppData
        programs_dir = os.path.join(local_app_data, "Programs")
        if os.path.isdir(programs_dir):
            for entry in os.listdir(programs_dir):
                if "FreeCAD" in entry:
                    sub_cand = os.path.join(programs_dir, entry, "bin", "freecadcmd.exe")
                    if os.path.isfile(sub_cand):
                        return sub_cand

    # 3. Check Program Files
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    if os.path.isdir(program_files):
        for entry in os.listdir(program_files):
            if "FreeCAD" in entry:
                cand = os.path.join(program_files, entry, "bin", "freecadcmd.exe")
                if os.path.isfile(cand):
                    return cand

    return None


def run_headless_cad(
    params: Dict[str, Any],
    output_dir: Optional[str] = None,
    export_step: bool = False,
    export_stl: bool = False,
    mock: bool = False
) -> Dict[str, Any]:
    """Executes FreeCAD in headless mode to generate wing solids.

    Args:
        params: Geometric parameters dictionary from aerodynamic sizing.
        output_dir: Target directory for exported CAD solids.
        export_step: Whether to export a STEP solid.
        export_stl: Whether to export an STL surface mesh.
        mock: If True, bypasses FreeCAD and returns analytical approximations.

    Returns:
        dict: Mass properties and generation status.
    """
    freecad_path = find_freecad_cmd()

    if mock or not freecad_path:
        if not mock:
            print("Notice: freecadcmd executable not found. Utilizing analytical CAD mock.")
        return _mock_cad_properties(params, output_dir, export_step, export_stl)

    # Prepare command for freecadcmd
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    script_path = os.path.join(repo_root, "cad", "build_wing.py").replace("\\", "/")

    args_list = [script_path, "--json-params", json.dumps(params)]
    if output_dir:
        clean_out = os.path.abspath(output_dir).replace("\\", "/")
        args_list.extend(["--output-dir", clean_out])
    if export_step:
        args_list.append("--export-step")
    if export_stl:
        args_list.append("--export-stl")

    args_repr = repr(args_list)
    script_repr = repr(script_path)

    python_snippet = (
        f"import sys; "
        f"sys.argv = {args_repr}; "
        f"exec(open({script_repr}).read())"
    )

    cmd = [freecad_path, "-c", python_snippet]

    try:
        proc = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=120
        )
        stdout = proc.stdout

        # Extract JSON marker from FreeCAD stdout
        marker = "__CAD_RESULT_JSON__:"
        for line in stdout.splitlines():
            if marker in line:
                json_str = line.split(marker, 1)[1].strip()
                return json.loads(json_str)

        raise RuntimeError(f"Could not locate CAD result in FreeCAD stdout:\n{stdout}")

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as err:
        print(f"Error during headless FreeCAD execution: {err}", file=sys.stderr)
        if hasattr(err, "stderr") and err.stderr:
            print(f"FreeCAD Stderr:\n{err.stderr}", file=sys.stderr)
        raise


def _mock_cad_properties(
    params: Dict[str, Any],
    output_dir: Optional[str] = None,
    export_step: bool = False,
    export_stl: bool = False
) -> Dict[str, Any]:
    """Generates synthetic CAD mass properties when FreeCAD is unavailable."""
    span = float(params.get("span_mm", 1400.0))
    root_chord = float(params.get("root_chord_mm", 212.0))
    tip_chord = float(params.get("tip_chord_mm", 138.0))

    # Analytical approximation of half-wing volume with 12% NACA thickness
    mean_chord = (root_chord + tip_chord) / 2.0
    half_span = span / 2.0
    area_cross_section = 0.68 * mean_chord * (mean_chord * 0.12)
    half_volume_mm3 = round(area_cross_section * half_span, 1)

    both_volume = half_volume_mm3 * 2.0
    printed_mass_g = both_volume * 0.000085
    hardware_mass_g = 58.0
    total_wing_mass_kg = round((printed_mass_g + hardware_mass_g) / 1000.0, 3)

    exported_files = []
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        if export_step:
            step_file = os.path.join(output_dir, "wing_assembly.step")
            with open(step_file, "w", encoding="utf-8") as f:
                f.write("/* Mock STEP CAD Solid */\n")
            exported_files.append(step_file)
        if export_stl:
            main_stl = os.path.join(output_dir, "wing_main.stl")
            aileron_stl = os.path.join(output_dir, "wing_aileron.stl")
            assembly_stl = os.path.join(output_dir, "wing_assembly.stl")
            for p in (main_stl, aileron_stl, assembly_stl):
                with open(p, "w", encoding="utf-8") as f:
                    f.write("solid mock\nendsolid mock\n")
                exported_files.append(p)

    return {
        "status": "success",
        "mock": True,
        "span_mm": span,
        "root_chord_mm": root_chord,
        "tip_chord_mm": tip_chord,
        "half_volume_mm3": half_volume_mm3,
        "total_wing_mass_kg": total_wing_mass_kg,
        "center_of_gravity": [round(root_chord * 0.45, 2), round(half_span * 0.43, 2), 12.0],
        "build_envelope_mm": {
            "chord_x": root_chord,
            "span_y": half_span,
            "thickness_z": round(root_chord * 0.12, 1)
        },
        "exported_files": exported_files
    }
