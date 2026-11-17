"""Unit and integration tests for Heewing T1S Ranger electronics CAD geometry."""
import math
import os
import pytest

from cad.components.wire_channels import WireChannelGenerator
from middleware.bridge_cad import find_freecad_cmd, run_headless_cad


def test_pcb_wire_routing_planner():
    """Verifies non-crossing PCB waypoints, 45-deg diagonals, and even root exits."""
    root_exit_x = 83.6
    spacing = 6.0
    esc_pwr_start = (49.85, 82.5)
    esc_dat_start = (49.85, 92.5)
    servo_start = (99.6, 149.5)

    pwr_wp = WireChannelGenerator._plan_pcb_waypoints_xy(
        esc_pwr_start, root_exit_x - spacing, lead_direction="+x"
    )
    dat_wp = WireChannelGenerator._plan_pcb_waypoints_xy(
        esc_dat_start, root_exit_x, lead_direction="+x"
    )
    srv_wp = WireChannelGenerator._plan_pcb_waypoints_xy(
        servo_start, root_exit_x + spacing, lead_direction="-y"
    )

    # ESC traces exit straight aft (+X) out of the rear motor mount slot
    for wp in (pwr_wp, dat_wp):
        assert wp[1][1] == pytest.approx(wp[0][1])
        assert wp[1][0] > wp[0][0]

    # Evenly spaced root exits ordered fore-to-aft
    assert pwr_wp[-1] == pytest.approx((root_exit_x - spacing, -3.0))
    assert dat_wp[-1] == pytest.approx((root_exit_x, -3.0))
    assert srv_wp[-1] == pytest.approx((root_exit_x + spacing, -3.0))

    # Final bus segments are parallel along -Y (constant X) for at least ~18 mm
    for wp in (pwr_wp, dat_wp, srv_wp):
        assert len(wp) == 4
        assert wp[-2][0] == pytest.approx(wp[-1][0])
        assert wp[-2][1] >= 18.0

    # Diagonal segment entering the parallel bus is 45 degrees (|dx| == |dy|)
    for wp in (pwr_wp, dat_wp, srv_wp):
        dx = abs(wp[-2][0] - wp[-3][0])
        dy = abs(wp[-2][1] - wp[-3][1])
        assert dx == pytest.approx(dy, abs=1e-6)

    # Filleted sampling produces unit tangents, >= 1.5 mm station spacing, and monotonic Y
    for wp in (pwr_wp, dat_wp, srv_wp):
        samples = WireChannelGenerator._sample_filleted_path(wp, fillet_radius=8.0)
        assert len(samples) >= 8
        for x, y, tx, ty in samples:
            assert math.hypot(tx, ty) == pytest.approx(1.0, abs=1e-6)
        dists = [
            math.hypot(samples[i + 1][0] - samples[i][0], samples[i + 1][1] - samples[i][1])
            for i in range(len(samples) - 1)
        ]
        assert all(d >= 1.5 - 1e-6 for d in dists)
        ys = [s[1] for s in samples]
        assert all(ys[i] >= ys[i + 1] - 1e-9 for i in range(len(ys) - 1))
        # Final tangent points straight along -Y
        assert samples[-1][2] == pytest.approx(0.0, abs=1e-6)
        assert samples[-1][3] == pytest.approx(-1.0, abs=1e-6)


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


