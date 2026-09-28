"""Automated CFD wind tunnel fluid domain generator for FreeCAD.

This macro cuts the wing and aileron geometry out of a wind tunnel domain
to create a clean, watertight fluid volume for CFD meshing (CfdOF, OpenFOAM).
"""
import os
import sys
import FreeCAD as App
import Part

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def clean_broken_features(body_obj):
    """Removes broken or empty PartDesign Boolean features from the body."""
    if not body_obj or not hasattr(body_obj, "Group"):
        return

    doc = body_obj.Document
    for child in list(body_obj.Group):
        if child.TypeId == "PartDesign::Boolean":
            shape = getattr(child, "Shape", None)
            # Remove if shape is empty or null
            if shape is None or shape.isNull():
                print(f"Removing empty feature: {child.Name}")
                doc.removeObject(child.Name)

    # Ensure body tip points to the last valid feature (e.g. Pad001)
    if body_obj.Group:
        valid_features = [o for o in body_obj.Group if hasattr(o, "Shape") and not o.Shape.isNull()]
        if valid_features:
            body_obj.Tip = valid_features[-1]


def get_or_create_tunnel_base(doc, wing_obj, aileron_obj):
    """Finds existing wind tunnel body or creates a parametric bounding box."""
    # Check for existing PartDesign Body representing wind tunnel
    for obj_name in ["Body", "Wind_Tunnel_Body", "Tunnel_Body"]:
        obj = doc.getObject(obj_name)
        if obj and hasattr(obj, "Shape") and not obj.Shape.isNull():
            clean_broken_features(obj)
            return obj

    # If no tunnel body exists, compute parametric bounding box around wing
    print("No existing tunnel body found. Creating parametric wind tunnel box...")
    bbox = wing_obj.Shape.BoundBox
    if aileron_obj and hasattr(aileron_obj, "Shape") and not aileron_obj.Shape.isNull():
        bbox.add(aileron_obj.Shape.BoundBox)

    chord_ref = max(bbox.XLength, 200.0)
    span_ref = max(bbox.YLength, 400.0)

    # Standard aerodynamic CFD domain proportions:
    # 2-3 chords upstream, 5-6 chords downstream, 1.5 spans wide, 2-3 spans high
    x_min = bbox.XMin - (2.5 * chord_ref)
    x_max = bbox.XMax + (5.5 * chord_ref)
    y_min = bbox.YMin - (0.5 * span_ref)
    y_max = bbox.YMax + (1.0 * span_ref)
    z_min = bbox.ZMin - (1.5 * chord_ref)
    z_max = bbox.ZMax + (1.5 * chord_ref)

    box = doc.getObject("Wind_Tunnel_Box")
    if not box:
        box = doc.addObject("Part::Box", "Wind_Tunnel_Box")
    box.Label = "Wind_Tunnel_Enclosure"
    box.Length = x_max - x_min
    box.Width = y_max - y_min
    box.Height = z_max - z_min
    box.Placement.Base = App.Vector(x_min, y_min, z_min)
    return box


def build_wind_tunnel_domain(doc=None):
    """Fuses wing components and cuts them from the wind tunnel domain."""
    if doc is None:
        doc = App.ActiveDocument
        if not doc:
            # Fallback to MBSE_Params_CFD.FCStd if active document is not open
            cfd_path = os.path.join(SCRIPT_DIR, "MBSE_Params_CFD.FCStd")
            if os.path.exists(cfd_path):
                doc = App.openDocument(cfd_path)
                App.setActiveDocument(doc.Name)
            else:
                raise RuntimeError("No active FreeCAD document found.")

    wing_obj = doc.getObject("MBSE_Parametric_Wing")
    aileron_obj = doc.getObject("MBSE_Parametric_Aileron")

    if not wing_obj or not hasattr(wing_obj, "Shape") or wing_obj.Shape.isNull():
        raise ValueError("MBSE_Parametric_Wing (Wing_Main) not found or has invalid shape.")

    cutter_shapes = [wing_obj]
    if aileron_obj and hasattr(aileron_obj, "Shape") and not aileron_obj.Shape.isNull():
        cutter_shapes.append(aileron_obj)

    # 1. Locate or create the wind tunnel base solid
    tunnel_base = get_or_create_tunnel_base(doc, wing_obj, aileron_obj)
    doc.recompute()

    # 2. Clean up any legacy/failing fusion objects
    for bad_name in ["Wing_Aero_Fusion", "Wing_Aero_Cutters", "_CFD_Domain_WingCut"]:
        bad_obj = doc.getObject(bad_name)
        if bad_obj:
            doc.removeObject(bad_obj.Name)

    # 3. Create or update parametric fluid domain cut
    # For CFD, we cut using the clean aerodynamic wing surface (MBSE_Parametric_Wing_Aero)
    # to avoid 3D-printing micro-gaps and non-manifold pin-hinge edges in the mesh.
    aero_cutter = doc.getObject("MBSE_Parametric_Wing_Aero") or wing_obj

    cut_obj = doc.getObject("CFD_Fluid_Domain")
    if not cut_obj:
        cut_obj = doc.addObject("Part::Cut", "CFD_Fluid_Domain")
    cut_obj.Label = "CFD_Fluid_Domain"
    cut_obj.Base = tunnel_base
    cut_obj.Tool = aero_cutter
    cut_obj.Visibility = True

    # 4. Hide raw wind tunnel base to avoid visual overlap
    tunnel_base.Visibility = False

    doc.recompute()

    if not cut_obj.Shape.isValid():
        raise RuntimeError("Generated CFD fluid domain geometry is invalid.")
    if not cut_obj.Shape.isClosed():
        raise RuntimeError("Generated CFD fluid domain is non-manifold (open shell).")

    # 5. Apply GUI aesthetics if running in an interactive session
    try:
        import FreeCADGui as Gui
        if Gui.ActiveDocument:
            gui_doc = Gui.ActiveDocument
            g_cut = gui_doc.getObject(cut_obj.Name)
            if g_cut:
                g_cut.Transparency = 75
                # Light aero blue color (RGB normalized)
                g_cut.ShapeColor = (0.70, 0.85, 1.00)
                g_cut.show()

            for hidden in [tunnel_base, aero_cutter]:
                g_h = gui_doc.getObject(hidden.Name)
                if g_h:
                    g_h.hide()

            for surface in [wing_obj, aileron_obj]:
                if surface:
                    g_s = gui_doc.getObject(surface.Name)
                    if g_s:
                        g_s.show()

            Gui.SendMsgToActiveView("ViewFit")
    except Exception:
        pass

    print("Success: CFD Wind Tunnel Fluid Domain successfully generated.")
    print(f"  - Fluid Domain Volume: {cut_obj.Shape.Volume:.2f} mm^3")
    print(f"  - Solids Count: {len(cut_obj.Shape.Solids)}")
    print(f"  - Manifold Watertight: {cut_obj.Shape.isClosed()}")
    return cut_obj


if __name__ == "__main__":
    build_wind_tunnel_domain()
