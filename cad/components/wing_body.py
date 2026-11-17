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
        self._upper_pts, self._lower_pts = self._split_airfoil_surfaces(raw_points)

    @staticmethod
    def _split_airfoil_surfaces(raw_points):
        """Splits normalized airfoil points into sorted (x, z) upper and lower branches."""
        le_idx = min(range(len(raw_points)), key=lambda i: raw_points[i].x)
        first_half = [(p.x, p.z) for p in raw_points[: le_idx + 1]]
        second_half = [(p.x, p.z) for p in raw_points[le_idx:]]
        first_half.sort(key=lambda pt: pt[0])
        second_half.sort(key=lambda pt: pt[0])
        # Determine which branch is upper vs lower by mean z
        mean_first = sum(pt[1] for pt in first_half) / max(1, len(first_half))
        mean_second = sum(pt[1] for pt in second_half) / max(1, len(second_half))
        if mean_first >= mean_second:
            return first_half, second_half
        return second_half, first_half

    @staticmethod
    def _interp_branch_z(branch, u):
        """Piecewise-linearly interpolates normalized z at normalized chord u in [0, 1]."""
        if u <= branch[0][0]:
            return branch[0][1]
        if u >= branch[-1][0]:
            return branch[-1][1]
        for i in range(len(branch) - 1):
            x0, z0 = branch[i]
            x1, z1 = branch[i + 1]
            if x0 <= u <= x1:
                if abs(x1 - x0) < 1e-9:
                    return 0.5 * (z0 + z1)
                t = (u - x0) / (x1 - x0)
                return z0 + t * (z1 - z0)
        return branch[-1][1]

    def get_surface_z(self, x, y):
        """Returns (z_bottom, z_top) in mm at global (x, y)."""
        chord = self.get_chord_at(y)
        le = self.get_le_position(y)
        u = max(0.0, min(1.0, (float(x) - le.x) / chord))
        z_bot = le.z + chord * self._interp_branch_z(self._lower_pts, u)
        z_top = le.z + chord * self._interp_branch_z(self._upper_pts, u)
        return z_bot, z_top

    def get_max_thickness_x(self, y):
        """Returns the global X coordinate of maximum airfoil thickness at span station y."""
        chord = self.get_chord_at(y)
        le = self.get_le_position(y)
        best_u = 0.30
        best_t = -1.0
        for i in range(1, 100):
            u = i / 100.0
            t = self._interp_branch_z(self._upper_pts, u) - self._interp_branch_z(self._lower_pts, u)
            if t > best_t:
                best_t = t
                best_u = u
        return le.x + best_u * chord

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
