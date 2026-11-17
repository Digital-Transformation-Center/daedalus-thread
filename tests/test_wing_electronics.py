"""Integration tests for Heewing T1S Ranger electronics CAD geometry."""
import os
import pytest

from middleware.bridge_cad import find_freecad_cmd, run_headless_cad


@pytest.mark.skipif(
    find_freecad_cmd() is None,
    reason="freecadcmd is required for real CAD solid verification",
)
def test_heewing_electronics_cad_generation(tmp_path):
    """Verifies motor nacelle, ESC bay, side servo pocket, and wire channels."""
    out_dir = str(tmp_path / "heewing_wing")
    res = run_headless_cad(
        params={},
        output_dir=out_dir,
        export_step=True,
        export_stl=True,
        mock=False,
    )

    assert res["status"] == "success"
    assert res["half_volume_mm3"] > 0

    elec = res["electronics"]
    assert 85.0 <= elec["motor"]["y_center_mm"] <= 90.0
    assert elec["motor"]["esc_cavity_depth_mm"] >= 42.0
    assert elec["motor"]["peg_x_mm"] > elec["motor"]["x_face_mm"]
    assert elec["wire_channels_mm"]["servo_channel_mm"] + 20.0 <= 200.0
    assert elec["wire_channels_mm"]["esc_power_channel_mm"] < 150.0
    assert elec["wire_channels_mm"]["esc_data_channel_mm"] < 150.0
    assert elec["root_wire_exit_x_mm"] == pytest.approx(83.6, abs=1.0)

    expected_files = (
        "wing_assembly.step",
        "wing_main.stl",
        "wing_aileron.stl",
        "motor_mount_top.stl",
        "motor_mount_bottom.stl",
        "wing_assembly.stl",
    )
    for fname in expected_files:
        fpath = os.path.join(out_dir, fname)
        assert os.path.isfile(fpath)
        assert os.path.getsize(fpath) > 0
