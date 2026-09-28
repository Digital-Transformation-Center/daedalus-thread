"""Parametric wing generator orchestrator."""
import math
import os
import sys
import json
import importlib
import FreeCAD as App
import Part

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import components.airfoil as c_airfoil
import components.wing_body as c_wing_body
import components.aileron as c_aileron
import components.servo_pocket as c_servo_pocket

# Ensure modules are reloaded when macro is executed in an open FreeCAD session
importlib.reload(c_airfoil)
importlib.reload(c_wing_body)
importlib.reload(c_aileron)
importlib.reload(c_servo_pocket)

load_airfoil_points = c_airfoil.load_airfoil_points
WingGeometry = c_wing_body.WingGeometry
AileronGenerator = c_aileron.AileronGenerator
ServoPocket = c_servo_pocket.ServoPocket

def resolve_path(path_str):
    """Converts relative paths to absolute paths anchored to CAD folder."""
    clean_path = str(path_str).strip("'\"").strip()
    if os.path.isabs(clean_path):
        return clean_path
    return os.path.normpath(os.path.join(SCRIPT_DIR, clean_path))

def get_param(sheet, alias, default_val):
    """Safely retrieves a parameter from spreadsheet alias or returns default."""
    try:
        val = sheet.get(alias)
        if val is not None and str(val).strip() != "":
            if isinstance(default_val, float):
                return float(val)
            if isinstance(default_val, int):
                return int(val)
            return str(val).strip()
    except Exception:
        pass
    return default_val

def update_spreadsheet_definitions(sheet, new_params=None):
    """Populates MBSE_Params spreadsheet with parameter values."""
    param_definitions = [
        ("A1", "Span", "B1", "Span", "1800.0"),
        ("A2", "RootChord", "B2", "RootChord", "240.0"),
        ("A3", "TipChord", "B3", "TipChord", "160.0"),
        ("A4", "SweepAngle", "B4", "SweepAngle", "3.5"),
        ("A5", "DihedralAngle", "B5", "DihedralAngle", "2.0"),
        ("A6", "AirfoilPath", "B6", "AirfoilPath", "airfoils/NACA_2412.dat"),
        ("A7", "AileronStartRatio", "B7", "AileronStartRatio", "0.20"),
        ("A8", "AileronEndRatio", "B8", "AileronEndRatio", "0.70"),
        ("A9", "AileronChordRatio", "B9", "AileronChordRatio", "0.25"),
        ("A10", "HingeGap", "B10", "HingeGap", "0.6"),
        ("A11", "HingeBevelAngle", "B11", "HingeBevelAngle", "35.0"),
        ("A12", "HingePinDiameter", "B12", "HingePinDiameter", "1.6"),
        ("A13", "HingeTabCount", "B13", "HingeTabCount", "3"),
        ("A14", "ServoType", "B14", "ServoType", "HeeWing_FX5G"),
        ("A15", "ServoSpanOffsetRatio", "B15", "ServoSpanOffsetRatio", "0.25"),
        ("A16", "PitchAngle", "B16", "PitchAngle", "0.0"),
    ]
    
    # Apply new parameters if provided
    if new_params:
        for lbl_cell, lbl_val, val_cell, alias, default_str in param_definitions:
            if alias in new_params:
                val_str = str(new_params[alias])
                sheet.set(lbl_cell, lbl_val)
                sheet.set(val_cell, val_str)
                sheet.setAlias(val_cell, alias)
            else:
                try:
                    existing_val = sheet.get(alias)
                except Exception:
                    existing_val = None
                if existing_val is None:
                    sheet.set(lbl_cell, lbl_val)
                    sheet.set(val_cell, default_str)
                    sheet.setAlias(val_cell, alias)
    else:
        for lbl_cell, lbl_val, val_cell, alias, val_str in param_definitions:
            try:
                try:
                    existing_val = sheet.get(alias)
                except Exception:
                    existing_val = None

                if existing_val is None:
                    sheet.set(lbl_cell, lbl_val)
                    sheet.set(val_cell, val_str)
                    sheet.setAlias(val_cell, alias)
            except Exception:
                pass

