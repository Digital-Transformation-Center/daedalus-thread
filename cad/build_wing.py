"""Parametric wing generator orchestrator."""
import math
import os
import sys
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

def update_spreadsheet_definitions(sheet):
    """Populates MBSE_Params spreadsheet with aileron and servo parameter rows if missing."""
    param_definitions = [
        ("A7", "AileronStartRatio", "B7", "AileronStartRatio", "0.20"),
        ("A8", "AileronEndRatio", "B8", "AileronEndRatio", "0.70"),
        ("A9", "AileronChordRatio", "B9", "AileronChordRatio", "0.25"),
        ("A10", "HingeGap", "B10", "HingeGap", "0.6"),
        ("A11", "HingeBevelAngle", "B11", "HingeBevelAngle", "35.0"),
        ("A12", "HingePinDiameter", "B12", "HingePinDiameter", "1.6"),
        ("A13", "HingeTabCount", "B13", "HingeTabCount", "3"),
        ("A14", "ServoType", "B14", "ServoType", "HeeWing_FX5G"),
        ("A15", "ServoSpanOffsetRatio", "B15", "ServoSpanOffsetRatio", "0.25"),
    ]
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

def generate_wing():
    """Builds parametric wing with printed pin-hinge aileron and servo pocket."""
    doc = App.ActiveDocument
    if not doc:
        print("Error: No active FreeCAD document found.")
        return

    sheets = doc.getObjectsByLabel("MBSE_Params")
    sheet = sheets[0] if sheets else None
    if not sheet:
        print("Error: Could not find spreadsheet 'MBSE_Params'.")
        return

    update_spreadsheet_definitions(sheet)
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

    print(f"Building wing loft: Span={span}mm, Root={root_chord}mm, Tip={tip_chord}mm")
    wing_geom = WingGeometry(span, root_chord, tip_chord, sweep_deg, dihedral_deg, raw_points)
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

    # Position at ~50% local chord
    x_servo = le_servo.x + (chord_servo * 0.50)

    # Determine bottom skin surface Z at (x_servo, y_servo)
    wire_servo = wing_geom.get_profile_wire_at(y_servo)
    pts_wire = wire_servo.discretize(200)
    nearby_pts = [p for p in pts_wire if abs(p.x - x_servo) < 1.0]
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

    # Document Features
    # 1. Main Wing Body
    wing_obj = doc.getObject("MBSE_Parametric_Wing")
    if not wing_obj:
        wing_obj = doc.addObject("Part::Feature", "MBSE_Parametric_Wing")
    wing_obj.Shape = wing_solid
    wing_obj.Label = "Wing_Main"

    # 2. Aileron Control Surface
    aileron_obj = doc.getObject("MBSE_Parametric_Aileron")
    if not aileron_obj:
        aileron_obj = doc.addObject("Part::Feature", "MBSE_Parametric_Aileron")
    aileron_obj.Shape = aileron_solid
    aileron_obj.Label = "Wing_Aileron"

    doc.recompute()
    print("Success: Parametric wing and aileron successfully generated.")

if __name__ == "__main__":
    generate_wing()
