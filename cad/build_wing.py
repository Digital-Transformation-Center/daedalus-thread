import FreeCAD as App
import Part
import math
import os

# Identify the project directory relative to this script file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def resolve_path(path_str):
    """Converts relative paths to absolute paths anchored to the project folder."""
    clean_path = str(path_str).strip("'\"").strip()
    
    # Return as-is if already an absolute path
    if os.path.isabs(clean_path):
        return clean_path
        
    # Combine relative path with the script directory
    return os.path.normpath(os.path.join(SCRIPT_DIR, clean_path))

def load_airfoil_points(dat_path):
    """Parses standard Selig or Lednicer formatted .dat airfoil files."""
    resolved_path = resolve_path(dat_path)
    
    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"Airfoil file not found at: {resolved_path}")
        
    points = []
    with open(resolved_path, 'r') as f:
        lines = f.readlines()
        
    # Skip non-numeric header text and parse coordinates
    for line in lines:
        parts = line.strip().split()
        if len(parts) == 2:
            try:
                x = float(parts[0])
                z = float(parts[1])
                # DAT coordinates are X (chord) and Z (thickness), Y is along the span
                points.append(App.Vector(x, 0, z))
            except ValueError:
                continue # Skip header lines containing string labels
                
    if not points:
        raise ValueError(f"No valid coordinate data parsed from file: {resolved_path}")

    # Ensure spline curve loop closes properly at the trailing edge
    if points[0] != points[-1]:
        points.append(points[0])
        
    return points

def generate_wing():
    doc = App.ActiveDocument
    if not doc:
        print("Error: No active FreeCAD document found.")
        return

    # Label-safe fetch: Finds spreadsheet by display name/label
    sheets = doc.getObjectsByLabel("MBSE_Params")
    sheet = sheets[0] if sheets else None

    if not sheet:
        print("Error: Could not find any spreadsheet with the label 'MBSE_Params'.")
        return

    # Extract parametric values from spreadsheet aliases
    try:
        span = float(sheet.get("Span"))
        root_chord = float(sheet.get("RootChord"))
        tip_chord = float(sheet.get("TipChord"))
        sweep_deg = float(sheet.get("SweepAngle"))
        dihedral_deg = float(sheet.get("DihedralAngle"))
        raw_airfoil_path = sheet.get("AirfoilPath")
    except Exception as e:
        print(f"Error reading parameter aliases from 'MBSE_Params': {e}")
        return

    airfoil_path = resolve_path(raw_airfoil_path)
    print(f"Loading airfoil from: {airfoil_path}")

    # Parse .dat geometry
    raw_points = load_airfoil_points(airfoil_path)

    half_span = span / 2.0
    sweep_rad = math.radians(sweep_deg)
    dihedral_rad = math.radians(dihedral_deg)

    # Calculate 3D offsets for the tip section
    tip_x = half_span * math.tan(sweep_rad)
    tip_y = half_span
    tip_z = half_span * math.tan(dihedral_rad)

    # Scale and position Root Profile
    root_pts = [App.Vector(p.x * root_chord, 0, p.z * root_chord) for p in raw_points]
    root_spline = Part.BSplineCurve()
    root_spline.interpolate(root_pts)
    root_wire = Part.Wire(root_spline.toShape())

    # Scale and position Tip Profile
    tip_pts = [
        App.Vector(
            (p.x * tip_chord) + tip_x,
            tip_y,
            (p.z * tip_chord) + tip_z
        ) for p in raw_points
    ]
    tip_spline = Part.BSplineCurve()
    tip_spline.interpolate(tip_pts)
    tip_wire = Part.Wire(tip_spline.toShape())

    # Generate 3D Solid Loft
    loft_shape = Part.makeLoft([root_wire, tip_wire], True) # True = Solid

    # Create or update the Wing object in the document tree
    wing_obj = doc.getObject("MBSE_Parametric_Wing")
    if not wing_obj:
        wing_obj = doc.addObject("Part::Feature", "MBSE_Parametric_Wing")
    
    wing_obj.Shape = loft_shape
    doc.recompute()
    print(f"Success: Wing solid successfully built using '{os.path.basename(airfoil_path)}'.")

if __name__ == "__main__":
    generate_wing()