def generate_wing(params_override=None, output_dir=None):
    """Builds parametric wing with printed pin-hinge aileron and servo pocket."""
    doc = App.ActiveDocument
    if not doc:
        fcstd_path = os.path.join(SCRIPT_DIR, "MBSE_Params.FCStd")
        if os.path.exists(fcstd_path):
            doc = App.openDocument(fcstd_path)
            App.setActiveDocument(doc.Name)
        else:
            doc = App.newDocument("MBSE_Wing_Doc")

    sheets = doc.getObjectsByLabel("MBSE_Params")
    sheet = sheets[0] if sheets else None
    if not sheet:
        sheet = doc.addObject("Spreadsheet::Sheet", "MBSE_Params")

    update_spreadsheet_definitions(sheet, params_override)
    doc.recompute()

    # Core Wing Parameters
    span = float(sheet.get("Span"))
    root_chord = float(sheet.get("RootChord"))
    tip_chord = float(sheet.get("TipChord"))
    sweep_deg = float(sheet.get("SweepAngle"))
    dihedral_deg = float(sheet.get("DihedralAngle"))
    raw_airfoil_path = sheet.get("AirfoilPath")

    airfoil_path = resolve_path(raw_airfoil_path)
    print(f"Loading airfoil from: {airfoil_path}")
    raw_points = load_airfoil_points(airfoil_path)

    # Aileron & Hinge Parameters
    aileron_start = get_param(sheet, "AileronStartRatio", 0.20)
    aileron_end = get_param(sheet, "AileronEndRatio", 0.70)
    aileron_chord = get_param(sheet, "AileronChordRatio", 0.25)
    hinge_gap = get_param(sheet, "HingeGap", 0.6)
    bevel_angle = get_param(sheet, "HingeBevelAngle", 35.0)
    pin_dia = get_param(sheet, "HingePinDiameter", 1.6)
    tab_count = get_param(sheet, "HingeTabCount", 3)

    # Servo Parameters
    servo_type = str(get_param(sheet, "ServoType", "HeeWing_FX5G")).strip("'\"")
    servo_span_offset_ratio = get_param(sheet, "ServoSpanOffsetRatio", 0.25)

    # Aerodynamic Pitch (Angle of Attack)
    pitch_deg = get_param(sheet, "PitchAngle", 0.0)

    print(f"Building wing loft: Span={span}mm, Root={root_chord}mm, Tip={tip_chord}mm, Pitch={pitch_deg}deg")
    wing_geom = WingGeometry(span, root_chord, tip_chord, sweep_deg, dihedral_deg, raw_points, pitch_deg=pitch_deg)
    raw_wing_solid = wing_geom.build_solid(num_stations=2)

    print(f"Generating aileron: span [{aileron_start*100:.1f}% - {aileron_end*100:.1f}%], chord {aileron_chord*100:.1f}%")
    aileron_gen = AileronGenerator(
        wing_geom,
        start_ratio=aileron_start,
        end_ratio=aileron_end,
        chord_ratio=aileron_chord,
        hinge_gap=hinge_gap,
        bevel_angle=bevel_angle,
        pin_dia=pin_dia,
        tab_count=tab_count
    )
    wing_solid, aileron_solid = aileron_gen.build_aileron_and_cutters(raw_wing_solid)

    # Dynamic Servo Placement
    y_servo = (aileron_start + servo_span_offset_ratio * (aileron_end - aileron_start)) * wing_geom.half_span
    le_servo = wing_geom.get_le_position(y_servo)
    chord_servo = wing_geom.get_chord_at(y_servo)

    # Position at ~50% local chord (accounting for wing pitch)
    x_unrot = le_servo.x + (chord_servo * 0.50)
    pt_servo_mid = wing_geom.rotate_point_at(x_unrot, y_servo, le_servo.z)
    x_servo = pt_servo_mid.x

    # Determine bottom skin surface Z at (x_servo, y_servo)
    wire_servo = wing_geom.get_profile_wire_at(y_servo)
    pts_wire = wire_servo.discretize(200)
    nearby_pts = [p for p in pts_wire if abs(p.x - x_servo) < 2.0]
    z_bottom = min([p.z for p in nearby_pts]) if nearby_pts else (le_servo.z - chord_servo * 0.06)

    servo_center = App.Vector(x_servo, y_servo, z_bottom)
    print(f"Adding servo pocket: Type={servo_type} at Y={y_servo:.1f}mm, X={x_servo:.1f}mm, Z_bottom={z_bottom:.1f}mm")

    servo_pocket_gen = ServoPocket(servo_type=servo_type)
    servo_cutter = servo_pocket_gen.create_cutter(
        center_pos=servo_center,
        wing_bottom_z=z_bottom,
        wing_geom=wing_geom
    )

    wing_solid = wing_solid.cut(servo_cutter)

    # Ensure manifold solid geometry
    wing_solid = c_wing_body.ensure_manifold_solid(wing_solid)
    aileron_solid = c_wing_body.ensure_manifold_solid(aileron_solid)

    # Clean up any legacy objects, previous hack objects, and PartDesign bodies
    cleanup_names = [
        "Geometry_Sources",
        "_Wing_Main_Source",
        "_Wing_Aileron_Source",
        "BaseFeature",
        "BaseFeature001",
        "MBSE_Parametric_Wing_Shape",
        "MBSE_Parametric_Aileron_Shape",
        "BaseShape",
        "BaseShape001",
        "Wing_Main_Shape",
        "Wing_Aileron_Shape",
    ]
    for name in cleanup_names:
        obj = doc.getObject(name)
        if obj:
            try:
                doc.removeObject(obj.Name)
            except Exception:
                pass

    # Ensure MBSE_Parametric_Wing and MBSE_Parametric_Aileron are Part::Feature objects
    for obj_name in ["MBSE_Parametric_Wing", "MBSE_Parametric_Aileron"]:
        existing = doc.getObject(obj_name)
        if existing and existing.TypeId != "Part::Feature":
            doc.removeObject(existing.Name)

    # 1. Main Wing Feature (Part::Feature for direct rendering and boolean CFD cutting)
    wing_obj = doc.getObject("MBSE_Parametric_Wing")
    if not wing_obj:
        wing_obj = doc.addObject("Part::Feature", "MBSE_Parametric_Wing")
    wing_obj.Label = "Wing_Main"
    wing_obj.Shape = wing_solid
    wing_obj.Visibility = True

    # 2. Aileron Control Surface Feature (Part::Feature)
    aileron_obj = doc.getObject("MBSE_Parametric_Aileron")
    if not aileron_obj:
        aileron_obj = doc.addObject("Part::Feature", "MBSE_Parametric_Aileron")
    aileron_obj.Label = "Wing_Aileron"
    aileron_obj.Shape = aileron_solid
    aileron_obj.Visibility = True

    # 3. Clean Aerodynamic Wing Surface (for CFD fluid domain cutting without 3D-print micro-gaps)
    aero_obj = doc.getObject("MBSE_Parametric_Wing_Aero")
    if not aero_obj:
        aero_obj = doc.addObject("Part::Feature", "MBSE_Parametric_Wing_Aero")
    aero_obj.Label = "Wing_Clean_Aero"
    aero_obj.Shape = raw_wing_solid
    aero_obj.Visibility = False

    doc.recompute()

    # GUI view updates if running inside interactive FreeCAD session
    try:
        import FreeCADGui as Gui
        if Gui.ActiveDocument:
            gui_doc = Gui.ActiveDocument
            for obj in [wing_obj, aileron_obj]:
                g_obj = gui_doc.getObject(obj.Name)
                if g_obj:
                    g_obj.show()
            Gui.SendMsgToActiveView("ViewFit")
    except Exception:
        pass

    print("Success: Parametric wing and aileron successfully generated as clean manifold Part::Feature objects.")

    # Export STL and STEP if output_dir specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        wing_stl = os.path.join(output_dir, "wing_main.stl")
        aileron_stl = os.path.join(output_dir, "wing_aileron.stl")
        step_path = os.path.join(output_dir, "wing_assembly.step")
        fcstd_path = os.path.join(output_dir, "generated_wing.FCStd")

        try:
            wing_solid.exportStl(wing_stl)
            aileron_solid.exportStl(aileron_stl)
            Part.export([wing_obj, aileron_obj], step_path)
            doc.saveAs(fcstd_path)
            print(f"Exported CAD models to {output_dir}:")
            print(f"  - {wing_stl}")
            print(f"  - {aileron_stl}")
            print(f"  - {step_path}")
            print(f"  - {fcstd_path}")
        except Exception as e:
            print(f"Warning during file export: {e}")

if __name__ == "__main__":
    params_override = None
    output_dir = None

    # Only parse configuration payload if explicitly passed a JSON file
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".json") and os.path.exists(sys.argv[1]):
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            data = json.load(f)
            params_override = data.get("cad_parameters", data)
            output_dir = data.get("output_dir", None)

        if len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
            output_dir = sys.argv[2]

    generate_wing(params_override=params_override, output_dir=output_dir)
