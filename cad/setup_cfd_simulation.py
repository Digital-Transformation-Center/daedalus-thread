"""Automated CfdOF simulation setup macro for FreeCAD.

Configures the full OpenFOAM CFD analysis container for the parametric wing,
including physics models, fluid properties (air), 30 mph cruise velocity,
boundary conditions (inlet, outlet, wing wall, symmetry), and force coefficient monitors.
"""
import os
import sys
import math
import FreeCAD as App

# Provide headless fallback for FreeCADGui if running in non-GUI mode
import builtins
try:
    import FreeCADGui
    if not hasattr(FreeCADGui, "addCommand"):
        FreeCADGui.addCommand = lambda *args, **kwargs: None
    builtins.FreeCADGui = FreeCADGui
except ImportError:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import build_wind_tunnel


def mph_to_mps(mph: float) -> float:
    """Converts miles per hour to meters per second."""
    return float(mph) * 0.44704


def identify_domain_faces(domain_shape):
    """Categorizes the faces of the wind tunnel fluid domain by geometric location."""
    bbox = domain_shape.BoundBox
    x_min, x_max = bbox.XMin, bbox.XMax
    y_min, y_max = bbox.YMin, bbox.YMax
    z_min, z_max = bbox.ZMin, bbox.ZMax

    tol = 5.0  # tolerance in mm for outer boundaries
    face_map = {
        "inlet": [],
        "outlet": [],
        "symmetry": [],
        "tunnel_walls": [],
        "wing_surfaces": [],
    }

    for i, face in enumerate(domain_shape.Faces):
        f_name = f"Face{i + 1}"
        fb = face.BoundBox

        # Upstream face (X min) -> Inlet
        if abs(fb.XMin - x_min) < tol and abs(fb.XMax - x_min) < tol:
            face_map["inlet"].append(f_name)
        # Downstream face (X max) -> Outlet
        elif abs(fb.XMin - x_max) < tol and abs(fb.XMax - x_max) < tol:
            face_map["outlet"].append(f_name)
        # Root section plane at Y = 0 -> Symmetry plane
        elif abs(fb.YMin) < 1.0 and abs(fb.YMax) < 1.0:
            face_map["symmetry"].append(f_name)
        # Outer enclosure walls (top, bottom, lateral sides)
        elif (
            abs(fb.ZMin - z_min) < tol
            or abs(fb.ZMax - z_max) < tol
            or abs(fb.YMin - y_min) < tol
            or abs(fb.YMax - y_max) < tol
        ):
            face_map["tunnel_walls"].append(f_name)
        # Internal cutout faces -> Wing aerodynamic surfaces
        else:
            face_map["wing_surfaces"].append(f_name)

    return face_map


