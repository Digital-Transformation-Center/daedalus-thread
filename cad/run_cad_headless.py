"""
Headless FreeCAD execution wrapper.
Locates FreeCAD executable and invokes build_wing.py to render CAD models and export STL/STEP files.
"""
import os
import sys
import subprocess
import json
import shutil
from typing import Dict, Any


def find_freecad_executable() -> str:
    """Finds freecadcmd or freecad executable on Windows or system PATH."""
    cmd = shutil.which("freecadcmd") or shutil.which("freecad")
    if cmd:
        return cmd

    candidate_paths = [
        r"C:\Users\kuederrj\AppData\Local\Programs\FreeCAD 1.1\bin\freecadcmd.exe",
        r"C:\Users\kuederrj\AppData\Local\Programs\FreeCAD 1.1\bin\freecad.exe",
        r"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe",
        r"C:\Program Files\FreeCAD 0.21\bin\freecadcmd.exe",
        r"C:\Program Files\FreeCAD 0.20\bin\freecadcmd.exe",
    ]

    for path in candidate_paths:
        if os.path.exists(path):
            return path

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        programs_dir = os.path.join(local_app_data, "Programs")
        if os.path.exists(programs_dir):
            for item in os.listdir(programs_dir):
                if "FreeCAD" in item:
                    exe = os.path.join(programs_dir, item, "bin", "freecadcmd.exe")
                    if os.path.exists(exe):
                        return exe
                    exe = os.path.join(programs_dir, item, "bin", "freecad.exe")
                    if os.path.exists(exe):
                        return exe

    raise FileNotFoundError("Could not locate FreeCAD executable. Please ensure FreeCAD is installed.")


def run_cad_generation(cad_payload: Dict[str, Any], output_dir: str) -> bool:
    """
    Executes FreeCAD in headless mode to generate wing and export output STL/STEP files.
    """
    freecad_exe = find_freecad_executable()
    cad_dir = os.path.dirname(os.path.abspath(__file__))
    build_script = os.path.join(cad_dir, "build_wing.py")

    os.makedirs(output_dir, exist_ok=True)
    temp_config = os.path.join(output_dir, "temp_cad_params.json")

    payload_with_output = dict(cad_payload)
    payload_with_output["output_dir"] = output_dir

    with open(temp_config, "w", encoding="utf-8") as f:
        json.dump(payload_with_output, f, indent=2)

    # Construct Python execution snippet for freecadcmd -c
    py_code = (
        f"import sys, os; "
        f"script_path = r'{build_script}'; "
        f"sys.argv = [script_path, r'{temp_config}', r'{output_dir}']; "
        f"exec(open(script_path, encoding='utf-8').read(), {{'__file__': script_path, '__name__': '__main__'}})"
    )

    cmd = [freecad_exe, "-c", py_code]
    print(f"Launching FreeCAD headless generator...")

    result = subprocess.run(cmd, capture_output=True, text=True)

    print("--- FreeCAD Output ---")
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if os.path.exists(temp_config):
        try:
            os.remove(temp_config)
        except OSError:
            pass

    expected_stl = os.path.join(output_dir, "wing_main.stl")
    return os.path.exists(expected_stl)
