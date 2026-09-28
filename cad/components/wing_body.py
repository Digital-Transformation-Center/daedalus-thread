"""Wing body geometry and station interpolation."""
import math
import FreeCAD as App
import Part
from components.airfoil import create_profile_wire

def ensure_manifold_solid(shape, min_volume=1.0):
    """Ensures that a shape is a clean, single manifold Part.Solid."""
    if shape is None:
        raise ValueError("Cannot make manifold solid from None shape.")

    if hasattr(shape, "Solids") and shape.Solids:
        # Sort solids by volume descending
        sorted_solids = sorted(shape.Solids, key=lambda s: s.Volume, reverse=True)
        max_vol = sorted_solids[0].Volume
        # Filter out tiny degenerate sliver solids from boolean operations
        cutoff = max(min_volume, max_vol * 1e-3)
        solids = [s for s in sorted_solids if s.Volume >= cutoff]
        if not solids:
            solids = [sorted_solids[0]]

        if len(solids) == 1:
            solid = solids[0]
        else:
            solid = solids[0]
            for s in solids[1:]:
                solid = solid.fuse(s)
    elif getattr(shape, "ShapeType", "") == "Solid":
        solid = shape
    else:
        try:
            solid = Part.Solid(shape)
        except Exception as e:
            raise ValueError(f"Failed to convert shape to Part.Solid: {e}")

    if not solid.isClosed():
        raise ValueError("Generated wing geometry is non-manifold (open shell or unclosed volume).")
    if not solid.isValid():
        raise ValueError("Generated wing geometry is invalid.")

    return solid

class WingGeometry:
    """Manages spanwise parameter interpolation and base loft generation."""

    def __init__(self, span, root_chord, tip_chord, sweep_deg, dihedral_deg, raw_points, pitch_deg=0.0):
        self.span = float(span)
        self.half_span = self.span / 2.0
        self.root_chord = float(root_chord)
        self.tip_chord = float(tip_chord)
        self.sweep_rad = math.radians(float(sweep_deg))
        self.dihedral_rad = math.radians(float(dihedral_deg))
        self.raw_points = raw_points
        self.pitch_deg = float(pitch_deg)

    def get_chord_at(self, y):
        """Returns the chord length at spanwise station y."""
        ratio = max(0.0, min(1.0, y / self.half_span))
        return self.root_chord + ratio * (self.tip_chord - self.root_chord)

    def get_le_position(self, y):
        """Returns leading edge (X, Y, Z) coordinates at span station y."""
        x = y * math.tan(self.sweep_rad)
        z = y * math.tan(self.dihedral_rad)
        return App.Vector(x, y, z)

    def rotate_point_at(self, x, y, z):
        """Rotates a 3D point about the local aerodynamic quarter-chord (c/4) axis at station y."""
        if abs(self.pitch_deg) < 1e-6:
            return App.Vector(x, y, z)
        chord = self.get_chord_at(y)
        le = self.get_le_position(y)
        pivot_x = le.x + (0.25 * chord)
        pivot_z = le.z
        rad = math.radians(self.pitch_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        dx = x - pivot_x
        dz = z - pivot_z
        x_rot = pivot_x + (dx * cos_a) + (dz * sin_a)
        z_rot = pivot_z - (dx * sin_a) + (dz * cos_a)
        return App.Vector(x_rot, y, z_rot)

    def get_profile_wire_at(self, y):
        """Returns the 3D airfoil wire at span station y."""
        chord = self.get_chord_at(y)
        le = self.get_le_position(y)
        return create_profile_wire(self.raw_points, chord, le.x, y, le.z, pitch_deg=self.pitch_deg)

    def build_solid(self, num_stations=2):
        """Builds a solid loft for the wing half-span."""
        if num_stations < 2:
            num_stations = 2
            
        wires = []
        for i in range(num_stations):
            y = (i / (num_stations - 1)) * self.half_span
            wires.append(self.get_profile_wire_at(y))
            
        loft = Part.makeLoft(wires, True) # Solid
        return ensure_manifold_solid(loft)