@pytest.mark.skipif(
    find_freecad_cmd() is None,
    reason="freecadcmd is required for real CAD solid verification",
)
def test_wire_slots_cleanly_cut_from_wing():
    """Verifies all three wire slots are 100% cut out of the wing solid with zero residual."""
    import subprocess

    freecad_cmd = find_freecad_cmd()
    check_script = (
        "import sys; sys.path.insert(0, 'cad'); "
        "from components.airfoil import load_airfoil_points; "
        "from components.wing_body import WingGeometry; "
        "from components.aileron import AileronGenerator; "
        "from components.servo_pocket import ServoPocket; "
        "from components.motor_mount import MotorMount; "
        "from components.wire_channels import WireChannelGenerator; "
        "raw = load_airfoil_points('cad/airfoils/NACA_2412.dat'); "
        "wg = WingGeometry(1400.0, 212.0, 138.0, 3.5, 2.0, raw); "
        "raw_wing = wg.build_solid(2); "
        "wing, _ = AileronGenerator(wg, 0.20, 0.70, 0.25, 0.6, 35.0, 1.6, 3).build_aileron_and_cutters(raw_wing); "
        "mm = MotorMount(87.5, 12.0); "
        "wing = wing.cut(mm.build_wing_saddle_cutter(wg)); "
        "_, _, esc_xy, motor_info = mm.build_clamshell_brackets(wg, raw_wing, wing); "
        "sc, tabs, sxy, _ = ServoPocket('HeeWing_FX5G').create_geometry(107.3, 157.5, wg); "
        "wing = wing.cut(sc); "
        "wing = wing.fuse(tabs) if tabs is not None else wing; "
        "root_exit_x = wg.get_max_thickness_x(0.0) + 20.0; "
        "wc, _ = WireChannelGenerator().create_all_channels("
        "wg, sxy, esc_xy, root_exit_x, "
        "esc_taper_start_x=motor_info['esc_taper_start_x_mm'], "
        "esc_recess_depth=mm.recess_depth, "
        "esc_z_c=motor_info['z_center_mm']"
        "); "
        "wf = wing.cut(wc); "
        "assert wf.isValid(); "
        "assert len(wc.Solids) == 3; "
        "assert all(wf.common(s).Volume < 1e-3 for s in wc.Solids); "
        "print('SLOTS_CLEAN_OK')"
    )
    proc = subprocess.run([freecad_cmd, "-c", check_script], capture_output=True, text=True, check=True)
    assert "SLOTS_CLEAN_OK" in proc.stdout


@pytest.mark.skipif(
    find_freecad_cmd() is None,
    reason="freecadcmd is required for real CAD solid verification",
)
def test_servo_model_and_press_fit_cutout():
    """Verifies clean servo model validity and zero-undercut press-in wing cutout."""
    import subprocess

    freecad_cmd = find_freecad_cmd()
    check_script = (
        "import sys; sys.path.insert(0, 'cad'); "
        "import FreeCAD as App, Part; "
        "from components.airfoil import load_airfoil_points; "
        "from components.wing_body import WingGeometry; "
        "from components.servo_model import ServoModel; "
        "from components.servo_pocket import ServoPocket; "
        "raw = load_airfoil_points('cad/airfoils/NACA_2412.dat'); "
        "wg = WingGeometry(1400.0, 212.0, 138.0, 3.5, 2.0, raw); "
        "wing = wg.build_solid(2); "
        "sp = ServoPocket('HeeWing_FX5G', tolerance=0.12); "
        "sc, tabs, _, info = sp.create_geometry(107.3, 157.5, wg); "
        "assert tabs is None; "
        "assert info['tolerance_mm'] == 0.12; "
        "nominal = sp.build_nominal_servo(107.3, 157.5, wg); "
        "assert nominal.isValid() and nominal.Volume > 3000.0; "
        "wing_cut = wing.cut(sc); "
        "assert wing_cut.isValid(); "
        "assert wing_cut.common(nominal).Volume < 1e-3; "
        "sweep_0 = ServoModel('HeeWing_FX5G').build_press_cutter_solid("
        "107.3, 157.5, info['floor_z_mm'], nominal.BoundBox.ZMax + 20.0, tolerance=0.0"
        "); "
        "assert wing_cut.common(sweep_0).Volume < 1e-3; "
        "print('SERVO_PRESS_FIT_OK')"
    )
    proc = subprocess.run([freecad_cmd, "-c", check_script], capture_output=True, text=True, check=True)
    assert "SERVO_PRESS_FIT_OK" in proc.stdout
