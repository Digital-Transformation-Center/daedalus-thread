"""Airfoil parsing and geometric transformation helpers."""
import os
import FreeCAD as App
import Part

def load_airfoil_points(dat_path):
    """Parses Selig or Lednicer formatted .dat airfoil coordinates.
    
    Coordinates in dat file are normalized: X (chord), Z (thickness).
    Returns a list of FreeCAD App.Vector(x, 0, z).
    """
    if not os.path.isabs(dat_path):
        dat_path = os.path.abspath(dat_path)
        
    if not os.path.exists(dat_path):
        raise FileNotFoundError(f"Airfoil file not found: {dat_path}")

    points = []
    with open(dat_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                try:
                    x = float(parts[0])
                    z = float(parts[1])
                    points.append(App.Vector(x, 0.0, z))
                except ValueError:
                    continue

    if not points:
        raise ValueError(f"No coordinate data found in {dat_path}")

    # Close the profile at trailing edge if needed
    if (points[0] - points[-1]).Length > 1e-5:
        points.append(points[0])

    return points

def create_profile_wire(raw_points, chord, offset_x, span_y, offset_z):
    """Scales normalized airfoil points and transforms them to 3D space.
    
    Args:
        raw_points: List of normalized App.Vector(x, 0, z)
        chord: Local chord length (mm)
        offset_x: Leading edge X position (mm)
        span_y: Y position along the half-span (mm)
        offset_z: Leading edge Z position (mm)
        
    Returns:
        Part.Wire: Closed wire of the airfoil cross-section.
    """
    pts = [
        App.Vector(
            (p.x * chord) + offset_x,
            span_y,
            (p.z * chord) + offset_z
        )
        for p in raw_points
    ]
    spline = Part.BSplineCurve()
    spline.interpolate(pts)
    return Part.Wire(spline.toShape())
