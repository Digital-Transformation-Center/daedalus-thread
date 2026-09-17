"""Aileron generation with printed pin hinge geometry and boolean cutter."""
import math
import FreeCAD as App
import Part

class AileronGenerator:
    """Generates the aileron solid and wing cutting tools with true 3D alignment."""

    def __init__(
        self,
        wing_geom,
        start_ratio=0.55,
        end_ratio=0.92,
        chord_ratio=0.25,
        hinge_gap=0.6,
        bevel_angle=35.0,
        pin_dia=1.6,
        tab_count=3
    ):
        self.wg = wing_geom
        self.y_start = float(start_ratio) * wing_geom.half_span
        self.y_end = float(end_ratio) * wing_geom.half_span
        self.chord_ratio = float(chord_ratio)
        self.hinge_gap = float(hinge_gap)
        self.bevel_angle = float(bevel_angle)
        self.pin_dia = float(pin_dia)
        self.tab_count = int(tab_count)
        # Camber midpoint offset ratio at 75% chord for NACA 2412
        self.camber_ratio = 0.01332

    def get_hinge_point(self, y):
        """Calculates hinge center point on the profile camber line at spanwise station y."""
        chord = self.wg.get_chord_at(y)
        le = self.wg.get_le_position(y)
        hx = le.x + chord * (1.0 - self.chord_ratio)
        hy = y
        # Center precisely on the airfoil mean camber line inside the wing core
        hz = le.z + chord * self.camber_ratio
        return App.Vector(hx, hy, hz)

    def build_aileron_and_cutters(self, wing_solid):
        """Constructs the separated aileron and cutting tool for the wing.
        
        Returns:
            tuple: (wing_with_hinges, aileron_with_hinges)
        """
        p_in = self.get_hinge_point(self.y_start)
        p_out = self.get_hinge_point(self.y_end)

        chord_in = self.wg.get_chord_at(self.y_start)
        chord_out = self.wg.get_chord_at(self.y_end)
        max_chord = max(chord_in, chord_out)
        cutter_len = max_chord * self.chord_ratio + 60.0
        cutter_h = max_chord * 0.6 + 30.0
        gap = self.hinge_gap

        # 1. Lofted Raw Aileron Extraction Solid
        w_in = Part.makePolygon([
            App.Vector(p_in.x, self.y_start, p_in.z - cutter_h / 2.0),
            App.Vector(p_in.x + cutter_len, self.y_start, p_in.z - cutter_h / 2.0),
            App.Vector(p_in.x + cutter_len, self.y_start, p_in.z + cutter_h / 2.0),
            App.Vector(p_in.x, self.y_start, p_in.z + cutter_h / 2.0),
            App.Vector(p_in.x, self.y_start, p_in.z - cutter_h / 2.0)
        ])
        w_out = Part.makePolygon([
            App.Vector(p_out.x, self.y_end, p_out.z - cutter_h / 2.0),
            App.Vector(p_out.x + cutter_len, self.y_end, p_out.z - cutter_h / 2.0),
            App.Vector(p_out.x + cutter_len, self.y_end, p_out.z + cutter_h / 2.0),
            App.Vector(p_out.x, self.y_end, p_out.z + cutter_h / 2.0),
            App.Vector(p_out.x, self.y_end, p_out.z - cutter_h / 2.0)
        ])
        raw_cut_prism = Part.makeLoft([Part.Wire(w_in), Part.Wire(w_out)], True, True)
        raw_aileron = wing_solid.common(raw_cut_prism)

        # 2. Oversized Lofted Cutter to carve out Aileron Bay from Wing
        w_cut_in = Part.makePolygon([
            App.Vector(p_in.x - gap, self.y_start - gap, p_in.z - cutter_h / 2.0),
            App.Vector(p_in.x + cutter_len, self.y_start - gap, p_in.z - cutter_h / 2.0),
            App.Vector(p_in.x + cutter_len, self.y_start - gap, p_in.z + cutter_h / 2.0),
            App.Vector(p_in.x - gap, self.y_start - gap, p_in.z + cutter_h / 2.0),
            App.Vector(p_in.x - gap, self.y_start - gap, p_in.z - cutter_h / 2.0)
        ])
        w_cut_out = Part.makePolygon([
            App.Vector(p_out.x - gap, self.y_end + gap, p_out.z - cutter_h / 2.0),
            App.Vector(p_out.x + cutter_len, self.y_end + gap, p_out.z - cutter_h / 2.0),
            App.Vector(p_out.x + cutter_len, self.y_end + gap, p_out.z + cutter_h / 2.0),
            App.Vector(p_out.x - gap, self.y_end + gap, p_out.z + cutter_h / 2.0),
            App.Vector(p_out.x - gap, self.y_end + gap, p_out.z - cutter_h / 2.0)
        ])
        wing_bay_cutter = Part.makeLoft([Part.Wire(w_cut_in), Part.Wire(w_cut_out)], True, True)
        wing_cutout = wing_solid.cut(wing_bay_cutter)

        # 3. Lofted Hinge Bevel Cutters on Aileron leading edge
        bevel_prism = self._create_bevel_cutter(p_in, p_out, cutter_h)
        aileron_body = raw_aileron.cut(bevel_prism)

        # 4. Generate Clean Interlocking Hinge Barrels with Toleranced Pockets & Pin Bore
        wing_with_hinges, aileron_with_hinges = self._add_pin_hinges(
            wing_cutout, aileron_body, p_in, p_out
        )

        return wing_with_hinges, aileron_with_hinges

    def _create_bevel_cutter(self, p_in, p_out, height):
        """Creates lofted V-shaped cutter to relieve aileron leading edge for deflection."""
        rad = math.radians(self.bevel_angle)
        dx = (height / 2.0) * math.tan(rad)

        w_in_1 = Part.makePolygon([
            App.Vector(p_in.x, self.y_start - 3.0, p_in.z),
            App.Vector(p_in.x + dx, self.y_start - 3.0, p_in.z + height / 2.0),
            App.Vector(p_in.x - dx, self.y_start - 3.0, p_in.z + height / 2.0),
            App.Vector(p_in.x, self.y_start - 3.0, p_in.z)
        ])
        w_out_1 = Part.makePolygon([
            App.Vector(p_out.x, self.y_end + 3.0, p_out.z),
            App.Vector(p_out.x + dx, self.y_end + 3.0, p_out.z + height / 2.0),
            App.Vector(p_out.x - dx, self.y_end + 3.0, p_out.z + height / 2.0),
            App.Vector(p_out.x, self.y_end + 3.0, p_out.z)
        ])
        top_bevel = Part.makeLoft([Part.Wire(w_in_1), Part.Wire(w_out_1)], True, True)

        w_in_2 = Part.makePolygon([
            App.Vector(p_in.x, self.y_start - 3.0, p_in.z),
            App.Vector(p_in.x + dx, self.y_start - 3.0, p_in.z - height / 2.0),
            App.Vector(p_in.x - dx, self.y_start - 3.0, p_in.z - height / 2.0),
            App.Vector(p_in.x, self.y_start - 3.0, p_in.z)
        ])
        w_out_2 = Part.makePolygon([
            App.Vector(p_out.x, self.y_end + 3.0, p_out.z),
            App.Vector(p_out.x + dx, self.y_end + 3.0, p_out.z - height / 2.0),
            App.Vector(p_out.x - dx, self.y_end + 3.0, p_out.z - height / 2.0),
            App.Vector(p_out.x, self.y_end + 3.0, p_out.z)
        ])
        bot_bevel = Part.makeLoft([Part.Wire(w_in_2), Part.Wire(w_out_2)], True, True)

        return top_bevel.fuse(bot_bevel)

    def _add_pin_hinges(self, wing_cutout, aileron_body, p_in, p_out):
        """Creates interlocking hinge barrels with radial/axial clearance pockets and full-span pin tunnel."""
        span_vec = App.Vector(p_out.x - p_in.x, p_out.y - p_in.y, p_out.z - p_in.z)
        total_span = span_vec.Length
        dir_vec = App.Vector(span_vec.x / total_span, span_vec.y / total_span, span_vec.z / total_span)

        tab_radius = max(2.5, self.pin_dia + 0.9)
        pin_radius = self.pin_dia / 2.0
        intervals = self.tab_count * 2 + 1
        seg_len = total_span / intervals
        gap = self.hinge_gap

        # Continuous pin bore cylinder that extends from inboard of aileron ALL THE WAY past the wing tip
        # Distance along dir_vec from p_in to the wing tip plane (Y = half_span)
        y_tip = self.wg.half_span
        t_tip = (y_tip - p_in.y) / dir_vec.y
        inboard_margin = 20.0
        outboard_margin = 30.0 # Well past the tip face (Y > half_span) so it punches completely through
        pin_tunnel_length = inboard_margin + t_tip + outboard_margin
        bore_start = p_in - (dir_vec * inboard_margin)

        pin_bore = Part.makeCylinder(
            pin_radius + 0.15, # 0.15mm print clearance
            pin_tunnel_length,
            bore_start,
            dir_vec
        )

        wing_tabs = []
        aileron_tabs = []
        wing_clearance_cutters = []
        aileron_clearance_cutters = []

        for i in range(intervals):
            seg_start = p_in + (dir_vec * (i * seg_len))

            # Clearance pocket cutter: cuts a radial pocket (tab_radius + gap) into opposing body
            pocket_cutter = Part.makeCylinder(tab_radius + gap, seg_len, seg_start, dir_vec)

            # Actual tab barrel: sized with axial gap on neighbor interfaces
            if i == 0:
                barrel = Part.makeCylinder(tab_radius, seg_len - gap, seg_start, dir_vec)
            elif i == intervals - 1:
                barrel = Part.makeCylinder(tab_radius, seg_len - gap, seg_start + (dir_vec * gap), dir_vec)
            else:
                barrel = Part.makeCylinder(tab_radius, seg_len - (2.0 * gap), seg_start + (dir_vec * gap), dir_vec)

            if i % 2 == 0:
                # Wing tab (even): pocket cut from aileron, tab fused to wing
                wing_tabs.append(barrel)
                aileron_clearance_cutters.append(pocket_cutter)
            else:
                # Aileron tab (odd): pocket cut from wing, tab fused to aileron
                aileron_tabs.append(barrel)
                wing_clearance_cutters.append(pocket_cutter)

        # 1. Cut clearance pockets from opposite bodies so parts join smoothly
        wing = wing_cutout
        for wcc in wing_clearance_cutters:
            wing = wing.cut(wcc)

        aileron = aileron_body
        for acc in aileron_clearance_cutters:
            aileron = aileron.cut(acc)

        # 2. Fuse the barrels to their parent bodies
        for wt in wing_tabs:
            wing = wing.fuse(wt)

        for at in aileron_tabs:
            aileron = aileron.fuse(at)

        # 3. Drill continuous pin insertion bore through hinges and completely through the wing tip
        wing = wing.cut(pin_bore)
        aileron = aileron.cut(pin_bore)

        return wing, aileron
