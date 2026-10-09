"""Verification evaluation module closing the MBSE digital thread loop.

Compares analytical aero performance, powertrain metrics, and generated CAD
physical properties against SysML v2 requirements and records formal verdicts.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List


class VerificationEngine:
    """Evaluates system compliance against SysML requirements."""

    def __init__(self, requirements: Dict[str, Any]):
        self.requirements = requirements

    def evaluate(self, aero_results: Dict[str, Any], cad_results: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates verification cases and generates a compliance report."""
        checks: List[Dict[str, Any]] = []

        # 1. Stall Speed Verification Case
        if "maxStallSpeed" in self.requirements:
            max_stall = float(self.requirements["maxStallSpeed"])
            calc_stall = float(aero_results.get("calculated_stall_speed_mps", 0.0))
            stall_pass = calc_stall <= max_stall
            checks.append({
                "case_id": "verifyIcarusStall",
                "requirement_id": "icarusStallReq",
                "metric": "Stall Speed (m/s)",
                "required_limit": f"<= {max_stall:.2f}",
                "actual_value": calc_stall,
                "margin": round(max_stall - calc_stall, 2),
                "verdict": "PASS" if stall_pass else "FAIL"
            })

        # 2. Wingspan Limit Verification Case
        if "maxWingspan" in self.requirements:
            max_span = float(self.requirements["maxWingspan"])
            cad_span = float(cad_results.get("span_mm", 0.0))
            span_pass = cad_span <= max_span
            checks.append({
                "case_id": "verifyIcarusSpan",
                "requirement_id": "icarusSpanReq",
                "metric": "Wingspan (mm)",
                "required_limit": f"<= {max_span:.1f}",
                "actual_value": cad_span,
                "margin": round(max_span - cad_span, 1),
                "verdict": "PASS" if span_pass else "FAIL"
            })

        # 3. Wing Structural Mass Budget Verification Case
        if "maxWingMass" in self.requirements:
            max_mass = float(self.requirements["maxWingMass"])
            cad_mass = float(cad_results.get("total_wing_mass_kg", 0.0))
            mass_pass = cad_mass <= max_mass
            checks.append({
                "case_id": "verifyIcarusMass",
                "requirement_id": "icarusWingMassReq",
                "metric": "Wing Mass (kg)",
                "required_limit": f"<= {max_mass:.3f}",
                "actual_value": cad_mass,
                "margin": round(max_mass - cad_mass, 3),
                "verdict": "PASS" if mass_pass else "FAIL"
            })

        # 4. Flight Duration Verification Case
        if "minFlightDuration" in self.requirements:
            min_duration = float(self.requirements["minFlightDuration"])
            actual_duration = float(
                aero_results.get("achievable_duration_min", aero_results.get("flight_duration_target_min", 0.0))
            )
            duration_pass = actual_duration >= min_duration
            checks.append({
                "case_id": "verifyIcarusDuration",
                "requirement_id": "icarusDurationReq",
                "metric": "Flight Duration (min)",
                "required_limit": f">= {min_duration:.1f}",
                "actual_value": actual_duration,
                "margin": round(actual_duration - min_duration, 1),
                "verdict": "PASS" if duration_pass else "FAIL"
            })

        # 5. Payload Capacity Verification Case
        if "minPayloadMass" in self.requirements:
            min_payload = float(self.requirements["minPayloadMass"])
            actual_payload = float(aero_results.get("payload_mass_kg", 0.0))
            payload_pass = actual_payload >= min_payload
            checks.append({
                "case_id": "verifyIcarusPayload",
                "requirement_id": "icarusPayloadReq",
                "metric": "Payload Mass (kg)",
                "required_limit": f">= {min_payload:.2f}",
                "actual_value": actual_payload,
                "margin": round(actual_payload - min_payload, 2),
                "verdict": "PASS" if payload_pass else "FAIL"
            })

        overall_pass = all(c["verdict"] == "PASS" for c in checks) if checks else False

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_pass": overall_pass,
            "total_checks": len(checks),
            "passed_checks": sum(1 for c in checks if c["verdict"] == "PASS"),
            "checks": checks,
            "cad_summary": {
                "span_mm": cad_results.get("span_mm"),
                "root_chord_mm": cad_results.get("root_chord_mm"),
                "tip_chord_mm": cad_results.get("tip_chord_mm"),
                "total_wing_mass_kg": cad_results.get("total_wing_mass_kg"),
                "center_of_gravity": cad_results.get("center_of_gravity")
            },
            "aero_summary": {
                "wing_area_m2": aero_results.get("wing_area_m2"),
                "aspect_ratio": aero_results.get("aspect_ratio"),
                "design_cl_cruise": aero_results.get("design_cl_cruise"),
                "calculated_stall_speed_mps": aero_results.get("calculated_stall_speed_mps")
            },
            "mission_summary": {
                "total_mass_kg": aero_results.get("total_mass_kg"),
                "payload_mass_kg": aero_results.get("payload_mass_kg"),
                "battery_mass_kg": aero_results.get("battery_mass_kg"),
                "flight_duration_min": aero_results.get("achievable_duration_min"),
                "cruise_power_watts": aero_results.get("cruise_power_watts")
            }
        }

        return report

    @staticmethod
    def format_text_report(report: Dict[str, Any]) -> str:
        """Renders an ASCII verification summary table."""
        lines = [
            "=" * 78,
            "DAEDALUS THREAD - PHASE 1 DIGITAL THREAD VERIFICATION REPORT",
            "=" * 78,
            f"Timestamp: {report.get('timestamp')}",
            f"Overall Status: {'PASSED' if report.get('overall_pass') else 'FAILED'} "
            f"({report.get('passed_checks')}/{report.get('total_checks')} checks compliant)",
            "-" * 78,
            f"{'Case ID':<20} | {'Requirement':<18} | {'Limit':<10} | {'Actual':<8} | {'Verdict'}",
            "-" * 78,
        ]

        for c in report.get("checks", []):
            lines.append(
                f"{c['case_id']:<20} | {c['requirement_id']:<18} | {c['required_limit']:<10} | "
                f"{c['actual_value']:<8} | {c['verdict']}"
            )

        mission = report.get("mission_summary", {})
        cad = report.get("cad_summary", {})
        aero = report.get("aero_summary", {})

        lines.extend([
            "=" * 78,
            f"Total AUW: {mission.get('total_mass_kg')} kg | "
            f"Payload: {mission.get('payload_mass_kg')} kg | "
            f"Battery: {mission.get('battery_mass_kg')} kg",
            f"Duration: {mission.get('flight_duration_min')} min | "
            f"Cruise Power: {mission.get('cruise_power_watts')} W",
            f"CAD CG [X, Y, Z]: {cad.get('center_of_gravity')} mm | "
            f"Wing Mass: {cad.get('total_wing_mass_kg')} kg",
            f"Wing Area: {aero.get('wing_area_m2')} m^2 | "
            f"Cruise CL: {aero.get('design_cl_cruise')}",
            "=" * 78
        ])

        return "\n".join(lines)
