"""Removable 2-piece clamshell motor mount contoured to the wing leading edge."""
import math
import FreeCAD as App
import Part


class MotorMount:
    """Generates wing saddle/ESC cavity cutters and skin-conforming clamshell brackets."""

    def __init__(
        self,
        span_y=87.5,
        protrusion=12.0,
        nose_width=25.0,
        nose_height=20.0,
        hole_spacing_y=21.0,
        hole_spacing_z=12.0,
        pilot_dia=1.25,
        screw_depth=6.0,
        nub_radius=2.25,
        saddle_length=44.0,
        saddle_half_width=14.0,
        recess_depth=1.8,
        front_bulkhead_t=3.0,
        center_bore_dia=14.0,
        center_bore_depth=4.0,
        esc_cavity_width=15.5,
        esc_cavity_height=11.0,
        esc_cavity_depth=44.0,
        bay_wall_t=2.0,
        bay_clearance=0.15,
        peg_offset_from_le=39.0,
        peg_dia=5.5,
    ):
        self.span_y = float(span_y)
        self.protrusion = float(protrusion)
        self.nose_width = float(nose_width)
        self.nose_height = float(nose_height)
        self.hole_spacing_y = float(hole_spacing_y)
        self.hole_spacing_z = float(hole_spacing_z)
        self.pilot_dia = float(pilot_dia)
        self.screw_depth = float(screw_depth)
        self.nub_radius = float(nub_radius)
        self.saddle_length = float(saddle_length)
        self.saddle_half_width = float(saddle_half_width)
        self.recess_depth = float(recess_depth)
        self.front_bulkhead_t = float(front_bulkhead_t)
        self.center_bore_dia = float(center_bore_dia)
        self.center_bore_depth = float(center_bore_depth)
        self.esc_cavity_width = float(esc_cavity_width)
        self.esc_cavity_height = float(esc_cavity_height)
        self.esc_cavity_depth = float(esc_cavity_depth)
        self.bay_wall_t = float(bay_wall_t)
        self.bay_clearance = float(bay_clearance)
        self.peg_offset_from_le = float(peg_offset_from_le)
        self.peg_dia = float(peg_dia)

    def get_mount_frame(self, wing_geom):
        """Returns (x_face, y_center, z_center, le) aligned with the local camber line."""
        le = wing_geom.get_le_position(self.span_y)
        x_face = le.x - self.protrusion
        # Center Z on the airfoil thickness midpoint inside the ESC bay
        # so upper and lower skins maintain balanced wall thickness.
        z_bot_mid, z_top_mid = wing_geom.get_surface_z(le.x + 18.0, self.span_y)
        z_center = 0.5 * (z_bot_mid + z_top_mid)
        return x_face, self.span_y, z_center, le

    def _bay_half_width(self):
        """Returns half-width of the central ESC housing bay cutout in the wing."""
        return self.esc_cavity_width / 2.0 + self.bay_wall_t + self.bay_clearance

    def _esc_end_x(self, x_face):
        """Returns the aft X coordinate of the internal ESC cavity."""
        return x_face + self.esc_cavity_depth

    def _make_rounded_rect_wire(self, x, y_center, z_center, width, height, radius=4.0, n_arc=6):
        """Creates a closed rounded-rectangle wire in the YZ plane at X = x."""
        hy = width / 2.0
        hz = height / 2.0
        r = min(radius, hy - 0.5, hz - 0.5)
        corners = [
            (y_center + hy - r, z_center + hz - r, 0.0, math.pi / 2.0),
            (y_center - hy + r, z_center + hz - r, math.pi / 2.0, math.pi),
            (y_center - hy + r, z_center - hz + r, math.pi, 1.5 * math.pi),
            (y_center + hy - r, z_center - hz + r, 1.5 * math.pi, 2.0 * math.pi),
        ]
        pts = []
        for cy, cz, a0, a1 in corners:
            for i in range(n_arc):
                ang = a0 + (a1 - a0) * (i / (n_arc - 1))
                pts.append(App.Vector(x, cy + r * math.cos(ang), cz + r * math.sin(ang)))
        pts.append(pts[0])
        return Part.Wire(Part.makePolygon(pts))

    def _make_wing_section_wire(self, wing_geom, x, y0, y1, n_span=9):
        """Samples the exact upper and lower airfoil contour across [y0, y1] at X = x."""
        upper_pts = []
        lower_pts = []
        for i in range(n_span):
            t = i / (n_span - 1)
            yi = y0 + t * (y1 - y0)
            zb, zt = wing_geom.get_surface_z(x, yi)
            # Ensure non-degenerate thickness near the leading edge
            if zt - zb < 0.2:
                z_mid = 0.5 * (zb + zt)
                zb = z_mid - 0.1
                zt = z_mid + 0.1
            upper_pts.append(App.Vector(x, yi, zt))
            lower_pts.append(App.Vector(x, yi, zb))
        pts = upper_pts + list(reversed(lower_pts)) + [upper_pts[0]]
        return Part.Wire(Part.makePolygon(pts))

    def build_wing_saddle_cutter(self, wing_geom):
        """Builds the cutter for the 3D skin saddle, central ESC bay, peg bore, and wire trench."""
        x_face, y_c, z_c, le = self.get_mount_frame(wing_geom)
        y0 = y_c - self.saddle_half_width
        y1 = y_c + self.saddle_half_width
        x_saddle_end = le.x + self.saddle_length
        x_esc_end = self._esc_end_x(x_face)

        # 1. 3D spanwise upper & lower skin saddle recesses following sweep/dihedral/taper
        upper_wires = []
        lower_wires = []
        n_pts = 10
        x_start = min(
            wing_geom.get_le_position(y0).x,
            wing_geom.get_le_position(y1).x,
        ) - 1.0
        for i in range(n_pts):
            t = i / (n_pts - 1)
            xi = x_start + t * (x_saddle_end - x_start)
            zb0, zt0 = wing_geom.get_surface_z(xi, y0)
            zb1, zt1 = wing_geom.get_surface_z(xi, y1)
            z_top_ceil = max(zt0, zt1) + 6.0
            z_bot_floor = min(zb0, zb1) - 6.0

            upper_wires.append(
                Part.Wire(Part.makePolygon([
                    App.Vector(xi, y0, zt0 - self.recess_depth),
                    App.Vector(xi, y1, zt1 - self.recess_depth),
                    App.Vector(xi, y1, z_top_ceil),
                    App.Vector(xi, y0, z_top_ceil),
                    App.Vector(xi, y0, zt0 - self.recess_depth),
                ]))
            )
            lower_wires.append(
                Part.Wire(Part.makePolygon([
                    App.Vector(xi, y0, z_bot_floor),
                    App.Vector(xi, y1, z_bot_floor),
                    App.Vector(xi, y1, zb1 + self.recess_depth),
                    App.Vector(xi, y0, zb0 + self.recess_depth),
                    App.Vector(xi, y0, z_bot_floor),
                ]))
            )

        upper_recess = Part.makeLoft(upper_wires, True, True)
        lower_recess = Part.makeLoft(lower_wires, True, True)

        # 2. Central through-wing ESC housing bay cutout
        bay_hw = self._bay_half_width()
        x_bay_end = x_esc_end + 2.5
        bay_slot = Part.makeBox(
            x_bay_end - (x_start - 2.0),
            2.0 * bay_hw,
            60.0,
            App.Vector(x_start - 2.0, y_c - bay_hw, z_c - 30.0),
        )

        # 3. Aft clamping peg bore through the solid rear wing tongue
        x_peg = le.x + self.peg_offset_from_le
        peg_bore = Part.makeCylinder(
            (self.peg_dia + 0.3) / 2.0,
            50.0,
            App.Vector(x_peg, y_c, z_c - 25.0),
            App.Vector(0, 0, 1),
        )

        # 4. Inboard sub-housing wire trench above the lower skin flange
        x_trench_start = x_esc_end - 9.0
        x_trench_end = x_esc_end + 0.5
        z_bot_tr, _ = wing_geom.get_surface_z(0.5 * (x_trench_start + x_trench_end), y0)
        wire_trench = Part.makeBox(
            x_trench_end - x_trench_start,
            bay_hw + 1.5,
            (z_bot_tr + self.recess_depth + 3.0) - (z_bot_tr - 3.0),
            App.Vector(x_trench_start, y0 - 0.5, z_bot_tr - 3.0),
        )

        cutter = (
            upper_recess.fuse(lower_recess)
            .fuse(bay_slot)
            .fuse(peg_bore)
            .fuse(wire_trench)
        )
        return cutter

    def _build_skin_conforming_outer_solid(self, wing_geom, raw_wing_solid, x_face, y_c, z_c, le):
        """Builds the outer clamshell envelope matching the exact wing skin over the saddle."""
        y0 = y_c - self.saddle_half_width
        y1 = y_c + self.saddle_half_width
        x_saddle_end = le.x + self.saddle_length
        x_blend = le.x + 5.0

        # Exact wing skin volume over [x_blend, x_saddle_end] x [y0, y1]
        saddle_mask = Part.makeBox(
            x_saddle_end - x_blend,
            2.0 * self.saddle_half_width,
            80.0,
            App.Vector(x_blend, y0, z_c - 40.0),
        )
        wing_skin_shell = raw_wing_solid.common(saddle_mask)

        # Smooth aerodynamic nose fairing from front motor face to x_blend + 1.0 mm
        w_front = self._make_rounded_rect_wire(
            x_face, y_c, z_c, self.nose_width, self.nose_height, radius=4.5
        )
        zb_le, zt_le = wing_geom.get_surface_z(le.x + 1.5, y_c)
        mid_h = max(self.nose_height * 0.85, (zt_le - zb_le) + 4.0)
        mid_w = 0.5 * (self.nose_width + 2.0 * self.saddle_half_width)
        w_mid = self._make_rounded_rect_wire(
            le.x, y_c, z_c, mid_w, mid_h, radius=3.0
        )
        w_blend = self._make_wing_section_wire(wing_geom, x_blend + 1.0, y0, y1)
        nose_fairing = Part.makeLoft([w_front, w_mid, w_blend], True, False)

        return nose_fairing.fuse(wing_skin_shell)

    def _add_motor_bosses(self, shell, x_face, y_c, z_c):
        """Fuses 4 corner screw-boss nubs and returns their pilot hole cutters."""
        dy = self.hole_spacing_y / 2.0
        dz = self.hole_spacing_z / 2.0
        x_dir = App.Vector(1, 0, 0)
        nub_len = self.protrusion + 2.0
        taper_len = 8.0

        pilot_holes = []
        for sy in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                hy = y_c + sy * dy
                hz = z_c + sz * dz
                nub_cyl = Part.makeCylinder(
                    self.nub_radius, nub_len, App.Vector(x_face, hy, hz), x_dir
                )
                nub_cone = Part.makeCone(
                    self.nub_radius, 0.5, taper_len, App.Vector(x_face + nub_len, hy, hz), x_dir
                )
                shell = shell.fuse(nub_cyl).fuse(nub_cone)
                pilot_holes.append(
                    Part.makeCylinder(
                        self.pilot_dia / 2.0,
                        self.screw_depth + 0.5,
                        App.Vector(x_face - 0.5, hy, hz),
                        x_dir,
                    )
                )
        return shell, pilot_holes

    def build_clamshell_brackets(self, wing_geom, raw_wing_solid, recessed_wing_solid):
        """Builds the removable top and bottom clamshell brackets contoured to the wing.

        Args:
            wing_geom: WingGeometry instance.
            raw_wing_solid: Un-cut 3D wing loft used to derive exact outer skin contours.
            recessed_wing_solid: Wing solid after saddle and ESC bay cutters are applied.

        Returns:
            tuple: (top_bracket, bottom_bracket, esc_wire_exit_xy, info_dict)
        """
        x_face, y_c, z_c, le = self.get_mount_frame(wing_geom)
        y0 = y_c - self.saddle_half_width
        x_esc_start = x_face + self.front_bulkhead_t
        x_esc_end = self._esc_end_x(x_face)

        # 1. Outer envelope matching the displaced wing skin + front nose fairing
        shell = self._build_skin_conforming_outer_solid(
            wing_geom, raw_wing_solid, x_face, y_c, z_c, le
        )
        shell, pilot_holes = self._add_motor_bosses(shell, x_face, y_c, z_c)

        # 2. Mate inner face to the recessed wing and central bay cutout
        shell = shell.cut(recessed_wing_solid)

        # 3. Cut front center bore, internal ESC cavity, pilot holes, and bottom motor wire notch
        x_dir = App.Vector(1, 0, 0)
        internal_cutter = pilot_holes[0]
        for h in pilot_holes[1:]:
            internal_cutter = internal_cutter.fuse(h)

        center_bore = Part.makeCylinder(
            self.center_bore_dia / 2.0,
            self.center_bore_depth + 0.5,
            App.Vector(x_face - 0.5, y_c, z_c),
            x_dir,
        )
        esc_box = Part.makeBox(
            x_esc_end - x_esc_start,
            self.esc_cavity_width,
            self.esc_cavity_height,
            App.Vector(
                x_esc_start,
                y_c - self.esc_cavity_width / 2.0,
                z_c - self.esc_cavity_height / 2.0,
            ),
        )
        # Bottom (-Z) motor phase wire notch behind the motor mounting plate into the ESC bay
        motor_wire_notch = Part.makeBox(
            self.front_bulkhead_t + 4.5,
            8.0,
            (z_c - self.esc_cavity_height / 2.0 + 2.0) - (z_c - 15.0),
            App.Vector(x_face - 0.5, y_c - 4.0, z_c - 15.0),
        )
        internal_cutter = (
            internal_cutter.fuse(center_bore).fuse(esc_box).fuse(motor_wire_notch)
        )
        shell = shell.cut(internal_cutter)

        # 4. Split horizontally at Z = z_c (0.15 mm total print clearance)
        split_gap = 0.075
        span_box = self.saddle_half_width * 2.0 + 12.0
        len_box = self.protrusion + self.saddle_length + 12.0
        top_mask = Part.makeBox(
            len_box,
            span_box,
            40.0,
            App.Vector(x_face - 6.0, y_c - span_box / 2.0, z_c + split_gap),
        )
        bot_mask = Part.makeBox(
            len_box,
            span_box,
            40.0,
            App.Vector(x_face - 6.0, y_c - span_box / 2.0, z_c - 40.0 - split_gap),
        )
        top_bracket = shell.common(top_mask)
        bottom_bracket = shell.common(bot_mask)

        # 5. Rear through-wing clamping peg on top_bracket + countersunk screw hole on bottom_bracket
        x_peg = le.x + self.peg_offset_from_le
        z_bot_peg, z_top_peg = wing_geom.get_surface_z(x_peg, y_c)
        peg_bottom_z = z_bot_peg + 1.5
        peg_top_z = z_top_peg - 0.5
        peg_solid = Part.makeCylinder(
            self.peg_dia / 2.0,
            peg_top_z - peg_bottom_z,
            App.Vector(x_peg, y_c, peg_bottom_z),
            App.Vector(0, 0, 1),
        )
        peg_pilot = Part.makeCylinder(
            self.pilot_dia / 2.0,
            6.5,
            App.Vector(x_peg, y_c, peg_bottom_z - 0.5),
            App.Vector(0, 0, 1),
        )
        top_bracket = top_bracket.fuse(peg_solid).cut(peg_pilot)

        # Remove any wing peg-bore pillar above the lower skin flange on bottom_bracket
        peg_pillar_clear = Part.makeCylinder(
            (self.peg_dia + 0.6) / 2.0,
            30.0,
            App.Vector(x_peg, y_c, z_bot_peg + self.recess_depth + 0.1),
            App.Vector(0, 0, 1),
        )
        screw_clear = Part.makeCylinder(
            0.9,
            self.recess_depth + 2.0,
            App.Vector(x_peg, y_c, z_bot_peg - 1.0),
            App.Vector(0, 0, 1),
        )
        screw_head = Part.makeCone(
            1.75,
            0.9,
            1.0,
            App.Vector(x_peg, y_c, z_bot_peg - 0.1),
            App.Vector(0, 0, 1),
        )
        bottom_bracket = bottom_bracket.cut(
            peg_pillar_clear.fuse(screw_clear).fuse(screw_head)
        )

        # 6. Enclosed sub-housing ESC wire exit on the aft-inboard side (keeps outer bottom skin smooth)
        exit_x = x_esc_end - 4.5
        exit_y = y0
        z_bot_exit, _ = wing_geom.get_surface_z(exit_x, exit_y)
        inner_channel = Part.makeBox(
            9.0,
            (y_c - self.esc_cavity_width / 2.0 + 2.0) - (y0 - 0.5),
            z_c - (z_bot_exit + 1.2),
            App.Vector(exit_x - 4.5, y0 - 0.5, z_bot_exit + 1.2),
        )
        bottom_bracket = bottom_bracket.cut(inner_channel)

        info = {
            "x_face_mm": round(x_face, 2),
            "y_center_mm": round(y_c, 2),
            "z_center_mm": round(z_c, 2),
            "peg_x_mm": round(x_peg, 2),
            "esc_cavity_depth_mm": round(self.esc_cavity_depth, 2),
            "esc_wire_exit_xy_mm": [round(exit_x, 2), round(exit_y, 2)],
        }
        return top_bracket, bottom_bracket, (exit_x, exit_y), info
