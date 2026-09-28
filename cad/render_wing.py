"""
Wing rendering and visual asset generation module.
Produces 3D CAD renders using ParaView and aerodynamic profile plots using Matplotlib.
"""
import os
import sys
import subprocess
import shutil
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PARAVIEW_CANDIDATES = [
    r"C:\Users\kuederrj\AppData\Local\ParaView-6.2.0-RC2-Windows-Python3.12-msvc2017-AMD64\bin\pvpython.exe",
]


def find_pvpython() -> str:
    """Locates pvpython executable on Windows or system PATH."""
    cmd = shutil.which("pvpython")
    if cmd:
        return cmd
    for p in PARAVIEW_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def render_wing_cad(
    wing_stl_path: str,
    aileron_stl_path: str,
    output_png_path: str,
    image_width: int = 1600,
    image_height: int = 900
) -> bool:
    """
    Renders a 3D isometric view of the wing assembly STL models using ParaView headless.
    Returns True if rendering succeeded.
    """
    if not os.path.exists(wing_stl_path):
        print(f"Warning: Wing STL not found at {wing_stl_path}")
        return False

    pvpython_exe = find_pvpython()
    if not pvpython_exe:
        print("Note: ParaView pvpython not located. Skipping 3D CAD render.")
        return False

    os.makedirs(os.path.dirname(os.path.abspath(output_png_path)), exist_ok=True)

    # Temporary rendering script executed via pvpython
    has_aileron = os.path.exists(aileron_stl_path)
    script_content = f"""
import os
from paraview.simple import (
    _DisableFirstRenderCameraReset,
    STLReader,
    CreateRenderView,
    Show,
    ColorBy,
    ResetCamera,
    Render,
    SaveScreenshot
)

_DisableFirstRenderCameraReset()

view = CreateRenderView()
view.ViewSize = [{image_width}, {image_height}]
view.OrientationAxesVisibility = 0
view.UseColorPaletteForBackground = 0
view.Background = [0.94, 0.96, 0.98]

# Load Main Wing
w_reader = STLReader(registrationName='Wing_Main', FileNames=[r'{wing_stl_path}'])
dw = Show(w_reader, view)
dw.SetRepresentationType('Surface')
ColorBy(dw, None) # Clear default STLSolidLabeling colormap
dw.DiffuseColor = [0.20, 0.46, 0.82] # Clean aviation blue
dw.AmbientColor = [0.12, 0.28, 0.50]
dw.Specular = 0.3
dw.SpecularPower = 25.0

if {has_aileron}:
    a_reader = STLReader(registrationName='Wing_Aileron', FileNames=[r'{aileron_stl_path}'])
    da = Show(a_reader, view)
    da.SetRepresentationType('Surface')
    ColorBy(da, None) # Clear default colormap to apply diffuse color
    da.DiffuseColor = [1.00, 0.46, 0.05] # Vibrant aerospace safety orange
    da.AmbientColor = [0.55, 0.22, 0.02]
    da.Specular = 0.4
    da.SpecularPower = 25.0

# Position camera for full-span horizontal framing showing top surface and aileron
view.CameraFocalPoint = [125.0, 388.0, 17.0]
view.CameraPosition = [600.0, 200.0, 700.0]
view.CameraViewUp = [0.0, 0.0, 1.0]

view.ResetCamera()
cam = view.GetActiveCamera()
cam.Dolly(0.85) # Zoom out to ensure full wingspan fits comfortably in frame

Render()
SaveScreenshot(r'{output_png_path}', view, ImageResolution=[{image_width}, {image_height}])
print('CAD 3D screenshot saved successfully.')
"""

    temp_script = os.path.join(os.path.dirname(os.path.abspath(output_png_path)), "_temp_render_script.py")
    try:
        with open(temp_script, "w", encoding="utf-8") as f:
            f.write(script_content)

        res = subprocess.run([pvpython_exe, temp_script], capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(output_png_path):
            return True
        else:
            print(f"ParaView render notice: {res.stderr}")
            return False
    except Exception as e:
        print(f"Error invoking ParaView render: {e}")
        return False
    finally:
        if os.path.exists(temp_script):
            try:
                os.remove(temp_script)
            except OSError:
                pass


def render_airfoil_plot(
    airfoil_dat_path: str,
    output_png_path: str,
    airfoil_name: str = "Airfoil Profile"
) -> bool:
    """
    Renders an aerodynamic cross-section plot showing upper and lower surfaces, chord line, and camber.
    """
    if not os.path.exists(airfoil_dat_path):
        print(f"Warning: Airfoil DAT file not found at {airfoil_dat_path}")
        return False

    os.makedirs(os.path.dirname(os.path.abspath(output_png_path)), exist_ok=True)

    coords = []
    with open(airfoil_dat_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    header = lines[0].strip() if lines else airfoil_name
    for line in lines[1:]:
        parts = line.strip().split()
        if len(parts) >= 2:
            try:
                coords.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue

    if not coords:
        return False

    pts = np.array(coords)
    x = pts[:, 0]
    y = pts[:, 1]

    fig, ax = plt.subplots(figsize=(10, 3.8), dpi=150)
    fig.patch.set_facecolor("#FAFAFC")
    ax.set_facecolor("#FFFFFF")

    # Plot airfoil outline
    ax.plot(x, y, color="#1E3A8A", linewidth=2.2, label=f"{header} Outline")
    ax.fill(x, y, color="#3B82F6", alpha=0.18)

    # Reference chord line
    ax.axhline(0, color="#9CA3AF", linestyle="--", linewidth=1.0, label="Chord Line (y=0)")

    ax.set_title(f"Generated Airfoil Cross-Section: {header}", fontsize=12, fontweight="bold", pad=12, color="#1F2937")
    ax.set_xlabel("Normalized Chord (x/c)", fontsize=10, color="#374151")
    ax.set_ylabel("Normalized Thickness (y/c)", fontsize=10, color="#374151")
    ax.set_xlim(-0.02, 1.05)
    ax.set_ylim(-0.15, 0.20)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle=":", alpha=0.6, color="#D1D5DB")
    ax.legend(loc="upper right", framealpha=0.9, fontsize=9)

    plt.tight_layout()
    plt.savefig(output_png_path, dpi=150, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    return os.path.exists(output_png_path)