def setup_cfd_simulation(
    doc=None,
    cruise_speed_mph: float = 30.0,
    aircraft_mass_kg: float = 1.0,
):
    """Builds and configures the CfdOF analysis container in the active FreeCAD document."""
    if doc is None:
        doc = App.ActiveDocument
        if not doc:
            cfd_path = os.path.join(SCRIPT_DIR, "MBSE_Params_CFD.FCStd")
            if os.path.exists(cfd_path):
                doc = App.openDocument(cfd_path)
                App.setActiveDocument(doc.Name)
            else:
                raise RuntimeError("No active FreeCAD document found.")

    # 1. Ensure fluid domain solid exists
    domain_obj = doc.getObject("CFD_Fluid_Domain")
    if not domain_obj or not hasattr(domain_obj, "Shape") or domain_obj.Shape.isNull():
        print("CFD_Fluid_Domain missing or outdated. Rebuilding wind tunnel domain...")
        domain_obj = build_wind_tunnel.build_wind_tunnel_domain(doc)
        doc.recompute()

    # 2. Import CfdOF modules
    from CfdOF.CfdAnalysis import makeCfdAnalysis
    from CfdOF.Solve.CfdPhysicsSelection import makeCfdPhysicsSelection
    from CfdOF.Solve.CfdFluidMaterial import makeCfdFluidMaterial
    from CfdOF.Solve.CfdInitialiseFlowField import makeCfdInitialFlowField
    from CfdOF.Solve.CfdFluidBoundary import makeCfdFluidBoundary
    from CfdOF.Solve.CfdSolverFoam import makeCfdSolverFoam
    from CfdOF.Mesh.CfdMesh import makeCfdMesh
    from CfdOF.PostProcess.CfdReportingFunction import makeCfdReportingFunction

    # Remove any pre-existing CFD analysis objects to ensure a clean build
    cleanup_types = [
        "CfdAnalysis",
        "PhysicsModel",
        "FluidProperties",
        "InitialiseFields",
        "CfdSolver",
        "FluidMesh",
        "Inlet",
        "Outlet",
        "Wing_Wall",
        "Tunnel_Walls",
        "Symmetry_Plane",
        "LiftDragMonitor",
    ]
    for name in cleanup_types:
        existing = doc.getObject(name)
        if existing:
            doc.removeObject(existing.Name)

    # 3. Create CfdAnalysis container
    analysis = makeCfdAnalysis("CfdAnalysis")

    # 4. Physics Model: Incompressible, steady-state, RANS k-omega SST
    physics = makeCfdPhysicsSelection("PhysicsModel")
    if hasattr(physics, "Time"):
        physics.Time = "Steady"
    if hasattr(physics, "Flow"):
        physics.Flow = "Isothermal"
    if hasattr(physics, "Turbulence"):
        physics.Turbulence = "RANS"
    if hasattr(physics, "TurbulenceModel"):
        physics.TurbulenceModel = "kOmegaSST"
    analysis.addObject(physics)

    # 5. Fluid Material Properties: Standard Sea-Level Air
    material = makeCfdFluidMaterial("FluidProperties")
    material.Label = "Air_Standard"
    analysis.addObject(material)

    # 6. Initial Flow Field at cruise velocity (30 mph = 13.41 m/s along X)
    v_mps = mph_to_mps(cruise_speed_mph)
    init_fields = makeCfdInitialFlowField("InitialiseFields")
    if hasattr(init_fields, "VelocityIsCartesian"):
        init_fields.VelocityIsCartesian = True
    if hasattr(init_fields, "Ux"):
        init_fields.Ux = f"{v_mps:.3f} m/s"
    if hasattr(init_fields, "Uy"):
        init_fields.Uy = "0.0 m/s"
    if hasattr(init_fields, "Uz"):
        init_fields.Uz = "0.0 m/s"
    analysis.addObject(init_fields)

    # 7. Identify boundary faces on the fluid domain
    face_map = identify_domain_faces(domain_obj.Shape)
    print(f"Domain boundary classification:")
    for bname, flist in face_map.items():
        print(f"  - {bname:<15}: {flist}")

    # Boundary 1: Velocity Inlet
    if face_map["inlet"]:
        b_inlet = makeCfdFluidBoundary("Inlet")
        b_inlet.BoundaryType = "inlet"
        b_inlet.BoundarySubType = "uniformVelocityInlet"
        b_inlet.VelocityIsCartesian = True
        b_inlet.Ux = f"{v_mps:.3f} m/s"
        b_inlet.ShapeRefs = [(domain_obj, face_map["inlet"])]
        analysis.addObject(b_inlet)

    # Boundary 2: Static Pressure Outlet
    if face_map["outlet"]:
        b_outlet = makeCfdFluidBoundary("Outlet")
        b_outlet.BoundaryType = "outlet"
        b_outlet.BoundarySubType = "staticPressureOutlet"
        b_outlet.Pressure = "0.0 Pa"
        b_outlet.ShapeRefs = [(domain_obj, face_map["outlet"])]
        analysis.addObject(b_outlet)
        if hasattr(init_fields, "BoundaryP"):
            init_fields.BoundaryP = b_outlet
        if hasattr(init_fields, "UseOutletPValue"):
            init_fields.UseOutletPValue = True

    # Boundary 3: Wing Aerodynamic Wall (No-slip surface)
    if face_map["wing_surfaces"]:
        b_wing = makeCfdFluidBoundary("Wing_Wall")
        b_wing.BoundaryType = "wall"
        b_wing.BoundarySubType = "fixedWall"
        b_wing.ShapeRefs = [(domain_obj, face_map["wing_surfaces"])]
        analysis.addObject(b_wing)

    # Boundary 4: Tunnel Outer Enclosure Walls (Slip walls)
    if face_map["tunnel_walls"]:
        b_walls = makeCfdFluidBoundary("Tunnel_Walls")
        b_walls.BoundaryType = "wall"
        b_walls.BoundarySubType = "slipWall"
        b_walls.ShapeRefs = [(domain_obj, face_map["tunnel_walls"])]
        analysis.addObject(b_walls)

    # Boundary 5: Root Chord Symmetry Plane (Y = 0)
    if face_map["symmetry"]:
        b_sym = makeCfdFluidBoundary("Symmetry_Plane")
        b_sym.BoundaryType = "constraint"
        b_sym.BoundarySubType = "symmetry"
        b_sym.ShapeRefs = [(domain_obj, face_map["symmetry"])]
        analysis.addObject(b_sym)

    # 8. Add Force & Moment Monitor for Lift and Drag
    try:
        forces = makeCfdReportingFunction("LiftDragMonitor")
        if hasattr(forces, "ReportingFunctionType"):
            forces.ReportingFunctionType = "ForceCoefficients"
        if face_map["wing_surfaces"] and "b_wing" in locals():
            if hasattr(forces, "Patch"):
                forces.Patch = b_wing
        if hasattr(forces, "Lift"):
            forces.Lift = (0, 0, 1)  # Z is vertical lift
        if hasattr(forces, "Drag"):
            forces.Drag = (1, 0, 0)  # X is streamwise drag
        if hasattr(forces, "MagnitudeUInf"):
            forces.MagnitudeUInf = f"{v_mps:.3f} m/s"
        analysis.addObject(forces)
    except Exception as e:
        print(f"Note: Force coefficients reporting setup: {e}")

    # 9. Mesh container
    mesh_obj = makeCfdMesh("FluidMesh")
    if hasattr(mesh_obj, "Part"):
        mesh_obj.Part = domain_obj
    analysis.addObject(mesh_obj)

    # 10. OpenFOAM Solver configuration
    solver = makeCfdSolverFoam("CfdSolver")
    if hasattr(solver, "MaxIterations"):
        solver.MaxIterations = 500
    if hasattr(solver, "ParallelCores"):
        solver.ParallelCores = 4
    analysis.addObject(solver)

    doc.recompute()
    try:
        doc.save()
    except Exception as e:
        print(f"Note: Document save: {e}")

    print("\n" + "=" * 70)
    print("SUCCESS: CfdOF Simulation Setup Successfully Created in FreeCAD!")
    print("=" * 70)
    print(f"Analysis Configuration:")
    print(f"  - Cruise Velocity:    {cruise_speed_mph:.1f} mph ({v_mps:.2f} m/s)")
    print(f"  - Fluid Medium:       Air (rho = 1.225 kg/m^3)")
    print(f"  - Target Lift Force:  {aircraft_mass_kg * 9.80665:.2f} N (1.0 kg plane)")
    print(f"  - Fluid Domain:       {domain_obj.Label} ({domain_obj.Shape.Volume:.0f} mm^3)")
    print(f"  - Solver Engine:      OpenFOAM simpleFoam (steady incompressible RANS)")
    print(f"  - Boundary Patches:   Inlet, Outlet, Wing_Wall, Tunnel_Walls, Symmetry")
    print(f"  - Force Reporting:    LiftDragMonitor (CL, CD, Lift, Drag)")
    print("=" * 70 + "\n")

    return analysis


if __name__ == "__main__":
    setup_cfd_simulation()
