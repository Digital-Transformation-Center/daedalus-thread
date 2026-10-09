"""Initialization script for local SysML v2 REST API repository.

Connects to the SysML v2 REST API server, checks health, and ensures the
Icarus-DT1 project exists with an initial commit.
"""

import sys
import time
import requests

DEFAULT_SERVER_URL = "http://localhost:9000"
PROJECT_NAME = "Icarus-DT1"
PROJECT_DESC = "Daedalus Thread Phase 1 - Aerodynamic Digital Thread Spine"


def wait_for_server(base_url=DEFAULT_SERVER_URL, max_attempts=15, delay=2):
    """Waits for the SysML v2 API server to become ready."""
    print(f"Checking SysML v2 server health at: {base_url}")
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.get(f"{base_url}/projects", timeout=5)
            if resp.status_code == 200:
                print("SysML v2 server is online and responding.")
                return True
        except requests.exceptions.RequestException:
            pass
        print(f"Waiting for server... (attempt {attempt}/{max_attempts})")
        time.sleep(delay)
    return False


def get_or_create_project(base_url=DEFAULT_SERVER_URL, name=PROJECT_NAME, desc=PROJECT_DESC):
    """Retrieves an existing project by name or creates a new one."""
    projects_url = f"{base_url}/projects"
    resp = requests.get(projects_url, timeout=10)
    resp.raise_for_status()

    projects = resp.json()
    for proj in projects:
        if proj.get("name") == name:
            print(f"Project '{name}' already exists with ID: {proj.get('@id')}")
            return proj

    # Create new project
    payload = {
        "@type": "Project",
        "name": name,
        "description": desc
    }
    create_resp = requests.post(projects_url, json=payload, timeout=10)
    create_resp.raise_for_status()
    created = create_resp.json()
    print(f"Successfully created project '{name}' with ID: {created.get('@id')}")
    return created


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERVER_URL
    if not wait_for_server(base_url):
        print(f"Error: Could not reach SysML v2 server at {base_url}", file=sys.stderr)
        sys.exit(1)

    project = get_or_create_project(base_url)
    print(f"Initialization complete for project {project.get('name')}.")


if __name__ == "__main__":
    main()
