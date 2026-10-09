"""Parametric wing generator orchestrator for Daedalus Thread.

Supports both interactive execution inside FreeCAD GUI (via spreadsheet)
and headless CLI invocation driven by physics sizing middleware.
"""

import argparse
import importlib
import json
import math
import os
import sys

import FreeCAD as App
import Part

try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = os.path.abspath("cad")

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
    """Populates MBSE_Params spreadsheet with parameter rows if missing."""
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


def generate_wing(params=None, output_dir=None, export_step=False, export_stl=False):
    """Builds parametric wing with printed pin-hinge aileron and servo pocket.

    Args:
        params: Optional dictionary of parameters overriding spreadsheet.
        output_dir: Optional path to export generated CAD solids.
        export_step: Flag to export STEP geometry.
        export_stl: Flag to export STL meshes.

    Returns:
        dict: Mass properties and generation status.
    """
    doc = App.ActiveDocument
    headless = False

    if not doc:
        doc = App.newDocument("Daedalus_Wing")
        headless = True

    params = params or {}

    # Read from spreadsheet if no explicit params provided
    if not params:
        sheets = doc.getObjectsByLabel("MBSE_Params")
        sheet = sheets[0] if sheets else None
        if sheet:
            update_spreadsheet_definitions(sheet)
            doc.recompute()
            params = {
                "span": float(sheet.get("Span")),
                "root_chord": float(sheet.get("RootChord")),
                "tip_chord": float(sheet.get("TipChord")),
                "sweep_deg": float(sheet.get("SweepAngle")),
                "dihedral_deg": float(sheet.get("DihedralAngle")),
                "airfoil_path": sheet.get("AirfoilPath"),
                "aileron_start": get_param(sheet, "AileronStartRatio", 0.20),
                "aileron_end": get_param(sheet, "AileronEndRatio", 0.70),
                "aileron_chord": get_param(sheet, "AileronChordRatio", 0.25),
                "hinge_gap": get_param(sheet, "HingeGap", 0.6),
                "bevel_angle": get_param(sheet, "HingeBevelAngle", 35.0),
                "pin_dia": get_param(sheet, "HingePinDiameter", 1.6),
                "tab_count": get_param(sheet, "HingeTabCount", 3),
                "servo_type": str(get_param(sheet, "ServoType", "HeeWing_FX5G")).strip("'\""),
                "servo_span_offset_ratio": get_param(sheet, "ServoSpanOffsetRatio", 0.25),
            }
        else:
            # Fallback default parameters
            params = {
                "span": 1400.0,
                "root_chord": 212.0,
                "tip_chord": 138.0,
                "sweep_deg": 3.5,
                "dihedral_deg": 2.0,
                "airfoil_path": "airfoils/NACA_2412.dat",
                "aileron_start": 0.20,
                "aileron_end": 0.70,
                "aileron_chord": 0.25,
                "hinge_gap": 0.6,
                "bevel_angle": 35.0,
                "pin_dia": 1.6,
                "tab_count": 3,
                "servo_type": "HeeWing_FX5G",
                "servo_span_offset_ratio": 0.25,
            }

    span = float(params.get("span", 1400.0))
    root_chord = float(params.get("root_chord", 212.0))
    tip_chord = float(params.get("tip_chord", 138.0))
    sweep_deg = float(params.get("sweep_deg", 3.5))
    dihedral_deg = float(params.get("dihedral_deg", 2.0))
    raw_airfoil_path = params.get("airfoil_path", "airfoils/NACA_2412.dat")

    airfoil_path = resolve_path(raw_airfoil_path)
    if not os.path.isfile(airfoil_path):
        # Fallback to default airfoil in cad folder
        airfoil_path = os.path.join(SCRIPT_DIR, "airfoils", "NACA_2412.dat")

    raw_points = load_airfoil_points(airfoil_path)

    aileron_start = float(params.get("aileron_start", 0.20))
    aileron_end = float(params.get("aileron_end", 0.70))
    aileron_chord = float(params.get("aileron_chord", 0.25))
    hinge_gap = float(params.get("hinge_gap", 0.6))
    bevel_angle = float(params.get("bevel_angle", 35.0))
    pin_dia = float(params.get("pin_dia", 1.6))
    tab_count = int(params.get("tab_count", 3))

    servo_type = str(params.get("servo_type", "HeeWing_FX5G")).strip("'\"")
    servo_span_offset_ratio = float(params.get("servo_span_offset_ratio", 0.25))

    wing_geom = WingGeometry(span, root_chord, tip_chord, sweep_deg, dihedral_deg, raw_points)
    raw_wing_solid = wing_geom.build_solid(num_stations=2)

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
    x_servo = le_servo.x + (chord_servo * 0.50)

    wire_servo = wing_geom.get_profile_wire_at(y_servo)
    pts_wire = wire_servo.discretize(200)
    nearby_pts = [p for p in pts_wire if abs(p.x - x_servo) < 1.0]
    z_bottom = min([p.z for p in nearby_pts]) if nearby_pts else (le_servo.z - chord_servo * 0.06)

    servo_center = App.Vector(x_servo, y_servo, z_bottom)
    servo_pocket_gen = ServoPocket(servo_type=servo_type)
    servo_cutter = servo_pocket_gen.create_cutter(
        center_pos=servo_center,
        wing_bottom_z=z_bottom,
        wing_geom=wing_geom
    )

    wing_solid = wing_solid.cut(servo_cutter)

    # Add/Update Document Objects
    wing_obj = doc.getObject("MBSE_Parametric_Wing")
    if not wing_obj:
        wing_obj = doc.addObject("Part::Feature", "MBSE_Parametric_Wing")
    wing_obj.Shape = wing_solid
    wing_obj.Label = "Wing_Main"

    aileron_obj = doc.getObject("MBSE_Parametric_Aileron")
    if not aileron_obj:
        aileron_obj = doc.addObject("Part::Feature", "MBSE_Parametric_Aileron")
    aileron_obj.Shape = aileron_solid
    aileron_obj.Label = "Wing_Aileron"

    doc.recompute()

    # Calculate Solid Mass & Physical Properties
    half_wing_volume_mm3 = float(wing_solid.Volume)
    aileron_volume_mm3 = float(aileron_solid.Volume)
    total_half_volume_mm3 = half_wing_volume_mm3 + aileron_volume_mm3

    # Structural mass estimate for LW-PLA printed wing with 2 perimeters, infill,
    # plus carbon fiber spar and servo hardware allocation:
    # LW-PLA printed density ~0.000085 g/mm3 effective bulk density
    # Dual wings + 2 servos (18g) + 6mm CF spar joiners (40g)
    both_wings_solid_volume = total_half_volume_mm3 * 2.0
    printed_mass_g = both_wings_solid_volume * 0.000085
    hardware_mass_g = 58.0
    total_wing_mass_kg = round((printed_mass_g + hardware_mass_g) / 1000.0, 3)

    if hasattr(wing_solid, "CenterOfGravity"):
        cg = wing_solid.CenterOfGravity
        cg_coords = [round(cg.x, 2), round(cg.y, 2), round(cg.z, 2)]
    elif hasattr(wing_solid, "CenterOfMass"):
        cg = wing_solid.CenterOfMass
        cg_coords = [round(cg.x, 2), round(cg.y, 2), round(cg.z, 2)]
    else:
        bb = wing_solid.BoundBox
        cg_coords = [round(bb.Center.x, 2), round(bb.Center.y, 2), round(bb.Center.z, 2)]

    wing_bb = wing_solid.BoundBox
    results = {
        "status": "success",
        "span_mm": span,
        "root_chord_mm": root_chord,
        "tip_chord_mm": tip_chord,
        "half_volume_mm3": round(total_half_volume_mm3, 1),
        "total_wing_mass_kg": total_wing_mass_kg,
        "center_of_gravity": cg_coords,
        "build_envelope_mm": {
            "chord_x": round(wing_bb.XLength, 1),
            "span_y": round(wing_bb.YLength, 1),
            "thickness_z": round(wing_bb.ZLength, 1)
        },
        "exported_files": []
    }

    # Optional geometry exports
    if output_dir:
        output_dir = os.path.normpath(str(output_dir).strip("'\""))
        os.makedirs(output_dir, exist_ok=True)
        if export_step:
            step_path = os.path.join(output_dir, "wing_assembly.step")
            Part.export([wing_obj, aileron_obj], step_path)
            results["exported_files"].append(step_path)
        if export_stl:
            try:
                import MeshPart
                # Separate printable parts for slicing
                main_stl_path = os.path.join(output_dir, "wing_main.stl")
                mesh_main = MeshPart.meshFromShape(Shape=wing_solid, MaxLength=5.0)
                mesh_main.write(main_stl_path)
                results["exported_files"].append(main_stl_path)

                aileron_stl_path = os.path.join(output_dir, "wing_aileron.stl")
                mesh_aileron = MeshPart.meshFromShape(Shape=aileron_solid, MaxLength=3.0)
                mesh_aileron.write(aileron_stl_path)
                results["exported_files"].append(aileron_stl_path)

                # Combined assembly reference
                assembly_stl_path = os.path.join(output_dir, "wing_assembly.stl")
                compound = Part.makeCompound([wing_solid, aileron_solid])
                mesh_asm = MeshPart.meshFromShape(Shape=compound, MaxLength=5.0)
                mesh_asm.write(assembly_stl_path)
                results["exported_files"].append(assembly_stl_path)
            except Exception as e:
                sys.stderr.write(f"Warning: Failed to export STL: {e}\n")

    print("__CAD_RESULT_JSON__:" + json.dumps(results))
    return results


