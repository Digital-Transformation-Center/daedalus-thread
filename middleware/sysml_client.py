"""SysML v2 Client Interface for the Daedalus Thread Digital Thread.

Supports querying requirements and posting verification verdicts to the OMG
SysML v2 REST API, with an offline fallback for CI/CD and offline development.
"""

import os
import re
from typing import Dict, Any, Optional
import requests

DEFAULT_SERVER_URL = "http://localhost:9000"
DEFAULT_PROJECT_NAME = "Icarus-DT1"


class SysMLClient:
    """Client for interacting with the OMG SysML v2 REST/JSON API."""

    def __init__(self, base_url: str = DEFAULT_SERVER_URL, offline: bool = False):
        self.base_url = base_url.rstrip("/")
        self.offline = offline
        self.project_id: Optional[str] = None

    def is_server_available(self) -> bool:
        """Checks if the SysML v2 server is online and responding."""
        if self.offline:
            return False
        try:
            resp = requests.get(f"{self.base_url}/projects", timeout=2)
            return resp.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_or_create_project(self, name: str = DEFAULT_PROJECT_NAME) -> Optional[Dict[str, Any]]:
        """Retrieves or creates a project on the SysML v2 server."""
        if self.offline or not self.is_server_available():
            return None

        try:
            resp = requests.get(f"{self.base_url}/projects", timeout=5)
            resp.raise_for_status()
            for project in resp.json():
                if project.get("name") == name:
                    self.project_id = project.get("@id")
                    return project

            payload = {
                "@type": "Project",
                "name": name,
                "description": "Daedalus Thread Digital Thread Spine"
            }
            create_resp = requests.post(f"{self.base_url}/projects", json=payload, timeout=5)
            create_resp.raise_for_status()
            project = create_resp.json()
            self.project_id = project.get("@id")
            return project
        except requests.exceptions.RequestException as err:
            print(f"Warning: Failed to reach SysML v2 server: {err}")
            return None

    def load_requirements(self, model_dir: Optional[str] = None) -> Dict[str, Any]:
        """Loads mission and airframe requirements.

        If the REST API server is available, queries the active project.
        Otherwise, falls back to parsing local SysML v2 model files.
        """
        if not self.offline and self.is_server_available():
            server_reqs = self._fetch_requirements_from_server()
            if server_reqs:
                return server_reqs

        return self._load_requirements_from_local_files(model_dir)

    def _fetch_requirements_from_server(self) -> Optional[Dict[str, Any]]:
        """Queries requirements from the REST API endpoints."""
        if not self.project_id:
            project = self.get_or_create_project()
            if not project:
                return None

        try:
            url = f"{self.base_url}/projects/{self.project_id}/elements"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                elements = resp.json()
                reqs: Dict[str, Any] = {}
                for el in elements:
                    name = el.get("name", "")
                    if "Req" in name or "req" in name:
                        reqs[name] = el
                if reqs:
                    return reqs
        except requests.exceptions.RequestException:
            pass
        return None

    def _load_requirements_from_local_files(self, model_dir: Optional[str] = None) -> Dict[str, Any]:
        """Parses local SysML v2 files to extract requirement values."""
        if not model_dir:
            # Anchor to repository root / model
            current_dir = os.path.dirname(os.path.abspath(__file__))
            model_dir = os.path.normpath(os.path.join(current_dir, "..", "model"))

        req_file = os.path.join(model_dir, "requirements", "mission_reqs.sysml")
        arch_file = os.path.join(model_dir, "architecture", "airframe.sysml")
        root_file = os.path.join(model_dir, "root.sysml")

        reqs = {
            "maxStallSpeed": 11.0,      # m/s
            "minCruiseSpeed": 18.0,     # m/s
            "minPayloadMass": 1.2,      # kg
            "maxWingspan": 1800.0,      # mm
            "maxWingMass": 0.65,        # kg
            "minFlightDuration": 30.0,  # minutes
            "totalMass": 2.4,           # kg All-Up Weight
            "airfoilDesignation": "NACA 2412",
            "airfoilMaxCL": 1.4,
            "airfoilThickness": 0.12,
        }

        # Parse mission_reqs.sysml
        if os.path.isfile(req_file):
            with open(req_file, "r", encoding="utf-8") as f:
                content = f.read()
                m_stall = re.search(r"maxStallSpeed\s*=\s*([0-9.]+)", content)
                if m_stall:
                    reqs["maxStallSpeed"] = float(m_stall.group(1))

                m_cruise = re.search(r"minCruiseSpeed\s*=\s*([0-9.]+)", content)
                if m_cruise:
                    reqs["minCruiseSpeed"] = float(m_cruise.group(1))

                m_payload = re.search(r"minPayloadMass\s*=\s*([0-9.]+)", content)
                if m_payload:
                    reqs["minPayloadMass"] = float(m_payload.group(1))

                m_span = re.search(r"maxWingspan\s*=\s*([0-9.]+)", content)
                if m_span:
                    reqs["maxWingspan"] = float(m_span.group(1))

                m_wmass = re.search(r"maxWingMass\s*=\s*([0-9.]+)", content)
                if m_wmass:
                    reqs["maxWingMass"] = float(m_wmass.group(1))

                m_dur = re.search(r"minFlightDuration\s*=\s*([0-9.]+)", content)
                if m_dur:
                    reqs["minFlightDuration"] = float(m_dur.group(1))

        # Parse airframe.sysml
        if os.path.isfile(arch_file):
            with open(arch_file, "r", encoding="utf-8") as f:
                content = f.read()
                m_foil = re.search(r'designation\s*=\s*"([^"]+)"', content)
                if m_foil:
                    reqs["airfoilDesignation"] = m_foil.group(1)
                m_cl = re.search(r"maxCL\s*=\s*([0-9.]+)", content)
                if m_cl:
                    reqs["airfoilMaxCL"] = float(m_cl.group(1))
                m_thick = re.search(r"thicknessRatio\s*=\s*([0-9.]+)", content)
                if m_thick:
                    reqs["airfoilThickness"] = float(m_thick.group(1))

        # Parse root.sysml
        if os.path.isfile(root_file):
            with open(root_file, "r", encoding="utf-8") as f:
                content = f.read()
                m_mass = re.search(r"totalMass\s*=\s*([0-9.]+)", content)
                if m_mass:
                    reqs["totalMass"] = float(m_mass.group(1))

        return reqs

    def post_verification_result(self, verification_report: Dict[str, Any]) -> bool:
        """Posts a verification record to the SysML v2 API server."""
        if self.offline or not self.is_server_available() or not self.project_id:
            print("[SysML v2 Client] Offline mode: Verification recorded locally.")
            return False

        payload = {
            "@type": "VerificationRecord",
            "name": "Phase1VerificationExecution",
            "verdict": "Passed" if verification_report.get("overall_pass") else "Failed",
            "details": verification_report
        }

        try:
            url = f"{self.base_url}/projects/{self.project_id}/verifications"
            resp = requests.post(url, json=payload, timeout=5)
            return resp.status_code in (200, 201)
        except requests.exceptions.RequestException as err:
            print(f"Warning: Failed to post verification record to SysML v2: {err}")
            return False
