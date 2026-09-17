"""Wing body geometry and station interpolation."""
import math
import FreeCAD as App
import Part
from components.airfoil import create_profile_wire

class WingGeometry:
    """Manages spanwise parameter interpolation and base loft generation."""

    def __init__(self, span, root_chord, tip_chord, sweep_deg, dihedral_deg, raw_points):
        self.span = float(span)
        self.half_span = self.span / 2.0
        self.root_chord = float(root_chord)
        self.tip_chord = float(tip_chord)
        self.sweep_rad = math.radians(float(sweep_deg))
        self.dihedral_rad = math.radians(float(dihedral_deg))
        self.raw_points = raw_points

    def get_chord_at(self, y):
        """Returns the chord length at spanwise station y."""
        ratio = max(0.0, min(1.0, y / self.half_span))
        return self.root_chord + ratio * (self.tip_chord - self.root_chord)

    def get_le_position(self, y):
        """Returns leading edge (X, Y, Z) coordinates at span station y."""
        x = y * math.tan(self.sweep_rad)
        z = y * math.tan(self.dihedral_rad)
        return App.Vector(x, y, z)

    def get_profile_wire_at(self, y):
        """Returns the 3D airfoil wire at span station y."""
        chord = self.get_chord_at(y)
        le = self.get_le_position(y)
        return create_profile_wire(self.raw_points, chord, le.x, y, le.z)

    def build_solid(self, num_stations=2):
        """Builds a solid loft for the wing half-span."""
        if num_stations < 2:
            num_stations = 2
            
        wires = []
        for i in range(num_stations):
            y = (i / (num_stations - 1)) * self.half_span
            wires.append(self.get_profile_wire_at(y))
            
        return Part.makeLoft(wires, True) # Solid
