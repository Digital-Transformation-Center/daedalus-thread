"""Exports high-resolution CFD cross-section visuals at wing mid-span.

Can be run directly via:
    python cad/export_cfd_visuals.py
or using ParaView's pvpython:
    pvpython cad/export_cfd_visuals.py
"""
import os
import subprocess
import sys
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = r"C:\Users\kuederrj\DTC\projects\daedalus-thread\cad\output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Artifact directory for conversation embedding
ARTIFACT_DIR = r"C:\Users\kuederrj\.gemini\antigravity\brain\29d2d487-3b60-4742-96c9-b47e2872e391"

PARAVIEW_PYTHON = r"C:\Users\kuederrj\AppData\Local\ParaView-6.2.0-RC2-Windows-Python3.12-msvc2017-AMD64\bin\pvpython.exe"
CASE_DIR = r"C:\Users\kuederrj\CfdOF\case"
PV_FOAM_PATH = os.path.join(CASE_DIR, "pv.foam")


def run_paraview_postprocess():
    """Generates cross-section visuals using ParaView Python API."""
    from paraview.simple import (
        _DisableFirstRenderCameraReset,
        OpenFOAMReader,
        GetAnimationScene,
        Slice,
        CellDatatoPointData,
        CreateRenderView,
        Show,
        Hide,
        ColorBy,
        GetColorTransferFunction,
        GetScalarBar,
        Render,
        SaveScreenshot,
        SaveState,
    )

    _DisableFirstRenderCameraReset()

    if not os.path.exists(PV_FOAM_PATH):
        raise FileNotFoundError(f"OpenFOAM case not found at {PV_FOAM_PATH}")

    print("1. Loading OpenFOAM case data...")
    pfoam = OpenFOAMReader(registrationName="pv.foam", FileName=PV_FOAM_PATH)
    pfoam.CaseType = "Reconstructed Case"
    pfoam.MeshRegions = ["internalMesh"]
    pfoam.CellArrays = ["p", "U", "k", "omega"]

    # 2. Advance to the final converged time step
    anim = GetAnimationScene()
    anim.UpdateAnimationUsingDataTimeSteps()
    if pfoam.TimestepValues:
        final_time = pfoam.TimestepValues[-1]
        anim.AnimationTime = final_time
        print(f"   Using converged solution at time step {final_time:.0f}")

    # 3. Create high-resolution Render View
    view = CreateRenderView()
    view.ViewSize = [1600, 800]
    view.Background = [0.94, 0.96, 0.98]  # Clean publication background
    view.OrientationAxesVisibility = 0

    # 4. Hide raw 3D volume box so it doesn't block the cross-section
    Hide(pfoam, view)

    # 5. Create Slice at Wing Mid-Span (Y = 0.16 m, perpendicular to span)
    midspan_y = 0.16
    center_x = 0.167
    center_z = 0.017
    slice_filter = Slice(registrationName="Midspan_Slice", Input=pfoam)
    slice_filter.SliceType = "Plane"
    slice_filter.SliceType.Origin = [center_x, midspan_y, center_z]
    slice_filter.SliceType.Normal = [0.0, 1.0, 0.0]

    # 6. Smooth Cell Data to Point Data for smooth contour bands
    smooth_slice = CellDatatoPointData(registrationName="Smooth_Slice", Input=slice_filter)

    disp = Show(smooth_slice, view)
    disp.SetRepresentationType("Surface")

    # Camera framing: flat 2D side view centered on the midspan airfoil
    view.CameraParallelProjection = 1
    view.CameraFocalPoint = [center_x, midspan_y, center_z]
    view.CameraPosition = [center_x, -0.80, center_z]
    view.CameraViewUp = [0.0, 0.0, 1.0]
    view.CameraParallelScale = 0.11

    # --- Render 1: Pressure Field (p) ---
    print("2. Rendering Air Pressure Contours...")
    ColorBy(disp, ("POINTS", "p"))
    lut_p = GetColorTransferFunction("p")
    try:
        lut_p.ApplyPreset("Jet", True)
    except Exception:
        pass
    disp.RescaleTransferFunctionToDataRange(True, False)

    sb_p = GetScalarBar(lut_p, view)
    sb_p.Title = "Pressure p [m2/s2]"
    sb_p.ComponentTitle = ""
    sb_p.Orientation = "Vertical"
    sb_p.WindowLocation = "Lower Left Corner"
    sb_p.TitleColor = [0.1, 0.1, 0.1]
    sb_p.LabelColor = [0.1, 0.1, 0.1]

    Render()
    out_p = os.path.join(OUTPUT_DIR, "cfd_midspan_pressure.png")
    SaveScreenshot(out_p, view, ImageResolution=[1600, 800])
    print(f"   -> Pressure graphic saved: {out_p}")

    if os.path.isdir(ARTIFACT_DIR):
        shutil.copy2(out_p, os.path.join(ARTIFACT_DIR, "cfd_midspan_pressure.png"))

    # Hide pressure scalar bar
    sb_p.Visibility = 0

    # --- Render 2: Velocity Field (U) ---
    print("3. Rendering Velocity Magnitude Contours (matching reference)...")
    ColorBy(disp, ("POINTS", "U"))
    lut_u = GetColorTransferFunction("U")
    try:
        lut_u.ApplyPreset("Jet", True)
    except Exception:
        pass
    disp.RescaleTransferFunctionToDataRange(True, False)

    sb_u = GetScalarBar(lut_u, view)
    sb_u.Visibility = 1
    sb_u.Title = "Velocity Magnitude |U| [m/s]"
    sb_u.ComponentTitle = ""
    sb_u.Orientation = "Vertical"
    sb_u.WindowLocation = "Lower Left Corner"
    sb_u.TitleColor = [0.1, 0.1, 0.1]
    sb_u.LabelColor = [0.1, 0.1, 0.1]

    Render()
    out_u = os.path.join(OUTPUT_DIR, "cfd_midspan_velocity.png")
    SaveScreenshot(out_u, view, ImageResolution=[1600, 800])
    print(f"   -> Velocity graphic saved: {out_u}")

    if os.path.isdir(ARTIFACT_DIR):
        shutil.copy2(out_u, os.path.join(ARTIFACT_DIR, "cfd_midspan_velocity.png"))

    # --- Save ParaView State File ---
    state_file = os.path.join(CASE_DIR, "Wing_MidSpan_CrossSection.pvsm")
    SaveState(state_file)
    print(f"4. Saved ParaView state file: {state_file}")

    print("\nSUCCESS: All mid-span CFD cross-section graphics generated successfully!")


def main():
    try:
        import paraview.simple
        run_paraview_postprocess()
        return
    except ImportError:
        pass

    if not os.path.exists(PARAVIEW_PYTHON):
        print(f"Error: ParaView Python not found at {PARAVIEW_PYTHON}")
        sys.exit(1)

    cmd = [PARAVIEW_PYTHON, os.path.abspath(__file__)]
    print(f"Executing ParaView post-processing: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
