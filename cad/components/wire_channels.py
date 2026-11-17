"""Bottom-surface press-fit keyhole wire channel generator."""
import math
import FreeCAD as App
import Part


class WireChannelGenerator:
    """Generates lofted bottom-surface keyhole channels for snap-in wire retention."""

    def __init__(self, num_stations=16):
        self.num_stations = max(4, int(num_stations))

    def _make_keyhole_wire(self, x, y, z_bot, wire_width, wire_thickness):
        """Creates a keyhole cross-section wire in the XZ plane at span station y."""
        mouth_half = max(0.55, (wire_width - 0.3) / 2.0)
        inner_half = (wire_width + 0.35) / 2.0

        z_below = z_bot - 1.5
        z_lip = z_bot + 0.6
        z_chamfer = z_lip + 0.35
        z_ceil = z_chamfer + wire_thickness + 0.8

        pts = [
            App.Vector(x - mouth_half, y, z_below),
            App.Vector(x + mouth_half, y, z_below),
            App.Vector(x + mouth_half, y, z_lip),
            App.Vector(x + inner_half, y, z_chamfer),
            App.Vector(x + inner_half, y, z_ceil),
            App.Vector(x - inner_half, y, z_ceil),
            App.Vector(x - inner_half, y, z_chamfer),
            App.Vector(x - mouth_half, y, z_lip),
            App.Vector(x - mouth_half, y, z_below),
        ]
        return Part.Wire(Part.makePolygon(pts))

    def create_channel(self, wing_geom, start_xy, end_xy, wire_width, wire_thickness):
        """Lofts a bottom-surface press-fit keyhole channel from start_xy to end_xy.

        Args:
            wing_geom: WingGeometry instance.
            start_xy: (x, y) start coordinate on wing (mm).
            end_xy: (x, y) end coordinate at wing root (mm, typically y <= 0).
            wire_width: Wire/ribbon width (mm).
            wire_thickness: Wire/ribbon thickness (mm).

        Returns:
            tuple: (channel_solid, path_length_mm)
        """
        x0, y0 = float(start_xy[0]), float(start_xy[1])
        x1, y1 = float(end_xy[0]), float(end_xy[1])

        wires = []
        path_pts = []
        for i in range(self.num_stations):
            t = i / (self.num_stations - 1)
            xi = x0 + t * (x1 - x0)
            yi = y0 + t * (y1 - y0)
            # Clamp y >= 0 when querying airfoil surface, keep yi for root overhang
            y_query = max(0.0, min(wing_geom.half_span, yi))
            z_bot, _ = wing_geom.get_surface_z(xi, y_query)
            wires.append(self._make_keyhole_wire(xi, yi, z_bot, wire_width, wire_thickness))
            path_pts.append(App.Vector(xi, yi, z_bot))

        channel_solid = Part.makeLoft(wires, True, True)

        path_len = 0.0
        for i in range(len(path_pts) - 1):
            if path_pts[i + 1].y >= 0.0:
                path_len += (path_pts[i + 1] - path_pts[i]).Length
            elif path_pts[i].y > 0.0:
                # Interpolate segment up to Y = 0
                frac = path_pts[i].y / (path_pts[i].y - path_pts[i + 1].y)
                path_len += frac * (path_pts[i + 1] - path_pts[i]).Length

        return channel_solid, path_len

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
    ):
        """Generates all bottom-surface press-fit channels exiting at the wing root.

        Returns:
            tuple: (combined_cutter, lengths_dict)
        """
        y_root_out = -3.0

        # 1. Servo ribbon channel
        servo_ch, servo_len = self.create_channel(
            wing_geom,
            servo_feed_xy,
            (root_exit_x, y_root_out),
            servo_wire_w,
            servo_wire_t,
        )

        # 2. ESC power pair channel (starts at inboard saddle edge, exits at root_exit_x - 4.5 mm)
        esc_pwr_ch, esc_pwr_len = self.create_channel(
            wing_geom,
            (esc_inboard_xy[0] - 2.5, esc_inboard_xy[1] + 0.5),
            (root_exit_x - 4.5, y_root_out),
            esc_power_w,
            esc_power_t,
        )

        # 3. ESC data pair channel (parallel, exits at root_exit_x + 4.5 mm)
        esc_dat_ch, esc_dat_len = self.create_channel(
            wing_geom,
            (esc_inboard_xy[0] + 2.5, esc_inboard_xy[1] + 0.5),
            (root_exit_x + 4.5, y_root_out),
            esc_data_w,
            esc_data_t,
        )

        combined = servo_ch.fuse(esc_pwr_ch).fuse(esc_dat_ch)
        lengths = {
            "servo_channel_mm": round(servo_len, 2),
            "esc_power_channel_mm": round(esc_pwr_len, 2),
            "esc_data_channel_mm": round(esc_dat_len, 2),
        }
        return combined, lengths
