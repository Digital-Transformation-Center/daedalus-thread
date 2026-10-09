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
    asm_stl = os.path.join(output_dir, "wing_assembly.stl")
    asm_step = os.path.join(output_dir, "wing_assembly.step")

    assert os.path.isfile(main_stl)
    assert os.path.isfile(aileron_stl)
    assert os.path.isfile(asm_stl)
    assert os.path.isfile(asm_step)
    assert os.path.getsize(main_stl) > 0
    assert os.path.getsize(aileron_stl) > 0
