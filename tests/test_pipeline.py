"""
Unit tests for MBSE-to-CAD pipeline modules.
"""
import os
import unittest
import tempfile
import shutil
from generators.airfoil_generator import parse_naca_code, generate_naca4_coords, generate_naca4_dat
from middleware.wing_sizer import WingSizer
from middleware.sysml_adapter import SysMLAdapter


class TestAirfoilGenerator(unittest.TestCase):
    def test_parse_naca_code(self):
        code, m, p, t = parse_naca_code("NACA 2412")
        self.assertEqual(code, "2412")
        self.assertAlmostEqual(m, 0.02)
        self.assertAlmostEqual(p, 0.4)
        self.assertAlmostEqual(t, 0.12)

    def test_generate_naca4_dat(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = os.path.join(temp_dir, "NACA_4412.dat")
            generate_naca4_dat("4412", out_path, num_points=50)
            self.assertTrue(os.path.exists(out_path))
            with open(out_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            self.assertIn("NACA 4412", lines[0])
            self.assertGreater(len(lines), 50)


class TestWingSizer(unittest.TestCase):
    def setUp(self):
        self.sizer = WingSizer()

    def test_calculate_sizing(self):
        mission_reqs = {
            "cruise_speed": 18.0,
            "stall_speed_max": 11.0,
            "payload_mass": 1.2,
            "max_span_mm": 2000.0,
            "flight_duration_min": 30.0
        }
        res = self.sizer.calculate_sizing(mission_reqs)
        self.assertGreater(res["span_mm"], 1000.0)
        self.assertLessEqual(res["span_mm"], 2000.0)
        self.assertGreater(res["root_chord_mm"], res["tip_chord_mm"])
        self.assertEqual(res["airfoil_designation"], "NACA 4412")


class TestSysMLAdapter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.adapter = SysMLAdapter(cad_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_process_mission(self):
        mission_reqs = {
            "cruise_speed": 20.0,
            "stall_speed_max": 12.0,
            "payload_mass": 1.0,
            "max_span_mm": 1800.0,
            "flight_duration_min": 45.0,
        }
        result = self.adapter.process_mission(mission_reqs)
        self.assertIn("sizing_results", result)
        self.assertIn("cad_parameters", result)
        self.assertIn("PitchAngle", result["cad_parameters"])
        self.assertTrue(os.path.exists(result["airfoil_file_path"]))

    def test_parse_sysml_five_requirements(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        reqs_file = os.path.join(root_dir, "model", "requirements", "mission_reqs.sysml")
        parsed = self.adapter.parse_sysml_requirements(reqs_file)
        self.assertIn("cruise_speed", parsed)
        self.assertIn("stall_speed_max", parsed)
        self.assertIn("payload_mass", parsed)
        self.assertIn("max_span_mm", parsed)
        self.assertIn("flight_duration_min", parsed)
        self.assertEqual(parsed["cruise_speed"], 18.0)
        self.assertEqual(parsed["stall_speed_max"], 11.0)
        self.assertEqual(parsed["payload_mass"], 1.2)
        self.assertEqual(parsed["max_span_mm"], 1800.0)
        self.assertEqual(parsed["flight_duration_min"], 45.0)

    def test_sync_to_sysml(self):
        sizing_results = {
            "span_mm": 1750.0,
            "root_chord_mm": 230.0,
            "tip_chord_mm": 150.0,
            "sweep_angle_deg": 3.5,
            "dihedral_angle_deg": 2.0,
            "pitch_angle_deg": 2.5,
            "wing_area_m2": 0.33,
            "aspect_ratio": 7.5,
            "cruise_cl": 0.42,
            "total_mass_kg": 3.1,
            "payload_mass_kg": 1.2,
            "battery_mass_kg": 0.7,
            "flight_duration_min": 45.0,
            "airfoil_designation": "NACA 4412",
            "airfoil_max_camber_percent": 4.0,
            "airfoil_max_thickness_percent": 12.0,
        }
        out_sysml = os.path.join(self.temp_dir, "test_airframe.sysml")
        written_path = self.adapter.sync_to_sysml(sizing_results, out_sysml)
        self.assertTrue(os.path.exists(written_path))
        with open(written_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("part generatedUavWing : WingAssembly", content)
        self.assertIn("span = 1750.0", content)
        self.assertIn("flightDurationMin = 45.0", content)

    def test_verification_report(self):
        mission_reqs = {
            "cruise_speed": 18.0,
            "stall_speed_max": 11.0,
            "payload_mass": 1.2,
            "max_span_mm": 1800.0,
            "flight_duration_min": 45.0,
        }
        sizing = self.adapter.sizer.calculate_sizing(mission_reqs)
        aero = {
            "flight_performance": {
                "stall_speed_gross_mps": 10.5,
                "stall_speed_gross_mph": 23.5,
                "payload_capacity": {
                    "payload_safe_max_kg": 1.35,
                    "payload_absolute_max_kg": 1.80,
                },
                "cruise_condition": {
                    "speed_mps": 18.0,
                    "power_watts": 28.0,
                    "lift_to_drag": 13.0,
                    "cl_required": 0.45,
                    "is_stalled": False,
                }
            }
        }
        report = self.adapter.generate_verification_report(
            mission_reqs=mission_reqs,
            sizing_results=sizing,
            aero_results=aero,
            output_dir=self.temp_dir,
        )
        self.assertEqual(report["overall_status"], "SUCCESS")
        self.assertEqual(len(report["checks"]), 5)
        for check in report["checks"]:
            self.assertEqual(check["status"], "PASS")
        self.assertTrue(os.path.exists(report["json_file"]))
        self.assertTrue(os.path.exists(report["markdown_file"]))


class TestWingAeroSimulator(unittest.TestCase):
    def setUp(self):
        from cad.simulate_aerodynamics import WingAeroSimulator
        self.sim = WingAeroSimulator(
            span_mm=700.0,
            root_chord_mm=200.0,
            tip_chord_mm=90.0,
            pitch_deg=4.0,
        )

    def test_stall_speed(self):
        v_stall = self.sim.compute_stall_speed(1.0)
        self.assertGreater(v_stall, 20.0)
        self.assertLess(v_stall, 30.0)

    def test_max_payload(self):
        payload = self.sim.compute_max_payload(cruise_speed_mph=30.0, empty_mass_kg=0.5)
        self.assertGreater(payload["gross_safe_max_kg"], 0.5)
        self.assertGreater(payload["payload_safe_max_kg"], 0.0)
        self.assertGreater(payload["gross_absolute_max_kg"], payload["gross_safe_max_kg"])

    def test_pitch_trim_state(self):
        trim = self.sim.compute_pitch_trim_state(speed_mph=30.0, aircraft_mass_kg=1.0)
        self.assertEqual(trim["pitch_deg"], 4.0)
        self.assertGreater(trim["cl_at_level_fuselage"], 0.0)
        self.assertIn("fuselage_trim_angle_deg", trim)


if __name__ == "__main__":
    unittest.main()