def parse_cli_args():
    """Parses command-line arguments when invoked headlessly via freecadcmd."""
    parser = argparse.ArgumentParser(description="Headless FreeCAD Wing Generator")
    parser.add_argument("--json-params", type=str, help="JSON string with input parameters")
    parser.add_argument("--output-dir", type=str, help="Directory to save exported CAD models")
    parser.add_argument("--export-step", action="store_true", help="Export STEP file")
    parser.add_argument("--export-stl", action="store_true", help="Export STL file")
    parser.add_argument("--span", type=float, help="Wingspan in mm")
    parser.add_argument("--root-chord", type=float, help="Root chord in mm")
    parser.add_argument("--tip-chord", type=float, help="Tip chord in mm")

    # In FreeCAD freecadcmd, extra arguments might precede our script
    args, unknown = parser.parse_known_args()
    return args


if __name__ == "__main__":
    cli_args = parse_cli_args()
    input_params = {}
    if cli_args.json_params:
        try:
            input_params = json.loads(cli_args.json_params)
        except Exception as e:
            print(f"Warning: Failed to parse --json-params: {e}", file=sys.stderr)

    if cli_args.span:
        input_params["span"] = cli_args.span
    if cli_args.root_chord:
        input_params["root_chord"] = cli_args.root_chord
    if cli_args.tip_chord:
        input_params["tip_chord"] = cli_args.tip_chord

    generate_wing(
        params=input_params,
        output_dir=cli_args.output_dir,
        export_step=cli_args.export_step,
        export_stl=cli_args.export_stl
    )
