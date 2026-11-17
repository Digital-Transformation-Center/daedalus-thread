"""Bottom-surface friction-fit wire slot generator."""
import math

try:
    import FreeCAD as App
    import Part
except ImportError:  # Allow pure-Python path-planning tests without FreeCAD
    App = None
    Part = None


class WireChannelGenerator:
    """Generates lofted bottom-surface flat friction-fit slots for edge-on wire retention."""

    def __init__(self, num_stations=16):
        self.num_stations = max(4, int(num_stations))

    def _make_slot_wire(
        self,
        x,
        y,
        z_bot,
        wire_width,
        wire_thickness,
        tangent_xy=(0.0, -1.0),
        z_floor=None,
        z_ceil=None,
    ):
        """Creates a flat friction-fit rectangular slot wire perpendicular to tangent_xy.

        Wires/ribbons are inserted edge-on: the narrower dimension (wire_thickness)
        is the lateral track width and the larger dimension (wire_width) is the
        slot depth into the wing above z_bot.
        """
        half_w = float(wire_thickness) / 2.0

        tx, ty = float(tangent_xy[0]), float(tangent_xy[1])
        t_len = math.hypot(tx, ty)
        if t_len < 1e-9:
            nx, ny = 1.0, 0.0
        else:
            tx, ty = tx / t_len, ty / t_len
            nx, ny = -ty, tx

        z_below = (z_bot - 2.0) if z_floor is None else float(z_floor)
        z_top = (z_bot + float(wire_width)) if z_ceil is None else float(z_ceil)

        def pt(lat, z):
            return App.Vector(x + lat * nx, y + lat * ny, z)

        pts = [
            pt(-half_w, z_below),
            pt(half_w, z_below),
            pt(half_w, z_top),
            pt(-half_w, z_top),
            pt(-half_w, z_below),
        ]
        return Part.Wire(Part.makePolygon(pts))

    def _make_keyhole_wire(
        self, x, y, z_bot, wire_width, wire_thickness, tangent_xy=(0.0, -1.0)
    ):
        """Backward-compatible alias for _make_slot_wire."""
        return self._make_slot_wire(
            x, y, z_bot, wire_width, wire_thickness, tangent_xy=tangent_xy
        )

    @staticmethod
    def _plan_pcb_waypoints_xy(
        start_xy,
        exit_x,
        y_root_out=-3.0,
        lead_out_y=6.0,
        min_parallel_run=18.0,
        lead_direction="-y",
    ):
        """Plans a 0/45/90-degree PCB-style polyline from start_xy to (exit_x, y_root_out)."""
        x0, y0 = float(start_xy[0]), float(start_xy[1])
        x1 = float(exit_x)
        y_out = float(y_root_out)

        if y0 <= 0.0:
            return [(x0, y0), (x1, y_out)]

        waypoints = [(x0, y0)]
        if lead_direction == "+x":
            lead = float(lead_out_y)
            if x1 > x0:
                lead = min(lead, max(0.0, 0.5 * (x1 - x0)))
            x_lead = x0 + lead
            y_lead = y0
            if lead > 1e-6:
                waypoints.append((x_lead, y_lead))
        else:
            lead = min(float(lead_out_y), max(0.0, 0.2 * y0))
            x_lead = x0
            y_lead = y0 - lead
            if lead > 1e-6:
                waypoints.append((x_lead, y_lead))

        dx = x1 - x_lead
        if abs(dx) < 1e-6:
            waypoints.append((x1, y_out))
            return waypoints

        bus_run = min(float(min_parallel_run), max(0.0, 0.4 * y_lead))
        avail_y = max(0.0, y_lead - bus_run)

        # Avoid < 2 mm chordwise stubs by allowing the 45-deg diagonal whenever
        # at least 15 mm of parallel bus remains before Y = 0.
        if abs(dx) <= avail_y or (y_lead - abs(dx) >= 15.0 and abs(dx) - avail_y < 2.0):
            y_bus = y_lead - abs(dx)
            waypoints.append((x1, y_bus))
        else:
            sign_x = 1.0 if dx > 0.0 else -1.0
            x_corner = x1 - sign_x * avail_y
            if abs(x_corner - x_lead) >= 1.5:
                waypoints.append((x_corner, y_lead))
            if avail_y > 1e-6:
                waypoints.append((x1, bus_run))
            else:
                waypoints.append((x1, y_lead))

        waypoints.append((x1, y_out))
        return waypoints

    @staticmethod
    def _sample_filleted_path(
        waypoints_xy, fillet_radius=8.0, pts_per_arc=6, step_mm=12.0
    ):
        """Samples a 2D polyline with circular-arc fillets, returning (x, y, tx, ty)."""
        cleaned = []
        for pt in waypoints_xy:
            px, py = float(pt[0]), float(pt[1])
            if not cleaned or math.hypot(px - cleaned[-1][0], py - cleaned[-1][1]) > 1e-6:
                cleaned.append((px, py))

        if len(cleaned) < 2:
            raise ValueError("Need at least two distinct waypoints to sample a path.")

        n = len(cleaned)
        if n == 2 or fillet_radius <= 0.0:
            samples = []
            for i in range(n - 1):
                p0, p1 = cleaned[i], cleaned[i + 1]
                seg_len = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
                tx = (p1[0] - p0[0]) / seg_len
                ty = (p1[1] - p0[1]) / seg_len
                k_steps = max(2, int(math.ceil(seg_len / step_mm)))
                start_k = 0 if i == 0 else 1
                for k in range(start_k, k_steps + 1):
                    t = k / k_steps
                    samples.append((
                        p0[0] + t * (p1[0] - p0[0]),
                        p0[1] + t * (p1[1] - p0[1]),
                        tx,
                        ty,
                    ))
            return samples

        # Precompute fillet trims at interior vertices
        fillets = []
        for i in range(1, n - 1):
            p_prev, p_curr, p_next = cleaned[i - 1], cleaned[i], cleaned[i + 1]
            v_in = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
            v_out = (p_next[0] - p_curr[0], p_next[1] - p_curr[1])
            len_in = math.hypot(*v_in)
            len_out = math.hypot(*v_out)
            u_in = (v_in[0] / len_in, v_in[1] / len_in)
            u_out = (v_out[0] / len_out, v_out[1] / len_out)

            dot = max(-1.0, min(1.0, u_in[0] * u_out[0] + u_in[1] * u_out[1]))
            cross = u_in[0] * u_out[1] - u_in[1] * u_out[0]
            if abs(cross) < 1e-6:
                fillets.append(None)
                continue

            alpha = math.acos(dot)
            trim_ideal = fillet_radius * math.tan(alpha / 2.0)
            trim = min(trim_ideal, 0.45 * len_in, 0.45 * len_out)
            r_eff = trim / math.tan(alpha / 2.0)

            t_in = (p_curr[0] - trim * u_in[0], p_curr[1] - trim * u_in[1])
            t_out = (p_curr[0] + trim * u_out[0], p_curr[1] + trim * u_out[1])
            turn_sign = 1.0 if cross > 0.0 else -1.0
            n_in = (-turn_sign * u_in[1], turn_sign * u_in[0])
            center = (t_in[0] + r_eff * n_in[0], t_in[1] + r_eff * n_in[1])
            theta0 = math.atan2(t_in[1] - center[1], t_in[0] - center[0])
            dtheta = turn_sign * alpha
            fillets.append((t_in, t_out, center, r_eff, theta0, dtheta, turn_sign))

        samples = []

        def append_sample(x, y, tx, ty):
            if not samples or math.hypot(x - samples[-1][0], y - samples[-1][1]) > 1e-4:
                samples.append((x, y, tx, ty))

        def append_straight(p0, p1):
            seg_len = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            if seg_len < 1e-4:
                return
            tx = (p1[0] - p0[0]) / seg_len
            ty = (p1[1] - p0[1]) / seg_len
            k_steps = max(1, int(math.ceil(seg_len / step_mm)))
            for k in range(k_steps + 1):
                t = k / k_steps
                append_sample(
                    p0[0] + t * (p1[0] - p0[0]),
                    p0[1] + t * (p1[1] - p0[1]),
                    tx,
                    ty,
                )

        cursor = cleaned[0]
        for idx, fillet in enumerate(fillets):
            if fillet is None:
                p_curr = cleaned[idx + 1]
                append_straight(cursor, p_curr)
                cursor = p_curr
                continue

            t_in, t_out, center, r_eff, theta0, dtheta, turn_sign = fillet
            append_straight(cursor, t_in)
            for k in range(pts_per_arc + 1):
                theta = theta0 + (k / pts_per_arc) * dtheta
                ax = center[0] + r_eff * math.cos(theta)
                ay = center[1] + r_eff * math.sin(theta)
                tx = -turn_sign * math.sin(theta)
                ty = turn_sign * math.cos(theta)
                append_sample(ax, ay, tx, ty)
            cursor = t_out

        append_straight(cursor, cleaned[-1])
        if len(samples) <= 2:
            return samples

        # Enforce minimum spacing between intermediate loft stations to prevent
        # near-coincident cross-sections from causing BOPAlgo SelfIntersect.
        min_step_dist = 1.5
        filtered = [samples[0]]
        for s in samples[1:-1]:
            if math.hypot(s[0] - filtered[-1][0], s[1] - filtered[-1][1]) >= min_step_dist:
                filtered.append(s)
        if math.hypot(samples[-1][0] - filtered[-1][0], samples[-1][1] - filtered[-1][1]) < min_step_dist and len(filtered) > 1:
            filtered[-1] = samples[-1]
        else:
            filtered.append(samples[-1])
        return filtered

    @staticmethod
    def _compute_inboard_path_length(path_pts):
        """Computes 3D path length for the portion of path_pts with y >= 0."""
        path_len = 0.0
        for i in range(len(path_pts) - 1):
            p0, p1 = path_pts[i], path_pts[i + 1]
            if p0.y >= 0.0 and p1.y >= 0.0:
                path_len += (p1 - p0).Length
            elif p0.y > 0.0 and p1.y < 0.0:
                frac = p0.y / (p0.y - p1.y)
                path_len += frac * (p1 - p0).Length
            elif p0.y < 0.0 and p1.y > 0.0:
                frac = p1.y / (p1.y - p0.y)
                path_len += frac * (p1 - p0).Length
        return path_len

    def create_routed_channel(
        self,
        wing_geom,
        waypoints_xy,
        wire_width,
        wire_thickness,
        fillet_radius=8.0,
    ):
        """Lofts a bottom-surface flat friction-fit slot along a filleted 2D path."""
        samples = self._sample_filleted_path(waypoints_xy, fillet_radius=fillet_radius)
        wires = []
        path_pts = []
        for xi, yi, tx, ty in samples:
            y_query = max(0.0, min(wing_geom.half_span, yi))
            z_bot, _ = wing_geom.get_surface_z(xi, y_query)
            wires.append(
                self._make_slot_wire(
                    xi, yi, z_bot, wire_width, wire_thickness, tangent_xy=(tx, ty)
                )
            )
            path_pts.append(App.Vector(xi, yi, z_bot))

        channel_solid = Part.makeLoft(wires, True, True)
        return channel_solid, self._compute_inboard_path_length(path_pts)

    def create_channel(self, wing_geom, start_xy, end_xy, wire_width, wire_thickness):
        """Lofts a straight bottom-surface flat friction-fit slot from start_xy to end_xy."""
        x0, y0 = float(start_xy[0]), float(start_xy[1])
        x1, y1 = float(end_xy[0]), float(end_xy[1])
        tx, ty = x1 - x0, y1 - y0

        wires = []
        path_pts = []
        for i in range(self.num_stations):
            t = i / (self.num_stations - 1)
            xi = x0 + t * (x1 - x0)
            yi = y0 + t * (y1 - y0)
            y_query = max(0.0, min(wing_geom.half_span, yi))
            z_bot, _ = wing_geom.get_surface_z(xi, y_query)
            wires.append(
                self._make_slot_wire(
                    xi, yi, z_bot, wire_width, wire_thickness, tangent_xy=(tx, ty)
                )
            )
            path_pts.append(App.Vector(xi, yi, z_bot))

        channel_solid = Part.makeLoft(wires, True, True)
        return channel_solid, self._compute_inboard_path_length(path_pts)

    def _create_tapered_esc_entry(
        self,
        wing_geom,
        x_esc_start,
        x_saddle_end,
        y_pos,
        wire_width,
        wire_thickness,
        recess_depth=1.8,
        z_c=None,
    ):
        """Creates an individual tapered slot from the ESC bay down behind the clamshell shell.

        For x <= x_saddle_end, z_floor stays at z_bot + recess_depth so the motor mount
        bottom shell is never cut. Behind x_saddle_end it emerges onto the bottom surface.
        """
        x_start = float(x_esc_start)
        x_end = float(x_saddle_end)
        x_taper_end = x_end + 5.0
        x_overlap = x_end + 6.0

        zb_start, _ = wing_geom.get_surface_z(x_start, y_pos)
        z_ceil_esc = (
            max(float(z_c), zb_start + recess_depth + float(wire_width) + 1.0)
            if z_c is not None
            else zb_start + recess_depth + float(wire_width) + 2.5
        )

        # Stations:
        # - For x <= x_end - 0.2: z_floor sits 0.8 mm below recess ceiling (into empty space,
        #   avoiding coplanar thin-wall slivers while never touching bottom_bracket).
        # - z_ceil maintains full wire_width + 0.5 mm clearance above recess_depth up to x_end,
        #   then tapers smoothly down to zb + wire_width by x_end + 5.0.
        stations = [
            (x_start, True, 0.0, 0.0),
            (0.5 * (x_start + x_end), True, 0.5, 0.0),
            (x_end - 0.2, True, 1.0, 0.0),
            (x_end + 0.2, False, 1.0, 0.05),
            (x_taper_end, False, 1.0, 1.0),
            (x_overlap, False, 1.0, 1.0),
        ]
        wires = []
        for xi, above_shell, esc_frac, post_frac in stations:
            zb, _ = wing_geom.get_surface_z(xi, y_pos)
            z_floor = (zb + recess_depth - 0.8) if above_shell else (zb - 2.0)
            z_ceil_at_saddle = zb + recess_depth + float(wire_width) + 0.5
            z_ceil_slot = zb + float(wire_width)
            if post_frac == 0.0:
                z_ceil = z_ceil_esc + esc_frac * (z_ceil_at_saddle - z_ceil_esc)
            else:
                z_ceil = z_ceil_at_saddle + post_frac * (z_ceil_slot - z_ceil_at_saddle)
            wires.append(
                self._make_slot_wire(
                    xi,
                    y_pos,
                    zb,
                    wire_width,
                    wire_thickness,
                    tangent_xy=(1.0, 0.0),
                    z_floor=z_floor,
                    z_ceil=z_ceil,
                )
            )
        return Part.makeLoft(wires, True, True), (x_end - x_start)

    def create_all_channels(
        self,
        wing_geom,
        servo_feed_xy,
        esc_inboard_xy,
        root_exit_x,
        servo_wire_w=2.4,
        servo_wire_t=0.6,
        esc_power_w=3.2,
        esc_power_t=1.4,
        esc_data_w=1.7,
        esc_data_t=0.7,
        channel_spacing=6.0,
        fillet_radius=8.0,
        lead_out_y=6.0,
        min_parallel_run=18.0,
        esc_taper_start_x=None,
        esc_recess_depth=1.8,
        esc_z_c=None,
        esc_peg_offset=5.0,
    ):
        """Generates PCB-routed bottom-surface flat friction-fit slots exiting evenly at the root.

        Exits are ordered fore-to-aft as (esc_power, esc_data, servo) to avoid crossings.
        ESC power enters on the fuselage side (y_c - esc_peg_offset) and ESC data on the
        outboard side (y_c + esc_peg_offset) of the clamshell clamping peg.

        Returns:
            tuple: (combined_cutter, lengths_dict)
        """
        y_root_out = -3.0

        esc_pwr_start = (esc_inboard_xy[0], esc_inboard_xy[1] - esc_peg_offset)
        esc_dat_start = (esc_inboard_xy[0], esc_inboard_xy[1] + esc_peg_offset)

        esc_pwr_waypoints = self._plan_pcb_waypoints_xy(
            esc_pwr_start,
            root_exit_x - channel_spacing,
            y_root_out=y_root_out,
            lead_out_y=lead_out_y,
            min_parallel_run=min_parallel_run,
            lead_direction="+x",
        )
        esc_dat_waypoints = self._plan_pcb_waypoints_xy(
            esc_dat_start,
            root_exit_x,
            y_root_out=y_root_out,
            lead_out_y=lead_out_y,
            min_parallel_run=min_parallel_run,
            lead_direction="+x",
        )
        servo_waypoints = self._plan_pcb_waypoints_xy(
            servo_feed_xy,
            root_exit_x + channel_spacing,
            y_root_out=y_root_out,
            lead_out_y=lead_out_y,
            min_parallel_run=min_parallel_run,
            lead_direction="-y",
        )

        esc_pwr_ch, esc_pwr_len = self.create_routed_channel(
            wing_geom, esc_pwr_waypoints, esc_power_w, esc_power_t, fillet_radius=fillet_radius
        )
        esc_dat_ch, esc_dat_len = self.create_routed_channel(
            wing_geom, esc_dat_waypoints, esc_data_w, esc_data_t, fillet_radius=fillet_radius
        )

        if esc_taper_start_x is not None:
            x_saddle_end = esc_inboard_xy[0] - 0.5
            pwr_taper, pwr_taper_len = self._create_tapered_esc_entry(
                wing_geom,
                esc_taper_start_x,
                x_saddle_end,
                esc_pwr_start[1],
                esc_power_w,
                esc_power_t,
                recess_depth=esc_recess_depth,
                z_c=esc_z_c,
            )
            dat_taper, dat_taper_len = self._create_tapered_esc_entry(
                wing_geom,
                esc_taper_start_x,
                x_saddle_end,
                esc_dat_start[1],
                esc_data_w,
                esc_data_t,
                recess_depth=esc_recess_depth,
                z_c=esc_z_c,
            )
            esc_pwr_ch = esc_pwr_ch.fuse(pwr_taper)
            esc_dat_ch = esc_dat_ch.fuse(dat_taper)
            esc_pwr_len += pwr_taper_len
            esc_dat_len += dat_taper_len

        servo_ch, servo_len = self.create_routed_channel(
            wing_geom, servo_waypoints, servo_wire_w, servo_wire_t, fillet_radius=fillet_radius
        )

        combined = servo_ch.fuse(esc_pwr_ch).fuse(esc_dat_ch)
        lengths = {
            "servo_channel_mm": round(servo_len, 2),
            "esc_power_channel_mm": round(esc_pwr_len, 2),
            "esc_data_channel_mm": round(esc_dat_len, 2),
        }
        return combined, lengths
