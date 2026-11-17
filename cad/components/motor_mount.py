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
        nose_width=26.0,
        nose_height=20.0,
        nose_corner_radius=3.0,
        hole_spacing_y=21.0,
        hole_spacing_z=12.0,
        pilot_dia=1.25,
        screw_depth=6.0,
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
        self.nose_corner_radius = float(nose_corner_radius)
        self.hole_spacing_y = float(hole_spacing_y)
        self.hole_spacing_z = float(hole_spacing_z)
        self.pilot_dia = float(pilot_dia)
        self.screw_depth = float(screw_depth)
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

    def _make_rounded_rect_face(self, x, y_center, z_center, width, height, radius=3.0):
        """Creates a planar rounded-rectangle face in the YZ plane at X = x."""
        hy = width / 2.0
        hz = height / 2.0
        r = min(radius, hy - 0.5, hz - 0.5)

        # Build 4 corner arcs and 4 straight edges so the extrusion uses exact planes/cylinders
        p_tr_v = App.Vector(x, y_center + hy, z_center + hz - r)
        p_tr_h = App.Vector(x, y_center + hy - r, z_center + hz)
        p_tl_h = App.Vector(x, y_center - hy + r, z_center + hz)
        p_tl_v = App.Vector(x, y_center - hy, z_center + hz - r)
        p_bl_v = App.Vector(x, y_center - hy, z_center - hz + r)
        p_bl_h = App.Vector(x, y_center - hy + r, z_center - hz)
        p_br_h = App.Vector(x, y_center + hy - r, z_center - hz)
        p_br_v = App.Vector(x, y_center + hy, z_center - hz + r)

        s2 = math.sqrt(0.5)
        edges = [
            Part.Arc(
                p_tr_v,
                App.Vector(x, y_center + hy - r + r * s2, z_center + hz - r + r * s2),
                p_tr_h,
            ).toShape(),
            Part.LineSegment(p_tr_h, p_tl_h).toShape(),
            Part.Arc(
                p_tl_h,
                App.Vector(x, y_center - hy + r - r * s2, z_center + hz - r + r * s2),
                p_tl_v,
            ).toShape(),
            Part.LineSegment(p_tl_v, p_bl_v).toShape(),
            Part.Arc(
                p_bl_v,
                App.Vector(x, y_center - hy + r - r * s2, z_center - hz + r - r * s2),
                p_bl_h,
            ).toShape(),
            Part.LineSegment(p_bl_h, p_br_h).toShape(),
            Part.Arc(
                p_br_h,
                App.Vector(x, y_center + hy - r + r * s2, z_center - hz + r - r * s2),
                p_br_v,
            ).toShape(),
            Part.LineSegment(p_br_v, p_tr_v).toShape(),
        ]
        wire = Part.Wire(edges)
        return Part.Face(wire)

    def _build_esc_rear_wall_ports(
        self,
        wing_geom,
        x_esc_end,
        y_c,
        z_c,
        esc_power_t=1.4,
        esc_power_w=3.2,
        esc_data_t=0.7,
        esc_data_w=1.7,
    ):
        """Builds two individual rear ESC wall ports on opposite sides of the clamping peg.

        The ports sit strictly above z_bot + recess_depth so the bottom shell stays intact.
        """
        x_front = x_esc_end - 1.5
        x_back = x_esc_end + self.bay_wall_t + 1.5
        y_pwr = y_c - 5.0
        y_dat = y_c + 5.0

        ports = []
        for y_p, track_w, slot_h in (
            (y_pwr, esc_power_t, esc_power_w),
            (y_dat, esc_data_t, esc_data_w),
        ):
            zb_p, _ = wing_geom.get_surface_z(x_esc_end, y_p)
            z_floor = zb_p + self.recess_depth
            z_ceil = max(z_c + 0.5, z_floor + slot_h + 1.0)
            ports.append(
                Part.makeBox(
                    x_back - x_front,
                    track_w,
                    z_ceil - z_floor,
                    App.Vector(x_front, y_p - track_w / 2.0, z_floor),
                )
            )
        return ports[0].fuse(ports[1])

    def _build_smooth_recess_solid(
        self, wing_geom, x_start, x_end, y0, y1, is_upper, num_pts=40
    ):
        """Builds a smooth BSplineSurface recess solid between y0 and y1."""
        wires = []
        for y in (y0, y1):
            spline_pts = []
            for i in range(num_pts):
                # Cosine clustering gives dense sampling near the high-curvature leading edge
                t = 0.5 * (1.0 - math.cos(math.pi * i / (num_pts - 1)))
                xi = x_start + t * (x_end - x_start)
                zb, zt = wing_geom.get_surface_z(xi, y)
                z_off = (zt - self.recess_depth) if is_upper else (zb + self.recess_depth)
                spline_pts.append(App.Vector(xi, y, z_off))

            bs = Part.BSplineCurve()
            bs.interpolate(spline_pts)
            z_ext = (
                (max(p.z for p in spline_pts) + 8.0)
                if is_upper
                else (min(p.z for p in spline_pts) - 8.0)
            )
            p_start = spline_pts[0]
            p_end = spline_pts[-1]
            p_ext_end = App.Vector(p_end.x, y, z_ext)
            p_ext_start = App.Vector(p_start.x, y, z_ext)
            wires.append(
                Part.Wire([
                    bs.toShape(),
                    Part.LineSegment(p_end, p_ext_end).toShape(),
                    Part.LineSegment(p_ext_end, p_ext_start).toShape(),
                    Part.LineSegment(p_ext_start, p_start).toShape(),
                ])
            )
        return Part.makeLoft(wires, True)

    def build_wing_saddle_cutter(self, wing_geom):
        """Builds the cutter for the 3D skin saddle, central ESC bay, and peg bore."""
        x_face, y_c, z_c, le = self.get_mount_frame(wing_geom)
        y0 = y_c - self.saddle_half_width
        y1 = y_c + self.saddle_half_width
        x_saddle_end = le.x + self.saddle_length
        x_esc_end = self._esc_end_x(x_face)

        # 1. Smooth 3D spanwise upper & lower skin saddle recesses following sweep/dihedral/taper
        x_start = min(
            wing_geom.get_le_position(y0).x,
            wing_geom.get_le_position(y1).x,
        ) - 1.0
        upper_recess = self._build_smooth_recess_solid(
            wing_geom, x_start, x_saddle_end, y0, y1, is_upper=True
        )
        lower_recess = self._build_smooth_recess_solid(
            wing_geom, x_start, x_saddle_end, y0, y1, is_upper=False
        )

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

        cutter = (
            upper_recess.fuse(lower_recess)
            .fuse(bay_slot)
            .fuse(peg_bore)
        )
        return cutter

    def _build_skin_conforming_outer_solid(self, wing_geom, raw_wing_solid, x_face, y_c, z_c, le):
        """Builds the outer clamshell envelope: straight rounded-rect motor nose + exact wing skin."""
        y0 = y_c - self.saddle_half_width
        y1 = y_c + self.saddle_half_width
        x_saddle_end = le.x + self.saddle_length

        # Exact wing skin volume over [le.x - 1.0, x_saddle_end] x [y0, y1]
        x_skin_start = min(
            wing_geom.get_le_position(y0).x,
            wing_geom.get_le_position(y1).x,
        ) - 1.0
        saddle_mask = Part.makeBox(
            x_saddle_end - x_skin_start,
            2.0 * self.saddle_half_width,
            80.0,
            App.Vector(x_skin_start, y0, z_c - 40.0),
        )
        wing_skin_shell = raw_wing_solid.common(saddle_mask)

        # Straight rounded-rectangle motor mount block extending back until it merges into the wing skin
        nose_face = self._make_rounded_rect_face(
            x_face, y_c, z_c, self.nose_width, self.nose_height, radius=self.nose_corner_radius
        )
        extrude_len = self.protrusion + min(35.0, self.saddle_length - 4.0)
        nose_block = nose_face.extrude(App.Vector(extrude_len, 0, 0))

        return nose_block.fuse(wing_skin_shell)

    def _make_pilot_holes(self, x_face, y_c, z_c):
        """Creates the 4 corner motor-plate pilot hole cutters."""
        dy = self.hole_spacing_y / 2.0
        dz = self.hole_spacing_z / 2.0
        x_dir = App.Vector(1, 0, 0)
        pilot_holes = []
        for sy in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                pilot_holes.append(
                    Part.makeCylinder(
                        self.pilot_dia / 2.0,
                        self.screw_depth + 0.5,
                        App.Vector(x_face - 0.5, y_c + sy * dy, z_c + sz * dz),
                        x_dir,
                    )
                )
        return pilot_holes

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

        # 1. Outer envelope: straight rounded-rect motor nose + exact wing skin over the saddle
        shell = self._build_skin_conforming_outer_solid(
            wing_geom, raw_wing_solid, x_face, y_c, z_c, le
        )
        pilot_holes = self._make_pilot_holes(x_face, y_c, z_c)

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
        z_bots_peg = []
        z_tops_peg = []
        for dx in (-2.5, 0.0, 2.5):
            for dy in (-2.5, 0.0, 2.5):
                zb, zt = wing_geom.get_surface_z(x_peg + dx, y_c + dy)
                z_bots_peg.append(zb)
                z_tops_peg.append(zt)
        z_bot_peg_min = min(z_bots_peg)
        z_bot_peg_max = max(z_bots_peg)
        z_bot_peg, z_top_peg = wing_geom.get_surface_z(x_peg, y_c)

        peg_bottom_z = z_bot_peg_max + self.recess_depth + 0.15
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

        # Remove the entire wing peg-bore pillar above the lower skin flange on bottom_bracket
        peg_pillar_clear = Part.makeCylinder(
            (self.peg_dia + 0.6) / 2.0,
            30.0,
            App.Vector(x_peg, y_c, z_bot_peg_min + self.recess_depth),
            App.Vector(0, 0, 1),
        )
        screw_r = 0.9
        screw_clear = Part.makeCylinder(
            screw_r,
            (z_bot_peg_max + self.recess_depth + 1.5) - (z_bot_peg_min - 2.0),
            App.Vector(x_peg, y_c, z_bot_peg_min - 2.0),
            App.Vector(0, 0, 1),
        )
        # 45-deg countersink extending strictly below z_bot_peg_min so the rim is never clipped
        csk_top_z = z_bot_peg + 0.9
        csk_bot_z = z_bot_peg_min - 1.5
        csk_bot_r = screw_r + (csk_top_z - csk_bot_z)
        screw_head = Part.makeCone(
            csk_bot_r,
            screw_r,
            csk_top_z - csk_bot_z,
            App.Vector(x_peg, y_c, csk_bot_z),
            App.Vector(0, 0, 1),
        )
        bottom_bracket = bottom_bracket.cut(
            peg_pillar_clear.fuse(screw_clear).fuse(screw_head)
        )

        # 6. Individual rear ESC wall ports on opposite sides of the clamping peg (bottom shell uncut)
        x_saddle_end = le.x + self.saddle_length
        rear_ports = self._build_esc_rear_wall_ports(wing_geom, x_esc_end, y_c, z_c)
        bottom_bracket = bottom_bracket.cut(rear_ports)

        exit_x = x_saddle_end + 0.5
        exit_y = y_c

        info = {
            "x_face_mm": round(x_face, 2),
            "y_center_mm": round(y_c, 2),
            "z_center_mm": round(z_c, 2),
            "peg_x_mm": round(x_peg, 2),
            "esc_cavity_depth_mm": round(self.esc_cavity_depth, 2),
            "esc_taper_start_x_mm": round(x_esc_end - 1.5, 2),
            "esc_saddle_end_x_mm": round(x_saddle_end, 2),
            "esc_power_y_mm": round(y_c - 5.0, 2),
            "esc_data_y_mm": round(y_c + 5.0, 2),
            "esc_wire_exit_xy_mm": [round(exit_x, 2), round(exit_y, 2)],
        }
        return top_bracket, bottom_bracket, (exit_x, exit_y), info
