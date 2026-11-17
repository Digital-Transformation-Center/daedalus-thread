"""Top-surface side-mounted friction-fit servo pocket generator."""
import FreeCAD as App
import Part

from components.servo_model import SERVO_SPECS, ServoModel

# Backward-compatible alias for callers inspecting SERVO_PRESETS
SERVO_PRESETS = SERVO_SPECS


class ServoPocket:
    """Generates a press-in friction-fit cutter derived from a 3D servo model."""

    def __init__(self, servo_type="HeeWing_FX5G", tolerance=0.12):
        self.model = ServoModel(servo_type=servo_type)
        self.specs = self.model.specs
        self.tolerance = float(tolerance)

    def _sample_wing_z(self, center_x, center_y, wing_geom):
        """Samples min/max top and bottom wing surface Z across the servo footprint."""
        half_x = self.specs["ear_span_x"] / 2.0
        half_y_in = self.specs["body_height_y"] / 2.0 + self.specs["wire_boot_len_y"]
        half_y_out = (
            self.specs["body_height_y"] / 2.0
            + self.specs["boss_protrusion_y"]
            + self.specs["spline_protrusion_y"]
        )
        z_tops = []
        z_bots = []
        for dx in (-half_x, 0.0, half_x):
            for dy in (-half_y_in, 0.0, half_y_out):
                zb, zt = wing_geom.get_surface_z(center_x + dx, center_y + dy)
                z_bots.append(zb)
                z_tops.append(zt)
        return min(z_bots), min(z_tops), max(z_tops)

    def build_nominal_servo(self, center_x, center_y, wing_geom):
        """Returns the clean nominal 3D servo solid seated inside the pocket."""
        _, z_top_min, _ = self._sample_wing_z(center_x, center_y, wing_geom)
        floor_z = z_top_min - self.specs["body_thickness_z"]
        return self.model.build_nominal_solid(center_x, center_y, floor_z)

    def create_geometry(self, center_x, center_y, wing_geom):
        """Creates press-in servo cutter, feed-through coordinates, and metadata.

        Args:
            center_x: Chordwise center X (mm).
            center_y: Spanwise center Y (mm).
            wing_geom: WingGeometry instance.

        Returns:
            tuple: (cutter_solid, snap_tabs_solid_or_none, feed_xy, info_dict)
        """
        dz = self.specs["body_thickness_z"]
        z_bot_min, z_top_min, z_top_max = self._sample_wing_z(center_x, center_y, wing_geom)

        pocket_floor_z = z_top_min - dz
        pocket_top_z = z_top_max + 2.0

        # 1. Press-in (-Z) swept cutter derived from the 3D servo model
        cutter = self.model.build_press_cutter_solid(
            center_x,
            center_y,
            pocket_floor_z,
            pocket_top_z,
            tolerance=self.tolerance,
        )

        # 2. Aft linkage horn clearance slot aligned to the output spline axis
        spline_x, spline_y = self.model.get_spline_center_xy(center_x, center_y)
        arm_slot_len = 18.0
        arm_slot_w = 4.0
        arm_z_bot = pocket_floor_z - self.tolerance
        arm_slot = Part.makeBox(
            arm_slot_len,
            arm_slot_w,
            pocket_top_z - arm_z_bot,
            App.Vector(
                spline_x - 2.0,
                spline_y - arm_slot_w / 2.0,
                arm_z_bot,
            ),
        )
        cutter = cutter.fuse(arm_slot)

        # 3. Vertical ribbon-wire feed-through hole at the wire exit boot
        feed_x, feed_y = self.model.get_wire_boot_xy(center_x, center_y)
        feed_w = max(3.4, self.specs["wire_width"] + 1.0)
        feed_t = max(2.0, self.specs["wire_thickness"] + 1.4)
        feed_hole = Part.makeBox(
            feed_w,
            feed_t,
            (pocket_floor_z + 1.0) - (z_bot_min - 2.0),
            App.Vector(feed_x - feed_w / 2.0, feed_y - feed_t / 2.0, z_bot_min - 2.0),
        )
        cutter = cutter.fuse(feed_hole)

        info = {
            "servo_type": self.model.servo_type,
            "x_center_mm": round(center_x, 2),
            "y_center_mm": round(center_y, 2),
            "floor_z_mm": round(pocket_floor_z, 2),
            "tolerance_mm": round(self.tolerance, 3),
            "feed_x_mm": round(feed_x, 2),
            "feed_y_mm": round(feed_y, 2),
            "depth_mm": round(dz, 2),
        }
        return cutter, None, (feed_x, feed_y), info
