"""End-to-end integration tests for the Daedalus Thread pipeline."""

import json
import os
from middleware.run_pipeline import run_pipeline


def test_end_to_end_pipeline(tmp_path):
    """Executes the complete Digital Thread flow from requirements to CAD and verification."""
    output_dir = str(tmp_path / "test_run")

    exit_code = run_pipeline(
        offline=True,
        mock_cad=False,
        export_step=False,
        export_stl=False,
        output_dir=output_dir
    )

    assert exit_code == 0
    report_file = os.path.join(output_dir, "verification_report.json")
    assert os.path.isfile(report_file)


def test_end_to_end_mission_parameters_stl_export(tmp_path):
    """Validates pipeline execution driven purely by the 5 mission parameters with STL output."""
    output_dir = str(tmp_path / "test_mission_run")

    exit_code = run_pipeline(
        offline=True,
        mock_cad=False,
        export_step=True,
        export_stl=True,
        output_dir=output_dir,
        cruise_speed=18.0,
        stall_speed=11.0,
        payload_mass=1.2,
        max_span=1800.0,
        duration=30.0
    )

    assert exit_code == 0

    # Verification report validation
    report_file = os.path.join(output_dir, "verification_report.json")
    assert os.path.isfile(report_file)

    with open(report_file, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert report["overall_pass"] is True
    assert report["total_checks"] == 5
    assert report["passed_checks"] == 5

    # Check 3D printable STL and STEP files
    main_stl = os.path.join(output_dir, "wing_main.stl")
    aileron_stl = os.path.join(output_dir, "wing_aileron.stl")
    motor_top_stl = os.path.join(output_dir, "motor_mount_top.stl")
    motor_bot_stl = os.path.join(output_dir, "motor_mount_bottom.stl")
    asm_stl = os.path.join(output_dir, "wing_assembly.stl")
    asm_step = os.path.join(output_dir, "wing_assembly.step")

    assert os.path.isfile(main_stl)
    assert os.path.isfile(aileron_stl)
    assert os.path.isfile(motor_top_stl)
    assert os.path.isfile(motor_bot_stl)
    assert os.path.isfile(asm_stl)
    assert os.path.isfile(asm_step)
    assert os.path.getsize(main_stl) > 0
    assert os.path.getsize(aileron_stl) > 0
    assert os.path.getsize(motor_top_stl) > 0
    assert os.path.getsize(motor_bot_stl) > 0


def test_motor_mount_esc_cavity_and_skin_conformance():
    """Validates clamshell bracket B-Rep validity, ESC cavity clearance, and flush wing skin."""
    import subprocess
    from middleware.bridge_cad import find_freecad_cmd

    freecad_cmd = find_freecad_cmd()
    if not freecad_cmd:
        return

    check_script = (
        "import sys; sys.path.insert(0, 'cad'); "
        "import FreeCAD as App, Part; "
        "from components.airfoil import load_airfoil_points; "
        "from components.wing_body import WingGeometry; "
        "from components.motor_mount import MotorMount; "
        "pts = load_airfoil_points('cad/airfoils/NACA_2412.dat'); "
        "wg = WingGeometry(1400.0, 212.0, 138.0, 3.5, 2.0, pts); "
        "raw = wg.build_solid(2); "
        "mm = MotorMount(); "
        "rec = raw.cut(mm.build_wing_saddle_cutter(wg)); "
        "top, bot, exit_xy, info = mm.build_clamshell_brackets(wg, raw, rec); "
        "xf, yc, zc, le = mm.get_mount_frame(wg); "
        "esc = Part.makeBox("
        "mm.esc_cavity_depth - mm.front_bulkhead_t, "
        "mm.esc_cavity_width, mm.esc_cavity_height, "
        "App.Vector(xf + mm.front_bulkhead_t, yc - mm.esc_cavity_width / 2.0, zc - mm.esc_cavity_height / 2.0)"
        "); "
        "aft = Part.makeBox(20.0, 40.0, 60.0, App.Vector(le.x + 36.0, yc - 20.0, zc - 30.0)); "
        "assert rec.isValid() and top.isValid() and bot.isValid(); "
        "assert rec.common(esc).Volume < 1e-3; "
        "assert top.common(esc).Volume < 1e-3; "
        "assert bot.common(esc).Volume < 1e-3; "
        "assert top.common(aft).cut(raw).Volume < 1e-2; "
        "assert bot.common(aft).cut(raw).Volume < 1e-2; "
        "assert abs(exit_xy[1] - (yc - mm.saddle_half_width)) < 1e-3; "
        "print('MOTOR_MOUNT_OK')"
    )
    proc = subprocess.run([freecad_cmd, "-c", check_script], capture_output=True, text=True, check=True)
    assert "MOTOR_MOUNT_OK" in proc.stdout
